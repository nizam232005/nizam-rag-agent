import logging
import uuid
import os
import tempfile
import shutil

from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
import inngest
import inngest.fast_api
from dotenv import load_dotenv
from google import genai

from data_loader import load_and_chunk_pdf, embed_texts
from vector_db import QdrantStorage
from custom_types import RAGChunkAndSource, RAGUpsertResult, RAGSearchResult, RAQQueryResult

load_dotenv()

# ---------------------------------------------------------------------------
# Gemini client for RAG answer generation
# ---------------------------------------------------------------------------
gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
LLM_MODEL = "gemini-2.0-flash"

# ---------------------------------------------------------------------------
# Inngest client
# ---------------------------------------------------------------------------
inngest_client = inngest.Inngest(
    app_id="rag_app",
    logger=logging.getLogger("uvicorn"),
    is_production=os.getenv("INNGEST_ENV", "dev") != "dev",
)

# ===================================================================
# Inngest Function 1: Ingest PDF
# ===================================================================
@inngest_client.create_function(
    fn_id="rag_ingest_pdf",
    trigger=inngest.TriggerEvent(event="rag/ingest_pdf"),
)
async def rag_ingest_pdf(ctx: inngest.Context):
    """Load a PDF, chunk it, embed chunks, and upsert into Qdrant."""

    def _load() -> dict:
        pdf_path = ctx.event.data.get("file_path")
        source_id = ctx.event.data.get("source_id", pdf_path)
        chunks = load_and_chunk_pdf(pdf_path)
        return RAGChunkAndSource(
            chunks=chunks,
            source_id=source_id,
        ).model_dump()

    def _upsert(chunks_and_src: dict) -> dict:
        if isinstance(chunks_and_src, dict):
            chunks_and_src = RAGChunkAndSource(**chunks_and_src)
        chunks = chunks_and_src.chunks
        source_id = chunks_and_src.source_id

        vectors = embed_texts(chunks)

        ids = [
            str(uuid.uuid5(uuid.NAMESPACE_URL, f"{source_id}_{i}"))
            for i in range(len(chunks))
        ]

        payloads = [
            {"text": chunks[i], "source": source_id}
            for i in range(len(chunks))
        ]

        QdrantStorage().upsert(ids, vectors, payloads)

        return RAGUpsertResult(ingested=len(chunks)).model_dump()

    chunks_and_src = await ctx.step.run("load_and_chunk_pdf", _load)

    ingested = await ctx.step.run(
        "embed_and_upsert",
        lambda: _upsert(chunks_and_src),
    )

    return ingested


# ===================================================================
# Inngest Function 2: RAG Query
# ===================================================================
@inngest_client.create_function(
    fn_id="rag_query",
    trigger=inngest.TriggerEvent(event="rag/query"),
)
async def rag_query(ctx: inngest.Context):
    """Embed a question, retrieve context from Qdrant, and answer with Gemini."""

    question = ctx.event.data.get("question", "")

    # Step 1 — Embed the question
    def _embed_question() -> dict:
        vectors = embed_texts([question])
        return {"vector": vectors[0]}

    embedded = await ctx.step.run("embed_question", _embed_question)

    # Step 2 — Search Qdrant for relevant chunks
    def _search(query_vec: dict) -> dict:
        vector = query_vec["vector"]
        results = QdrantStorage().search(vector, top_k=5)
        return RAGSearchResult(
            contexts=results["contexts"],
            sources=results["sources"],
        ).model_dump()

    search_result = await ctx.step.run(
        "search_qdrant",
        lambda: _search(embedded),
    )

    # Step 3 — Generate answer with Gemini
    def _generate_answer(search_data: dict) -> dict:
        contexts = search_data["contexts"]
        sources = search_data["sources"]

        if not contexts:
            return RAQQueryResult(
                answer="I couldn't find any relevant information in the uploaded documents.",
                sources=[],
                num_contexts=0,
            ).model_dump()

        context_block = "\n\n---\n\n".join(contexts)

        prompt = (
            "You are a helpful assistant. Answer the user's question based ONLY on the "
            "provided context. If the context does not contain enough information, say so clearly.\n\n"
            f"CONTEXT:\n{context_block}\n\n"
            f"QUESTION:\n{question}\n\n"
            "ANSWER:"
        )

        response = gemini_client.models.generate_content(
            model=LLM_MODEL,
            contents=prompt,
        )

        return RAQQueryResult(
            answer=response.text,
            sources=sources,
            num_contexts=len(contexts),
        ).model_dump()

    result = await ctx.step.run(
        "generate_answer",
        lambda: _generate_answer(search_result),
    )

    return result


# ===================================================================
# FastAPI App + Endpoints
# ===================================================================
app = FastAPI(title="RAG Agent API", version="1.0.0")

# Register Inngest functions
inngest.fast_api.serve(
    app,
    inngest_client,
    functions=[rag_ingest_pdf, rag_query],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/ingest")
async def ingest_pdf(file: UploadFile = File(...)):
    """Upload a PDF file and trigger the ingestion pipeline."""
    upload_dir = os.path.join(tempfile.gettempdir(), "rag_uploads")
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, file.filename)

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    await inngest_client.send(
        inngest.Event(
            name="rag/ingest_pdf",
            data={"file_path": file_path, "source_id": file.filename},
        )
    )

    return JSONResponse(
        content={
            "message": f"Ingestion started for '{file.filename}'",
            "source_id": file.filename,
        },
        status_code=202,
    )


@app.post("/query")
async def query(payload: dict):
    """Send a question and get an answer from the RAG pipeline."""
    question = payload.get("question", "")
    if not question:
        return JSONResponse(
            content={"error": "No question provided"}, status_code=400
        )

    await inngest_client.send(
        inngest.Event(
            name="rag/query",
            data={"question": question},
        )
    )

    return JSONResponse(
        content={
            "message": "Query submitted. Results will be processed by Inngest.",
            "question": question,
        },
        status_code=202,
    )

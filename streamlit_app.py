import streamlit as st
import requests
import os
import tempfile
from dotenv import load_dotenv
from data_loader import embed_texts
from vector_db import QdrantStorage
from google import genai

load_dotenv()

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
LLM_MODEL = "gemini-2.0-flash"

# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="RAG Agent",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Custom CSS for a premium dark look
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* Global */
    .stApp {
        font-family: 'Inter', sans-serif;
    }

    /* Header styling */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.5rem;
        font-weight: 700;
        text-align: center;
        padding: 1rem 0;
        margin-bottom: 0.5rem;
    }

    .sub-header {
        text-align: center;
        color: #9ca3af;
        font-size: 1.1rem;
        font-weight: 300;
        margin-bottom: 2rem;
    }

    /* Card styling */
    .card {
        background: rgba(30, 30, 46, 0.6);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 2rem;
        margin-bottom: 1.5rem;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }

    .card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 32px rgba(102, 126, 234, 0.15);
    }

    /* Status badges */
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.8rem;
        font-weight: 500;
    }

    .badge-success {
        background: rgba(34, 197, 94, 0.15);
        color: #22c55e;
        border: 1px solid rgba(34, 197, 94, 0.3);
    }

    .badge-info {
        background: rgba(59, 130, 246, 0.15);
        color: #3b82f6;
        border: 1px solid rgba(59, 130, 246, 0.3);
    }

    /* Answer box */
    .answer-box {
        background: rgba(30, 30, 46, 0.7);
        border-left: 4px solid #667eea;
        border-radius: 0 12px 12px 0;
        padding: 1.5rem;
        margin: 1rem 0;
        line-height: 1.7;
    }

    /* Source chip */
    .source-chip {
        display: inline-block;
        background: rgba(118, 75, 162, 0.2);
        border: 1px solid rgba(118, 75, 162, 0.4);
        border-radius: 8px;
        padding: 0.3rem 0.8rem;
        margin: 0.25rem;
        font-size: 0.85rem;
        color: #c4b5fd;
    }

    /* Divider */
    .custom-divider {
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(102, 126, 234, 0.3), transparent);
        margin: 2rem 0;
        border: none;
    }

    /* Hide streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 8px 20px;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown('<div class="main-header">🧠 RAG Agent</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">Upload documents and ask intelligent questions powered by Gemini & Qdrant</div>',
    unsafe_allow_html=True,
)
st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
tab_ingest, tab_query = st.tabs(["📄 Ingest PDF", "💬 Ask a Question"])

# ===================================================================
# Tab 1: Ingest PDF
# ===================================================================
with tab_ingest:
    st.markdown("### Upload a PDF Document")
    st.markdown("Your document will be chunked, embedded, and stored in the vector database for retrieval.")

    uploaded_file = st.file_uploader(
        "Choose a PDF file",
        type=["pdf"],
        help="Upload a PDF document to add to the knowledge base",
    )

    if uploaded_file is not None:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"""
            <div class="card">
                <strong>📎 {uploaded_file.name}</strong><br>
                <span style="color: #9ca3af;">Size: {uploaded_file.size / 1024:.1f} KB</span>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            ingest_btn = st.button("🚀 Start Ingestion", use_container_width=True, type="primary")

        if ingest_btn:
            with st.spinner("Processing document..."):
                try:
                    # Save uploaded file temporarily
                    upload_dir = os.path.join(tempfile.gettempdir(), "rag_uploads")
                    os.makedirs(upload_dir, exist_ok=True)
                    file_path = os.path.join(upload_dir, uploaded_file.name)

                    with open(file_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())

                    # Process directly (more reliable than going through Inngest for UI feedback)
                    from data_loader import load_and_chunk_pdf, embed_texts
                    from vector_db import QdrantStorage
                    import uuid

                    progress = st.progress(0, text="Loading PDF...")
                    chunks = load_and_chunk_pdf(file_path)
                    progress.progress(30, text=f"Loaded {len(chunks)} chunks. Generating embeddings...")

                    vectors = embed_texts(chunks)
                    progress.progress(70, text="Storing in vector database...")

                    source_id = uploaded_file.name
                    ids = [
                        str(uuid.uuid5(uuid.NAMESPACE_URL, f"{source_id}_{i}"))
                        for i in range(len(chunks))
                    ]
                    payloads = [
                        {"text": chunks[i], "source": source_id}
                        for i in range(len(chunks))
                    ]

                    QdrantStorage().upsert(ids, vectors, payloads)
                    progress.progress(100, text="Done!")

                    st.markdown(f"""
                    <div class="card">
                        <span class="status-badge badge-success">✓ Success</span>
                        <h4 style="margin-top: 0.75rem;">Document Ingested</h4>
                        <p><strong>{len(chunks)}</strong> chunks embedded and stored in Qdrant</p>
                        <p>Source: <span class="source-chip">{uploaded_file.name}</span></p>
                    </div>
                    """, unsafe_allow_html=True)

                except Exception as e:
                    st.error(f"❌ Ingestion failed: {str(e)}")

# ===================================================================
# Tab 2: Ask a Question
# ===================================================================
with tab_query:
    st.markdown("### Ask a Question")
    st.markdown("Your question will be matched against stored documents to generate an AI-powered answer.")

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            if msg["role"] == "assistant":
                st.markdown(f'<div class="answer-box">{msg["content"]}</div>', unsafe_allow_html=True)
                if msg.get("sources"):
                    sources_html = " ".join(
                        [f'<span class="source-chip">📄 {s}</span>' for s in msg["sources"]]
                    )
                    st.markdown(f"**Sources:** {sources_html}", unsafe_allow_html=True)
                if msg.get("num_contexts"):
                    st.markdown(
                        f'<span class="status-badge badge-info">{msg["num_contexts"]} context chunks used</span>',
                        unsafe_allow_html=True,
                    )
            else:
                st.markdown(msg["content"])

    # Chat input
    question = st.chat_input("Ask a question about your documents...")

    if question:
        # Add user message
        st.session_state.messages.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        # Generate answer
        with st.chat_message("assistant"):
            with st.spinner("🔍 Searching documents and generating answer..."):
                try:
                    # Step 1: Embed the question
                    query_vector = embed_texts([question])[0]

                    # Step 2: Search Qdrant
                    results = QdrantStorage().search(query_vector, top_k=5)
                    contexts = results["contexts"]
                    sources = results["sources"]

                    if not contexts:
                        answer = "I couldn't find any relevant information in the uploaded documents. Please make sure you've ingested some PDFs first."
                        sources = []
                        num_contexts = 0
                    else:
                        # Step 3: Generate answer with Gemini
                        context_block = "\n\n---\n\n".join(contexts)
                        prompt = f"""You are a helpful assistant. Answer the user's question based ONLY on the 
provided context. If the context does not contain enough information, say so clearly.

CONTEXT:
{context_block}

QUESTION:
{question}

ANSWER:"""

                        response = gemini_client.models.generate_content(
                            model=LLM_MODEL,
                            contents=prompt,
                        )
                        answer = response.text
                        num_contexts = len(contexts)

                    # Display answer
                    st.markdown(f'<div class="answer-box">{answer}</div>', unsafe_allow_html=True)

                    if sources:
                        sources_html = " ".join(
                            [f'<span class="source-chip">📄 {s}</span>' for s in sources]
                        )
                        st.markdown(f"**Sources:** {sources_html}", unsafe_allow_html=True)

                    if num_contexts:
                        st.markdown(
                            f'<span class="status-badge badge-info">{num_contexts} context chunks used</span>',
                            unsafe_allow_html=True,
                        )

                    # Save to history
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": answer,
                        "sources": sources,
                        "num_contexts": num_contexts,
                    })

                except Exception as e:
                    error_msg = f"❌ Query failed: {str(e)}"
                    st.error(error_msg)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": error_msg,
                    })

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### ⚙️ Configuration")

    st.markdown(f"""
    <div class="card">
        <p><strong>LLM Model:</strong> {LLM_MODEL}</p>
        <p><strong>Embedding:</strong> gemini-embedding-001</p>
        <p><strong>Vector DB:</strong> Qdrant</p>
        <p><strong>Chunk Size:</strong> 1000 tokens</p>
        <p><strong>Chunk Overlap:</strong> 200 tokens</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### 📊 Status")
    try:
        qdrant = QdrantStorage()
        collection_info = qdrant.client.get_collection("docs")
        point_count = collection_info.points_count
        st.markdown(f"""
        <div class="card">
            <span class="status-badge badge-success">● Connected</span>
            <p style="margin-top: 0.5rem;"><strong>{point_count}</strong> vectors stored</p>
        </div>
        """, unsafe_allow_html=True)
    except Exception:
        st.markdown("""
        <div class="card">
            <span class="status-badge" style="background: rgba(239,68,68,0.15); color: #ef4444; border: 1px solid rgba(239,68,68,0.3);">
                ● Disconnected
            </span>
            <p style="margin-top: 0.5rem; color: #9ca3af;">Start Qdrant to enable the vector database.</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)
    st.markdown(
        '<p style="text-align:center; color:#6b7280; font-size:0.8rem;">'
        "Built with Gemini · Qdrant · Inngest · Streamlit"
        "</p>",
        unsafe_allow_html=True,
    )

# 🧠 RAG Agent

A Retrieval-Augmented Generation (RAG) agent that ingests PDF documents, stores embeddings in a vector database, and answers questions using Google Gemini.

## Tech Stack

| Component       | Technology                   |
|-----------------|------------------------------|
| **LLM**         | Google Gemini 2.0 Flash      |
| **Embeddings**  | Gemini Embedding 001 (3072d) |
| **Vector DB**   | Qdrant                       |
| **Orchestration**| Inngest                     |
| **Backend**     | FastAPI                      |
| **Frontend**    | Streamlit                    |
| **Deployment**  | Railway + Qdrant Cloud       |

## Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Streamlit   │────▶│   FastAPI    │────▶│   Inngest    │
│  Frontend    │     │   Backend    │     │  Orchestrator│
└──────────────┘     └──────┬───────┘     └──────────────┘
                           │
                    ┌──────┴───────┐
                    │              │
               ┌────▼────┐  ┌─────▼─────┐
               │ Gemini  │  │  Qdrant   │
               │   API   │  │ Vector DB │
               └─────────┘  └───────────┘
```

## Local Development

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (Python package manager)
- [Docker](https://www.docker.com/) (for Qdrant)
- [Node.js](https://nodejs.org/) (for Inngest CLI)

### Setup

1. **Clone and install dependencies:**
   ```bash
   git clone <repo-url>
   cd rag_agent
   uv sync
   ```

2. **Configure environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your GEMINI_API_KEY
   ```

3. **Start Qdrant (Docker):**
   ```bash
   docker run -p 6333:6333 -p 6334:6334 -v %cd%\qdrant_storage:/qdrant/storage qdrant/qdrant
   ```

4. **Start FastAPI backend:**
   ```bash
   uv run uvicorn main:app --reload
   ```

5. **Start Inngest Dev Server:**
   ```bash
   npx inngest-cli@latest dev --no-discovery -u http://127.0.0.1:8000/api/inngest
   ```

6. **Start Streamlit UI:**
   ```bash
   uv run streamlit run streamlit_app.py
   ```

### Usage

1. Open Streamlit at `http://localhost:8501`
2. Go to the **📄 Ingest PDF** tab and upload a PDF document
3. Switch to the **💬 Ask a Question** tab and ask questions about the document

## API Endpoints

| Method | Endpoint       | Description                          |
|--------|----------------|--------------------------------------|
| GET    | `/health`      | Health check                         |
| POST   | `/ingest`      | Upload a PDF for ingestion           |
| POST   | `/query`       | Submit a question (async via Inngest)|
| POST   | `/api/inngest` | Inngest webhook endpoint             |

## Deployment (Railway + Qdrant Cloud + Inngest Cloud)

### 1. Set up Qdrant Cloud

1. Sign up at [cloud.qdrant.io](https://cloud.qdrant.io)
2. Create a free-tier cluster
3. Copy the **Cluster URL** and **API Key**

### 2. Set up Inngest Cloud

1. Sign up at [inngest.com](https://inngest.com)
2. Create a new app
3. Copy the **Event Key** and **Signing Key**

### 3. Deploy to Railway

1. Push your code to GitHub
2. Go to [railway.app](https://railway.app) and create a new project
3. **Create Service 1 — FastAPI Backend:**
   - Connect your GitHub repo
   - Railway will detect the `Dockerfile` automatically
   - Set environment variables:
     ```
     GEMINI_API_KEY=your_key
     QDRANT_URL=https://your-cluster.cloud.qdrant.io
     QDRANT_API_KEY=your_qdrant_key
     INNGEST_EVENT_KEY=your_event_key
     INNGEST_SIGNING_KEY=your_signing_key
     INNGEST_ENV=production
     ```
   - Note the deployed URL (e.g., `https://rag-api-xxx.up.railway.app`)

4. **Create Service 2 — Streamlit Frontend:**
   - Add a new service from the same repo
   - Set the Dockerfile path to `Dockerfile.streamlit`
   - Set environment variables:
     ```
     GEMINI_API_KEY=your_key
     QDRANT_URL=https://your-cluster.cloud.qdrant.io
     QDRANT_API_KEY=your_qdrant_key
     API_BASE_URL=https://rag-api-xxx.up.railway.app
     ```

5. **Connect Inngest Cloud:**
   - In Inngest Cloud dashboard, set the app URL to:
     `https://rag-api-xxx.up.railway.app/api/inngest`

### Environment Variables Reference

| Variable              | Required | Description                                |
|-----------------------|----------|--------------------------------------------|
| `GEMINI_API_KEY`      | ✅       | Google Gemini API key                      |
| `QDRANT_URL`          | ✅ (prod)| Qdrant Cloud cluster URL                   |
| `QDRANT_API_KEY`      | ✅ (prod)| Qdrant Cloud API key                       |
| `INNGEST_EVENT_KEY`   | ✅ (prod)| Inngest Cloud event key                    |
| `INNGEST_SIGNING_KEY` | ✅ (prod)| Inngest Cloud signing key                  |
| `INNGEST_ENV`         | ❌       | Set to `production` for prod (default: dev)|
| `API_BASE_URL`        | ❌       | FastAPI URL for Streamlit (default: localhost)|

## License

MIT

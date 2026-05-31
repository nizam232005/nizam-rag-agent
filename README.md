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

## Deployment (Render + Streamlit Community Cloud + Qdrant Cloud + Inngest Cloud)

### 1. Set up Qdrant Cloud

1. Sign up at [cloud.qdrant.io](https://cloud.qdrant.io)
2. Create a free-tier cluster
3. Copy the **Cluster URL** and **API Key**

### 2. Set up Inngest Cloud

1. Sign up at [inngest.com](https://inngest.com)
2. Create a new app
3. Copy the **Event Key** (under Manage → Keys) and **Signing Key**

### 3. Deploy FastAPI Backend to Render (Free)

1. Push your code to GitHub
2. Go to [render.com](https://render.com) and sign up (free)
3. Click **"New +"** → **"Web Service"**
4. Connect your GitHub repo (`rag-agent`)
5. Configure:
   - **Name**: `rag-agent-api`
   - **Runtime**: Docker
   - **Dockerfile Path**: `./Dockerfile`
   - **Plan**: Free
6. Add **Environment Variables**:
   ```
   GEMINI_API_KEY=your_key
   QDRANT_URL=https://your-cluster.cloud.qdrant.io
   QDRANT_API_KEY=your_qdrant_key
   INNGEST_EVENT_KEY=your_event_key
   INNGEST_SIGNING_KEY=your_signing_key
   INNGEST_ENV=production
   ```
7. Click **"Create Web Service"**
8. Note the deployed URL (e.g., `https://rag-agent-api.onrender.com`)

### 4. Deploy Streamlit Frontend to Streamlit Community Cloud (Free)

1. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub
2. Click **"New app"**
3. Select your repo, branch (`master`), and main file (`streamlit_app.py`)
4. Go to **"Advanced settings"** → **"Secrets"** and paste:
   ```toml
   GEMINI_API_KEY = "your_key"
   QDRANT_URL = "https://your-cluster.cloud.qdrant.io"
   QDRANT_API_KEY = "your_qdrant_key"
   API_BASE_URL = "https://rag-agent-api.onrender.com"
   ```
5. Click **"Deploy"**

### 5. Connect Inngest Cloud

In the Inngest Cloud dashboard, enter the App URL:
```
https://rag-agent-api.onrender.com/api/inngest
```

### Environment Variables Reference

| Variable              | Required | Description                                |
|-----------------------|----------|-------------------------------------------|
| `GEMINI_API_KEY`      | ✅       | Google Gemini API key                      |
| `QDRANT_URL`          | ✅ (prod)| Qdrant Cloud cluster URL                   |
| `QDRANT_API_KEY`      | ✅ (prod)| Qdrant Cloud API key                       |
| `INNGEST_EVENT_KEY`   | ✅ (prod)| Inngest Cloud event key                    |
| `INNGEST_SIGNING_KEY` | ✅ (prod)| Inngest Cloud signing key                  |
| `INNGEST_ENV`         | ❌       | Set to `production` for prod (default: dev)|
| `API_BASE_URL`        | ❌       | FastAPI URL for Streamlit (default: localhost)|

## License

MIT


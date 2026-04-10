# Multimodal RAG Chat

## 1. Overview

A **Multimodal Retrieval-Augmented Generation (RAG)** system that lets you upload and chat with your documents, images, audio, and video files. You ingest content through a drag-and-drop dashboard, and then ask questions in a ChatGPT-style streaming chat interface. The system finds the most relevant content from your uploads and generates a grounded answer — it will never make up information outside of what you've ingested.

**Supported input types:**
- Plain text (paste directly)
- PDF documents
- Images (PNG, JPEG)
- Audio files (MP3, WAV)
- Video files (MP4, MOV)

---

## 2. Tech Stack

**Backend**
- Python 3.11+
- FastAPI
- Uvicorn
- OpenAI Python SDK (pointed at Euri API)
- Pinecone (vector database)
- PyPDF2 (PDF parsing)
- LangChain Text Splitters (chunking)
- imageio-ffmpeg (video frame extraction)
- Tenacity (retry with exponential back-off)
- python-dotenv

**Frontend**
- Next.js 15 (App Router)
- TypeScript
- Tailwind CSS v4
- React 19

**External APIs**
- Euri API (`https://api.euron.one/api/v1/euri`) — single provider for both embedding and LLM
- Gemini Embedding 2 Preview — converts all content to 768-dimensional vectors
- GPT-4o-mini — generates answers from retrieved context

---

## 3. How It Works (Architecture)

### Ingestion Flow

```
User uploads file (Ingest Page)
        │
        ▼
Processor splits content into chunks
(text → 1024-token chunks, PDF → 6-page batches,
 image → batches of 6, audio → as-is, video → 120s segments + frame description)
        │
        ▼
Euri API (gemini-embedding-2-preview) → 768-dim vector per chunk
        │
        ▼
Pinecone upsert (with metadata: source_type, filename, chunk_index, preview, timestamp)
```

### Query / Chat Flow

```
User types question (Chat Page)
        │
        ▼
Euri API embeds question → 768-dim query vector
        │
        ▼
Pinecone similarity search → top 5 matching chunks
        │
        ▼
Prompt built: system instruction + retrieved context + question
        │
        ▼
Euri API (gpt-4o-mini, stream=True) → token stream via SSE
        │
        ▼
Frontend accumulates tokens → displays answer + source cards
```

### Pinecone Namespaces

Each modality is stored in a separate namespace so queries can be filtered by source type:

| Namespace | Content |
|---|---|
| `ns_text` | Plain text |
| `ns_pdf` | PDF documents |
| `ns_image` | Images |
| `ns_audio` | Audio files |
| `ns_video` | Video files |

---

## 4. Setup Steps

### Prerequisites
- Python 3.11+
- Node.js 18+ and npm
- Euri API key (from [euron.one](https://euron.one))
- Pinecone API key (from [pinecone.io](https://pinecone.io))

### Backend

```bash
git clone <your-repo-url>
cd "Multimodal RAG Chat/backend"

python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux

pip install -r requirements.txt
```

Create `backend/.env`:

```env
EURI_API_KEY=your_euri_api_key_here
EURI_BASE_URL=https://api.euron.one/api/v1/euri
EURI_EMBEDDING_MODEL=gemini-embedding-2-preview
EURI_LLM_MODEL=gpt-4o-mini
PINECONE_API_KEY=your_pinecone_api_key_here
PINECONE_INDEX_NAME=rag-multimodal
```

Start the backend:

```bash
uvicorn app.main:app --reload --port 8000
```

API docs available at: `http://localhost:8000/docs`

### Frontend

```bash
cd "Multimodal RAG Chat/frontend"
npm install
```

Create `frontend/.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Start the frontend:

```bash
npm run dev
```

App available at: `http://localhost:3000`

---

## 5. API Endpoints

### Ingestion

| Method | Endpoint | Description |
|---|---|---|
| POST | `/ingest/text` | Ingest raw text (JSON body) |
| POST | `/ingest/pdf` | Ingest a PDF file |
| POST | `/ingest/image` | Ingest one or more images |
| POST | `/ingest/audio` | Ingest an audio file |
| POST | `/ingest/video` | Ingest a video file |

### Query

| Method | Endpoint | Description |
|---|---|---|
| POST | `/query` | Ask a question — JSON response |
| POST | `/query/stream` | Ask a question — SSE streaming response |

### Utility

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/ingested` | List all ingested files |
| DELETE | `/ingested` | Delete a file's vectors from Pinecone |

---

## 6. Project Structure

```
Multimodal RAG Chat/
├── backend/
│   ├── .env                    # API keys (git-ignored)
│   ├── requirements.txt
│   └── app/
│       ├── main.py             # FastAPI app entry point
│       ├── config.py           # Settings from environment variables
│       ├── models/schemas.py   # Pydantic request/response models
│       ├── services/
│       │   ├── euri_client.py  # Shared OpenAI client → Euri
│       │   ├── embedding.py    # Embed all modalities
│       │   ├── vectorstore.py  # Pinecone operations
│       │   ├── llm.py          # LLM generation + streaming
│       │   └── rag_pipeline.py # Orchestration layer
│       ├── processors/
│       │   ├── text_processor.py
│       │   ├── pdf_processor.py
│       │   ├── image_processor.py
│       │   ├── audio_processor.py
│       │   └── video_processor.py
│       └── routers/
│           ├── ingest.py
│           └── query.py
└── frontend/
    ├── .env.local              # API URL (git-ignored)
    ├── package.json
    └── src/
        ├── app/
        │   ├── chat/page.tsx   # Chat interface
        │   └── ingest/page.tsx # Ingestion dashboard
        ├── components/         # UI components
        ├── lib/
        │   ├── api.ts          # Backend API calls
        │   └── types.ts        # TypeScript interfaces
        └── hooks/
            ├── useChat.ts      # Chat state + streaming
            └── useIngest.ts    # Upload state
```

---

## 7. Environment Variables

| Variable | Where | Description |
|---|---|---|
| `EURI_API_KEY` | `backend/.env` | Euri API key for embedding + LLM |
| `PINECONE_API_KEY` | `backend/.env` | Pinecone API key |
| `PINECONE_INDEX_NAME` | `backend/.env` | Pinecone index (default: `rag-multimodal`) |
| `EURI_LLM_MODEL` | `backend/.env` | LLM model (default: `gpt-4o-mini`) |
| `EURI_EMBEDDING_MODEL` | `backend/.env` | Embedding model (default: `gemini-embedding-2-preview`) |
| `NEXT_PUBLIC_API_URL` | `frontend/.env.local` | Backend URL (default: `http://localhost:8000`) |

---

## 8. Running Tests

```bash
cd backend
pytest
```

Tests cover all processors, embedding functions, Pinecone operations, and the full RAG pipeline. External API calls are mocked.

---

## License

MIT

# Multimodal RAG Chat

A production-grade **Multimodal Retrieval-Augmented Generation (RAG)** system that ingests text, PDFs, images, audio, and video — embeds them using **Gemini Embedding 2 Preview** via the **Euri API** — stores vectors in **Pinecone** — and answers questions through a **ChatGPT-style streaming chat UI** built with Next.js.

---

## Features

- **5 modalities supported** — plain text, PDF, PNG/JPEG images, MP3/WAV audio, MP4/MOV video
- **Streaming responses** — LLM answers stream token-by-token via Server-Sent Events (SSE)
- **Source attribution** — every answer is backed by retrieved source references with file name, type, and relevance score
- **Modality filter** — narrow queries to a specific source type (e.g. "search only PDFs")
- **Ingestion dashboard** — drag-and-drop file uploader with per-file progress and status
- **Dark-themed UI** — ChatGPT-style interface, responsive for desktop and tablet
- **Single API provider** — both embedding and LLM generation go through the Euri API (OpenAI-compatible)

---

## Tech Stack

| Layer | Technology |
|---|---|
| Embedding model | `gemini-embedding-2-preview` via Euri API |
| Vector database | Pinecone (serverless, cosine, 768 dims) |
| LLM | `gpt-4o-mini` via Euri API |
| Backend framework | FastAPI (Python 3.11+) |
| Frontend framework | Next.js 15 (App Router, TypeScript) |
| Styling | Tailwind CSS v4 |
| Text splitting | LangChain `RecursiveCharacterTextSplitter` |
| PDF parsing | PyPDF2 |
| Video processing | ffmpeg via `imageio-ffmpeg` |
| Retry logic | Tenacity (exponential back-off) |

---

## Project Structure

```
Multimodal RAG Chat/
├── backend/
│   ├── .env                        # Secrets (git-ignored)
│   ├── requirements.txt
│   ├── pytest.ini
│   └── app/
│       ├── main.py                 # FastAPI app, CORS, lifespan startup
│       ├── config.py               # Settings loaded from env vars
│       ├── models/
│       │   └── schemas.py          # Pydantic request/response models
│       ├── services/
│       │   ├── euri_client.py      # Shared OpenAI client → Euri base URL
│       │   ├── embedding.py        # Embed all modalities via Euri
│       │   ├── vectorstore.py      # Pinecone upsert, query, delete, list
│       │   ├── llm.py              # LLM generate + SSE stream + video describe
│       │   └── rag_pipeline.py     # Orchestrates embed → retrieve → generate
│       ├── processors/
│       │   ├── text_processor.py   # Chunking with RecursiveCharacterTextSplitter
│       │   ├── pdf_processor.py    # PyPDF2 page extraction, 6-page batches
│       │   ├── image_processor.py  # Validates PNG/JPEG, batches up to 6
│       │   ├── audio_processor.py  # Validates MP3/WAV for native embedding
│       │   └── video_processor.py  # ffmpeg segmentation + frame extraction
│       └── routers/
│           ├── ingest.py           # POST /ingest/{text,pdf,image,audio,video}
│           └── query.py            # POST /query and /query/stream
└── frontend/
    ├── .env.local                  # NEXT_PUBLIC_API_URL (git-ignored)
    ├── package.json
    └── src/
        ├── app/
        │   ├── layout.tsx          # Root layout with Sidebar
        │   ├── chat/page.tsx       # Chat interface
        │   └── ingest/page.tsx     # Ingestion dashboard
        ├── components/
        │   ├── chat/               # ChatWindow, MessageBubble, ChatInput, SourceCard, StreamingText
        │   ├── ingest/             # IngestDashboard, FileUploader, TextInput, IngestionStatus, IngestedFiles
        │   └── layout/             # Sidebar, Header
        ├── lib/
        │   ├── api.ts              # All fetch calls to the backend
        │   └── types.ts            # TypeScript interfaces for all payloads
        └── hooks/
            ├── useChat.ts          # Chat state management + streaming
            └── useIngest.ts        # Upload state management
```

---

## Prerequisites

- **Python 3.11+**
- **Node.js 18+** and npm
- **Euri API key** — get one at [euron.one](https://euron.one)
- **Pinecone API key** — get one at [pinecone.io](https://pinecone.io)
- *(Optional)* **ffmpeg** — for accurate video segmentation and frame extraction (falls back gracefully if not installed)

---

## Setup

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd "Multimodal RAG Chat"
```

### 2. Configure backend environment

Create `backend/.env`:

```env
EURI_API_KEY=your_euri_api_key_here
EURI_BASE_URL=https://api.euron.one/api/v1/euri
EURI_EMBEDDING_MODEL=gemini-embedding-2-preview
EURI_LLM_MODEL=gpt-4o-mini
PINECONE_API_KEY=your_pinecone_api_key_here
PINECONE_INDEX_NAME=rag-multimodal
```

### 3. Install backend dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 4. Configure frontend environment

Create `frontend/.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 5. Install frontend dependencies

```bash
cd frontend
npm install
```

---

## Running

### Start the backend

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`.  
Interactive docs: `http://localhost:8000/docs`

### Start the frontend

```bash
cd frontend
npm run dev
```

The UI will be available at `http://localhost:3000`.

---

## Usage

### Ingest content

1. Navigate to **`/ingest`** in the browser
2. **Drag and drop** any supported file, or **paste raw text** in the text area
3. Supported file types:

   | Type | Extensions |
   |---|---|
   | Text | _(paste directly in textarea)_ |
   | PDF | `.pdf` |
   | Image | `.png`, `.jpg`, `.jpeg` |
   | Audio | `.mp3`, `.wav` |
   | Video | `.mp4`, `.mov` |

4. Each file shows upload progress and a success/error status

### Ask questions

1. Navigate to **`/chat`**
2. Type your question and press **Enter** (Shift+Enter for a newline)
3. Optionally select a **source type filter** to restrict retrieval to a specific modality
4. The assistant streams the answer token-by-token with source cards shown below each response

---

## API Reference

### Ingestion

| Method | Endpoint | Description |
|---|---|---|
| POST | `/ingest/text` | Ingest raw text (JSON body: `{text, source_name?}`) |
| POST | `/ingest/pdf` | Ingest a PDF file (multipart upload) |
| POST | `/ingest/image` | Ingest one or more images (multipart upload) |
| POST | `/ingest/audio` | Ingest an audio file (multipart upload) |
| POST | `/ingest/video` | Ingest a video file (multipart upload) |

### Query

| Method | Endpoint | Description |
|---|---|---|
| POST | `/query` | Ask a question — returns JSON response |
| POST | `/query/stream` | Ask a question — returns SSE streaming response |

**Query request body:**
```json
{
  "question": "What is the main topic?",
  "source_type": "pdf",
  "top_k": 5
}
```

### Utility

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/ingested` | List all ingested files with metadata |
| DELETE | `/ingested?source_type=pdf&source_file=report.pdf` | Delete a file's vectors |

---

## Architecture

### RAG Pipeline

```
User question (Chat UI)
    │
    ▼
POST /query/stream
    │
    ▼
Embed question → Euri API (gemini-embedding-2-preview) → 768-dim vector
    │
    ▼
Pinecone similarity search (cosine, top_k=5)
    │
    ▼
Retrieved chunks + metadata
    │
    ▼
Build prompt: system instruction + context + question
    │
    ▼
Euri LLM (gpt-4o-mini, stream=True) → SSE token stream
    │
    ▼
Frontend accumulates tokens → displays answer + source cards
```

### Ingestion Pipeline (per modality)

| Modality | Processing |
|---|---|
| Text | Chunked with `RecursiveCharacterTextSplitter` (1024 tokens, 256 overlap) |
| PDF | Text extracted per page, batched into groups of ≤6 pages |
| Image | Validated PNG/JPEG, batched into groups of ≤6, base64-encoded as data URIs |
| Audio | Validated MP3/WAV, passed natively as base64 data URI — no transcription |
| Video | Segmented into ≤120s clips via ffmpeg; frames extracted → vision LLM describes content → text chunked and embedded |

### Pinecone Namespaces

Each modality is stored in its own namespace to enable filtered queries:

| Namespace | Modality |
|---|---|
| `ns_text` | Plain text |
| `ns_pdf` | PDF documents |
| `ns_image` | Images |
| `ns_audio` | Audio files |
| `ns_video` | Video files |

---

## Model Constraints

| Modality | Limit | How handled |
|---|---|---|
| Text | 8192 tokens per request | Chunked before embedding |
| Images | 6 per embedding call | Batched in groups of ≤6 |
| PDF | 6 pages per embedding call | Batched in groups of ≤6 pages |
| Audio | Native — no limit specified | Single embedding call |
| Video | 120 seconds per segment | Split into 120s clips |
| Vector output | 768 dimensions | Fixed — Pinecone index uses `dimension=768` |

---

## Testing

```bash
cd backend
pytest
```

Tests use `pytest-asyncio` for async tests. All external API calls (Euri, Pinecone) are mocked in unit tests.

| Test file | Coverage |
|---|---|
| `test_embedding.py` | All embedding functions with mocked API |
| `test_vectorstore.py` | Upsert, query, delete, list with mocked Pinecone |
| `test_processors.py` | All 5 processors with sample inputs |
| `test_rag_pipeline.py` | Full pipeline end-to-end with mocks |

---

## Environment Variable Reference

### Backend (`backend/.env`)

| Variable | Required | Default | Description |
|---|---|---|---|
| `EURI_API_KEY` | Yes | — | API key for all Euri calls |
| `EURI_BASE_URL` | No | `https://api.euron.one/api/v1/euri` | Euri endpoint |
| `EURI_EMBEDDING_MODEL` | No | `gemini-embedding-2-preview` | Embedding model |
| `EURI_LLM_MODEL` | No | `gpt-4o-mini` | LLM model |
| `PINECONE_API_KEY` | Yes | — | Pinecone authentication |
| `PINECONE_INDEX_NAME` | No | `rag-multimodal` | Pinecone index name |

### Frontend (`frontend/.env.local`)

| Variable | Required | Default | Description |
|---|---|---|---|
| `NEXT_PUBLIC_API_URL` | Yes | — | Backend base URL |

---

## Key Design Decisions

- **Single API provider** — both embedding and LLM use the same Euri key and base URL via the OpenAI Python SDK. No Google SDK is used.
- **Audio is embedded natively** — no speech-to-text step. The embedding model accepts audio data URIs directly.
- **Video uses vision LLM** — frames are extracted and described by the LLM, then the text description is chunked and embedded. This enables semantic search over video content.
- **No hallucination** — the system prompt strictly instructs the LLM to answer only from retrieved context, and to explicitly say so when context is insufficient.
- **Streaming is mandatory** — the chat interface uses SSE for token-by-token streaming. The `useChat` hook manages partial state updates with React's `useState`.

---

## License

MIT

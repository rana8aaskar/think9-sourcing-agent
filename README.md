# Think9 Cross-Portfolio Sourcing Agent

An agentic framework that turns **messy, unstructured vendor data** (quote PDFs,
WhatsApp chats, emails, spreadsheets) into **consolidated buying power** across a
portfolio of 30+ consumer brands — and flags supply risk along the way.

Built as the first module of a shared *intelligence layer*: the catalog, the
agents and the control plane are portfolio-level, so onboarding the next brand is
a config change, not a project.

## Architecture & Structure

This project is split into two deployable services:

1. **`backend/`**: A Python FastAPI service that wraps the core agent logic.
2. **`frontend/`**: A Next.js (App Router) dashboard UI.

## Running Locally

### Backend (Python API & CLI)

The backend runs either as a CLI script or a FastAPI server. The default offline extraction mode uses deterministic parsing and requires no API keys. The live extraction mode uses Claude (Anthropic).

```bash
cd backend
pip install -r requirements.txt

# Run the CLI directly
python run.py

# Or start the FastAPI server
uvicorn api:app --port 8000 --reload
```

Once running, the API is available at `http://localhost:8000`.
- `GET /api/report` - Returns the full JSON report.
- `POST /api/analyze` - Parses a pasted vendor quote dynamically.

### Frontend (Next.js Dashboard)

The frontend is a single-page dashboard built with Next.js and Tailwind CSS.

```bash
cd frontend
npm install

# Start the dev server
npm run dev
```

Open `http://localhost:3000` to view the dashboard. Ensure the backend is running at `http://localhost:8000` (the default API URL).

## Deployment

### Deploying the Backend (Railway)

1. Connect your GitHub repository to [Railway](https://railway.app/).
2. Set the **Root Directory** of the service to `/backend`.
3. Railway will auto-detect Python, install `requirements.txt`, and use the `Procfile` to run:
   `uvicorn api:app --host 0.0.0.0 --port $PORT`
4. *(Optional)* To enable live Claude extraction, set the `ANTHROPIC_API_KEY` environment variable in Railway.

### Deploying the Frontend (Vercel)

1. Connect your repository to [Vercel](https://vercel.com/).
2. Set the **Framework Preset** to Next.js and the **Root Directory** to `frontend`.
3. Add an Environment Variable:
   - `NEXT_PUBLIC_API_URL` = `<your-railway-backend-url>`
4. Deploy.

## Design notes

- **Human-in-the-loop by construction.** The agent proposes; a named buyer approves.
  Sign-off gates sit before any consolidation decision, supplier switch, or PO.
- **Nothing hardcoded.** Savings and risk flags are computed from whatever the
  extractor emits, so the numbers move when the inputs move.
- **Scales by design.** A new brand points its demand + vendors at the same shared
  catalog and control plane; more brands deepen demand pools and unlock better
  MOQ breaks for everyone already on the platform.

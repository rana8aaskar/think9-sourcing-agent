import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

if "OPENAI_API_KEY" in os.environ:
    os.environ["OPENAI_API_KEY"] = os.environ["OPENAI_API_KEY"].strip()
if "ANTHROPIC_API_KEY" in os.environ:
    os.environ["ANTHROPIC_API_KEY"] = os.environ["ANTHROPIC_API_KEY"].strip()

from service import build_report, analyze_document

app = FastAPI(title="Think9 Sourcing API")

origins_str = os.environ.get("FRONTEND_ORIGIN", "*")
origins = [o.strip() for o in origins_str.split(",")] if origins_str != "*" else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
def health():
    return {"status": "ok"}

@app.get("/api/report")
def get_report(live: bool = True):
    # Graceful fallback if live=true but no API keys are provided
    if live and not os.environ.get("ANTHROPIC_API_KEY") and not os.environ.get("OPENAI_API_KEY"):
        live = False
        
    try:
        return build_report(live=live)
    except Exception as e:
        import traceback
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=500, content={"error": str(e), "traceback": traceback.format_exc()})

class AnalyzeRequest(BaseModel):
    text: str
    source_type: str
    vendor: str

@app.post("/api/analyze")
def post_analyze(req: AnalyzeRequest):
    live = bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY"))
    return analyze_document(text=req.text, source_type=req.source_type, vendor=req.vendor, live=live)

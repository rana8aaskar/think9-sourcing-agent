"""
Think9 Sourcing Agent — FastAPI backend.

Endpoints
---------
GET  /api/health          liveness probe
POST /api/run             run the full pipeline; returns JSON report
GET  /api/report/xlsx     download the Excel action file
GET  /api/report/html     download the HTML brief

Deploy on Railway — the Procfile at the repo root calls:
    uvicorn backend.main:app --host 0.0.0.0 --port $PORT
"""
from __future__ import annotations

import dataclasses
import os
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

# ── Make sourcing_agent importable when this module is loaded from backend/ ──
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from sourcing_agent.llm import AnthropicExtractor, LocalExtractor   # noqa: E402
from sourcing_agent.ingest import ingest_all                         # noqa: E402
from sourcing_agent.normalize import Catalog, normalize              # noqa: E402
from sourcing_agent.bundle import load_demand, find_bundles          # noqa: E402
from sourcing_agent.risk import assess                               # noqa: E402
from sourcing_agent import report                                    # noqa: E402

# ── Paths ────────────────────────────────────────────────────────────────────
DATA = _ROOT / "data"
OUT  = _ROOT / "outputs"

# ── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Think9 Sourcing Agent API",
    description="Ingest vendor quotes → normalize → bundle → risk → report",
    version="1.0.0",
)

# Allow all origins so the Vercel frontend can call Railway
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Pipeline helper ───────────────────────────────────────────────────────────
def _run_pipeline(live: bool = False):
    """Run the full agent pipeline and return raw results."""
    OUT.mkdir(exist_ok=True)

    extractor = AnthropicExtractor() if live else LocalExtractor()

    raw          = ingest_all(DATA, extractor)
    catalog      = Catalog(DATA / "canonical_catalog.csv")
    quotes, unmatched = normalize(raw, catalog)
    demand       = load_demand(DATA / "brand_demand.csv")
    bundles      = find_bundles(quotes, demand)
    risks        = assess(quotes)

    # Write artefacts so download endpoints work immediately after a run
    report.write_json(OUT / "sourcing_report.json",      quotes, bundles, risks)
    report.write_html(OUT / "sourcing_report.html",      quotes, bundles, risks)
    report.write_xlsx(OUT / "sourcing_action_file.xlsx", quotes, bundles, risks)

    return raw, quotes, unmatched, bundles, risks


# ── Routes ───────────────────────────────────────────────────────────────────
@app.get("/api/health", tags=["meta"])
def health():
    """Liveness probe for Railway / load-balancers."""
    return {"status": "ok", "service": "think9-sourcing-agent"}


@app.post("/api/run", tags=["agent"])
def run_agent(live: bool = Query(False, description="Use AnthropicExtractor (needs ANTHROPIC_API_KEY)")):
    """
    Run the full sourcing-agent pipeline.

    - **live=false** (default) — deterministic offline extractor, no API key needed.
    - **live=true** — production Claude extractor; requires `ANTHROPIC_API_KEY` env var.

    Returns the full report as JSON.
    """
    try:
        raw, quotes, unmatched, bundles, risks = _run_pipeline(live)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    annual_savings = sum(b.annual_saving for b in bundles)
    high_risks     = sum(1 for r in risks if r.severity == "HIGH")

    return {
        "summary": {
            "raw_items":          len(raw),
            "normalized_quotes":  len(quotes),
            "unmatched":          len(unmatched),
            "bundle_count":       len(bundles),
            "risk_count":         len(risks),
            "high_risk_count":    high_risks,
            "annual_savings_inr": annual_savings,
            "extractor":          "claude-live" if live else "offline-deterministic",
        },
        "bundles": [dataclasses.asdict(b) for b in bundles],
        "risks":   [dataclasses.asdict(r) for r in risks],
        "quotes":  [q.to_dict()           for q in quotes],
    }


@app.get("/api/report/xlsx", tags=["downloads"])
def download_xlsx():
    """Download the Excel action file (auto-runs pipeline if not yet generated)."""
    path = OUT / "sourcing_action_file.xlsx"
    if not path.exists():
        try:
            _run_pipeline()
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="think9_sourcing_action_file.xlsx",
    )


@app.get("/api/report/html", tags=["downloads"])
def download_html():
    """Download the HTML buyer brief (auto-runs pipeline if not yet generated)."""
    path = OUT / "sourcing_report.html"
    if not path.exists():
        try:
            _run_pipeline()
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
    return FileResponse(path, media_type="text/html", filename="think9_sourcing_report.html")

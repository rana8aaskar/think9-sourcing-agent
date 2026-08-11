"""
Reusable service layer that wraps the Think9 agent pipeline.
"""
from __future__ import annotations

import dataclasses
from pathlib import Path

import os
from sourcing_agent.llm import AnthropicExtractor, OpenAIExtractor, LocalExtractor
from sourcing_agent.ingest import ingest_all
from sourcing_agent.normalize import Catalog, normalize
from sourcing_agent.bundle import load_demand, find_bundles
from sourcing_agent.risk import assess
from sourcing_agent.schema import RawLineItem

BACKEND_DIR = Path(__file__).resolve().parent
DATA_DIR = BACKEND_DIR / "data"

def get_extractor(live: bool):
    if not live:
        return LocalExtractor(), "offline-deterministic"
    
    # Check for Anthropic first
    if os.environ.get("ANTHROPIC_API_KEY"):
        return AnthropicExtractor(), "claude-live"
        
    # Fallback to OpenAI
    if os.environ.get("OPENAI_API_KEY"):
        return OpenAIExtractor(), "openai-live"
        
    return LocalExtractor(), "offline-deterministic"

def build_report(live: bool = False) -> dict:
    """
    Run the full sourcing pipeline and return the report dictionary.
    """
    extractor, mode = get_extractor(live)
    
    raw = ingest_all(DATA_DIR, extractor)
    catalog = Catalog(DATA_DIR / "canonical_catalog.csv")
    quotes, unmatched = normalize(raw, catalog)
    demand = load_demand(DATA_DIR / "brand_demand.csv")
    bundles = find_bundles(quotes, demand)
    risks = assess(quotes)
    
    total_annual_savings = sum(b.annual_saving for b in bundles)
    high_risks = sum(1 for r in risks if r.severity == "HIGH")
    
    return {
        "meta": {
            "extraction_mode": mode,
            "total_annual_savings": total_annual_savings,
            "raw_items": len(raw),
            "normalized_quotes": len(quotes),
            "unmatched": len(unmatched),
            "bundle_count": len(bundles),
            "risk_count": len(risks),
            "high_risk_count": high_risks,
        },
        "bundles": [dataclasses.asdict(b) for b in bundles],
        "risks": [dataclasses.asdict(r) for r in risks],
        "quotes": [q.to_dict() for q in quotes]
    }

def analyze_document(text: str, source_type: str, vendor: str, live: bool = False) -> dict:
    """
    Run just the extractor + normalize on a single pasted document.
    """
    extractor, _ = get_extractor(live)
    catalog = Catalog(DATA_DIR / "canonical_catalog.csv")
    
    # Extract
    raw_items = extractor.extract(
        text=text, vendor=vendor, source_type=source_type, source_file="Pasted"
    )
    
    # Normalize
    quotes, unmatched = normalize(raw_items, catalog)
    
    # We return the original raw item info mixed with whether it matched or not
    results = []
    
    # Map matched quotes
    matched_by_raw = {q.raw_description: q for q in quotes}
    
    for raw in raw_items:
        match = matched_by_raw.get(raw.raw_description)
        if match:
            results.append({
                "raw_description": raw.raw_description,
                "unit_price": raw.unit_price,
                "uom": raw.uom,
                "normalized": True,
                "canonical_name": match.canonical_name,
                "category": match.category,
                "match_confidence": match.match_confidence
            })
        else:
            results.append({
                "raw_description": raw.raw_description,
                "unit_price": raw.unit_price,
                "uom": raw.uom,
                "normalized": False,
                "canonical_name": None,
                "category": None,
                "match_confidence": 0.0
            })
            
    return {"items": results}

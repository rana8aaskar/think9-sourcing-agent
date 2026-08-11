"""Typed schema shared across the agent pipeline."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from datetime import date
from typing import Optional


@dataclass
class RawLineItem:
    """A single priced line as pulled out of one messy vendor document,
    BEFORE it is mapped to a canonical item."""
    vendor: str
    raw_description: str
    unit_price: float
    currency: str = "INR"
    moq: Optional[int] = None
    lead_time_days: Optional[int] = None
    uom: str = "piece"
    quote_valid_until: Optional[str] = None  # ISO date string
    source_type: str = "unknown"             # pdf | whatsapp | email | csv
    source_file: str = ""


@dataclass
class NormalizedQuote:
    """A raw line resolved to a canonical catalog item."""
    canonical_id: str
    canonical_name: str
    category: str
    vendor: str
    unit_price: float
    uom: str
    moq: Optional[int]
    lead_time_days: Optional[int]
    quote_valid_until: Optional[str]
    match_confidence: float
    raw_description: str
    source_file: str

    def to_dict(self):
        return asdict(self)


@dataclass
class BundleOpportunity:
    canonical_id: str
    canonical_name: str
    category: str
    brands: list[str]
    combined_monthly_qty: float
    current_blended_price: float
    best_vendor: str
    best_price: float
    unit_saving: float
    monthly_saving: float
    annual_saving: float
    rationale: str


@dataclass
class RiskFlag:
    severity: str            # HIGH | MEDIUM | LOW
    canonical_id: str
    canonical_name: str
    risk_type: str
    detail: str
    recommended_action: str

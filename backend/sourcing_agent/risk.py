"""Supply-risk engine. Scans the normalized quote set for exposure that a
human buyer would otherwise catch late (or not at all)."""
from __future__ import annotations
from collections import defaultdict
from datetime import date

from .schema import NormalizedQuote, RiskFlag

_TODAY = date(2026, 8, 11)
_LEAD_WARN = 30          # days
_VARIANCE_WARN = 0.15    # 15% spread across vendors
_EXPIRY_WARN = 10        # days


def _days_to(iso: str | None):
    if not iso:
        return None
    try:
        y, m, d = map(int, iso.split("-"))
        return (date(y, m, d) - _TODAY).days
    except Exception:
        return None


def assess(quotes: list[NormalizedQuote]) -> list[RiskFlag]:
    by_item = defaultdict(list)
    for q in quotes:
        by_item[q.canonical_id].append(q)

    flags: list[RiskFlag] = []
    for cid, qs in by_item.items():
        name = qs[0].canonical_name
        vendors = {q.vendor for q in qs}

        # 1. single-source exposure
        if len(vendors) == 1:
            flags.append(RiskFlag(
                severity="HIGH" if qs[0].category == "Ingredient" else "MEDIUM",
                canonical_id=cid, canonical_name=name, risk_type="Single source",
                detail=f"Only one approved vendor ({next(iter(vendors))}).",
                recommended_action="Qualify a second supplier; hold safety stock."))

        # 2. long lead time
        leads = [q.lead_time_days for q in qs if q.lead_time_days]
        if leads and min(leads) > _LEAD_WARN:
            flags.append(RiskFlag(
                severity="MEDIUM", canonical_id=cid, canonical_name=name,
                risk_type="Long lead time",
                detail=f"Best available lead time is {min(leads)} days.",
                recommended_action="Increase reorder buffer; forecast earlier."))

        # 3. expiring quote (esp. if it's the cheapest)
        for q in qs:
            dleft = _days_to(q.quote_valid_until)
            if dleft is not None and 0 <= dleft <= _EXPIRY_WARN:
                cheapest = min(qs, key=lambda x: x.unit_price)
                tag = " (currently the cheapest quote)" if q is cheapest else ""
                flags.append(RiskFlag(
                    severity="HIGH" if q is cheapest else "LOW",
                    canonical_id=cid, canonical_name=name,
                    risk_type="Quote expiring",
                    detail=f"{q.vendor}'s quote expires in {dleft} day(s){tag}.",
                    recommended_action="Confirm PO or re-quote before expiry."))

        # 4. price variance across vendors
        prices = [q.unit_price for q in qs]
        if len(prices) > 1:
            spread = (max(prices) - min(prices)) / min(prices)
            if spread >= _VARIANCE_WARN:
                flags.append(RiskFlag(
                    severity="LOW", canonical_id=cid, canonical_name=name,
                    risk_type="Price variance",
                    detail=f"{spread*100:.0f}% spread between vendors "
                           f"(Rs {min(prices):.2f}-{max(prices):.2f}).",
                    recommended_action="Use spread as leverage to renegotiate."))

    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    flags.sort(key=lambda f: order[f.severity])
    return flags

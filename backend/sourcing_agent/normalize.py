"""Resolve messy vendor descriptions to canonical catalog IDs.

Strategy: normalise the string, try an exact alias hit, then fall back to a
fuzzy ratio against every alias. This is the step that lets the system see that
'30ml amber droppr bottle', '30ml Ambr Glass Bottle with Dropper' and
'Amber Dropper Bottle 30ml' are all the SAME item bought by different brands —
which is what makes cross-brand bundling possible.
"""
from __future__ import annotations
import csv
import re
from difflib import SequenceMatcher
from pathlib import Path

from .schema import RawLineItem, NormalizedQuote

_FUZZY_THRESHOLD = 0.62


def _norm(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


class Catalog:
    def __init__(self, path: Path):
        self.rows = []
        self._alias_index = {}
        for r in csv.DictReader(path.open(encoding="utf-8")):
            aliases = [a.strip() for a in r["aliases"].split("|")]
            r["_aliases"] = aliases
            self.rows.append(r)
            for a in aliases + [r["canonical_name"]]:
                self._alias_index[_norm(a)] = r

    def match(self, description: str):
        key = _norm(description)
        if key in self._alias_index:
            return self._alias_index[key], 1.0
        best, best_score = None, 0.0
        for r in self.rows:
            for a in r["_aliases"] + [r["canonical_name"]]:
                score = SequenceMatcher(None, key, _norm(a)).ratio()
                if score > best_score:
                    best, best_score = r, score
        if best and best_score >= _FUZZY_THRESHOLD:
            return best, round(best_score, 3)
        return None, best_score


def normalize(items: list[RawLineItem], catalog: Catalog):
    out, unmatched = [], []
    for it in items:
        row, conf = catalog.match(it.raw_description)
        if row is None:
            unmatched.append((it, conf))
            continue
        out.append(NormalizedQuote(
            canonical_id=row["canonical_id"],
            canonical_name=row["canonical_name"],
            category=row["category"],
            vendor=it.vendor,
            unit_price=it.unit_price,
            uom=it.uom,
            moq=it.moq,
            lead_time_days=it.lead_time_days,
            quote_valid_until=it.quote_valid_until,
            match_confidence=conf,
            raw_description=it.raw_description,
            source_file=it.source_file,
        ))
    return out, unmatched

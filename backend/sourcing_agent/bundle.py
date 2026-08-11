"""Cross-brand bundling optimizer.

For every canonical item:
  1. sum demand across all brands that buy it,
  2. find the cheapest vendor quote whose MOQ the *combined* volume can clear,
  3. compare against what the brands pay today (their blended current price),
  4. quantify the saving if procurement is consolidated to that vendor.

The insight the whole pitch rests on: a single brand ordering 6,000 units can't
clear a 10,000-unit MOQ price break — but two brands buying the same bottle can.
"""
from __future__ import annotations
import csv
from collections import defaultdict
from pathlib import Path

from .schema import NormalizedQuote, BundleOpportunity


def load_demand(path: Path):
    demand = defaultdict(list)   # canonical_id -> [(brand, qty, current_price)]
    for r in csv.DictReader(path.open(encoding="utf-8")):
        demand[r["canonical_id"]].append(
            (r["brand"], float(r["monthly_qty"]), float(r["current_unit_price"])))
    return demand


def find_bundles(quotes: list[NormalizedQuote], demand) -> list[BundleOpportunity]:
    by_item = defaultdict(list)
    for q in quotes:
        by_item[q.canonical_id].append(q)

    opportunities = []
    for cid, brand_rows in demand.items():
        vendor_quotes = by_item.get(cid, [])
        if not vendor_quotes:
            continue
        brands = [b for b, _, _ in brand_rows]
        combined_qty = sum(q for _, q, _ in brand_rows)
        spend_now = sum(q * p for _, q, p in brand_rows)
        blended_now = spend_now / combined_qty

        # vendors we can actually use at the COMBINED volume
        eligible = [q for q in vendor_quotes
                    if (q.moq is None or q.moq <= combined_qty)]
        if not eligible:
            continue
        best = min(eligible, key=lambda q: q.unit_price)
        if best.unit_price >= blended_now:
            continue  # no saving

        unit_saving = round(blended_now - best.unit_price, 3)
        monthly = round(unit_saving * combined_qty, 2)
        name = vendor_quotes[0].canonical_name
        category = vendor_quotes[0].category
        multi = len(brands) > 1
        rationale = (
            f"{len(brands)} brands buy this. Combined {combined_qty:,.0f}/mo "
            f"clears {best.vendor}'s MOQ of "
            f"{best.moq if best.moq else 0:,} at Rs {best.unit_price:.2f} "
            f"vs current blended Rs {blended_now:.2f}."
        ) if multi else (
            f"Single-brand volume {combined_qty:,.0f}/mo qualifies for "
            f"{best.vendor} at Rs {best.unit_price:.2f} vs Rs {blended_now:.2f}."
        )

        opportunities.append(BundleOpportunity(
            canonical_id=cid,
            canonical_name=name,
            category=category,
            brands=brands,
            combined_monthly_qty=combined_qty,
            current_blended_price=round(blended_now, 3),
            best_vendor=best.vendor,
            best_price=best.unit_price,
            unit_saving=unit_saving,
            monthly_saving=monthly,
            annual_saving=round(monthly * 12, 2),
            rationale=rationale,
        ))
    opportunities.sort(key=lambda o: o.annual_saving, reverse=True)
    return opportunities

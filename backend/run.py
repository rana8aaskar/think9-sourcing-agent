#!/usr/bin/env python3
"""
Think9 Cross-Portfolio Sourcing Agent — end-to-end demo.

Run:  python run.py
"""
import argparse
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from service import build_report

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

INR = "\u20b9"
BAR = "=" * 68

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true",
                    help="use AnthropicExtractor (needs SDK + API key)")
    args = ap.parse_args()
    
    # Build report dict
    report = build_report(args.live)
    meta = report["meta"]
    bundles = report["bundles"]
    risks = report["risks"]

    # ---- console summary ----
    print(BAR)
    print(f" THINK9 SOURCING AGENT   |   extraction: {meta['extraction_mode']}")
    print(BAR)
    print(f" Ingested   : {meta['raw_items']} raw line items from 5 vendor documents")
    print(f" Normalized : {meta['normalized_quotes']} quotes matched to canonical catalog"
          f"  ({meta['unmatched']} unmatched)")
    print(f" Bundles    : {meta['bundle_count']} cross-brand opportunities")
    print(f" Risks      : {meta['risk_count']} flags "
          f"({meta['high_risk_count']} high)")
    print(BAR)
    print(f"  ANNUAL SAVINGS IDENTIFIED:  {INR}{meta['total_annual_savings']:,.0f}")
    print(BAR)

    print("\n TOP BUNDLING OPPORTUNITIES")
    print(" " + "-" * 66)
    for b in bundles:
        print(f"  {b['canonical_name']}")
        print(f"    brands   : {', '.join(b['brands'])}  ->  {b['combined_monthly_qty']:,.0f}/mo")
        print(f"    price    : {INR}{b['current_blended_price']:.2f} -> "
              f"{INR}{b['best_price']:.2f} @ {b['best_vendor']}")
        print(f"    saving   : {INR}{b['annual_saving']:,.0f}/yr")
        print()

    print(" SUPPLY-RISK REGISTER")
    print(" " + "-" * 66)
    for r in risks:
        print(f"  [{r['severity']:^6}] {r['canonical_name']}  ({r['risk_type']})")
        print(f"           {r['detail']}")
    print()

if __name__ == "__main__":
    main()

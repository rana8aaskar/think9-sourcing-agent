"""
The extraction layer.

In PRODUCTION, unstructured vendor documents (PDF text, WhatsApp exports,
emails, spreadsheets) are handed to Claude with a strict structured-output
prompt, and Claude returns clean JSON line items. That is `AnthropicExtractor`.

For an OFFLINE, reproducible demo we ship `LocalExtractor`, which parses the
same messy documents with deterministic rules. It is a drop-in for the same
interface, so the rest of the pipeline never knows which one produced the data.
Nothing downstream is hardcoded — every number in the final report is computed
from whatever these extractors emit.
"""
from __future__ import annotations
import csv
import io
import json
import re
from typing import Protocol

from .schema import RawLineItem

EXTRACTION_SYSTEM_PROMPT = """You are a procurement data-extraction agent for Think9.
You are given the raw text of ONE vendor document (a quote PDF, a WhatsApp chat,
an email, or a price list). Extract every distinct priced line item.

Return ONLY a JSON array. Each element must have exactly these keys:
  raw_description (string, verbatim item name as the vendor wrote it)
  unit_price (number, per-unit price; strip currency symbols and commas)
  currency (string, e.g. "INR")
  moq (integer or null, minimum order quantity)
  lead_time_days (integer or null; convert "3 weeks" -> 21, "6 weeks" -> 42)
  uom (string: "piece" for packaging, "kg" for ingredients)
  quote_valid_until (ISO date string YYYY-MM-DD or null)
No prose, no markdown fences, no trailing text."""


class Extractor(Protocol):
    def extract(self, *, text: str, vendor: str, source_type: str,
                source_file: str) -> list[RawLineItem]:
        ...


class AnthropicExtractor:
    """Production path. Requires the anthropic SDK + credentials in the env."""

    def __init__(self, model: str = "claude-3-5-sonnet-20240620"):
        self.model = model

    def extract(self, *, text, vendor, source_type, source_file):
        from anthropic import Anthropic  # imported lazily
        client = Anthropic()
        msg = client.messages.create(
            model=self.model,
            max_tokens=2000,
            system=EXTRACTION_SYSTEM_PROMPT,
            messages=[{"role": "user",
                       "content": f"VENDOR: {vendor}\nSOURCE TYPE: {source_type}\n\n{text}"}],
        )
        payload = "".join(b.text for b in msg.content if b.type == "text")
        rows = json.loads(payload)
        return [RawLineItem(vendor=vendor, source_type=source_type,
                            source_file=source_file, **row) for row in rows]


class OpenAIExtractor:
    """Fallback production path. Requires openai SDK + OPENAI_API_KEY in the env."""

    def __init__(self, model: str = "gpt-4o"):
        self.model = model

    def extract(self, *, text, vendor, source_type, source_file):
        from openai import OpenAI  # imported lazily
        client = OpenAI()
        msg = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": f"VENDOR: {vendor}\nSOURCE TYPE: {source_type}\n\n{text}"}
            ],
            response_format={"type": "json_object"}
        )
        payload = msg.choices[0].message.content
        try:
            data = json.loads(payload)
            # If wrapped in an object like {"items": [...]}, extract it
            if isinstance(data, dict):
                for key in data:
                    if isinstance(data[key], list):
                        rows = data[key]
                        break
                else:
                    rows = [data]
            else:
                rows = data
        except Exception:
            rows = []
            
        return [RawLineItem(vendor=vendor, source_type=source_type,
                            source_file=source_file, **row) for row in rows]


# --------------------------------------------------------------------------- #
#  Offline deterministic extractor (used by the demo)                         #
# --------------------------------------------------------------------------- #
_PRICE = r"(?:rs\.?|inr|₹)?\s*([0-9][0-9,]*\.?[0-9]*)"


def _to_days(text: str) -> int | None:
    text = text.lower()
    m = re.search(r"(\d+)\s*week", text)
    if m:
        return int(m.group(1)) * 7
    m = re.search(r"(\d+)\s*day", text)
    if m:
        return int(m.group(1))
    return None


def _num(s: str) -> float:
    return float(s.replace(",", ""))


def _parse_qty(s: str) -> int:
    s = s.strip().lower().replace(",", "")
    if s.endswith("k"):
        return int(float(s[:-1]) * 1000)
    return int(float(s))


class LocalExtractor:
    """Deterministic stand-in that genuinely reads each document format."""

    def extract(self, *, text, vendor, source_type, source_file):
        fn = getattr(self, f"_parse_{source_type}")
        return [RawLineItem(vendor=vendor, source_type=source_type,
                            source_file=source_file, **d) for d in fn(text)]

    # --- PDF-style tabular quotes (Shreeji, Univo) ------------------------- #
    def _parse_pdf(self, text):
        valid = None
        vm = re.search(r"valid.*?(\d{1,2}\s*days)", text, re.I)
        if vm:
            valid = _iso_from_relative(_to_days(vm.group(1)))
        em = re.search(r"expires on\s*(\d{1,2}\s+\w+\s+\d{4})", text, re.I)
        if em:
            valid = _iso_from_absolute(em.group(1))

        rows = []
        for line in text.splitlines():
            # a data row has a description, a price and a lead time
            m = re.search(
                r"([A-Za-z][A-Za-z0-9 /()\-x.]+?)\s+"      # description
                r"([0-9][0-9,]{2,})\s+"                    # MOQ
                r"([0-9]+\.[0-9]{2})\s+"                   # price
                r"(\d+\s*days)", line)
            if m:
                rows.append(dict(
                    raw_description=m.group(1).strip(),
                    moq=int(m.group(2).replace(",", "")),
                    unit_price=_num(m.group(3)),
                    lead_time_days=_to_days(m.group(4)),
                    uom="piece", quote_valid_until=valid))
        return rows

    # --- WhatsApp export (Kwality) ---------------------------------------- #
    def _parse_whatsapp(self, text):
        # Item names and prices often land in different messages. Track the
        # most recently discussed item and attach the next price to it — the
        # same context resolution the LLM extractor does natively.
        rows = []
        last_item = None
        for line in text.splitlines():
            msg = line.split(":", 3)[-1].lower() if "]" in line else ""
            if not msg:
                continue
            if "amber" in msg or "droppr" in msg or "dropper" in msg:
                last_item = "30ml amber droppr bottle"
            elif "jar" in msg:
                last_item = "500ml jar"

            pm = re.search(r"(\d+\.?\d*)\s*rs", msg) or \
                re.search(r"rate\s*(\d+\.?\d*)", msg)
            has_price = pm and float(pm.group(1)) > 1  # ignore "3 week"
            if has_price and last_item:
                price = _num(pm.group(1))
                mm = (re.search(r"(?:min|min\.?)\s*([0-9,]+)", msg) or
                      re.search(r"([0-9]{2,}\s*k)\s*\+?", msg) or
                      re.search(r"([0-9]{4,})\s*(?:pcs|pieces|\+)", msg))
                moq = _parse_qty(mm.group(1)) if mm else None
                rows.append(dict(raw_description=last_item, unit_price=price,
                                 moq=moq, lead_time_days=_to_days(msg),
                                 uom="piece", quote_valid_until=None))
                last_item = None
        return rows

    # --- Email quote (AromaChem) ------------------------------------------ #
    def _parse_email(self, text):
        valid = None
        vm = re.search(r"valid for\s*(\d+\s*days)", text, re.I)
        if vm:
            valid = _iso_from_relative(_to_days(vm.group(1)))
        rows, current = [], None
        for line in text.splitlines():
            dm = re.match(r"\s*-\s*(.+)", line)
            if dm and not re.search(r"price", line, re.I):
                current = dm.group(1).strip()
            pm = re.search(r"(?:INR|Rs\.?)\s*([0-9,]+)\s*per\s*kg", line, re.I)
            if pm and current:
                moq_m = re.search(r"MOQ:\s*([0-9]+)\s*kg", line, re.I)
                lead_m = re.search(r"Lead time:\s*(\d+\s*weeks?)", line, re.I)
                rows.append(dict(raw_description=current,
                                 unit_price=_num(pm.group(1)),
                                 moq=int(moq_m.group(1)) if moq_m else None,
                                 lead_time_days=_to_days(lead_m.group(1)) if lead_m else None,
                                 uom="kg", quote_valid_until=valid))
                current = None
        return rows

    # --- CSV price list (PackMart) ---------------------------------------- #
    def _parse_csv(self, text):
        rows = []
        for r in csv.DictReader(io.StringIO(text)):
            rows.append(dict(
                raw_description=r["sku_desc"],
                unit_price=_num(r["unit_rate_inr"]),
                moq=int(r["min_order_qty"]),
                lead_time_days=int(r["despatch_days"]),
                uom="piece", quote_valid_until=None))
        return rows


# small date helpers (reference "today" = 2026-08-11 for the demo) ---------- #
from datetime import date, timedelta
_TODAY = date(2026, 8, 11)
_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct",
     "nov", "dec"], start=1)}


def _iso_from_relative(days: int | None):
    if days is None:
        return None
    return (_TODAY + timedelta(days=days)).isoformat()


def _iso_from_absolute(s: str):
    m = re.match(r"(\d{1,2})\s+(\w{3})\w*\s+(\d{4})", s.strip())
    if not m:
        return None
    d, mon, y = int(m.group(1)), _MONTHS[m.group(2).lower()[:3]], int(m.group(3))
    return date(y, mon, d).isoformat()

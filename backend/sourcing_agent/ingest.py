"""Registers the raw vendor sources and runs the extractor over all of them."""
from __future__ import annotations
from pathlib import Path
from .llm import Extractor
from .schema import RawLineItem

# (file, vendor, source_type)
SOURCES = [
    ("quote_shreeji.txt",       "Shreeji Packaging",  "pdf"),
    ("whatsapp_kwality.txt",    "Kwality Bottles",    "whatsapp"),
    ("email_aromachem.txt",     "AromaChem",          "email"),
    ("quote_univo.txt",         "Univo Pack",         "pdf"),
    ("pricelist_packmart.csv",  "PackMart Supplies",  "csv"),
]


def ingest_all(data_dir: Path, extractor: Extractor) -> list[RawLineItem]:
    items: list[RawLineItem] = []
    for fname, vendor, stype in SOURCES:
        text = (data_dir / fname).read_text(encoding="utf-8")
        got = extractor.extract(text=text, vendor=vendor,
                                source_type=stype, source_file=fname)
        items.extend(got)
    return items

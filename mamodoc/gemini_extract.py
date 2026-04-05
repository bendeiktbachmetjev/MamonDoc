from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from mamodoc.defaults import DEFAULT_GEMINI_MODEL
from mamodoc.models import CreditNoteGeminiPayload
from mamodoc.money_format import normalize_date_comma_spacing

SYSTEM_INSTRUCTION = """You are a document analyst for a Lithuanian ship provisions supplier (Unimars).
You receive a PDF invoice. Your job is to propose values for a CREDIT NOTE (Word template), not to copy the invoice layout.

Rules:
- Use European number formatting with comma as decimal separator in money strings when appropriate (e.g. 679,87 EUR).
- vessel_name: only the vessel name (e.g. ELBSTROM), no M/V prefix.
- inv1_id_before_comma: invoice id + ' of ' + month and day without the year suffix (e.g. 'UNI 2604/02 of April 03'). The template adds inv1_comma_year separately.
- If the invoice has a single total block, set has_second_invoice false and leave inv2_* at defaults.
- If there are two distinct invoice references to list (like two UNI numbers), set has_second_invoice true and fill inv2_*.
- Discount lines: if the invoice does not show a discount but a credit note would, infer reasonable discount fields consistent with gross and net if you can; otherwise align gross==net and discount_pct '0' and discount_eur '0,00 EUR'.
- Bank block: prefer supplier bank details from the invoice footer; otherwise use standard Unimars lines if visible.
- suggested_cn_number / suggested_cn_date: propose a new credit note id and issue date. suggested_cn_date MUST be the supplier invoice date as printed on the PDF (same wording if possible), NOT today's calendar date. If the invoice date is visible, never leave suggested_cn_date null.

Respond with JSON only, no markdown. The JSON must match this shape (all keys required, use null only where specified optional):
"""

JSON_SHAPE: dict[str, Any] = {
    "payer_company": "string",
    "supplier_name": "string",
    "supplier_city": "string",
    "supplier_country": "string",
    "vessel_name": "string",
    "suggested_cn_number": "string or null",
    "suggested_cn_date": "string or null",
    "inv1_id_before_comma": "string",
    "inv1_comma_year": "string",
    "inv1_gross": "string",
    "inv1_discount_pct": "string",
    "inv1_discount_eur": "string",
    "inv1_net": "string",
    "has_second_invoice": "boolean",
    "inv2_id_before_comma": "string",
    "inv2_comma_year": "string",
    "inv2_gross": "string",
    "inv2_discount_pct": "string",
    "inv2_discount_eur": "string",
    "inv2_net": "string",
    "total_ship": "string",
    "signer_company": "string",
    "signer_name": "string",
    "bank_name": "string",
    "bank_address": "string",
    "bank_swift": "string",
    "bank_account": "string",
}


def _default_cn_date() -> str:
    dt = datetime.now()
    return f"{dt.strftime('%B')} {dt.day}, {dt.year}"


def _infer_legacy_credit_note_date(payload: CreditNoteGeminiPayload) -> str:
    """Rebuild date from inv1_id_before_comma + inv1_comma_year when suggested_cn_date is missing."""
    parts = (payload.inv1_id_before_comma or "").split(" of ", 1)
    tail = parts[1].strip() if len(parts) > 1 else ""
    cy = (payload.inv1_comma_year or "").strip()
    if tail:
        return normalize_date_comma_spacing(f"{tail}{cy}".strip())
    return ""


def extract_from_invoice_pdf(
    pdf_path: Path,
    *,
    api_key: str | None = None,
    model_name: str = DEFAULT_GEMINI_MODEL,
) -> CreditNoteGeminiPayload:
    import google.generativeai as genai

    key = api_key or os.environ.get("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not set")

    genai.configure(api_key=key)
    model = genai.GenerativeModel(
        model_name,
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
        ),
    )

    pdf_bytes = pdf_path.read_bytes()
    prompt = SYSTEM_INSTRUCTION + json.dumps(JSON_SHAPE, ensure_ascii=False)

    response = model.generate_content(
        [
            {"mime_type": "application/pdf", "data": pdf_bytes},
            prompt,
        ]
    )

    raw = response.text
    if not raw:
        raise RuntimeError("Empty response from Gemini")

    data = json.loads(raw)
    return CreditNoteGeminiPayload.model_validate(data)


def resolve_cn_meta(
    payload: CreditNoteGeminiPayload,
    *,
    cn_number: str | None,
    cn_date: str | None,
) -> tuple[str, str]:
    num = (cn_number or payload.suggested_cn_number or "").strip()
    if not num:
        raise ValueError("Credit note number missing: pass --cn-number or ensure model returns suggested_cn_number")

    date_str = (cn_date or payload.suggested_cn_date or "").strip()
    if not date_str:
        date_str = _infer_legacy_credit_note_date(payload)
    if not date_str:
        date_str = _default_cn_date()
    return num, date_str

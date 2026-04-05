from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from mamodoc.models_ui import InvoiceUiGeminiPayload

UI_INSTRUCTION = """You analyze a supplier PDF invoice (ship provisions, Unimars-style).
Return JSON only, no markdown.

Extract:
- payer_company: legal payer / customer company (e.g. Kloska Rostock GmbH), NOT the vessel name.
- vessel_name: vessel only (e.g. ELBSTROM), strip M/V.
- currency: ISO-like code, default EUR.
- invoice_lines: list of objects. For EACH distinct invoice document / series total on this PDF, one row:
  - invoice_number: serial like UNI 2604/02
  - gross_display: gross total string as on document (with EUR if shown)
  - gross_eur: number (use dot as decimal) if you can read it reliably, else null
- suggested_credit_note_number: plausible next credit note id (UNI ######) if inferable, else null
- suggested_credit_note_date: human date for the credit note if inferable, else null

If multiple invoice totals exist, include each separately. If one invoice spans pages, use ONE line with the final gross total.

JSON shape (all top-level keys required):
"""

UI_JSON_SHAPE: dict[str, Any] = {
    "payer_company": "string",
    "vessel_name": "string",
    "currency": "string",
    "invoice_lines": [
        {
            "invoice_number": "string",
            "gross_display": "string",
            "gross_eur": "number or null",
        }
    ],
    "suggested_credit_note_number": "string or null",
    "suggested_credit_note_date": "string or null",
}


def extract_invoice_ui_from_pdf(
    pdf_path: Path,
    *,
    api_key: str | None = None,
    model_name: str = "gemini-2.0-flash",
) -> InvoiceUiGeminiPayload:
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
    prompt = UI_INSTRUCTION + json.dumps(UI_JSON_SHAPE, ensure_ascii=False)

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
    return InvoiceUiGeminiPayload.model_validate(data)

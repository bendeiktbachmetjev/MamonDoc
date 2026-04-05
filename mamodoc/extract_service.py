from __future__ import annotations

import tempfile
from decimal import Decimal
from pathlib import Path

from mamodoc.cn_counter import allocate_next_credit_note_number
from mamodoc.defaults import DEFAULT_GEMINI_MODEL
from mamodoc.gemini_extract import _default_cn_date
from mamodoc.gemini_ui_extract import extract_invoice_ui_from_pdf
from mamodoc.money_format import decimal_to_float_safe, format_eur, parse_eur_amount


def extract_ui_bundle(
    pdf_bytes: bytes,
    *,
    discount_percent: float,
    model_name: str = DEFAULT_GEMINI_MODEL,
) -> dict:
    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    try:
        tmp.write(pdf_bytes)
        tmp.close()
        payload = extract_invoice_ui_from_pdf(Path(tmp.name), model_name=model_name)
    finally:
        Path(tmp.name).unlink(missing_ok=True)

    currency = (payload.currency or "EUR").strip() or "EUR"
    cn_number = allocate_next_credit_note_number(
        suggested_seed=payload.suggested_credit_note_number,
    )
    cn_date = (payload.suggested_credit_note_date or "").strip() or _default_cn_date()

    lines_out: list[dict] = []
    total = Decimal("0")
    for row in payload.invoice_lines:
        parsed = parse_eur_amount(row.gross_display)
        if parsed is None and row.gross_eur is not None:
            parsed = Decimal(str(row.gross_eur))
        if parsed is None:
            parsed = Decimal("0")
        total += parsed
        lines_out.append(
            {
                "invoice_number": row.invoice_number.strip(),
                "gross_display": row.gross_display.strip(),
                "gross_amount": decimal_to_float_safe(parsed),
                "gross_formatted": format_eur(parsed, currency=currency),
            }
        )

    pct = Decimal(str(discount_percent))
    discount_amount = (total * pct / Decimal("100")).quantize(Decimal("0.01"))
    final_amount = (total - discount_amount).quantize(Decimal("0.01"))

    return {
        "payer_company": payload.payer_company.strip(),
        "credit_note_number": cn_number,
        "credit_note_date": cn_date,
        "vessel_name": payload.vessel_name.strip(),
        "currency": currency,
        "discount_percent": float(pct),
        "invoices": lines_out,
        "total_before_discount": {
            "amount": decimal_to_float_safe(total),
            "display": format_eur(total, currency=currency),
        },
        "discount_amount": {
            "amount": decimal_to_float_safe(discount_amount),
            "display": format_eur(discount_amount, currency=currency),
        },
        "final_after_discount": {
            "amount": decimal_to_float_safe(final_amount),
            "display": format_eur(final_amount, currency=currency),
        },
    }

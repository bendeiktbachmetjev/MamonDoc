from __future__ import annotations

import tempfile
from decimal import Decimal
from pathlib import Path

from mamodoc.cn_counter import peek_next_credit_note_number
from mamodoc.defaults import DEFAULT_GEMINI_MODEL
from mamodoc.gemini_extract import _default_cn_date
from mamodoc.gemini_ui_extract import extract_invoice_ui_from_pdf
from mamodoc.models_ui import InvoiceUiGeminiPayload, UiInvoiceLine
from mamodoc.money_format import decimal_to_float_safe, format_eur, parse_eur_amount, split_template_date


def _resolved_line_gross(row: UiInvoiceLine) -> Decimal:
    """
    Pick a single gross amount per invoice line for totals and discount math.

    The model sometimes puts a truncated value in gross_display (e.g. '87,00 EUR' from
    a total '679,87 EUR') while gross_eur still holds the full amount. When both parse
    and differ materially, the larger value is usually the real invoice total on these docs.
    """
    d = parse_eur_amount(row.gross_display)
    e: Decimal | None = None
    if row.gross_eur is not None:
        try:
            e = Decimal(str(row.gross_eur))
        except Exception:
            e = None

    if d is None or d <= 0:
        return e if e is not None and e > 0 else Decimal("0")
    if e is None or e <= 0:
        return d

    bigger = max(d, e)
    smaller = min(d, e)
    # Within 5%: treat as same total, keep display-derived for consistency with PDF wording.
    if (bigger - smaller) / bigger <= Decimal("0.05"):
        return d
    return bigger


def _fmt_discount_pct(pct: Decimal) -> str:
    if pct == pct.to_integral():
        return str(int(pct))
    s = f"{pct:.4f}".rstrip("0").rstrip(".")
    return s or "0"


def _allocate_discounts(grosses: list[Decimal], pct: Decimal) -> tuple[list[Decimal], list[Decimal]]:
    if not grosses:
        return [], []
    total = sum(grosses, start=Decimal("0"))
    if total <= 0:
        return [Decimal("0")] * len(grosses), list(grosses)
    total_disc = (total * pct / Decimal("100")).quantize(Decimal("0.01"))
    discs: list[Decimal] = []
    acc = Decimal("0")
    for i, g in enumerate(grosses):
        if i == len(grosses) - 1:
            di = (total_disc - acc).quantize(Decimal("0.01"))
        else:
            di = (total_disc * g / total).quantize(Decimal("0.01"))
            acc += di
        discs.append(di)
    nets = [(g - d).quantize(Decimal("0.01")) for g, d in zip(grosses, discs, strict=True)]
    return discs, nets


def build_bundle_from_payload(
    payload: InvoiceUiGeminiPayload,
    *,
    discount_percent: float,
    cn_number: str,
    cn_date: str,
) -> dict:
    currency = (payload.currency or "EUR").strip() or "EUR"
    cn_date_f = (cn_date or "").strip() or (payload.suggested_credit_note_date or "").strip() or _default_cn_date()
    fallback_date = (payload.suggested_credit_note_date or "").strip() or cn_date_f

    grosses: list[Decimal] = []
    for row in payload.invoice_lines:
        grosses.append(_resolved_line_gross(row))

    pct = Decimal(str(discount_percent))
    disc_amts, nets = _allocate_discounts(grosses, pct)
    pct_display = _fmt_discount_pct(pct)

    lines_out: list[dict] = []
    total = sum(grosses, start=Decimal("0"))
    total_discount = sum(disc_amts, start=Decimal("0")).quantize(Decimal("0.01"))
    final_amount = (total - total_discount).quantize(Decimal("0.01"))

    for row, g, d, n in zip(
        payload.invoice_lines,
        grosses,
        disc_amts,
        nets,
        strict=True,
    ):
        dt = (row.invoice_date_text or fallback_date).strip()
        left, comma_y = split_template_date(dt)
        id_before = f"{row.invoice_number.strip()} of {left}".strip()

        lines_out.append(
            {
                "invoice_number": row.invoice_number.strip(),
                "gross_display": row.gross_display.strip(),
                "gross_amount": decimal_to_float_safe(g),
                "gross_formatted": format_eur(g, currency=currency),
                "id_before_comma": id_before,
                "comma_year": comma_y if comma_y.endswith("  ") else f"{comma_y}  ",
                "discount_pct_display": pct_display,
                "discount_eur_formatted": format_eur(d, currency=currency),
                "net_formatted": format_eur(n, currency=currency),
            }
        )

    return {
        "payer_company": payload.payer_company.strip(),
        "credit_note_number": (cn_number or "").strip(),
        "credit_note_date": cn_date_f,
        "vessel_name": payload.vessel_name.strip(),
        "currency": currency,
        "discount_percent": float(pct),
        "supplier_name": payload.supplier_name.strip(),
        "supplier_city": payload.supplier_city.strip(),
        "supplier_country": payload.supplier_country.strip(),
        "signer_company": payload.signer_company.strip(),
        "signer_name": payload.signer_name.strip(),
        "bank_name": payload.bank_name.strip(),
        "bank_address": payload.bank_address.strip(),
        "bank_swift": payload.bank_swift.strip(),
        "bank_account": payload.bank_account.strip(),
        "invoices": lines_out,
        "total_before_discount": {
            "amount": decimal_to_float_safe(total),
            "display": format_eur(total, currency=currency),
        },
        "discount_amount": {
            "amount": decimal_to_float_safe(total_discount),
            "display": format_eur(total_discount, currency=currency),
        },
        "final_after_discount": {
            "amount": decimal_to_float_safe(final_amount),
            "display": format_eur(final_amount, currency=currency),
        },
    }


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

    cn_number = peek_next_credit_note_number(suggested_seed=payload.suggested_credit_note_number)
    cn_date = (payload.suggested_credit_note_date or "").strip() or _default_cn_date()
    return build_bundle_from_payload(
        payload,
        discount_percent=discount_percent,
        cn_number=cn_number,
        cn_date=cn_date,
    )

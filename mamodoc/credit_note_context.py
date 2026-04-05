from __future__ import annotations

from decimal import Decimal
from typing import Any

from mamodoc.models import CreditNoteGeminiPayload
from mamodoc.money_format import format_eur, parse_eur_amount

# Fallback when the model omits bank lines (layout still matches template).
_DEFAULT_BANK: dict[str, str] = {
    "bank_name": 'Bankas „SWEDBANK“ AB',
    "bank_address": "Konstitucijos pr. 20A, Vilnius, Lithuania",
    "bank_swift": "S.W.I.F.T. :HABALT LT22",
    "bank_account": "Account N..:LT40 7300 0100 9417 8770",
}


def _fmt_discount_pct(pct: Decimal) -> str:
    if pct == pct.to_integral():
        return str(int(pct))
    s = f"{pct:.4f}".rstrip("0").rstrip(".")
    return s or "0"


def build_docxtpl_context_from_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    """
    Map extract_ui_bundle() output (+ per-line discount fields) to credit_note_bank_transfer.docx variables.
    Template supports at most two invoice blocks.
    """
    invs: list[dict[str, Any]] = bundle.get("invoices") or []
    if len(invs) > 2:
        raise ValueError(
            "This Word template supports at most 2 invoices. "
            "Split the PDF or extend templates/credit_note_bank_transfer.docx."
        )

    currency = bundle.get("currency") or "EUR"
    pct = Decimal(str(bundle.get("discount_percent") or 0))

    def line_ctx(idx: int) -> dict[str, str]:
        if idx >= len(invs):
            return {
                "id_before_comma": "",
                "comma_year": ", 2026  ",
                "gross": "0,00 EUR",
                "discount_pct": "0",
                "discount_eur": "0,00 EUR",
                "net": "0,00 EUR",
            }
        row = invs[idx]
        id_before = (row.get("id_before_comma") or "").strip()
        comma_y = (row.get("comma_year") or ", 2026  ").strip()
        if not comma_y.startswith(","):
            comma_y = f", {comma_y}  "
        return {
            "id_before_comma": id_before,
            "comma_year": comma_y if comma_y.endswith("  ") else f"{comma_y}  ",
            "gross": row.get("gross_formatted") or "0,00 EUR",
            "discount_pct": row.get("discount_pct_display") or _fmt_discount_pct(pct),
            "discount_eur": row.get("discount_eur_formatted") or format_eur(Decimal("0"), currency=currency),
            "net": row.get("net_formatted") or format_eur(Decimal("0"), currency=currency),
        }

    a = line_ctx(0)
    b = line_ctx(1)
    has_second = len(invs) > 1

    bank_name = (bundle.get("bank_name") or "").strip() or _DEFAULT_BANK["bank_name"]
    bank_address = (bundle.get("bank_address") or "").strip() or _DEFAULT_BANK["bank_address"]
    bank_swift = (bundle.get("bank_swift") or "").strip() or _DEFAULT_BANK["bank_swift"]
    bank_account = (bundle.get("bank_account") or "").strip() or _DEFAULT_BANK["bank_account"]

    inv_lines = bundle.get("invoices") or []
    total_gross_display = (bundle.get("total_before_discount") or {}).get("display") or ""
    if inv_lines:
        row0 = inv_lines[0]
        idb = (row0.get("id_before_comma") or "").strip()
        parts = idb.split(" of ", 1)
        inv1_invoice_number = parts[0].strip() if parts else ""
        tail = parts[1].strip() if len(parts) > 1 else ""
        cy = (row0.get("comma_year") or "").strip()
        inv1_invoice_date = (
            f"{tail}{cy}".strip()
            if tail
            else (cy.lstrip(",").strip() or (bundle.get("credit_note_date") or ""))
        )
    else:
        inv1_invoice_number = ""
        inv1_invoice_date = bundle.get("credit_note_date") or ""

    return {
        "cn_number": bundle.get("credit_note_number") or "",
        "cn_date": bundle.get("credit_note_date") or "",
        "payer_company": bundle.get("payer_company") or "",
        "supplier_name": bundle.get("supplier_name") or "Unimars",
        "supplier_city": bundle.get("supplier_city") or "Klaipėda",
        "supplier_country": bundle.get("supplier_country") or "Lithuania",
        "vessel_name": bundle.get("vessel_name") or "",
        "inv1_id_before_comma": a["id_before_comma"],
        "inv1_comma_year": a["comma_year"],
        "inv1_gross": a["gross"],
        "inv1_discount_pct": a["discount_pct"],
        "inv1_discount_eur": a["discount_eur"],
        "inv1_net": a["net"],
        "has_second_invoice": has_second,
        "inv2_id_before_comma": b["id_before_comma"],
        "inv2_comma_year": b["comma_year"],
        "inv2_gross": b["gross"],
        "inv2_discount_pct": b["discount_pct"],
        "inv2_discount_eur": b["discount_eur"],
        "inv2_net": b["net"],
        "total_ship": (bundle.get("final_after_discount") or {}).get("display") or "",
        "signer_company": bundle.get("signer_company") or 'UAB "Unimars"',
        "signer_name": bundle.get("signer_name") or "Ina Selest",
        "bank_name": bank_name,
        "bank_address": bank_address,
        "bank_swift": bank_swift,
        "bank_account": bank_account,
        # templates/template new.docx (single visible invoice line)
        "inv1_invoice_number": inv1_invoice_number,
        "inv1_invoice_date": inv1_invoice_date,
        "total_gross": total_gross_display,
    }


def enrich_legacy_credit_note_context(
    ctx: dict[str, Any],
    payload: CreditNoteGeminiPayload,
    cn_date: str,
) -> None:
    """Add variables used by templates/template new.docx when using the legacy Gemini payload path."""
    parts = (payload.inv1_id_before_comma or "").split(" of ", 1)
    inv1_invoice_number = parts[0].strip() if parts else ""
    tail = parts[1].strip() if len(parts) > 1 else ""
    cy = (payload.inv1_comma_year or "").strip()
    inv1_invoice_date = (
        f"{tail}{cy}".strip()
        if tail
        else (cy.lstrip(",").strip() or cn_date)
    )
    g1 = parse_eur_amount(payload.inv1_gross) or Decimal("0")
    g2 = (
        (parse_eur_amount(payload.inv2_gross) or Decimal("0"))
        if payload.has_second_invoice
        else Decimal("0")
    )
    ctx["inv1_invoice_number"] = inv1_invoice_number
    ctx["inv1_invoice_date"] = inv1_invoice_date
    ctx["total_gross"] = format_eur(g1 + g2, currency="EUR")

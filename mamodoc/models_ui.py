from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field


class UiInvoiceLine(BaseModel):
    invoice_number: str = Field(description="Invoice / series id as on the PDF, e.g. UNI 2604/02")
    gross_display: str = Field(description="Gross total for this invoice as printed, with currency if present")
    gross_eur: float | None = Field(
        default=None,
        description="Numeric EUR total for this invoice if confidently readable",
    )


class InvoiceUiGeminiPayload(BaseModel):
    payer_company: str = Field(description="Payer / customer company (who pays), not the ship name")
    vessel_name: str = Field(description="Ship name only, no M/V prefix")
    currency: str = Field(default="EUR")
    invoice_lines: Annotated[
        list[UiInvoiceLine],
        Field(
            min_length=1,
            description="One entry per distinct invoice total; if only one invoice, single line",
        ),
    ]
    suggested_credit_note_number: str | None = Field(
        default=None,
        description="Suggested next credit note id e.g. UNI 261093, or null",
    )
    suggested_credit_note_date: str | None = Field(
        default=None,
        description="Suggested issue date text e.g. April 03, 2026",
    )

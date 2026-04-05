from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field, field_validator


class UiInvoiceLine(BaseModel):
    invoice_number: str = Field(description="Invoice / series id as on the PDF, e.g. UNI 2604/02")
    gross_display: str = Field(description="Gross total string as on document (with EUR if shown)")
    gross_eur: float | None = Field(
        default=None,
        description="Numeric total if confidently readable (dot decimal), else null",
    )
    invoice_date_text: str | None = Field(
        default=None,
        description="Invoice date as on PDF, e.g. 'April 03, 2026' (for credit note line layout)",
    )


class InvoiceUiGeminiPayload(BaseModel):
    payer_company: str = Field(description="Payer / customer company (who pays), not the vessel name")
    vessel_name: str = Field(description="Ship name only, no M/V prefix")
    currency: str = Field(default="EUR")
    invoice_lines: Annotated[
        list[UiInvoiceLine],
        Field(
            min_length=1,
            description="One entry per distinct invoice total; if one invoice, single line",
        ),
    ]
    suggested_credit_note_number: str | None = Field(
        default=None,
        description="Suggested next credit note id e.g. UNI 261093, or null",
    )
    suggested_credit_note_date: str | None = Field(
        default=None,
        description="Suggested credit note issue date e.g. April 03, 2026",
    )
    supplier_name: str = Field(default="Unimars")
    supplier_city: str = Field(default="Klaipėda")
    supplier_country: str = Field(default="Lithuania")
    signer_company: str = Field(default='UAB "Unimars"')
    signer_name: str = Field(default="Ina Selest")
    bank_name: str = Field(default="", description="Payee bank title as on invoice footer if visible")
    bank_address: str = Field(default="", description="Bank address line")
    bank_swift: str = Field(default="", description="SWIFT / S.W.I.F.T. line as printed")
    bank_account: str = Field(default="", description="Account number line as printed")

    @field_validator(
        "supplier_name",
        "supplier_city",
        "supplier_country",
        "signer_company",
        "signer_name",
        "bank_name",
        "bank_address",
        "bank_swift",
        "bank_account",
        mode="before",
    )
    @classmethod
    def _empty_if_null(cls, v: object) -> str:
        if v is None:
            return ""
        return str(v).strip()

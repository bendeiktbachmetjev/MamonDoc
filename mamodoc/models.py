from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


class CreditNoteGeminiPayload(BaseModel):
    """
    Fields returned by Gemini; aligned with templates/credit_note_bank_transfer.docx.
    """

    payer_company: str = Field(description="Customer / payer line as on credit note header")
    supplier_name: str = Field(default="Unimars")
    supplier_city: str = Field(default="Klaipėda")
    supplier_country: str = Field(default="Lithuania")
    vessel_name: str = Field(description="Vessel name without M/V prefix")

    suggested_cn_number: str | None = Field(
        default=None,
        description="Proposed credit note number after 'No.' (e.g. UNI 261093)",
    )
    suggested_cn_date: str | None = Field(
        default=None,
        description="Credit note date line as printed, e.g. 'April 03, 2026'",
    )

    inv1_id_before_comma: str = Field(
        description="Left part before comma+year, e.g. 'UNI 2604/02 of April 03'"
    )
    inv1_comma_year: str = Field(
        default=", 2026  ",
        description="Comma and year fragment before amount column, usually ', 2026  '",
    )
    inv1_gross: str = Field(description="Gross amount with currency, e.g. '679,87 EUR'")
    inv1_discount_pct: str = Field(description="Discount percent digits only, e.g. '12'")
    inv1_discount_eur: str = Field(description="Discount amount, e.g. '81,58 EUR'")
    inv1_net: str = Field(description="Net after discount, e.g. '598,29 EUR'")

    has_second_invoice: bool = Field(default=False)
    inv2_id_before_comma: str = Field(default="")
    inv2_comma_year: str = Field(default=", 2026  ")
    inv2_gross: str = Field(default="0,00 EUR")
    inv2_discount_pct: str = Field(default="0")
    inv2_discount_eur: str = Field(default="0,00 EUR")
    inv2_net: str = Field(default="0,00 EUR")

    total_ship: str = Field(description="Total for vessel line, e.g. '598,29 EUR'")

    signer_company: str = Field(default='UAB "Unimars"')
    signer_name: str = Field(default="Ina Selest")

    bank_name: str = Field(description='Bank title, e.g. \'Bankas „SWEDBANK“ AB\'')
    bank_address: str = Field()
    bank_swift: str = Field()
    bank_account: str = Field(description="Full account line as on credit note")

    @field_validator(
        "inv2_id_before_comma",
        "inv2_gross",
        "inv2_net",
        mode="before",
    )
    @classmethod
    def strip_optional(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.strip()
        return v

    def to_docxtpl_context(
        self,
        *,
        cn_number: str,
        cn_date: str,
    ) -> dict[str, Any]:
        return {
            "cn_number": cn_number,
            "cn_date": cn_date,
            "payer_company": self.payer_company,
            "supplier_name": self.supplier_name,
            "supplier_city": self.supplier_city,
            "supplier_country": self.supplier_country,
            "vessel_name": self.vessel_name,
            "inv1_id_before_comma": self.inv1_id_before_comma,
            "inv1_comma_year": self.inv1_comma_year,
            "inv1_gross": self.inv1_gross,
            "inv1_discount_pct": self.inv1_discount_pct,
            "inv1_discount_eur": self.inv1_discount_eur,
            "inv1_net": self.inv1_net,
            "has_second_invoice": self.has_second_invoice,
            "inv2_id_before_comma": self.inv2_id_before_comma,
            "inv2_comma_year": self.inv2_comma_year,
            "inv2_gross": self.inv2_gross,
            "inv2_discount_pct": self.inv2_discount_pct,
            "inv2_discount_eur": self.inv2_discount_eur,
            "inv2_net": self.inv2_net,
            "total_ship": self.total_ship,
            "signer_company": self.signer_company,
            "signer_name": self.signer_name,
            "bank_name": self.bank_name,
            "bank_address": self.bank_address,
            "bank_swift": self.bank_swift,
            "bank_account": self.bank_account,
        }

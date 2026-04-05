from __future__ import annotations

import re
from decimal import Decimal, ROUND_HALF_UP


def parse_eur_amount(text: str | None) -> Decimal | None:
    """Parse amounts like '679,87 EUR', '1 359,74', '679.87'."""
    if text is None:
        return None
    s = str(text).strip()
    if not s:
        return None
    s = re.sub(r"(?i)\s*eur\s*$", "", s).strip()
    s = s.replace(" ", "").replace("\u00a0", "")
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    s = re.sub(r"[^\d.\-]", "", s)
    if not s or s in {"-", "."}:
        return None
    try:
        return Decimal(s)
    except Exception:
        return None


def format_eur(amount: Decimal, *, currency: str = "EUR") -> str:
    q = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    sign = "-" if q < 0 else ""
    q = abs(q)
    integral, _, frac = f"{q:.2f}".partition(".")
    parts: list[str] = []
    while integral:
        parts.insert(0, integral[-3:])
        integral = integral[:-3]
    grouped = " ".join(parts) if parts else "0"
    display = f"{grouped},{frac}"
    return f"{sign}{display} {currency}".strip()


def decimal_to_float_safe(d: Decimal) -> float:
    return float(d)


def normalize_date_comma_spacing(text: str) -> str:
    """
    Fix missing space after comma in date phrases (e.g. 'April 03,2026' -> 'April 03, 2026').
    """
    if not text:
        return text
    return re.sub(r",([^\s,])", r", \1", text.strip())


def split_template_date(date_text: str) -> tuple[str, str]:
    """
    'April 03, 2026' or 'April 03,2026' -> ('April 03', ', 2026  ') for docxtpl inv*_id_before_comma / inv*_comma_year.
    """
    t = (date_text or "").strip()
    if not t:
        return "", ", 2026  "
    if "," in t:
        left, right = t.rsplit(",", 1)
        # Always ", YYYY" when rejoined with left (Gemini often returns "April 03,2026").
        return left.strip(), f", {right.strip()}  "
    return t, ", 2026  "

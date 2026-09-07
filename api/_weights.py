"""Product net weight, expressed in grams. Never infer shipping weight."""
import re
from decimal import Decimal


def weight_grams(value):
    if value is None or isinstance(value, bool):
        return None
    match = re.fullmatch(r'\s*(\d+(?:[.,]\d+)?)\s*(kg|kilogramos?|g|gr|gramos?)?\s*', str(value), re.I)
    if not match:
        return None
    number = Decimal(match[1].replace(',', '.'))
    if (match[2] or '').lower() in ('kg', 'kilogramo', 'kilogramos'):
        number *= 1000
    if not number.is_finite() or number <= 0:
        return None
    return float(number)

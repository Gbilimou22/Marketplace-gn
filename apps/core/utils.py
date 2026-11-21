import re

from django.core.exceptions import ValidationError


def normalize_guinean_phone_number(phone: str) -> str:
    """
    Normalizes a Guinean phone number to the international format +224XXXXXXXXX.

    Guinean phone numbers have 9 digits, typically starting with 6 (e.g., 620 12 34 56).
    Accepts formats:
    - '+224620123456'
    - '00224620123456'
    - '620123456'
    - '620 12 34 56' / '620-12-34-56'
    """
    if not phone:
        return ""

    cleaned = re.sub(r"[\s\-\.\(\)]", "", phone.strip())

    if cleaned.startswith("+224"):
        digits = cleaned[4:]
    elif cleaned.startswith("00224"):
        digits = cleaned[5:]
    elif cleaned.startswith("224") and len(cleaned) == 12:
        digits = cleaned[3:]
    else:
        digits = cleaned

    if not re.match(r"^6\d{8}$", digits):
        raise ValidationError(
            f"Le numéro de téléphone '{phone}' n'est pas un numéro guinéen valide à 9 chiffres commençant par 6."
        )

    return f"+224{digits}"

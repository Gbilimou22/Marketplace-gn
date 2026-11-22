from django import forms
from django.core.exceptions import ValidationError

from apps.core.utils import normalize_guinean_phone_number
from apps.shops.constants import GUINEAN_CITIES
from apps.shops.models import Shop


class ShopForm(forms.ModelForm):
    """
    Form used by sellers to create or update their shop.
    """

    city = forms.ChoiceField(
        choices=GUINEAN_CITIES,
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Ville / Commune",
    )

    class Meta:
        model = Shop
        fields = ["name", "city", "address", "whatsapp_number", "description", "logo"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-input", "placeholder": "Ex: Mode Guinéenne Conakry"}),
            "address": forms.TextInput(attrs={"class": "form-input", "placeholder": "Ex: Marché Madina, Bloc 3"}),
            "whatsapp_number": forms.TextInput(attrs={"class": "form-input", "placeholder": "620 12 34 56"}),
            "description": forms.Textarea(attrs={"class": "form-textarea", "rows": 4, "placeholder": "Décrivez vos produits et spécialités..."}),
            "logo": forms.FileInput(attrs={"class": "form-file"}),
        }

    def clean_whatsapp_number(self) -> str:
        raw_number = self.cleaned_data.get("whatsapp_number", "")
        try:
            return normalize_guinean_phone_number(raw_number)
        except ValidationError as err:
            raise forms.ValidationError(err.message) from err

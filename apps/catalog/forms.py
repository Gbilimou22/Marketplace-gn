from django import forms
from django.core.exceptions import ValidationError

from apps.catalog.models import Category, Product


class ProductForm(forms.ModelForm):
    """Form used by sellers to add or edit product listings."""

    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Catégorie",
    )

    class Meta:
        model = Product
        fields = ["category", "title", "description", "price_gnf", "condition", "brand", "stock"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-input", "placeholder": "Ex: iPhone 13 Pro 128 Go Bleu"}),
            "description": forms.Textarea(attrs={"class": "form-textarea", "rows": 5, "placeholder": "Décrivez l'état exact, les accessoires inclus..."}),
            "price_gnf": forms.NumberInput(attrs={"class": "form-input", "placeholder": "Ex: 4500000"}),
            "condition": forms.Select(attrs={"class": "form-select"}),
            "brand": forms.TextInput(attrs={"class": "form-input", "placeholder": "Ex: Apple, Samsung, Nike..."}),
            "stock": forms.NumberInput(attrs={"class": "form-input", "min": 0}),
        }

    def clean_price_gnf(self):
        price = self.cleaned_data.get("price_gnf")
        if not price or price <= 0:
            raise ValidationError("Le prix doit être strictement supérieur à 0 GNF.")
        return price

    def clean_stock(self):
        stock = self.cleaned_data.get("stock")
        if stock is None or stock < 0:
            raise ValidationError("La quantité en stock ne peut pas être négative.")
        return stock


class ProductImageUploadForm(forms.Form):
    """Form to upload a new product photo."""

    image = forms.ImageField(
        label="Photo de l'article",
        widget=forms.FileInput(attrs={"class": "form-file", "accept": "image/*"}),
    )
    is_cover = forms.BooleanField(
        required=False,
        label="Définir comme photo de couverture",
        widget=forms.CheckboxInput(attrs={"class": "form-checkbox"}),
    )

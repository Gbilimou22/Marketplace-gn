from django.core.management.base import BaseCommand

from apps.accounts.models import SellerProfile, User
from apps.accounts.services import seller_profile_request, seller_profile_verify
from apps.catalog.models import Category, Product
from apps.catalog.services import category_create, product_create, product_publish
from apps.shops.models import Shop
from apps.shops.services import shop_activate, shop_create


class Command(BaseCommand):
    help = "Initialise des données de test réalistes pour tester les Phases 1, 2 et 3."

    def handle(self, *args, **options):
        self.stdout.write("--- Initialisation des données de test ---")

        # 1. Création du superutilisateur admin
        admin_email = "admin@marketplace.gn"
        admin_pass = "Admin@224@224"
        admin_user = User.objects.filter(email=admin_email).first()
        if not admin_user:
            admin_user = User.objects.create_superuser(
                email=admin_email,
                password=admin_pass,
                full_name="Administrateur Marketplace",
                phone_number="+224620000000",
            )
            self.stdout.write(self.style.SUCCESS(f"Compte Administrateur créé : {admin_email} (mdp: {admin_pass})"))
        else:
            self.stdout.write(f"Compte Administrateur existant : {admin_email}")

        # 2. Création des catégories de référence
        categories_data = [
            (
                "Mode & Vêtements",
                "mode",
                "👗",
                [
                    ("Robes, Bazin & Wax", "robes-bazin-wax", "👘"),
                    ("Prêt-à-porter Homme", "pret-a-porter-homme", "👕"),
                    ("Chaussures & Sandales", "chaussures-sandales", "👠"),
                    ("Sacs & Accessoires", "sacs-accessoires", "👜"),
                ],
            ),
            (
                "Téléphones & Électronique",
                "electronique",
                "📱",
                [
                    ("Smartphones & Tablettes", "smartphones-tablettes", "📲"),
                    ("Ordinateurs & Laptops", "ordinateurs-laptops", "💻"),
                    ("Écouteurs, Casques & Audio", "audio-accessoires", "🎧"),
                    ("Accessoires & Chargeurs", "accessoires-chargeurs", "🔌"),
                ],
            ),
        ]

        created_categories = {}
        for parent_name, parent_slug, icon, children in categories_data:
            parent_cat = Category.objects.filter(slug=parent_slug).first()
            if not parent_cat:
                parent_cat = category_create(name=parent_name, slug=parent_slug, icon=icon)
            created_categories[parent_slug] = parent_cat

            for child_name, child_slug, child_icon in children:
                if not Category.objects.filter(slug=child_slug).exists():
                    child_cat = category_create(
                        name=child_name,
                        parent=parent_cat,
                        slug=child_slug,
                        icon=child_icon,
                    )
                    created_categories[child_slug] = child_cat

        self.stdout.write(self.style.SUCCESS("Catégories Mode & Électronique créées."))

        # 3. Création d'un compte vendeur test
        seller_email = "kadiatou@mode.gn"
        seller_pass = "Vendeur@224@224"
        seller_user = User.objects.filter(email=seller_email).first()
        if not seller_user:
            seller_user = User.objects.create_user(
                email=seller_email,
                password=seller_pass,
                full_name="Kadiatou Camara",
                phone_number="+224621112233",
            )
            self.stdout.write(self.style.SUCCESS(f"Compte Vendeur créé : {seller_email} (mdp: {seller_pass})"))

        # Profil vendeur
        seller_profile = seller_profile_request(user=seller_user)
        if seller_profile.status != SellerProfile.Status.VERIFIED:
            seller_profile_verify(
                profile=seller_profile,
                verified_by=admin_user,
                notes="Vérifié par appel téléphonique. Boutique physique à Madina confirmée.",
            )

        # 4. Création d'une boutique vérifiée
        shop_slug = "kadiatou-bazin-conakry"
        shop = Shop.objects.filter(slug=shop_slug).first()
        if not shop:
            shop = shop_create(
                owner=seller_profile,
                name="Kadiatou Bazin Conakry",
                city="Conakry - Matam",
                address="Marché Madina, Carrefour Avaria, Bloc C",
                whatsapp_number="+224621112233",
                description="Spécialiste du véritable Bazin Riche Getzner teinté et brodé main à Conakry. Tissus haute qualité pour vos cérémonies et fêtes.",
            )
            shop_activate(shop=shop, admin_user=admin_user, notes="Validation de la boutique Kadiatou Bazin.")
            self.stdout.write(self.style.SUCCESS(f"Boutique créée et activée : {shop.name}"))

        # 5. Création d'articles exemples
        robe_cat = Category.objects.filter(slug="robes-bazin-wax").first()
        if robe_cat and not Product.objects.filter(slug="ensemble-bazin-riche-violet-brode").exists():
            prod1 = product_create(
                shop=shop,
                user=seller_user,
                category=robe_cat,
                title="Ensemble Bazin Riche Violet Brodé Or",
                description="Superbe complet 3 pièces en Getzner de premier choix, teinture artisanale violette et broderie fils d'or réalisée par nos maîtres tailleurs.",
                price_gnf=650000,
                condition=Product.Condition.NEW,
                brand="Getzner Original",
                stock=4,
                status=Product.Status.PUBLISHED,
            )
            self.stdout.write(self.style.SUCCESS(f"Article publié : {prod1.title} ({prod1.price_gnf:,} GNF)"))

        # Boutique électronique exemple
        seller_electro_email = "moussa@tech.gn"
        seller_electro_user = User.objects.filter(email=seller_electro_email).first()
        if not seller_electro_user:
            seller_electro_user = User.objects.create_user(
                email=seller_electro_email,
                password="Tech@224@224",
                full_name="Moussa Diallo",
                phone_number="+224622334455",
            )
            electro_profile = seller_profile_request(user=seller_electro_user)
            seller_profile_verify(profile=electro_profile, verified_by=admin_user, notes="Vendeur tech Kaloum.")

            shop_electro = shop_create(
                owner=electro_profile,
                name="Diallo High-Tech",
                city="Conakry - Kaloum",
                address="Avenue de la République, face Trésor Public",
                whatsapp_number="+224622334455",
                description="Vente de smartphones neufs et reconditionnés avec garantie 6 mois. Accessoires d'origine.",
            )
            shop_activate(shop=shop_electro, admin_user=admin_user)

            phone_cat = Category.objects.filter(slug="smartphones-tablettes").first()
            if phone_cat:
                product_create(
                    shop=shop_electro,
                    user=seller_electro_user,
                    category=phone_cat,
                    title="iPhone 13 128 Go Bleu Pacifique",
                    description="iPhone 13 reconditionné état comme neuf, batterie 92%, fourni avec boîte et chargeur rapide.",
                    price_gnf=4800000,
                    condition=Product.Condition.REFURBISHED,
                    brand="Apple",
                    stock=2,
                    status=Product.Status.PUBLISHED,
                )

        self.stdout.write(self.style.SUCCESS("--- Données de test initialisées avec succès ! ---"))

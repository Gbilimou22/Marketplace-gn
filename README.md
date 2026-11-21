# Place de Marché Guinée (Django)

Plateforme web de commerce en ligne pour la Guinée (mode et électronique), centrée sur la confiance, la vérification des boutiques et la sécurisation des remises par code de livraison.

---

## 🚀 Prérequis

- **Python** : 3.12 ou supérieur (3.14 supporté)
- **Git**
- **Docker & Docker Compose** (pour PostgreSQL en local)

---

## 🛠️ Installation et Démarrage rapide

### 1. Cloner le dépôt
```bash
git clone <url-du-depot>
cd Marketplace
```

### 2. Configurer les variables d'environnement
Copiez le fichier `.env.example` vers `.env` :
```bash
cp .env.example .env
```

### 3. Démarrer la base de données PostgreSQL
Lancez l'instance PostgreSQL 16 via Docker Compose :
```bash
docker-compose up -d
```
Le conteneur expose le port `5432` avec les identifiants configurés par défaut dans `.env.example`.

### 4. Créer et activer l'environnement virtuel
Sur Windows (PowerShell) :
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 5. Installer les dépendances
```powershell
pip install -e ".[dev]"
```

### 6. Lancer les vérifications et tests
```powershell
# Vérification du code avec ruff
ruff check .

# Lancement de la suite de tests
pytest
```

---

## 📂 Architecture du Projet

```
Marketplace/
├── config/                  # Configuration Django (settings base, dev, prod)
├── apps/                    # Applications modulaires du monolithe
│   ├── core/                # Modèles de base (UUID, Timestamps), utilitaires
│   ├── accounts/            # Authentification, profils vendeurs
│   ├── shops/               # Gestion des boutiques
│   ├── catalog/             # Articles, catégories, photos WebP
│   ├── orders/              # Commandes, transitions d'état, codes de livraison
│   ├── reviews/             # Avis certifiés, réputation bayésienne
│   └── moderation/          # Signalements, journal d'audit
├── docs/                    # Décisions d'architecture (ADR)
├── templates/               # Gabarits Django (HTML + HTMX)
├── static/                  # Feuilles de style légères et assets
├── tests/                   # Suite de tests automatisés (pytest-django)
├── AGENTS.md                # Standards de code et règles non négociables
└── pyproject.toml           # Dépendances et configuration d'outils
```

---

## 🔒 Principes Clés

- **Devise** : Franc Guinéen (GNF), montants entiers stricts.
- **Fuseau horaire** : `Africa/Conakry` (UTC).
- **Sécurité** : UUID publics, requêtes systématiquement scopées par propriétaire, hachage des codes de livraison, pas de stockage de pièces d'identité.

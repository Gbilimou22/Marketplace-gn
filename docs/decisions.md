# Architecture Decision Records (ADR)

Ce document consigne les décisions d'architecture structurantes prises pour la plateforme Place de Marché Guinée.

---

## ADR 001 : Choix du socle technique (Monolithe Django modulaire, PostgreSQL, HTMX)

- **Date** : 2026-11-21
- **Statut** : Accepté

### Contexte
Le projet est une place de marché e-commerce (B2C/C2C) pour la Guinée, développée par un ingénieur solo avec un budget initial très contraint et un premier pilote dans ~2 mois avec 5 à 10 vendeurs. Les utilisateurs accèdent au site principalement depuis des smartphones sur des réseaux mobiles 3G/4G instables avec une tarification au volume de données.

### Décision
Nous retenons :
1. **Monolithe Django modulaire** :
   - Django LTS (5.1) et Python 3.12+ (Python 3.14 installé sur l'environnement de développement).
   - Découpage strict des applications (`accounts`, `shops`, `catalog`, `orders`, `reviews`, `moderation`, `core`).
   - Séparation interne des responsabilités : `services.py` (logique métier & mutations), `selectors.py` (lectures complexes & requêtes optimisées), `views.py` (HTTP & formulaires fins).
2. **PostgreSQL** :
   - Gestion native de la recherche plein texte (`SearchVector`), intégrité transactionnelle stricte.
   - Conteneurisé via Docker Compose pour le développement local.
3. **Templates Django + HTMX** :
   - Aucune étape de build JavaScript complexe (pas de Node.js, Webpack, ni Vite).
   - Poids des pages minimal pour respecter le budget data des acheteurs guinéens.
4. **Pas de file de tâches asynchrone (Celery/Redis) au MVP** :
   - Les calculs périodiques (score bayésien, agrégations) seront exécutés via des commandes Django (`manage.py`) orchestrées par des crons système.

### Alternatives écartées
- *Frontend découplé (React / Next.js) + Django REST Framework* :
  - Rejeté pour surcoût cognitif, complexité de synchronisation, et bundles JavaScript trop lourds pour les connexions mobiles guinéennes.
- *Microservices* :
  - Rejeté pour complexité opérationnelle disproportionnée pour un MVP solo.
- *Redis / Celery dès le départ* :
  - Rejeté pour éviter des coûts d'infrastructure et une charge de maintenance supplémentaire alors que le volume du pilote (5-10 vendeurs) ne le justifie pas.

### Conséquences et compromis
- **Avantages** : Déploiement ultra-simple sur un petit VPS (< 10 $/mois), réactivité de développement maximale, traçabilité des règles métier dans `services.py`.
- **Compromis** : Les calculs longs doivent être évités dans le cycle requête/réponse HTTP direct. L'orchestration par cron sera remplacée par une vraie file de messages lorsque le volume l'exigera.

---

## ADR 002 : Modèle User personnalisé UUID, authentification par email et profil SellerProfile

- **Date** : 2026-11-21
- **Statut** : Accepté

### Contexte
La plateforme nécessite une gestion des utilisateurs centrée sur l'e-mail (sans champ pseudo/username) et un modèle de rôle vendeur soumis à un contrôle strict. En Django, la déclaration de `AUTH_USER_MODEL` doit être effectuée avant la toute première migration pour éviter les problèmes de clés étrangères figées sur `auth.User`. De plus, la base de données PostgreSQL 18 locale (port 5433) est retenue pour le développement et la production.

### Décision
1. **Modèle `User` personnalisé** :
   - Clé primaire en UUID v4 (`UUIDModel`) pour rendre les identifiants publics non devinables.
   - `email` unique servant d'identifiant de connexion, normalisé en minuscules.
   - Normalisation stricte des numéros guinéens (+224 / 9 chiffres commençant par 6).
   - Intégration de `django-allauth` avec `ACCOUNT_LOGIN_METHODS = {'email'}`.
2. **Modèle `SellerProfile` distinct (OneToOne)** :
   - Statut à choix stricts : `pending`, `verified`, `suspended`.
   - Traçabilité de la vérification manuelle : `verified_by` (administrateur), `verified_at`, et `internal_notes`.
   - **Règle non négociable** : Aucune pièce d'identité n'est stockée en base de données.
3. **Couche de services et sélecteurs** :
   - Toute création d'utilisateur, demande de statut vendeur, vérification ou suspension transite exclusivement par `apps/accounts/services.py`.
   - Les requêtes de lecture complexes et filtrées sont centralisées dans `apps/accounts/selectors.py`.

### Conséquences et compromis
- **Avantages** : Zéro dette technique sur le modèle User ; sécurité dès la racine ; étanchéité entre compte acheteur simple et statut vendeur vérifié.
- **Compromis** : Nécessite une rigueur constante pour ne jamais contourner les services lors des transitions de statut.

---

## ADR 003 : Modèle Shop, validation administrative manuelle et canal direct WhatsApp (wa.me)

- **Date** : 2026-11-22
- **Statut** : Accepté

### Contexte
La boutique (`Shop`) est le pivot de la place de marché guinéenne. Les vendeurs habituels vendent sur les réseaux sociaux (WhatsApp, Facebook) ou dans les marchés physiques (Madina, etc.). Pour instaurer la confiance et respecter les contraintes de budget et de données mobiles en Guinée :
1. Une boutique ne doit pas être visible publiquement tant qu'elle n'a pas été inspectée et approuvée manuellement par l'administrateur.
2. Le contact doit être direct et sans coût d'API payante (Twilio, Meta WhatsApp Cloud API).

### Décision
1. **Cycle de vie de la boutique (`Shop.status`)** :
   - `DRAFT` : la boutique est créée par le vendeur, visible uniquement par lui-même.
   - `PENDING_REVIEW` : le vendeur soumet sa boutique pour vérification administrative.
   - `ACTIVE` : seul un administrateur (`is_staff`) peut activer la boutique après vérification. Cette activation valide automatiquement le profil vendeur (`SellerProfile`) s'il était en attente.
   - `SUSPENDED` : suspension immédiate par l'administrateur en cas de manquement.
2. **Canal de contact WhatsApp direct sans frais** :
   - Génération dynamique de liens standard `https://wa.me/224XXXXXXXX?text=...` pré-remplis avec encodage URL.
   - Zéro dépendance à une API tierce payante de messagerie.
3. **Contrôle d'accès et isolation des données** :
   - Les vues publiques (`ShopListView`, `ShopDetailView`) ne servent que les boutiques actives aux visiteurs anonymes.
   - Les propriétaires et administrateurs peuvent prévisualiser les boutiques non actives.
   - Les modifications (`shop_update`) imposent une vérification d'appartenance stricte (`shop.owner.user == request.user`).

### Conséquences et compromis
- **Avantages** : Aucun coût d'API pour les échanges vendeur/acheteur, protection absolue des acheteurs contre les boutiques frauduleuses grâce à la modération humaine.
- **Compromis** : Le volume d'activation dépend de la disponibilité de l'administrateur pour passer les appels ou vidéos de validation.

---

## ADR 004 : Catalogue de produits, pipeline WebP avec Pillow et recherche plein texte PostgreSQL

- **Date** : 2026-11-22
- **Statut** : Accepté

### Contexte
Le catalogue de mode et d'électronique en Guinée doit répondre à trois contraintes majeures :
1. Les acheteurs naviguent depuis des smartphones avec des connexions 3G/4G lentes et une tarification au Mo.
2. Les commerçants téléversent des photos directement depuis leurs smartphones, qui contiennent souvent des métadonnées de géolocalisation GPS privées et des résolutions démesurées (10 à 15 Mo).
3. Le moteur de recherche doit permettre de retrouver rapidement des articles par marque, modèle ou description sans recourir à un service tiers payant (comme Algolia ou Elasticsearch).

### Décision
1. **Modèles `Category`, `Product` et `ProductImage`** :
   - Catégories arborescentes (Mode, Électronique et sous-catégories) avec `on_delete=PROTECT` pour empêcher la destruction accidentelle d'articles.
   - Prix obligatoirement entiers en Francs Guinéens (`PositiveBigIntegerField`, minimum 1 GNF, pas de centimes).
   - États d'articles standardisés : `Neuf`, `Occasion`, `Reconditionné`.
   - Limite stricte de **8 photos par produit**.
2. **Pipeline d'optimisation d'images Pillow** :
   - Vérification du type MIME réel à l'ouverture du fichier (rejet strict des faux fichiers).
   - Suppression intégrale des métadonnées EXIF (anonymisation GPS complète).
   - Redimensionnement automatique si la dimension excède 1600 px (protection contre les bombes de décompression).
   - Compression et conversion en WebP natif (qualité 80), allégeant les fichiers de 70 à 90%.
3. **Recherche plein texte native PostgreSQL (`django.contrib.postgres`)** :
   - Utilisation de `SearchVector` pondéré sur le titre (A), la marque (B) et la description (C).
   - Filtres combinés (catégorie et enfants, ville de la boutique, état, fourchette de prix min/max).
4. **Lien de commande WhatsApp direct** :
   - Chaque fiche article génère automatiquement un lien `wa.me` pré-rempli avec le nom de l'article, son prix en GNF et le nom de la boutique.

### Conséquences et compromis
- **Avantages** : Préservation maximale du forfait internet des utilisateurs, respect absolu de la vie privée des vendeurs, rapidité de recherche sans coût d'infrastructure supplémentaire.
- **Compromis** : L'encodage WebP synchrone par Pillow consomme un peu de CPU à l'upload mais reste parfaitement adapté aux volumes d'une phase pilote solo.

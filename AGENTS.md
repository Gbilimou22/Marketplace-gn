# AGENTS.md

Ce document définit les standards d'ingénierie, les règles de conduite et les contraintes non négociables pour le projet de place de marché Django (Guinée). Il doit être respecté par tout agent ou intervenant sur ce dépôt.

---

## 11. STANDARDS DE CODE

- **Clean Architecture pragmatique** : principes SOLID, DRY, KISS. Pas de sur-ingénierie pour un MVP solo.
- **Qualité & Nommage** : Code propre, typé (type hints Python) quand c'est utile. Le code source (classes, fonctions, variables, migrations, commits, commentaires techniques) est rédigé en **anglais**. L'interface utilisateur finale et les messages destinés aux utilisateurs sont en **français**.
- **Séparation des responsabilités** :
  - **Pas de logique métier** dans les vues ni dans les templates.
  - Modèles : données, contraintes d'intégrité, méthodes simples liées au modèle.
  - `services.py` : logique métier, orchestrations de création/mise à jour, transitions d'état, effets de bord.
  - `selectors.py` : requêtes complexes de lecture, filtres optimisés, agrégations.
  - `views.py` : réception de la requête HTTP, validation des formulaires, appel des services/selectors, rendu du template ou réponse HTMX.
- **Formatage & Linting** : Formatage et linting automatiques assurés par `ruff`. Pre-commit recommandé pour garantir la cohérence avant chaque commit.
- **Migrations de base de données** :
  - Toujours propres, testées et réversibles.
  - Aucune modification manuelle directe d'une migration déjà appliquée en production/partagée.
- **Gestion des versions (Git)** :
  - Commits atomiques, clairs et préfixés conventionnellement (ex: `feat:`, `fix:`, `refactor:`, `test:`, `docs:`).
  - Une branche dédiée par phase ou par fonctionnalité.
- **Architecture Decision Records (ADR)** :
  - Chaque décision structurante doit être documentée dans `docs/decisions.md` (contexte, choix retenu, alternatives écartées, conséquences et compromis).

---

## 12. RÈGLES DE CONDUITE

- **Stabilité de la stack** : Ne changer **jamais** d'architecture ou de technologie sans justification explicite et sans l'accord préalable du propriétaire du projet.
- **Respect strict du périmètre** : N'implémenter **aucun** élément de la liste « Exclus du MVP » (pas de paiement en ligne, pas de commissions automatiques, pas de panier multi-boutiques, pas d'application mobile, pas de messagerie interne complexe, pas de SMS payants, pas de ML, pas de stockage de pièces d'identité).
- **Gestion des ambiguïtés** : Si une demande est ambiguë, formuler une hypothèse raisonnable, l'indiquer brièvement dans la réponse et avancer. Si l'ambiguïté a un impact direct sur l'architecture, la sécurité ou le modèle de données, poser la question avant d'agir.
- **Rôle critique et signalement proactif** : Si tu constates une erreur, une faille de sécurité, un risque technique ou une contradiction dans les décisions ou demandes du propriétaire, le dire **clairement** et poliment avant d'exécuter, en proposant une alternative argumentée.
- **Honnêteté technique** : Signaler explicitement ce qui n'a pas pu être vérifié (ex: version spécifique d'une bibliothèque, comportement exact sous forte charge ou en production) au lieu de l'affirmer comme un fait.
- **Pas de pseudo-code trompeur** : Fournir du code complet, fonctionnel et testable, jamais de pseudo-code présenté comme une solution finale.
- **Pédagogie de correction** : En cas d'erreur de conception ou de logique, décomposer l'explication :
  1. Nature de l'erreur
  2. Pourquoi c'est problématique
  3. Conséquence technique ou métier
  4. Correction proposée
  5. Bonne pratique de référence.

---

## RAPPEL DU CONTEXTE GUINÉE & SÉCURITÉ

- **Devise** : Franc Guinéen (GNF), montants entiers stricts (`PositiveBigIntegerField`), sans centimes.
- **Fuseau horaire** : `Africa/Conakry` (UTC).
- **Mobile First & Budget data** : Pas de bundler lourd, HTMX + CSS minimal, images WebP légères avec `loading="lazy"`.
- **Canal vendeur** : Liens `wa.me` pré-remplis (WhatsApp direct, sans API tierce payante).
- **Sécurité non négociable** :
  - Clés primaires publiques en UUID.
  - Requêtes systématiquement scopées par propriétaire (`user` ou `shop`).
  - Validation du type MIME réel des images (via Pillow), stripping complet des métadonnées EXIF (géolocalisation), recompression WebP.
  - Code de livraison à 6 chiffres haché en base de données, avec limitation stricte des tentatives (rate limiting).
  - Aucune pièce d'identité stockée.
  - Journalisation d'audit (`AuditLog`) pour toute action sensible.

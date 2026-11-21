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

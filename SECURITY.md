# Politique de sécurité

## Signaler une vulnérabilité

**Ne créez pas d'issue publique** pour une faille de sécurité.

Utilisez le canal privé **GitHub Security Advisories** :
[Security → Report a vulnerability](https://github.com/mlabarrere/Idefix/security/advisories/new).

Merci d'inclure : description, impact, étapes de reproduction et, si possible, un correctif proposé.
Réponse initiale visée sous **72 h** ; nous vous tiendrons informé de la remédiation.

## Périmètre

Idéfix traite des données de canaux Telegram publics dans un contexte institutionnel/OPSEC. Sont
particulièrement critiques :

- **Fuite de secret** (clés Supabase/Telegram/Mistral, session-strings) — priorité maximale.
- Exposition de données personnelles au-delà de ce qui est documenté (base légale RGPD dans les
  migrations Alembic).
- Contournement du scrub de secrets à l'export.

## Secrets — règles

- `.env*` est gitignoré (sauf `.env.example`). Ne committez jamais de vraie clé.
- Un hook `detect-private-key` (pre-commit) et le test `tests/test_export_secret_scrub.py`
  servent de filet.
- En cas de secret commité par erreur : **révoquez/roter la clé immédiatement**, puis retirez-la
  du suivi et de l'historique (`git filter-repo`).

## Versions supportées

Projet en phase PoC : seule la branche `main` est maintenue. Aucune garantie de support sur les
tags antérieurs.

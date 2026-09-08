# Contrat de donnees analytique — Idéfix

Ce document fixe le langage commun entre scoring, dossiers de preuve, export
statique, validation et webapp. Les modeles executables vivent dans
`src/shared/analytical_contract.py`.

## Principe

Idéfix ne produit pas un verdict automatique. Il produit des objets analytiques
auditables : claims, episodes, preuves de message, arêtes de coordination,
poches, runs de score et dossiers. Chaque objet doit porter sa mission, sa
fenêtre temporelle quand elle existe, sa méthode, ses limites et ses versions.

## Objets canoniques

| Objet | Rôle | Statut |
|---|---|---|
| `ClaimRecord` | Revendication canonique issue du registry. | Lot 1 actif |
| `ClaimVariant` | Variante linguistique ou semantique d'un claim. | Lot 1 actif |
| `EpisodeRecord` | Episode suivi : un ou plusieurs claims sur une fenêtre. | Lot 1 actif |
| `MessageEvidence` | Preuve message-level rattachable a claim, edge, poche ou dossier. | Lot 1 actif |
| `CoordinationEdgeEvidence` | Relation coordonnée entre deux canaux avec méthode, seuil et score. | Lot 1 actif |
| `ChannelRoleEvidence` | Rôle de canal et preuves associées. | Lot 1 actif |
| `PocketRecord` | Poche informationnelle mesurable sur une fenêtre. | Lot 1 actif |
| `ScoreRunRecord` | Enveloppe d'un run de scoring mission-scopé. | Lot 1 actif |
| `CoverageLimit` | Limite d'observation déclarée. | Lot 1 actif |
| `MethodVersion` | Versions nécessaires a la reproductibilité. | Lot 1 actif |

## Registry claims v0

Le fichier historique `data/claims/claims_fr.jsonl` reste la seed registry du PoC.
Il est normalisé par `src/registry/claims.py` vers `ClaimRecord`. Cette étape ne
branche pas encore `claim_proximity` dans le scoring ; elle stabilise le format
qui permettra de le faire proprement au lot suivant.

## Contraintes

- `AttributionTier` est limité à `T1` / `T2`.
- `ClaimRecord.claim_id` et `canonical_text` sont obligatoires.
- `PocketRecord` doit contenir au moins un canal.
- Les scores bornés sont dans `[0,1]`.
- Les arêtes de coordination doivent déclarer une méthode.
- Les outputs doivent porter `methodology_version_hash` au minimum, puis les
  versions scorer/edge-builder/claim-matcher quand disponibles.

## Prochain raccordement

Le Lot 2 devra brancher ce contrat sur :

1. la table PostgreSQL `episodes` ;
2. le calcul `claim_proximity` ;
3. l'export statique `episodes/` ;
4. `Evidence Dossier v1` ;
5. la validation externe.


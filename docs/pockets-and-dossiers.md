# Poches informationnelles et dossiers v1

Ce document décrit le début du Lot 4 : rendre les poches mesurables et préparer
un dossier de preuve v1 fondé sur le contrat analytique.

## Pocket score

Le score de poche est calculé par `src/pockets/scoring.py`. Il combine des
signaux bornés dans `[0,1]` :

| Signal | Poids | Sens |
|---|---:|---|
| `claim_exposure` | 0.25 | Exposition à des claims documentés. |
| `coordination_density` | 0.25 | Densité interne de coordination. |
| `bridge_presence` | 0.15 | Présence de canaux ponts. |
| `recidivism` | 0.15 | Récurrence multi-épisodes. |
| `stability` | 0.10 | Persistance temporelle. |
| `volume` | 0.10 | Volume observé. |

`coverage` est un multiplicateur : il ne peut que réduire le score si la
couverture est dégradée.

## Typologie

`infer_pocket_type` classe une poche en :

- `diffusion`
- `coordination`
- `bridging`
- `recidivism`
- `mixed`

Quand plusieurs signaux dominants sont proches, la poche est `mixed`.

## Dossier v1

Le dossier v1 vit dans `src/dossier/v1.py`. Il assemble :

- `EpisodeRecord`
- `ScoreRunRecord`
- `ChannelRoleEvidence`
- `PocketRecord`
- `CoordinationEdgeEvidence`
- `MessageEvidence`
- `CoverageLimit`
- `MethodVersion`

Le dossier v1 garde les contraintes institutionnelles : T1/T2 seulement,
coverage callout obligatoire, versions méthodologiques traçables.

## Exemple depuis bundle statique

`scripts/build_dossier_v1_example.py` génère un dossier `EvidenceDossierV1` depuis
un bundle déjà exporté sous `webapp/public/data/<mission>/`, sans base PostgreSQL
et sans appel Telegram.

Commandes :

```powershell
.\.venv\Scripts\python.exe scripts\build_dossier_v1_example.py --mission russosphere
.\.venv\Scripts\python.exe scripts\build_dossier_v1_example.py --mission gan
```

Sorties locales régénérables, non versionnées :

- `data/dossiers/evidence_dossier_v1_russosphere_example.json`
- `data/dossiers/evidence_dossier_v1_gan_example.json`

Ces dossiers sont des exemples de structure de preuve. Ils ne remplacent pas une
revue analyste et ne constituent pas un verdict opérationnel.

## Raccords restants

Le Lot 4 n'est pas terminé tant que :

1. les scripts communautaires ne produisent pas encore des `PocketRecord` réels ;
2. `export_static.py` n'exporte pas encore `pockets/` ;
3. la webapp n'affiche pas encore une vue de poche ;
4. `EvidenceDossierV1` n'est pas encore le dossier principal de l'export, même si
   des exemples peuvent maintenant être générés depuis les bundles statiques.

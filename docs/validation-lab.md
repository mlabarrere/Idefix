# Validation Lab — gold externe et corpus organique

Le Validation Lab ferme deux faiblesses connues de `docs/validation-state.md` :

1. la circularite du test de recuperation d'episode connu ;
2. l'absence de corpus organique francais pour mesurer les faux positifs.

Les schemas executables vivent dans `src/validation_lab/schema.py`.

## Gold episode externe

Un gold episode externe est un fichier JSON conforme a
`ExternalGoldEpisode`. Il doit documenter :

- une provenance externe ;
- une phrase d'independance expliquant que la liste n'est pas issue des scores
  Idéfix ni des allowlists du scorer ;
- au moins un canal `seed` ;
- des canaux identifies par `username` ou `channel_id` ;
- une confidence et une reference source par canal.

Template : `data/eval/templates/gold_episode.example.json`.

Les vrais fichiers utilisables par `scripts/eval_episode_recovery.py` doivent
être places sous `data/eval/` avec le nom `gold_episode_<nom>.json`. Les templates
restent dans `data/eval/templates/` pour ne pas être consommes comme gold reels.

## Corpus organique

Un corpus organique est un fichier JSON conforme a `OrganicControlCorpus`.
Il contient des groupes coordonnes non hostiles : médias, institutions,
militantisme, sport, événements civils ou autre catégorie documentée.

Template : `data/eval/templates/organic_control_corpus.example.json`.

Chaque groupe doit contenir au moins deux canaux et une rationale expliquant
pourquoi la coordination est attendue ou organique.

Les vrais fichiers utilisables par `scripts/eval_organic_control.py` doivent
être places sous `data/eval/` avec le nom `organic_control_<nom>.json`. Le script
calcule combien de canaux organiques documentes remontent dans le top suspicion
et declenche une alarme de faux positif si :

- au moins trois canaux organiques apparaissent dans le top 50 ;
- ou au moins deux canaux du même groupe organique apparaissent dans le top 50.

Si aucun corpus reel n'est present, le script ecrit un rapport non probant
`data/eval/organic_control.json` au lieu d'inventer un verdict.

## Garde-fous

- Un gold episode avec `excluded_from_scorer_inputs=false` est invalide.
- Un gold episode sans canal `seed` est invalide.
- Un canal sans `username` ni `channel_id` est invalide.
- Un corpus organique sans groupe est invalide.
- Un groupe organique avec un seul canal est invalide.

## Prochain raccordement

Le raccordement actuel :

- `scripts/eval_episode_recovery.py` lit les fichiers `gold_episode_*.json` au
  format `ExternalGoldEpisode` v1, avec fallback sur l'ancien format `{episode,
  seeds, relays}`.
- `scripts/eval_organic_control.py` lit les fichiers `organic_control_*.json` au
  format `OrganicControlCorpus` v1 et publie `organic_control.json`.

Le prochain incrément doit :

1. produire au moins un corpus organique reel ;
2. publier `docs/validation-state.md` v2 avec les nouveaux verdicts.

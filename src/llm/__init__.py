"""Piste LLM parallèle d'Idéfix (Mistral) — classification haut-niveau.

LOAD-BEARING : ce package est une PISTE PARALLÈLE. Il ne modifie jamais le score
de suspicion explicable (``src/scorer/channel_suspicion.py``), ni le bundle
``russosphere`` par défaut. Ses sorties vivent dans la table ``channel_llm_scores``
et des snapshots ``*_llm_snapshot.json`` dédiés, pour permettre la MESURE de
« Mistral seul » vs le baseline lexical (taxonomie regex × IDF).

Dépendance ``httpx`` confinée à l'extra optionnel ``llm`` (``uv sync --extra llm``)
et importée en LAZY dans ``mistral`` : importer ce package n'exige pas l'extra, et
le chemin export/golden par défaut n'embarque aucun code LLM.
"""

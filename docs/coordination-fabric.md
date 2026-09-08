# Coordination Fabric

La Coordination Fabric centralise les familles d'aretes de coordination, leurs
statuts, methodes, seuils et preuves attendues. Le registre executable vit dans
`src/coordination_fabric/config.py`.

## Signaux actifs

| Edge | Methode | Fenêtre |
|---|---|---|
| `CO_FORWARD` | Même origine forwardée dans la fenêtre. | 72 h |
| `CO_URL` | Même domaine registrable cité dans la fenêtre. | 72 h |
| `CO_URL_EXACT` | Même URL complète citée dans la fenêtre. | 72 h |
| `CO_HASHTAG` | Même hashtag cité dans la fenêtre. | 72 h |

Ces signaux sont déjà matérialisés par `src/graph/edges.py`.

## Signaux réservés

| Edge | Seuil graine | Condition d'activation |
|---|---:|---|
| `COPYPASTA` | 0.693 | Calibration D3lta ou équivalent sur corpus annoté. |
| `TEXT_SIM` | 0.715 | Backend embeddings et seuils validés. |
| `TRANSLATION` | 0.85 | Similarité cross-lingue calibrée. |
| `MEDIA_REUSE` | N/A | `media_hash` alimenté réellement. |

## Règle produit

Un seul signal de coordination reste faible. La coordination devient probante
quand plusieurs familles indépendantes convergent dans une même fenêtre, puis
quand les faux positifs organiques sont mesurés par le Validation Lab.


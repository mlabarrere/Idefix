# Gates des capacités avancées

Les capacités B9 sont conditionnelles. Elles ne doivent pas entrer dans le chemin
production tant que leurs données, seuils, limites et besoin sponsor ne sont pas
explicites.

Le gate exécutable vit dans `src/readiness/advanced_capabilities.py`.

## Capacités couvertes

| Capacité | Décision par défaut | Conditions minimales |
|---|---|---|
| `media_reuse` | Bloquée | `media_hash` alimenté, edges non vides, seuil documenté, contrôle organique, besoin sponsor confirmé. |
| `genai_origin_probability` | Bloquée | Détecteur choisi, limites OOD documentées, calibration disponible, faux positifs revus, besoin sponsor confirmé. |
| `gnn_misinfotelegraph_fr` | Bloquée | Gold set disponible, labels équilibrés, volume suffisant, baseline dépassée, explicabilité documentée, besoin sponsor confirmé. |
| `stix_serializer` | Bloquée | Chaîne CSIRT confirmée, mapping documenté, marquage TLP défini, consommateur validé, besoin sponsor confirmé. |

## Utilité

Ce gate évite qu'une capacité techniquement séduisante devienne une promesse
produit non défendable.

Exemples :

- sur l'infosphère France/Ukraine, un GNN ne doit pas remplacer le score
  explicable tant qu'il n'a pas de gold set channel-level équilibré ;
- sur le GAN / Charles de Gaulle, `MEDIA_REUSE` ne doit être activé que si les
  hashes médias sont réellement alimentés et produisent des edges vérifiables ;
- STIX reste conditionnel à une chaîne CSIRT sponsor qui consomme effectivement
  ce format.

## Statut

Au 2026-06-15, ces capacités restent **hors chemin critique**. Le module de gate
permet de rendre leur activation testable sans les activer.

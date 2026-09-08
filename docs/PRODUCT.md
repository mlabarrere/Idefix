# Idéfix — Documentation produit

## Ce qu'est Idéfix

Idéfix est un **système d'analyse de propagation et de coordination sur Telegram**. Il cartographie la façon dont une information se diffuse dans des réseaux de canaux publics, identifie les canaux qui jouent un rôle structurel dans cette diffusion, et produit des dossiers classés et explicables pour des analystes humains.

**Idéfix n'est pas un détecteur de fausses informations.** Il ne juge jamais la véracité d'un message. Il décrit des *structures observables* — qui forward quoi, à quelle vitesse, en coordination avec qui — et ne prononce jamais de verdict.

---

## Le problème

La désinformation coordonnée sur Telegram suit des schémas structurels identifiables :
- Un petit nombre de canaux *d'amorçage* injectent un narratif
- Des relayeurs coordonnés le repropagent dans plusieurs communautés simultanément
- La même infrastructure réapparaît épisode après épisode

Ces schémas sont **observables** dans le graphe de forwards publics, sans avoir besoin d'analyser le contenu ou de connaître les intentions des auteurs. L'analyse manuelle de milliers de canaux est impossible. Idéfix l'automatise.

---

## Ce qu'Idéfix produit

### Une file d'examen priorisée

Chaque canal analysé reçoit un **score de suspicion** composé de familles de signaux indépendants :

| Famille | Signal |
|---|---|
| **(b) Rôle en cascade** | Position structurelle dans le graphe de forwards (hub, pont inter-communautés, source d'amorçage) |
| **(c) Coordination** | Co-forwarding temporellement fenêtré, quasi-doublons de texte, co-citation de domaines |
| **(d) Récidive** | Réapparition du canal d'amorçage dans plusieurs épisodes distincts |
| **(f) Cohérence sémantique** | Distance au corpus français organique + proximité aux canaux adverses connus |

**Règle multi-source :** un canal ne franchit le seuil de signalement que si **au moins 2 familles distinctes** sont déclenchées. Un signal isolé est insuffisant par construction.

### Des dossiers d'épisode explicables

Pour chaque épisode de propagation détecté, Idéfix produit un dossier contenant :
- Les canaux impliqués avec leur score décomposé (contribution de chaque famille, poids, valeur)
- La chronologie de propagation avec vélocités réelles
- La traçabilité vers des sources structurelles vérifiables
- Le niveau de tier déclaré (T1 / T2) et son justificatif

### Une galaxie de communautés interactive

L'interface analyste affiche :
- Les **communautés** du réseau comme des nébuleuses (détection Leiden)
- Les **ponts** entre communautés (betweenness centrality)
- Les **scénarios narratifs** datés par phases, reconstructibles depuis les données
- Le score explicable de chaque canal au clic (5 familles + définitions)

---

## Ce qu'Idéfix ne fait pas

| Hors périmètre | Raison |
|---|---|
| Vérifier si un message est vrai ou faux | Hors périmètre — analyse structurelle uniquement |
| Observer des plateformes autres que Telegram | Couverture Telegram uniquement (limite déclarée dans chaque export) |
| Attribuer à un commanditaire (T3) | Franchit la frontière de l'enquête — hors périmètre |
| Agir sur les plateformes (signalement, suppression) | Arm-only — les sorties vont aux destinataires institutionnels |
| Analyser les messages privés ou les groupes fermés | MTProto lecture seule, canaux publics uniquement |
| Désanonymiser des membres | Non collecté — seules les métadonnées de canaux publics |

---

## Architecture en deux moitiés

```
PIPELINE HORS-LIGNE (Python)
  Collecte MTProto → Normalisation → Graphe d'arêtes → Scores → Export JSON
           ↓
INTERFACE ANALYSTE (React, statique)
  Lecture des bundles JSON → Galaxie → Dossiers → Zéro backend pendant la consultation
```

Les deux moitiés sont **strictement disjointes** : la webapp ne touche jamais la base de données et ne fait jamais d'appel Telegram. Elle lit uniquement des fichiers JSON pré-calculés. Un analyste peut consulter une mission sans que la collecte soit active.

---

## Missions

Le moteur est **thématiquement neutre**. La configuration d'une mission (univers de sources, lexique, pondérations, tableau de bord) est un fichier de paramètres, jamais un fork du code.

| Mission | Objet | Statut |
|---|---|---|
| `russosphere` | Désinformation coordonnée visant l'image, l'intégrité ou la souveraineté de la France | Active |
| `france_ukraine` | Narratifs russophones visant la France dans le contexte Ukraine | Active |
| `gan` | Empreinte informationnelle du groupe aéronaval (objectif OPSEC) | Données à venir |
| `dircom_minarm` | Transformation/déformation des messages officiels DIRCOM MinArm | Planifiée |

---

## Niveaux de tier

| Tier | Définition |
|---|---|
| **T1** | Comportement structurel suspect (score élevé, ≥ 2 familles déclenchées) |
| **T2** | T1 + récidive documentée inter-épisodes |
| **T3** | Attribution à un commanditaire du monde réel — **hors périmètre** |

Un canal T3 (attribution) constitue un défaut signalable. Idéfix produit des T1/T2 uniquement.

---

## Gouvernance et limites

### Limitation fondamentale (déclarée dans chaque export)

> **Telegram uniquement.** Une opération atteignant la France principalement via d'autres plateformes, sans étape Telegram, **ne sera pas détectée.** Ce qui est mesuré est une empreinte observable sur Telegram, jamais l'empreinte totale d'un phénomène.

Cette limite est un champ obligatoire de chaque bundle exporté. Elle est affichée en permanence dans l'interface analyste.

### Arm-only

Les sorties vont aux destinataires institutionnels désignés. Le système n'exécute jamais d'action sur les plateformes et ne publie jamais d'attribution lui-même.

### Collecte respectueuse des ToS

- Canaux publics uniquement
- Un seul compte dédié, sérialisé (jamais parallélisé)
- Discipline FLOOD_WAIT stricte
- Les identifiants de membres ne sont pas collectés
- Les secrets sont expurgés (clé par clé et valeur par valeur) de chaque export

### Spécification scientifique préalable

La méthodologie complète est publiée dans [`METHODOLOGY.md`](../METHODOLOGY.md) avec obligation de précédence (EIP-resistance) : le document doit être public **avant** toute sortie de détection en production.

---

## Pour aller plus loin

- **Installer** : [`docs/INSTALL.md`](./INSTALL.md)
- **Démarrage rapide** : [`docs/QUICKSTART.md`](./QUICKSTART.md)
- **Spécification scientifique** : [`METHODOLOGY.md`](../METHODOLOGY.md)
- **Pipeline de scripts** : [`scripts/README.md`](../scripts/README.md)
- **Contribuer** : [`CONTRIBUTING.md`](../CONTRIBUTING.md)

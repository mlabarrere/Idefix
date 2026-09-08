# Glossaire — Idéfix

Vocabulaire de référence pour tous les livrables (PRD, architecture, stories, dossiers). À aligner avec VIGINUM / EEAS / OSCE — pas « fake news ».

> **2026-05-26 — projet re-scopé Telegram-only** (X abandonné, paywall API). Les primitives ci-dessous ont été reconverties : *cascade retweet multi-saut → chaîne de forwards profondeur-1 + chaînes inter-canaux sur fenêtres multi-jours* ; *compte → canal* ; *Community Notes retiré*. Voir [`../_bmad-output/planning-artifacts/scope-change-telegram-only-2026-05-26.md`](../_bmad-output/planning-artifacts/scope-change-telegram-only-2026-05-26.md).

---

## Concepts d'analyse

**Épisode (de revendication)** — unité d'analyse fondamentale du système. Une revendication documentée + ses variants sémantiques tracés dans le temps. Le système ne cherche jamais « la fausseté en général » — seulement des familles de revendications documentées et leurs variants.

**Chaîne de forwards** *(forward chain)* — primitive de propagation Telegram : étoile de **profondeur-1** (chaque forward pointe directement vers le message d'origine) avec délais à queue lourde s'étalant sur des jours. Remplace la cascade retweet de l'ère X. L'unité analytique est le *fan-out à profondeur 1 depuis un canal-source* + les chaînes de re-forward inter-canaux, observés sur fenêtres multi-jours.

**Cascade** — terme générique conservé pour l'arbre de propagation observé d'une revendication. Sur Telegram, reconstruit à partir des **forwards** (et replies dans les groupes de discussion liés), pas des reposts/quotes X.

**Variant sémantique** — formulation alternative d'une même revendication (paraphrase, traduction, recontextualisation, recadrage d'image). Identifié via matching multilingue (MuMiN + LaBSE).

**Coordination** — convergence de plusieurs signaux comportementaux faibles (texte quasi-identique inter-canaux, co-URL, co-forwarding, sync temporelle multi-jours, réutilisation d'image/vidéo, motifs de mention/admin partagé) à travers un ensemble de canaux, au-delà du hasard. *Aucun signal seul* n'est fiable — c'est l'alignement multiplex qui compte.

**Graphe hétérogène dynamique** — nœuds : *channels, messages, URLs, media, claims*. Arêtes : forward (avec `delay_seconds`), reply, mention, co-share de domaine, similarité de texte au-dessus d'un seuil, réutilisation d'image/vidéo, sync temporelle, co-forwarding inter-canaux. Fenêtré dans le temps (multi-jours) ; communautés recalculées dynamiquement. *L'arête channel↔domaine (sites Pravda/Doppelganger cités par les canaux) est conservée — couche d'infra adverse P2, pas une 2ᵉ plateforme.*

---

## Rôles dans la cascade *(archétypes Telegram)*

**Seeding-source channel** *(canal-source de seeding)* — canal qui origine récurremment un narratif tôt, avant le fan-out. Analog Telegram de l'*initiator* ; cible primaire d'alerte précoce. Rarement = originateur au sens fort.

**Forward-hub** — canal dont le contenu est forwardé largement (fort fan-out à profondeur 1). Le plus visible — pas nécessairement le plus important.

**Cross-channel bridge** *(pont inter-canaux)* — canal qui transporte un narratif d'une communauté de canaux à une autre. **Souvent stratégiquement plus important que le forward-hub à fort volume.** Cible primaire de la cartographie de coordination.

**Reactivator** — canal qui réinjecte périodiquement un narratif ancien dans des conversations fraîches. Indicateur de récidive.

**Superpropagateur** — canal qui apparaît récurremment tôt dans les chaînes de forwards de contenu peu crédible. Identifié par la **forward-influence + récurrence de seeding** (analog Telegram de la métrique *Influence* de DeVerna et al. 2024), pas par nombre d'abonnés.

---

## Métriques

**Forward-influence** — forwards gagnés par du contenu peu crédible. Backbone de la famille de score 5.d (récidive inter-épisodes) ; analog Telegram de la métrique *Influence* (retweets gagnés) de DeVerna, Aiyappa, Pacheco, Bryden & Menczer, *PLOS One* 2024. *Bat le nombre d'abonnés et les heuristiques type Bot Score.*

**Rₜ narratif** — taux de reproduction effectif appliqué à un narratif (analogie épidémiologique). Sur Telegram, estimé sur fenêtres multi-jours ; estimation robuste exige plusieurs fenêtres de comparaison.

**Top-K precision (priority channels)** — des K canaux top-rankés sur un épisode historique, combien apparaissent dans le noyau de seeding/coordination identifié a posteriori. Métrique d'évaluation primaire.

**Gain temporel** *(temporal gain)* — heures/jours par lesquels l'alerte du POC précède l'identification publique par fact-checkers. Valeur ajoutée opérationnelle (capter la phase de *seeding*). *(Community Notes retiré — capteur X-only.)*

---

## Cinq familles de score (P1)

| # | Famille | Définition |
|---|---|---|
| 5.a | **Claim proximity** | Match sémantique à une revendication enregistrée. + sous-flag *authenticité de source vs. authenticité de revendication*. |
| 5.b | **Cascade role** | Classification dans les 4 archétypes Telegram : seeding-source / forward-hub / cross-channel bridge / reactivator. |
| 5.c | **Coordination** | Convergence multiplex de co-actions sur fenêtres multi-jours. |
| 5.d | **Cross-episode recidivism** | Apparition précoce répétée à travers plusieurs épisodes ; opérationalisé via forward-influence + récurrence de seeding. |
| 5.e | **GenAI-origin probability** | Audio cloning + deepfake video + LLM-text fingerprints (cible spécifiquement les modèles CopyCop). |

---

## Tiers d'attribution

| Tier | Nom | Ce qu'on prétend | Posture POC |
|---|---|---|---|
| **T1** | Diffusion observable | Premier canal-source visible, forward-hubs précoces, forme de fan-out | **Livrable primaire** |
| **T2** | Récurrence comportementale | Mêmes comptes / motifs à travers les épisodes | **Livrable secondaire** |
| **T3** | Attribution monde-réel | Une personne, une organisation, un État, un sponsor | **Hors périmètre** — exige preuves hors-plateforme |

Tout livrable qui mélange les tiers est un défaut. Chaque dossier doit déclarer son tier.

---

## Tiers de sévérité (T1–T5)

Échelle d'escalade opérationnelle (P3 CSIRT orchestration) — distincte des tiers d'attribution ci-dessus. Mapping public requis (NFR EIP-resistance). Changement de tier exige corroboration multi-source (≥ 3 signaux indépendants de ≥ 2 familles).

---

## Cadre légal &amp; institutionnel

**VIGINUM** — Service de vigilance et de protection contre les ingérences numériques étrangères. Créé 2021-07-13 sous le SGDSN. ~60 agents. Mandat : détecter et caractériser l'ingérence numérique *étrangère* du débat public français. *Le POC est conçu pour armer VIGINUM.*

**Arcom** — Autorité de régulation de la communication audiovisuelle et numérique. Coordinateur national au titre du DSA pour les plateformes désignées. 2ᵉ point d'atterrissage institutionnel de l'axiom #2.

**SGDSN** — Secrétariat général de la défense et de la sécurité nationale. Tutelle de VIGINUM. Coordination interministérielle.

**FIMI** — *Foreign Information Manipulation and Interference*. Terminologie officielle EEAS/UE. À préférer à « disinformation » dans les livrables stakeholders.

**DSA** — Digital Services Act (UE). Articles porteurs pour le POC : **Art. 36** (mécanisme de crise) et **Art. 40** (accès chercheurs / coordinateur national = Arcom pour la France).

**Loi anti-infox** — Loi du 22 décembre 2018. Procédure judiciaire d'urgence (48 h) pour suspendre la diffusion de fausses informations en période électorale.

**Loi 2024-850** (25 juillet 2024) — Loi visant à prévenir les ingérences étrangères en France. Cadre légal de prévention en complément du dispositif anti-infox.

**CNIL** — Commission nationale de l'informatique et des libertés. Données publiques = données personnelles. Le POC doit documenter base légale, durées de rétention, journal d'accès, règles de minimisation.

**Blackout 44 h** — Silence médiatique imposé par la loi électorale française dans les 44 heures précédant un scrutin. Fenêtre opérationnelle critique pour le POC (mode SOAR dédié pré/pendant/post-blackout). C'est ce qui a défait Macron Leaks 2017.

---

## Frameworks techniques

**DISARM** — taxonomie open-source de TTPs (Tactics, Techniques, Procedures) d'opérations d'influence. Modélisé sur MITRE ATT&amp;CK. *DISARM Red* = côté attaquant ; *DISARM Blue* = côté défense. Le POC émet ses détections en TTP IDs DISARM Red et structure ses playbooks SOAR en DISARM Blue.

**STIX 2.1 / TAXII 2.1** — standards OASIS de sérialisation et transport de cyber-threat-intelligence (juin 2021). Le POC emballe ses preuves en STIX. *Pas d'extension OASIS formelle pour le disinfo/FIMI à ce jour — opportunité de standardisation.*

**TLP** — *Traffic Light Protocol*. Marquage de partage d'information (WHITE/GREEN/AMBER/RED). Tous les packages de preuves du POC sont TLP-marqués.

**Chaîne de custody** — preuve cryptographique de l'intégrité d'une pièce et de la séquence de ses détenteurs. Requis pour les évidences admissibles en procédure judiciaire (loi anti-infox).

**MuMiN** — dataset multilingue de matching de revendications (arxiv 2202.11684 ; SIGIR 2022). 21,5 M tweets, 12 914 revendications fact-checkées, 41 langues incluant le français. Brique du sous-système P1.a.

**LaBSE** — *Language-agnostic BERT Sentence Embeddings*. Embeddings utilisés par MuMiN pour le matching multilingue.

**MAVOS-DD** — premier benchmark open-set multilingue audio-vidéo de détection de deepfake (arxiv 2505.11109, 2025). 8 langues, 250+ heures. Base du sous-système P1.e. *SOTA dégrade sur générateurs inconnus — bandes de confiance + flag « générateur inconnu » obligatoires.*

**Community Notes** — système d'annotation crowdsourcé de X. **Retiré du périmètre dans le re-scope Telegram-only du 2026-05-26** (capteur X-only, aucun équivalent Telegram). Les labels faibles / validation a posteriori proviennent désormais des **corpus de fact-checking** (AFP Factuel, Les Décodeurs, CheckNews, 20 Minutes). Conservé ici comme référence historique.

**TGStat** — annuaire indexant 2,7 M+ canaux Telegram (filtres pays/langue/catégorie). Outil canonique de découverte de canaux (référencé par le Bellingcat Toolkit). Sert de couche de discovery : seed depuis le DFRLab Pravda Dashboard → expansion via « canaux similaires » → filtre FR → validation manuelle opérateur.

**FLOOD_WAIT** — réponse de limitation de débit MTProto (champ `seconds` à respecter). Telegram ne publie pas de plafonds exacts. Discipline FLOOD_WAIT = équivalent Telegram de la gestion des rate-limit headers X.

**SOAR** — *Security Orchestration, Automation and Response*. Playbooks automatisés de réponse aux incidents. Modèle adopté pour P3.

---

## Adversaires (catalogue P2 fermé pour MVP)

**Doppelganger** *(RU)* — cloned French/European media domains + amplification bot. Meta déc. 2022 (Struktura + Social Media Agency) ; VIGINUM juin 2023.

**Media Brands / RRN** *(RU)* — *Reliable Russian News*. Création de marques médiatiques inauthentiques.

**Undercut** *(RU)* — un des « cinq IMSs » canonisés par EU DisinfoLab. Méthodologie moins documentée.

**Storm-1516** *(RU)* — désignation Microsoft Threat Intelligence. 100+ sites fake news + deepfakes vidéo. Rapport VIGINUM mai 2025 (modus operandi).

**Matriochka / Operation Overload** *(RU)* — opération *target-the-defender* qui noie les fact-checkers et journalistes. Rapport SGDSN/VIGINUM juin 2024.

**CopyCop** *(RU)* — Recorded Future mars 2024. 300+ sites mi-2025. LLM-generated, impersonates médias français. Fingerprint : `dolphin-2.9-llama3-8b` et `Llama-3-8B-Lexi-Uncensored` fine-tunés sur médias d'État russes.

**Cluster IUVM** *(IR)* — International Union of Virtual Media. Surface limitée ; liée à la position française sur Israël.

**APT28 / GRU Unit 26165** *(RU)* — cyber + leak ops. Attribution officielle française des Macron Leaks 2017. Convention de phrasing : *« matches tradecraft of GRU Unit 26165 (APT28) »*.

---

## Acteurs institutionnels alliés

**EEAS StratCom Task Force** — service européen d'action extérieure. Opère EUvsDisinfo. Publie le rapport annuel FIMI Threats (4ᵉ édition mars 2026 : 540 incidents en 2025).

**NATO StratCom CoE** *(Riga)* — steward du framework DISARM côté OTAN.

**Hybrid CoE** *(Helsinki)* — Centre d'excellence européen contre les menaces hybrides (EU + OTAN). Co-auteur des standards DISARM-FIMI.

**EU DisinfoLab** — ONG bruxelloise. Maintient le hub Doppelganger et la cartographie canonique des « cinq IMSs ».

**DFRLab** *(Atlantic Council)* — Digital Forensic Research Lab. 1 000+ investigations depuis 2016. Délivre le G7 Rapid Response Mechanism Digital Transnational Repression Detection Academy.

**Stanford Internet Observatory** — *démantelé juin 2024*. Cas d'école de la classe de NFR EIP-resistance du pilier P4.

**UW CIP** *(Center for an Informed Public, U. Washington)* — bras nord survivant de l'ancien EIP.

**Sciences Po médialab** — partenaire académique français potentiel. Manon Berriche est co-autrice de Basol et al. 2021 sur l'inoculation cross-culturelle en français.

---

## Concepts de gouvernance (P4)

**EIP-resistance** — classe de NFR (Non-Functional Requirement) imposée par le pilier P4. Recouvre : méthodologie pré-publiée 3 mois avant le live, vocabulaire à tiers, publication à deux vitesses, règle de corroboration multi-source, COI audités, ratio symétrique mensuel publié, checklist post-mortem EIP. *Chaque release-gate inclut un check EIP-resistance.*

**Ratio symétrique** *(symmetric topic ratio)* — publication mensuelle de la répartition topique des épisodes surfacés (gauche / droite / centre / autre). Garde-fou contre l'asymétrie qui a politiquement détruit l'EIP en 2023.

**Publication à deux vitesses** — note préliminaire rapide + note longue après corroboration multi-source. Calque OSCE.

**COI** — *Conflict of Interest*. Déclaration auditée pour chaque analyste ayant autorité d'escalade. Rotation des binômes.

**Multi-source corroboration rule** — aucune escalade T4/T5 sur un signal unique. Requis : ≥ 3 signaux indépendants de ≥ 2 familles.

**Audit trail public** — chaque interaction logguée dans un journal public en lecture seule (couche transparence du pilier P6).

---

## Concepts d'inoculation (P5)

**Pre-bunking / inoculation** — exposition préventive à une forme affaiblie de manipulation pour développer la résistance cognitive. Roozenbeek / van der Linden. Validé en français par Basol et al. 2021.

**Trusted-messenger partners** — partenaires externes (campagnes, fact-checkers, presse régionale) qui distribuent les pre-bunks sous *leur* marque. **Jamais sous marque gouvernementale.** Garde-fou critique contre le risque E-L1.

**Templates fallacieux** — types de raisonnement adressés par les pre-bunks (strawman, moving-the-goalposts, whataboutism…). *Moving-the-goalposts dépriorité* — polarise dans certaines populations (Biddlestone 2025).

---

## Concepts UX (P6)

**Console opérateur** — vue analyste VIGINUM/Arcom : triage + cascade visualization + dossier preview.

**Vue commanditaire / démo** — vue command-center : temps réel + mode replay sur cas Telegram-natifs (Matriochka 2024, Storm-1516 2024–2025, FR-législatives 2024 sous-graphe Telegram ; Pravda en continu). *(Macron Leaks 2017 retiré — Telegram négligeable en politique FR en 2017.)*

**Couche transparence publique** *(Public Transparency Layer)* — vue publique en lecture seule : ratio symétrique + audit méthodologique + comptes par tier de sévérité. **Elle est elle-même un artefact d'EIP-resistance**, pas un simple habillage.

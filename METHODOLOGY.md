# Idéfix — Methodology

**Version:** 0.3.0-poc
**Date:** 2026-06-29
**Status:** PoC (pre-publication — not yet in public record)
**Supersedes:** 0.2.0-poc (2026-06-10)

> This document must be published 3 months before any live detection output goes live (EIP-resistance requirement). Target: November 2026.
>
> **Change record 0.2.0 → 0.3.0:** a **semantic-coherence score family (f)** built on local sentence embeddings is now wired into the suspicion score, closing the gap where channel embeddings were computed for community detection but never consumed by scoring (§3.1, §3.4). **Episode discovery is now automatic** (density clustering with a semantic "why" block) rather than a hand-maintained registry (§4bis). The **multi-source gate is now traceable**: the exact set of triggered families is materialized per channel (`gate_families`, §3.2). A **non-circular validation track** has been built — an external organic-FR baseline, an external gold episode, and an embedding-discrimination ROC-AUC — to address the circularity and missing-organic-corpus gaps that bounded v0.2.0's claims (§8). Community snapshots are now **read back** by the pipeline for temporal drift analysis, not only pushed (§9).
>
> **Change record 0.1.0 → 0.2.0:** the detection core actually shipped is an **explainable per-channel suspicion score**, not the GraphSAGE+LSTM graph neural network described in 0.1.0. The GNN is repositioned as a later target (§7). The platform became **multi-mission** (§6). The validation state is documented honestly against four falsification experiments (§8). Infrastructure claims (Neo4j, Docker Compose) are corrected to the implemented stack (§9).

---

## 1. System overview

Idéfix is a **propagation-and-coordination analysis system** for Telegram public channels. It reconstructs observable diffusion, surfaces early seeding channels, detects coordinated behaviour, and produces ranked, explainable case files for human analysts. It is **not** a fake-news detector: it never labels individual posts true or false, and its output is a prioritized examination queue with per-signal evidence, never a verdict.

**Platform:** Telegram public channels only (MTProto). Single-platform coverage is the load-bearing limitation of this system and is disclosed in every output (§5).

**Operational model:** arm-only. Outputs flow to the designated institutional recipients (VIGINUM and Arcom for the default mission; the relevant OPSEC cell for the GAN mission). The system never executes platform action and never publishes attribution itself.

**Missions:** the engine is theme-agnostic; analytical scope is set per mission (§6). The default mission monitors coordinated disinformation attacking the image, integrity, or sovereignty of France. Thematic relevance **modulates severity; it never filters inclusion** (§3.3).

---

## 2. Detection architecture (as implemented)

The shipped detection core is an **explainable per-channel suspicion score** (`src/scorer/channel_suspicion.py`). The unit of analysis is the **channel**, not the message. The pipeline is fully offline:

```
MTProto ingestion → normalization → forward-edge derivation → thematic tagging
→ suspicion scoring (structural families + semantic family f) → episode discovery
→ community / porosity analysis → static JSON export → snapshot store (push/pull)
```

### Layer 1 — Graph construction
- Channel-centric multiplex graph in memory (NetworkX/igraph), backed by a PostgreSQL `edges` table.
- Edge families: **propagation** (FORWARD edges, oriented origin → relayer, carrying forward counts and `delay_seconds`), **influence** (domain citations, mentions), **coordination** (time-windowed co-forwarding, text similarity, co-URL — timestamps discriminate coordination from coincidence).
- Telegram's propagation primitive is the depth-1 forward star with heavy-tailed multi-day delays; analysis therefore aggregates over multi-day windows and across episodes rather than within single cascades.

### Layer 2 — Explainable suspicion score
- Score families (§3) computed on the forward projection and the coordination edges, combined by a transparent weighted sum, then modulated by bounded severity boosts (§3.3).
- Every component of every channel's score is preserved in the output (weights, per-family values, trigger status, boost detail) so that an analyst can justify any ranking from the dossier alone.

### Layer 3 — Institutional output
- Precomputed JSON evidence bundles with attribution tier declaration (T1/T2 only — §4).
- Mandatory coverage callout (single-platform-blindness disclosure — §5).
- Chain of custody: methodology version hash (SHA-256 of this document), timestamps, stable identifiers.
- Channels are followed by channel-ID (stable across handle rebrands); confidence is downgraded to "degraded/stale" when a channel has not been polled for 14 days or more.

---

## 3. The suspicion score

### 3.1 Score families

| Family | Status (PoC v0) | Method |
|--------|-----------------|--------|
| (a) Claim proximity | **Reserved (N/A in v0)** — no claim registry wired yet | Semantic match to a registered claim (BGE-M3), injectable seam |
| (b) Cascade role | **Active** | Bridge-Score composite (in-degree, eigenvector, clustering) on the forward graph; archetypes: seeding-source / forward-hub / cross-channel bridge / reactivator. Isolated channels are never counted as triggered (degenerate-centrality guard). |
| (c) Coordination | **Active** | Time-windowed coordination edges (default 72 h window): co-forwarding, near-identical text, co-URL; multi-type reinforcement raises the value |
| (d) Cross-episode recidivism | **Active** | Forward-influence (forwards earned) + seed-channel recurrence — not subscriber count, not bot heuristics |
| (e) GenAI-origin probability | **Reserved (N/A in v0)** — detector not wired | Seam for audio/video/LLM-text detectors |
| (f) Semantic coherence | **Active** (opt-in) | Local sentence-embedding signal (`src/scorer/embedding_signals.py`): distance of a channel's mean embedding to an organic-FR baseline centroid combined with proximity to known-adversary channel embeddings. A *content* signal, structurally independent of the graph-derived families (b)/(c)/(d) — see §3.4. |

### 3.2 Combination (default mission weights)

The base score is a weighted sum of **triggered** families, renormalized over the weights of the families present: (b) 0.30 · (c) 0.25 · (d) 0.30, with (a) 0.15 and (e) 0.15 reserved and excluded while N/A. The semantic family (f) is opt-in (enabled with `build_scores.py --embeddings`) and, when present, enters the same renormalized sum as an additional triggered family; it is excluded — exactly like a reserved family — when embeddings are not computed, so the structural-only score is unchanged. Confidence bands (lo/hi) propagate through the same combination. Weights are per-mission configuration (§6), published as part of this methodology.

**Multi-source gate:** a channel only crosses the gate when **at least 2 distinct families** are triggered (trigger threshold 0.3). Single signals are treated as unreliable by construction. Because (f) is a *content* signal independent of the graph families, a channel cleared by structure-plus-semantics carries genuinely independent corroboration, not two views of the same graph. The gate is **traceable**: the exact set of triggered family keys is materialized per channel (`gate_families`, migration `0008`) alongside the boolean `met`, so any tier assignment can be audited from the stored record. The gate also drives tier assignment (§4): gate met ⇒ T2 (behavioural recurrence), otherwise T1.

### 3.3 Severity modulation — bounded, upward-only, never a filter

Three signals **raise** the severity of an already-suspect channel. They are multiplicative on the base score, bounded, and they **never** gate or filter inclusion:

| Modulator | Bound | Basis |
|---|---|---|
| Reforward-from-suspect | ≤ +20 % | Fraction of inbound forwards originating from suspect-prior channels |
| Adversary-domain citation | ≤ +15 % (saturates at 5 citations) | Citation of documented adversary infrastructure (e.g. Pravda network, Doppelganger amplifiers) |
| Thematic targeting | ≤ +20 % | Cross-language thematic relevance score (France-targeting for the default mission, GAN-targeting for the GAN mission) |

**META-CONSTRAINT (load-bearing):** adversary linkage and thematic relevance modulate *severity*, never *inclusion*. The system surfaces **all** coordinated activity in the corpus; no channel is excluded from the queue for being off-theme or for lacking adversary linkage. Because the modulation is multiplicative, a channel with zero structural suspicion stays at zero regardless of its thematic relevance — legitimate press discussing France is not promoted. Conversely, French-keyword density (`fr_score`) is a display field only and is never used as a filter or anchor: an adversary channel operating in Russian or English with low French-keyword density can and must be able to rank at the top.

**Symmetry artefact:** every scored bundle publishes the share of the *full scored population* (not the displayed page) linked to documented adversary infrastructure versus organic, as a standing transparency ratio.

### 3.4 Semantic-coherence family (f)

Family (f) (`src/scorer/embedding_signals.py`) gives the score a **content** signal that is structurally independent of the graph. Each channel is represented by the mean of its longest messages' local sentence embeddings (`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, 384-dim, FR/RU/EN; deterministic, offline-cached — re-runs cost nothing). The family value combines two distances, both per-mission configuration:

- **baseline distance** `1 − cos(channel, organic-FR centroid)` — how far the channel reads from a basket of legitimate French outlets (`embedding_baseline_channels`);
- **adversary proximity** `max_i cos(channel, adversary_i)` — how closely it reads like a documented adversary channel (`embedding_adversary_channels`).

The value is a bounded weighted sum, clamped to [0, 1], with the contributing distances and the closest-adversary identifier preserved in the channel's evidence block — so a ranking driven by (f) is justifiable from the dossier alone (e.g. "reads like @X, @Y, @Z — all documented adversary channels — and 0.85 away from the French-press baseline"). The family **degrades gracefully**: if embeddings or the mission's baseline/adversary anchors are unavailable, (f) is simply absent and the structural score is returned unchanged. It is a *severity-independent corroboration* signal, not a filter: it can help a channel cross the multi-source gate (§3.2) but never excludes one.

> **Calibration knob.** The baseline/adversary anchor lists and the distance weights are tuned against the validation track (§8.3), not fixed in code as ground truth. The current anchors are a seed; the upgrade path is to source them from the organic-FR baseline corpus (`data/eval/baseline_organic_fr.json`) rather than from a handful of hard-coded handles.

---

## 4. Attribution tiers

| Tier | Claim | Evidence | Stance |
|------|-------|----------|--------|
| T1 — Observable diffusion | First-visible seeding channel, forward hubs, fan-out shape | MTProto public-channel data + graph reconstruction | **Primary deliverable** |
| T2 — Behavioural recurrence | Same channels/motifs across episodes, multi-family corroboration | Multi-episode aggregation + the multi-source gate (§3.2) | **Secondary deliverable** |
| T3 — Real-world attribution | A person, organization, state, sponsor | Off-platform corroboration | **OUT OF SCOPE — never claimed by this system** |

Tier assignment is mechanical and auditable: a channel is labelled T2 only when the multi-source gate is met; otherwise T1. Any output conflating tiers is a defect. "First-visible seeding channel" means first visible *within the Telegram corpus* — never "originator" in the strong sense.

### 4bis. Episode discovery

An **episode** is a coherent diffusion event — a set of channels propagating the same material over a bounded window. In v0.2.0 episodes were a hand-maintained registry (a single documented example); the discovery pipeline existed but was never wired to the output. In v0.3.0 episodes are **discovered automatically** (`scripts/mine_episodes.py`) and merged with any curated entries (`src/dossier/evidence.py::load_episodes`), so the registry is no longer a bottleneck.

Discovery pivots on shared diffusion artefacts — re-used media (`file_unique_id`), exact-match URLs, and forward republication — and labels each candidate cluster by TF-IDF over its vocabulary. Each discovered episode additionally carries a **semantic "why" block** (`pourquoi_embedding`) derived from family (f)'s embeddings: intra-cluster cohesion, mean distance of the cluster to the organic-FR baseline, and the cluster's top outliers. This is exactly the per-episode justification an analyst needs to read a discovered cluster as a coordinated event rather than a coincidence. Discovery never asserts tier above what the per-channel gate (§3.2) supports.

---

## 5. Coverage limits (disclosed in every output)

> "Ce dossier observe uniquement la couche d'ensemencement Telegram. Une opération atteignant la France principalement via d'autres plateformes sans étape Telegram ne sera PAS détectée."

This callout is a mandatory, validated field of every exported bundle. Additional standing limits:

- The graph is a **partial projection**: cross-platform relays, screenshots, re-cropped media, and private channels are invisible.
- Channels under a French legal block are invisible to an EU-anchored collector account; this blind spot is accepted for the PoC (those channels are already actioned by the judicial lever).
- Deletion detection runs by polling diff (≤ 15 min latency on hot channels) — no platform firehose exists.
- Per-mission callouts extend this disclosure (e.g. the GAN mission states that the measured footprint is the *Telegram-observable* footprint, never the total footprint — §6.2).

---

## 6. Multi-mission architecture

Idéfix is **one engine, N missions**. A mission is a *configuration* (source universe, lexicon, targeting weights, scoring profile, dashboard, export), never a code fork. The structural families (b)/(c)/(d) are theme-agnostic; missions differ in seeds, lexicons, relevance signals, weights, and any additional score families. The severity-not-inclusion constraint of §3.3 is generic and binds every mission.

### 6.1 Default mission — coordinated disinformation targeting France (`russosphere`)

The configuration described in §3: thematic scope restricted to narratives attacking the image, integrity, or sovereignty of France; relevance signal = cross-language France-targeting; outputs armed to VIGINUM/Arcom.

### 6.2 Pilot mission — GAN informational footprint (`gan`)

Measures the **Telegram-observable informational footprint** of the French Carrier Strike Group (*Charles de Gaulle*) with an OPSEC-minimization objective, and detects adversary capture/amplification of that footprint.

- **All mission-specific scores are named `telegram_*`** — a deliberate perimeter lock: the system measures the observable-on-Telegram footprint, never the total footprint (AIS, fitness-tracker leaks, X, press, satellite, and ship-spotting may feed Telegram but are not collected).
- Additional families: `telegram_visibility`, `telegram_velocity`, `telegram_source_diversity`, `telegram_disclosure_precision` (graded EEFI rubric on message text — severity grades are a calibration decision owned by the sponsor, seeded v0), `telegram_propagation`, `telegram_adverse_attention`. Structural families (b)/(c)/(d) are retained at reduced weight.
- **Neutral credibility prior:** channels discussing a friendly asset carry no presumption of suspicion (no suspect-prior assignment in this mission).
- Tiers: T1 = observable footprint + first discloser; T2 = recurrent monitor; T3 out of scope, as everywhere.

### 6.3 Planned mission — DIRCOM message diffusion (`dircom_minarm`)

Tracks reuse, transformation and distortion of official DIRCOM (ministère des Armées) communication on Telegram. As of v0.3.0 the mission is **packaged** (`src/missions/dircom_minarm/`: lexicon, source universe, scoring/dashboard/export profiles, semantic anchors) and auto-discovered by the registry, but kept `implemented=False` so it appears in the switcher yet refuses live selection until a crawl populates it. Listed for transparency of roadmap; flipping the flag activates it once data exists. Beyond the three named missions, a `france_ukraine` mission (narratives targeting France in the Ukraine conflict) is also implemented under the same engine.

---

## 7. Relationship to MisinfoTeleGraph — GNN as a later target

Version 0.1.0 of this document described a GraphSAGE+LSTM graph neural network (replicating MisinfoTeleGraph, arXiv:2506.22529) as the detection core. **That is not what is shipped, and this document no longer claims it.**

- **Shipped today:** the explainable suspicion score of §3. It was chosen deliberately: at PoC corpus scale, a supervised GNN is premature (no balanced channel-level gold set exists), and an explainable score is auditable end-to-end — a requirement for institutional use.
- **Later target:** the GraphSAGE+LSTM classifier remains the roadmap once (i) ingestion scales and (ii) a balanced channel-level annotation set exists. The score families of §3 are designed to become that model's input features; the methodology of MisinfoTeleGraph informs the graph schema and evaluation design today, not the deployed classifier.
- Per-message weak labelling against fact-check corpora was piloted and **pivoted away from** (per-message gold was ~97 % "true" — uninformative); supervision, when it comes, will be channel-level.

Coordination-detection thresholds (VIGINUM D3lta) and Bridge-Score cascade roles cited in 0.1.0 survive in adapted form inside families (c) and (b) respectively.

---

## 8. Validation state (honest disclosure)

The score has been subjected to a falsification battery now **computed on real scores** (russosphere, 3 699 scored channels materialised in `channel_scores`; forward graph 3 680 nodes / 6 889 edges). All numbers below are **reproducible** — committed under `docs/metrics/` and regenerable via `scripts/prep_eval_inputs.py` + `scripts/eval_*.py`. Full audit: `docs/scientific-audit.md`. We publish what is **proven**, what is **weak**, and what is **not yet computable** — not a marketing claim.

| Experiment | Question | Verdict (computed) | Strength |
|---|---|---|---|
| 1 — Centrality ablation [Spearman, 1904; Fawcett, 2006] | Is the score just centrality in disguise? | **PASS — no.** Spearman(suspicion, in-degree)=0.667, eigenvector=0.535, forward-influence=0.424, activity=0.317; Jaccard@50 ≤ 0.05 (in-degree 0.020, eigenvector 0.053). Falsification thresholds (Spearman>0.90 OR Jaccard@50>0.80) **not approached**. → `docs/metrics/ablation_centrality.json` | **Strong** (label-free) |
| 2 — Known-episode recovery (external gold) | Does it recover a documented operation? | **WEAK.** Against an **external, non-circular** gold (`gold_episode_dugin.json`): only 3/12 gold channels are in the corpus; recall@50=0.167 (chance 0.162, ×12.35), median rank 50. Caveat: the gold is **hypothetical** (not a real VIGINUM list) and the overlap is tiny. → `docs/metrics/episode_recovery.json` | **Weak** |
| 3 — Hostile vs organic discriminant | Does it separate hostile coordination from organic virality? | **MIXED, not stressed.** Among 446 coordinated channels: Spearman(suspicion, adversary-anchoring)=**0.765** (dominant), coordination alone=0.253, structural base=0.488. **0 organic candidates** in the corpus (seeded on the adversary) → the discriminant is not stressed. → `docs/metrics/discriminant_organic.json` | **Weak** |
| f — Embedding discrimination [Rousseeuw, 1987; Fawcett, 2006] | Does family (f) separate organic-FR from scored? | **WEAK + method caveat.** ROC-AUC=**0.506** (≈ chance), silhouette 0.003. But the test embeds **usernames only**, not message content as deployed family (f) does — so it does **not** test (f) as shipped. Recommendation: re-encode on content. → `docs/metrics/embedding_discrimination_russosphere.json` | **Weak (mis-specified)** |
| Significance (ROC-AUC vs gold, permutation, calibration) | Is the rigorous score significant vs gold? | **NOT COMPUTABLE.** `channel_gold` = 12 positives / **0 negatives** (no organic corpus) → ROC-AUC undefined. Blocked by the same gap as Exp 3. | **Blocked** |

**Standing claim, calibrated to the evidence:** the system is defensible as a **T1 demonstrator** — observable diffusion structure, **demonstrably separable from raw centrality** (Exp 1, computed) — **not** as a validated manipulation detector. Two gaps, both human-annotation work, still bound the claim: (1) a **real** external seed list for a documented episode (the current gold is hypothetical, 3/12 in-corpus); (2) a corpus of **organic French coordination** (the negative class — currently 0, which blocks Exp 3 and the significance ROC-AUC). Until they close, no output is presented as more than T1/T2 per §4.

### 8.2 Analytics vs embedding (computed)

Community detection (Leiden [Traag et al., 2019]) on russosphere, two tracks (full numbers: `docs/metrics/analytics_vs_embedding.json`; discussion: `docs/analytics-vs-embedding.md`): intra-cohesion 0.6709 → **0.7049 (+5.1 %)**, silhouette [Rousseeuw, 1987] −0.274 → 0.021, **modularity [Newman, 2006] 0.7547 → 0.6301**, kept communities 27 → 17, partition agreement **NMI 0.887 / ARI 0.528** [Danon et al., 2005; Hubert & Arabie, 1985]. The cohesion↑ / modularity↓ **trade-off** is expected, not a regression: the semantic `EMB_SIM` edges cross the link-graph communities (see `docs/analytics-vs-embedding.md`).

### 8.3 Non-circular validation track (status)

The *instruments* are built **and now run** on real scores; what remains is **real annotated data**:

- **External organic-FR baseline** (`scripts/bootstrap_baseline.py` → `data/eval/baseline_organic_fr.json`): 98 legitimate FR channels (anchors for family (f)). It is **not** a coordination corpus — it supplies anchors, not the organic *negatives* Exp 3/significance need.
- **External gold episode** (`data/eval/gold_episode_*.json`, schema `ExternalGoldEpisode`, `excluded_from_scorer_inputs=True`): **hypothetical**, 3/12 in-corpus — to be replaced by a real VIGINUM-sourced list.
- **Embedding-discrimination test** (`scripts/eval_embedding_discrimination.py`): runs (ROC-AUC 0.506) but mis-specified (usernames, not content) — fix before drawing conclusions.
- **Temporal drift** (`scripts/compare_snapshots.py`): reads snapshots back for longitudinal control (§9).

Honest bottom line: the cheap falsification (Exp 1) **passes on real, reproducible numbers**; the stronger claims remain blocked by the missing organic negative class and a real external gold.

### Evaluation framework

The system is evaluated as an **investigation tool**, not a classifier: top-K precision on priority channels, temporal gain over public fact-checker identification, reconstruction quality of the forward/seeding map, and analyst utility (triage time, stability and justifiability of explanations). It is never evaluated by "persuasion measured" or "influence proven".

---

## 9. Infrastructure and data handling (as implemented)

- **Offline pipeline only.** Python scripts run the full chain (ingest → normalize → edges → tag → score → discover episodes → analyze → export); the analyst interface is a **static web bundle** reading precomputed JSON — no live backend, no server-side detection at query time. The bundle is built and served on Vercel; a prebuild step (`webapp/scripts/pull-snapshots.mjs`) freezes the community snapshots into the bundle, so the browser never contacts the database.
- **Stack:** PostgreSQL (Supabase managed) for the message/edge/score store, in-memory NetworkX/igraph graph. No graph-database server, no container orchestration, no message bus — corrections to the Neo4j/Docker Compose claims of version 0.1.0.
- **Embeddings:** local `sentence-transformers` inference (multilingual MiniLM, 384-dim), deterministic and offline-cached (cache key = `sha256(model‖text)`), so family (f) and the semantic episode block cost nothing on re-run and require no paid API.
- **Snapshot store (bidirectional):** community snapshots are pushed to a protected Supabase table (`community_snapshots`, service-role access) and **read back** by the pipeline (`pull_snapshot`) for the temporal-drift control of §8.3 — they are no longer write-only.
- **Ingestion:** Telegram MTProto (Hydrogram client), public channels only, history backfill plus tiered polling, FLOOD_WAIT discipline, single dedicated read-only account. No grey collection, no scraping outside ToS, no deanonymization. Channel member identifiers are not collected.
- **Secrets:** the Telegram session and API credentials are execution dependencies and are scrubbed (by key and by value) from every export.
- **Official compliance posture:** legal basis, retention, deletion and access-control obligations are owned by the sponsor's official framework. They are not a standalone Idéfix product backlog stream. Idéfix keeps only the technical hooks requested for official exploitation: minimization, export classification, audit metadata, secret scrubbing, deletion/coverage events when required, and chain-of-custody fields.

---

## 10. Governance

- This methodology is published 3 months before any live detection output (EIP-resistance requirement). The exported bundles embed a hash of this document, so any methodology revision is detectable in the chain of custody.
- **Symmetric ratio** (adversary-linked vs organic share of the scored population) is computed on every full scoring run and published with the bundle (§3.3).
- **Multi-source corroboration** is enforced structurally: no T2 label, and no escalated severity tier, without ≥ 2 independent score families triggered (§3.2).
- **Arm-only:** outputs go to the designated institutional recipients only — never to platforms, never to the public, never to candidates or press.
- **Tiered vocabulary** (§4) is mandatory in every output; T3 claims are a reportable defect.
- The validation state (§8) ships with the methodology and is updated whenever the falsification battery is re-run; claims are bounded by the weakest relevant experiment.

---

## 11. References

Every methodological choice is grounded in the literature. Full bibliography (formatted, with DOIs/arXiv): **`docs/references.md`**. Independent audit of grounding (cited vs implemented vs uncited): **`docs/scientific-audit.md`**.

Key anchors: community detection — Leiden [Traag, Waltman & van Eck, 2019]; modularity [Newman, 2006]. Cluster/partition quality — silhouette [Rousseeuw, 1987]; NMI [Danon et al., 2005]; ARI [Hubert & Arabie, 1985]. Statistics — Benjamini-Hochberg FDR [1995]; Stouffer combination [1949]; bootstrap [Efron, 1979]; permutation tests [Good, 2000]; ROC-AUC [Fawcett, 2006]. NLP — TF-IDF [Spärck Jones, 1972]; Sentence-BERT [Reimers & Gurevych, 2019]; MiniLM [Wang et al., 2020]. Domain — Bridge Score [arXiv:2411.05922] (family b); coordinated inauthentic behavior [Pacheco et al., 2021; Giglietto et al., 2020]; VIGINUM D3lta (family c, text track deferred); MisinfoTeleGraph [arXiv:2506.22529] (GNN, later target, §7).

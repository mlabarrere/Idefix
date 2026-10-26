# Glossary

Reference vocabulary for all deliverables. Aligned with VIGINUM / EEAS / OSCE
usage — **not** 'fake news'.

French institutional terms are given in their official form, because they are
the terms of art in the operating jurisdiction and translating them would lose
their legal meaning. English glosses follow.

> **Scope note.** This glossary previously described a much larger system —
> pillars P1 to P6, DISARM TTP emission, STIX/TAXII packaging, SOAR playbooks,
> deepfake detection, pre-bunking campaigns. **None of that is implemented**, so
> it has been removed rather than left to read as capability. What remains is
> vocabulary for what the code actually does, plus the legal and institutional
> context it operates in.

---

## Analysis concepts

**Forward chain** — the Telegram propagation primitive: a **depth-1 star**, in
which each forward points directly at the origin message, with heavy-tailed
delays spanning days. The analytical unit is fan-out at depth 1 from a source
channel, plus inter-channel re-forward chains observed over multi-day windows.

**Cascade** — generic term for the observed propagation tree of a piece of
material. On Telegram it is reconstructed from **forwards**, not from reposts or
quotes.

**Coordination** — convergence of several weak behavioural signals across a set
of channels, beyond chance. *No single signal is reliable*; it is the multiplex
alignment that matters.

> As implemented, the coordination family establishes only that channels touched
> the same artefact within 72 hours, and it triggers on two distinct edge types
> regardless of timing. It does not estimate whether that convergence is beyond
> chance: there is no null model. See [D2](../limitations.md#d2) and
> [D5](../limitations.md#d5).

**Episode** — as implemented, a relation between one Russian-side channel and
one French-side channel: every shared artefact between the two (reused media,
exact URLs, forward republication) across the whole corpus, with no time
window (`scripts/mine_episodes.py::group_by_pair`). The side of a channel comes
from its French-keyword density, `fr_score`. The exact-URL pivot never fires
([D29](../limitations.md#d29)).

**Multiplex graph** — the channel-centric graph carrying several edge families
between the same pair of nodes. Nodes are channels and cited domains; edges are
forwards, mentions, domain citations and the windowed coordination families.
Full list: [`../method/02-graph-model.md`](../method/02-graph-model.md).

---

## Cascade archetypes

Assigned by a hard-coded priority cascade,
`src/scorer/cascade_role.py::classify_archetype`.

**Seeding-source channel** — a channel that recurrently originates material
early, before fan-out. Primary early-warning target. **Rarely an originator in
the strong sense** — 'first visible' is a statement about the observation
window, not about causation.

**Forward-hub** — a channel whose content is widely forwarded. The most visible
role, not necessarily the most important. Note that the classifier's fallback
branch also returns this label, so it covers two distinct structural situations.

**Cross-channel bridge** — a channel that carries material from one community to
another. Often more strategically significant than a high-volume forward hub.

**Reactivator** — a channel that periodically reinjects older material into
fresh conversation. An indicator of recurrence.

---

## Metrics

**Forward influence** — out-strength on the aggregate forward graph:
how much forwarding a channel's content earns. Preferred over subscriber count
and over bot-score heuristics. It is the backbone of score family (d).

> Family (d) is named 'recidivism' in the code and was long documented as
> cross-episode. It is not: there are no episodes in the computation. On the
> scoring path it is the significance of raw out-strength against the null
> model.

**Max-normalization** — dividing a raw score by the corpus maximum. Used by the
raw families (b) and (d), which still decide the archetype and feed the
dossier. It makes values comparable **within** a single run and meaningless
**across** runs, since one new hub rescales everyone
([D8](../limitations.md#d8)).

**Top-K precision** — of the K top-ranked channels for a historical episode, how
many appear in the seeding or coordination core identified afterwards. The
primary evaluation metric. Protocols:
[`../experiments/`](../experiments/).

**Temporal gain** — the lead time by which the system surfaces a channel ahead
of public identification by fact-checkers. The operational value proposition:
catching the seeding phase. Never measured to date.

---

## Score families

As implemented. See
[`../method/03-suspicion-score.md`](../method/03-suspicion-score.md).

| # | Family | What it computes | Status |
|---|---|---|---|
| (a) | Claim proximity | Semantic match to a registered claim | **Never wired.** No value has ever been produced |
| (b) | Cascade role | Bridge-Score composite on the forward graph | Active, with null model |
| (c) | Coordination | Windowed coordination edges: tightness and type diversity | Active, **no null model** |
| (d) | Recidivism | Out-degree and out-strength on the aggregate forward graph | Active, with null model |
| (e) | GenAI-origin probability | Detector seam | **Never wired.** `e_res = None` |
| (f) | Semantic coherence | Baseline distance and adversary proximity in embedding space | **Computed, not scored.** Never reaches the score, the gate or the bundle ([D19](../limitations.md#d19)) |

**Multi-source gate** — a channel *meets the gate* when at least **two
distinct families** trigger, and only then is it T2. Materialized per channel
as `gate_families`. The gate decides the tier only; it does not bound the
severity modulation ([D21](../limitations.md#d21)).

**Flagged** — in the set of channels that Benjamini–Hochberg control of the
false discovery rate rejects at the mission's `alpha`, computed on the
combined p-values across all scored channels (`flagged`, with its `q_value`,
in `src/scorer/channel_suspicion.py::compute_channel_queue`). Being flagged
changes neither the score, nor the gate, nor the tier, and it is independent of
meeting the gate. This glossary uses the word in no other sense.

> A second, inconsistent rule (at least 3 signals from at least 2 families)
> exists in `src/dossier/builder.py::build_episode_dossier`. It does not govern
> the production queue ([D16](../limitations.md#d16)).

---

## Attribution tiers

| Tier | Name | What is claimed | Stance |
|---|---|---|---|
| **T1** | Observable diffusion | First-visible source channel, early forward hubs, fan-out shape | **Primary deliverable** |
| **T2** | Behavioural recurrence | For a channel, the multi-source gate is met; for an episode, at least two distinct pivot types | **Secondary deliverable** |
| **T3** | Real-world attribution | A person, organization, state, sponsor | **Out of scope** — requires off-platform evidence |

Any deliverable that conflates tiers is a defect. Every dossier declares its
tier; the pipeline's one dossier hard-codes it
([D16](../limitations.md#d16)).

---

## Legal and institutional framework

**VIGINUM** — *Service de vigilance et de protection contre les ingérences
numériques étrangères*. French service for vigilance and protection against
foreign digital interference. Created 13 July 2021 under the SGDSN. Mandate: to
detect and characterize **foreign** digital interference in French public
debate.

**Arcom** — *Autorité de régulation de la communication audiovisuelle et
numérique*. French audiovisual and digital communication regulator; national
Digital Services Act coordinator for designated platforms.

**SGDSN** — *Secrétariat général de la défense et de la sécurité nationale*.
General Secretariat for Defence and National Security; VIGINUM's supervising
authority and the interministerial coordinator.

**Manipulations de l'information** — the official French term. Preferred over
'disinformation', and never 'fake news'.

**Ingérences numériques étrangères** — foreign digital interference. The
statutory scope of VIGINUM's mandate.

**FIMI** — *Foreign Information Manipulation and Interference*. Official
EEAS/EU terminology. Preferred over 'disinformation' in stakeholder
deliverables.

**DSA** — Digital Services Act (EU). Load-bearing articles: **Art. 36** (crisis
response mechanism) and **Art. 40** (researcher access; the national coordinator
for France is Arcom).

**Loi anti-infox** — Law of 22 December 2018. Provides an emergency judicial
procedure (48 hours) to suspend distribution of false information during an
election period.

**Loi 2024-850** — Law of 25 July 2024 on preventing foreign interference in
France.

**CNIL** — *Commission nationale de l'informatique et des libertés*. The French
data protection authority. Public data is still personal data: legal basis,
retention periods, access logging and minimization rules must be documented.

**Blackout 44 h** — the media silence imposed by French electoral law in the 44
hours preceding a vote. A critical operational window, since material published
inside it cannot be answered.

**FLOOD_WAIT** — the MTProto rate-limiting response, carrying a `seconds` field
that must be respected. Telegram publishes no exact ceilings, so respecting
`FLOOD_WAIT` and never parallelizing sessions is the entire discipline.

**Chain of custody** — cryptographic evidence of an artefact's integrity and of
the sequence of its holders. Required for evidence admissible in judicial
proceedings. Implemented here only in part: every bundle carries timestamps,
stable identifiers and a static methodology version string. A hash of
`METHODOLOGY.md` exists in the dossier schema, but no output carries it, and it
would ignore `docs/method/` ([D20](../limitations.md#d20),
[D23](../limitations.md#d23)).

**TGStat** — a directory indexing Telegram channels with country, language and
category filters. Used as a discovery layer: seed from a documented adversary
list, expand via 'similar channels', filter, then validate manually.

---

## Documented adversary infrastructure

The catalogue behind the adversary-domain severity modulator. These are
externally documented operations, not findings of this system.

**Doppelganger** *(RU)* — cloned French and European media domains with bot
amplification. Meta, December 2022; VIGINUM, June 2023.

**RRN / Media Brands** *(RU)* — *Reliable Russian News*. Creation of inauthentic
media brands.

**Undercut** *(RU)* — one of the five information-manipulation sets canonized by
EU DisinfoLab. Less thoroughly documented.

**Storm-1516** *(RU)* — Microsoft Threat Intelligence designation. Large network
of fake news sites plus video deepfakes. VIGINUM report, May 2025.

**Matriochka / Operation Overload** *(RU)* — a *target-the-defender* operation
that floods fact-checkers and journalists with verification requests.
SGDSN/VIGINUM report, June 2024.

**CopyCop** *(RU)* — Recorded Future, March 2024. LLM-generated sites
impersonating French outlets.

**IUVM cluster** *(IR)* — International Union of Virtual Media. Limited surface.

**APT28 / GRU Unit 26165** *(RU)* — cyber and leak operations. Phrasing
convention: *'matches tradecraft of GRU Unit 26165 (APT28)'* — never a direct
attribution claim, which would be T3.

---

## Allied institutional actors

**EEAS StratCom Task Force** — European External Action Service. Operates
EUvsDisinfo and publishes the annual FIMI Threats report.

**NATO StratCom CoE** *(Riga)* — NATO-side steward of the DISARM framework.

**Hybrid CoE** *(Helsinki)* — European Centre of Excellence for Countering
Hybrid Threats (EU and NATO).

**EU DisinfoLab** — Brussels NGO. Maintains the Doppelganger hub and the
canonical mapping of the five information-manipulation sets.

**DFRLab** *(Atlantic Council)* — Digital Forensic Research Lab.

**Stanford Internet Observatory** — dismantled in June 2024. The case study
behind this project's EIP-resistance requirements.

---

## Governance concepts

**EIP-resistance** — the requirement class derived from the Election Integrity
Partnership's political collapse. Covers: methodology published before going
live, tiered vocabulary, multi-source corroboration, a published symmetric
ratio, and audited conflicts of interest. No automated check enforces them.

**Symmetric ratio** — published breakdown of the scored population by adversary
linkage versus organic. A guard against the asymmetry that destroyed the EIP
politically.

> As implemented (`symmetric_ratio`, computed in
> `src/scorer/channel_suspicion.py::compute_channel_queue` and written to the
> bundle), the adversary side counts channels that are `suspect` or cite an
> adversary domain, and the other side is simply its complement. Since
> [D1](../limitations.md#d1) was fixed it no longer measures language, but its
> reach is bounded by the coverage of the adversary catalogue. The analyst
> interface does not display it.

**Arm-only** — output flows to designated institutional recipients. The system
never acts on platforms and never publishes attribution itself.

**Two-speed publication** — a fast preliminary note followed by a long note
after multi-source corroboration. Modelled on OSCE practice.

**COI** — conflict of interest. Audited declaration for any analyst with
escalation authority.

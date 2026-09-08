# `docs/` — documentation canonique stakeholder

Ce dossier contient les documents partageables avec les stakeholders
institutionnels (MinArm/EMA, VIGINUM, Arcom, SGDSN, partenaires académiques).
Les artefacts BMAD intermédiaires (brainstorming, recherche, brouillons,
décisions datées) vivent sous `_bmad-output/` — **local uniquement, non versionné**
(gitignoré) : les chemins `_bmad-output/…` cités plus bas ne sont pas présents dans
un clone nu.

> **2026-06-10 — grand nettoyage (Lot 0).** Les trois artefacts HTML obsolètes
> (`presentation.html`, `operational-plan.html`, `onboarding-report.html` —
> tous antérieurs au re-scope Telegram-only) ont été **supprimés** (historique
> git). Une présentation à jour est à régénérer après le pivot multi-mission.

## Inventaire `docs/`

| Fichier | Audience | Contenu |
|---|---|---|
| [`frontend.md`](./frontend.md) | Dev / design | **La galaxie narrative** : single-screen (galaxie → histoires → ego-focus → drawer), bundle statique par mission, budgets de performance |
| [`multi-mission.md`](./multi-mission.md) | Contributeurs | La plateforme « un moteur, N missions » (profils, pipeline `--mission`, scores `telegram_*`) |
| [`guerre-informationnelle-remediation.md`](./guerre-informationnelle-remediation.md) | Stakeholders / archi | Plan de remédiation pré-production par briques communes, issu de la gap analysis BMAD |
| [`analytical-contract.md`](./analytical-contract.md) | Dev / méthodo | Contrat de données commun : claims, épisodes, preuves, poches, runs de score |
| [`validation-lab.md`](./validation-lab.md) | Dev / validation | Contrats gold episode externe et corpus organique pour fermer les gaps de validation |
| [`coordination-fabric.md`](./coordination-fabric.md) | Dev / méthodo | Registre des signaux de coordination actifs/réservés, seuils et fenêtres |
| [`pockets-and-dossiers.md`](./pockets-and-dossiers.md) | Dev / méthodo | Score de poches informationnelles et contrat Evidence Dossier v1 |
| [`official-hardening.md`](./official-hardening.md) | Opérateur / sponsor | Rôles, marquage, secrets, chaîne de conservation et gate pré-production |
| [`advanced-capability-gates.md`](./advanced-capability-gates.md) | Dev / archi | Gates d'activation des capacités avancées : media reuse, GenAI, GNN, STIX |
| [`graph-model.md`](./graph-model.md) | Dev / méthodo | Modèle de graphe multiplex centré-canal (familles d'arêtes) |
| [`validation-state.md`](./validation-state.md) | Tous (honnêteté) | État de falsification du score de suspicion (4 expériences) |
| [`ops-runbook.md`](./ops-runbook.md) | Opérateur | Supabase primaire, rollback PostgreSQL local, pipeline offline, crawler cadencé |
| [`supabase-migration.md`](./supabase-migration.md) | Opérateur / dev | Format canonique dump/restore, cutover Supabase, sécurité et rollback anti-split-brain |
| [`demo-runbook.md`](./demo-runbook.md) | Démo | Fil de démo 5 min sur la webapp statique (galaxie + histoires) |
| [`migrations.md`](./migrations.md) | Dev | Alembic (head `0008`) |
| [`glossary.md`](./glossary.md) | Tous | Vocabulaire technique et institutionnel |
| [`agent-skills.md`](./agent-skills.md) | Dev | Manifeste des Agent Skills (pinnées via `skills-lock.json`) |
| [`audits/ponytail-2026-06.md`](./audits/ponytail-2026-06.md) | Dev | Audit ponytail (perf / Supabase-Vercel) |
| [`REPRISE_MAC.md`](./REPRISE_MAC.md) | Dev | Checklist de reprise d'environnement (Mac) |
| `../METHODOLOGY.md` | Public (cible) | Méthodologie pré-publiée (exigence EIP-resistance P4) — **à réviser post-pivots** |

Artefacts BMAD détaillés à consulter en complément :
`_bmad-output/planning-artifacts/gap-analysis-guerre-informationnelle-2026-06-15.md`,
`_bmad-output/planning-artifacts/remediation-plan-guerre-informationnelle-prod-2026-06-15.md`,
`_bmad-output/planning-artifacts/epics-v2-guerre-informationnelle-2026-06-15.md`,
`_bmad-output/planning-artifacts/analytical-data-contract-2026-06-15.md`,
`_bmad-output/planning-artifacts/validation-lab-contract-2026-06-15.md`,
`_bmad-output/planning-artifacts/coordination-fabric-contract-2026-06-15.md`,
`_bmad-output/planning-artifacts/pockets-dossier-v1-contract-2026-06-15.md`,
`_bmad-output/planning-artifacts/official-environment-hardening-contract-2026-06-15.md`.

À produire vers `docs/` quand mûrs : `product-brief.md` (depuis
`_bmad-output/planning-artifacts/briefs/`), `prd.md`, `architecture.md`
(la version canonique actuelle vit dans `_bmad-output/planning-artifacts/architecture-multi-mission-2026-06-09.md`).

## Pour commencer

1. Lire `CLAUDE.md` (racine) — contexte, scope-changes datés, contraintes verrouillées.
2. [`multi-mission.md`](./multi-mission.md) puis [`frontend.md`](./frontend.md) — la plateforme et son livrable.
3. [`glossary.md`](./glossary.md) — le vocabulaire.
4. `_bmad-output/planning-artifacts/` — recherche détaillée et décisions datées.

## Langues

Code, configs, identifiants : **anglais**. Documents stakeholder : **français
accepté**. Le vocabulaire institutionnel suit l'usage VIGINUM/UE
(*manipulations de l'information*, *ingérences numériques étrangères*) — pas
« fake news ».

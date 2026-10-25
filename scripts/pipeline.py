#!/usr/bin/env python
"""Offline pipeline runner: from the collected corpus in PostgreSQL to the webapp bundles.

Runs every OFFLINE stage, in order, for one mission or all of them. No stage
contacts Telegram or a paid API. The only network access is the one-time
download of the public sentence-transformers model by the embedding stages
(Hugging Face); ``--skip-embeddings`` drops those stages and never imports
sentence-transformers.

Each stage is an existing script under ``scripts/``, run as a subprocess with
``sys.executable`` from the repository root. The environment is inherited
(``DATABASE_URL`` included); ``PYTHONUTF8=1`` is set unless the caller chose
otherwise, because the scripts print non-cp1252 characters and would crash on
a Windows pipe.

Order is stage-major: each stage runs for every selected mission it applies
to before the next stage starts. ``db-wide`` stages run once, whatever the
mission selection, because their output is shared (``edges``,
``channels.extra.fr_score`` / ``gan_targeting``, read by every mission's
export). The runner itself never deletes anything: stages are idempotent
rewrites (``build_edges`` only upserts, see docs/limitations.md D18).

Usage:
    python scripts/pipeline.py [--mission {russosphere,france_ukraine,gan,all}] [--list]
                               [--only STAGE | --from STAGE] [--skip-embeddings]

Exit status: 0 when every selected stage succeeded, the failing stage's exit
code (non-zero) on the first failure, 2 on a usage error.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"

# Implemented missions, in run order (src/missions/*, ``implemented=True``;
# ``dircom_minarm`` is planned only). Kept in phase with the registry by a test.
MISSIONS: tuple[str, ...] = ("russosphere", "france_ukraine", "gan")
ALL = "all"
DB_WIDE = "db-wide"


@dataclass(frozen=True)
class Stage:
    """One pipeline stage = one script invocation per applicable mission.

    ``args`` may contain ``{mission}``, substituted per mission. ``missions``
    ``None`` means every mission; ``db_wide`` stages run once, without a
    mission. ``embeddings`` stages are dropped by ``--skip-embeddings``;
    ``no_embeddings_args`` are appended to the others under that flag.
    """

    name: str
    script: str
    summary: str
    args: tuple[str, ...] = ()
    missions: frozenset[str] | None = None
    db_wide: bool = False
    embeddings: bool = False
    no_embeddings_args: tuple[str, ...] = ()
    needs_db: bool = True

    def applies_to(self, mission: str) -> bool:
        return self.missions is None or mission in self.missions

    def scope(self) -> str:
        if self.db_wide:
            return DB_WIDE
        if self.missions is None:
            return "every mission"
        return ", ".join(m for m in MISSIONS if m in self.missions)


_RUSSOSPHERE = frozenset({"russosphere"})

# The validated sequence, declared once. Data dependencies, top to bottom:
# edges + tags -> channel_scores -> analysis snapshots -> layout -> export
# (reads channel_scores, the tags and dugin_cluster.json) -> stories (reads
# channels_index.json and porosity_snapshot.json from the bundle).
STAGES: tuple[Stage, ...] = (
    Stage("build_edges", "build_edges.py",
          "multiplex graph: table edges (upsert)", db_wide=True),
    Stage("tag_france", "tag_france.py",
          "channels.extra.fr_score (French keyword density)", db_wide=True),
    Stage("tag_gan", "tag_gan.py",
          "channels.extra.gan_targeting (GAN lexicon)", db_wide=True),
    Stage("build_scores", "build_scores.py",
          "channel_scores + scores_run_meta for the mission", ("--mission", "{mission}")),
    Stage("build_dossier", "build_dossier.py",
          "dugin_cluster.json, the scoring dossier of the registry episode",
          missions=_RUSSOSPHERE),
    Stage("analyze_communities", "analyze_communities.py",
          "russosphere_snapshot.json (Leiden communities + bridges)",
          ("--mission", "{mission}")),
    Stage("analyze_communities_embed", "analyze_communities_embed.py",
          "<mission>_embed_snapshot.json (communities with embedding edges)",
          ("--mission", "{mission}"), embeddings=True),
    Stage("precompute_galaxy_layout", "precompute_galaxy_layout.py",
          "x/y coordinates written into the galaxy snapshots",
          ("webapp/public/data/{mission}/russosphere_snapshot.json",
           "webapp/public/data/{mission}/{mission}_embed_snapshot.json"),
          needs_db=False),
    Stage("analyze_porosity", "analyze_porosity.py",
          "porosity_snapshot.json (RU -> FR traces)", missions=_RUSSOSPHERE),
    Stage("mine_episodes", "mine_episodes.py",
          "episodes_discovered.json (RU -> FR episodes)", ("--mission", "{mission}"),
          missions=_RUSSOSPHERE, no_embeddings_args=("--no-embeddings",)),
    Stage("build_gan_footprint", "build_gan_footprint.py",
          "gan_footprint.json (GAN theme readout)", missions=_RUSSOSPHERE),
    Stage("build_commenters", "build_commenters.py",
          "commenters.json (per-channel aggregate of the comments table)",
          ("--mission", "{mission}")),
    Stage("export_static", "export_static.py",
          "manifest, channels_index, channels/, graph, themes, episodes/",
          ("--mission", "{mission}")),
    Stage("build_stories", "build_stories.py",
          "stories.json (narrative selector)", ("--mission", "{mission}"),
          needs_db=False),
)

STAGE_NAMES: tuple[str, ...] = tuple(s.name for s in STAGES)


@dataclass(frozen=True)
class Step:
    """A stage bound to a mission (``None`` for a db-wide stage)."""

    stage: Stage
    mission: str | None

    @property
    def label(self) -> str:
        return self.stage.name if self.mission is None else f"{self.stage.name} [{self.mission}]"

    def command(self, skip_embeddings: bool) -> list[str]:
        mission = self.mission or ""
        args = [a.format(mission=mission) for a in self.stage.args]
        if skip_embeddings:
            args += list(self.stage.no_embeddings_args)
        return [sys.executable, str(SCRIPTS / self.stage.script), *args]


def select_stages(
    *, only: str | None = None, start: str | None = None, skip_embeddings: bool = False
) -> list[Stage]:
    """Stages to run, in declared order, after ``--only`` / ``--from`` / ``--skip-embeddings``."""
    stages = list(STAGES)
    if only is not None:
        stages = [s for s in stages if s.name == only]
    elif start is not None:
        stages = stages[STAGE_NAMES.index(start):]
    if skip_embeddings:
        stages = [s for s in stages if not s.embeddings]
    return stages


def build_plan(stages: list[Stage], missions: tuple[str, ...]) -> list[Step]:
    """Stage-major plan: each stage for every selected mission it applies to."""
    plan: list[Step] = []
    for stage in stages:
        if stage.db_wide:
            plan.append(Step(stage, None))
            continue
        plan.extend(Step(stage, m) for m in missions if stage.applies_to(m))
    return plan


def child_env() -> dict[str, str]:
    env = dict(os.environ)
    env.setdefault("PYTHONUTF8", "1")
    return env


def _fmt(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes, secs = divmod(int(round(seconds)), 60)
    return f"{minutes}m{secs:02d}s"


def print_list(stages: list[Stage], plan: list[Step]) -> None:
    planned = {s.stage.name for s in plan}
    print("Stages, in run order:")
    width = max(len(s.name) for s in STAGES)
    n = 0
    for stage in stages:
        if stage.name not in planned:
            continue
        n += 1
        runs = [s.mission or DB_WIDE for s in plan if s.stage.name == stage.name]
        tag = " [embeddings]" if stage.embeddings else ""
        print(f"  {n:>2}. {stage.name:<{width}}  {', '.join(runs)}{tag}")
        print(f"      {'':<{width}}  {stage.summary}")


def run_plan(plan: list[Step], *, skip_embeddings: bool) -> int:
    env = child_env()
    timings: list[tuple[str, float]] = []
    t_all = time.perf_counter()
    for i, step in enumerate(plan, 1):
        cmd = step.command(skip_embeddings)
        print(f"\n=== [{i}/{len(plan)}] {step.label}", flush=True)
        print("    $ " + " ".join(cmd[1:]), flush=True)
        t0 = time.perf_counter()
        proc = subprocess.run(cmd, cwd=REPO, env=env, check=False)
        dt = time.perf_counter() - t0
        timings.append((step.label, dt))
        if proc.returncode != 0:
            print(
                f"\nFAILED: {step.label} (exit {proc.returncode}) after {_fmt(dt)}. "
                f"Fix it, then resume with --from {step.stage.name}.",
                file=sys.stderr,
                flush=True,
            )
            _print_timings(timings, time.perf_counter() - t_all)
            return proc.returncode if proc.returncode > 0 else 1
        print(f"--- ok: {step.label} in {_fmt(dt)}", flush=True)
    _print_timings(timings, time.perf_counter() - t_all)
    return 0


def _print_timings(timings: list[tuple[str, float]], total: float) -> None:
    if not timings:
        return
    width = max(len(label) for label, _ in timings)
    print("\nStage timings:")
    for label, dt in timings:
        print(f"  {label:<{width}}  {_fmt(dt):>8}")
    print(f"  {'total':<{width}}  {_fmt(total):>8}", flush=True)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Run the offline pipeline (no Telegram, no paid API) for one or all missions.",
    )
    ap.add_argument("--mission", choices=(*MISSIONS, ALL), default=ALL,
                    help="mission to build (default: all)")
    ap.add_argument("--list", action="store_true",
                    help="print the stages that would run, in order, and exit")
    sel = ap.add_mutually_exclusive_group()
    sel.add_argument("--only", choices=STAGE_NAMES, metavar="STAGE",
                     help="run this stage only")
    sel.add_argument("--from", dest="start", choices=STAGE_NAMES, metavar="STAGE",
                     help="run from this stage to the end (resume)")
    ap.add_argument("--skip-embeddings", action="store_true",
                    help="drop the embedding stages; sentence-transformers is never imported")
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    missions = MISSIONS if args.mission == ALL else (args.mission,)
    stages = select_stages(only=args.only, start=args.start, skip_embeddings=args.skip_embeddings)
    plan = build_plan(stages, missions)
    if not plan:
        print(
            f"Nothing to run: no selected stage applies to --mission {args.mission}"
            + (" with --skip-embeddings" if args.skip_embeddings else "")
            + f". Stages: {', '.join(STAGE_NAMES)}.",
            file=sys.stderr,
        )
        return 2
    if args.list:
        print_list(stages, plan)
        return 0
    if any(s.stage.needs_db for s in plan) and not (
        os.environ.get("DATABASE_URL") or (REPO / ".env").is_file()
    ):
        print(
            "DATABASE_URL is not set (and there is no .env). Example: "
            "DATABASE_URL=postgresql+asyncpg://idefix:idefix@localhost:5433/idefix",
            file=sys.stderr,
        )
        return 2
    return run_plan(plan, skip_embeddings=args.skip_embeddings)


if __name__ == "__main__":
    raise SystemExit(main())

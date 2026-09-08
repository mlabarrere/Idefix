"""Pré-calcul offline des coordonnées 2D de la « galaxie » (post-passe DB-free).

But : supprimer la latence du force-layout (fCoSE) exécuté dans le navigateur en
inscrivant des coordonnées ``x``/``y`` DÉTERMINISTES directement dans les
snapshots déjà commités (``webapp/public/data/<mission>/*_snapshot.json``). Le
front-end pourra alors rendre avec un layout ``preset`` au lieu de recalculer une
disposition par force à chaque montage.

Ce script est une POST-PASSE : il ne régénère RIEN depuis Supabase/PostgreSQL. Il
lit UNIQUEMENT les JSON statiques du bundle, y ajoute ``x``/``y`` sur chaque
communauté et chaque canal, puis réécrit le fichier en place. Toutes les clés
existantes sont préservées ; seules ``x``/``y`` sont ajoutées/écrasées.

Modèle de disposition
---------------------
1. MÉTA-GRAPHE (communautés = nœuds) : ``networkx.spring_layout`` graine=42,
   pondéré par ``meta_graph.edges[].weight``, puis recentré et mis à l'échelle
   dans un rayon ``GALAXY_RADIUS``. → centroïde ``x``/``y`` de chaque communauté.
2. CANAUX d'une communauté : le snapshot ne porte AUCUNE arête intra-communauté,
   donc un vrai ressort n'aurait pas de structure à exploiter. On utilise à la
   place un disque de PHYLLOTAXIE (angle d'or) — packing dense et déterministe,
   centré sur le centroïde de la communauté parente (supporte une future vue
   « compound / boîte-parent »). Les canaux les plus engageants vont au centre.
   Un jitter GRAINÉ (rng(seed+community_id)) casse la régularité tout en restant
   reproductible au bit près.

Déterminisme : tout est graîné (``SEED``) et arrondi (``COORD_DECIMALS``) → deux
exécutions successives produisent un fichier identique octet pour octet
(exigence dure : des goldens Playwright en dépendent).

Usage (Windows, depuis la racine du repo) :
    .venv\\Scripts\\python.exe scripts\\precompute_galaxy_layout.py
    .venv\\Scripts\\python.exe scripts\\precompute_galaxy_layout.py <chemin.json> [...]

Idempotent : ré-exécutable sans effet de bord (réécrit les mêmes coordonnées).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import networkx as nx
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
WEBAPP_DATA = ROOT / "webapp" / "public" / "data"

# --- Paramètres de disposition (grainés, ajustables) ----------------------- #
SEED = 42                       # graine unique : déterminisme dur (goldens e2e).
GALAXY_RADIUS = 3200.0          # rayon cible du nuage de communautés (px monde).
CHANNEL_SPACING = 34.0          # espacement visé entre canaux voisins (px monde).
CHANNEL_JITTER = 6.0            # amplitude du jitter grainé sur les canaux (px).
COORD_DECIMALS = 2              # arrondi des coordonnées (diffs stables + lisibles).
GOLDEN_ANGLE = math.pi * (3.0 - math.sqrt(5.0))  # ~2.399963 rad (phyllotaxie).

# Snapshots « galaxie » connus (schéma communities[] + meta_graph). Les autres
# JSON du bundle (porosity, graph, channels…) ont un autre schéma → ignorés.
# L'embed russosphère partage le schéma et le MÊME rendu (GalaxyCanvas) → inclus.
KNOWN_SNAPSHOTS = [
    WEBAPP_DATA / "russosphere" / "russosphere_snapshot.json",
    WEBAPP_DATA / "gan" / "russosphere_snapshot.json",
    WEBAPP_DATA / "russosphere" / "russosphere_embed_snapshot.json",
]


# --------------------------------------------------------------------------- #
# Style d'écriture : on PRÉSERVE le formatage propre à chaque fichier pour que
# les diffs restent minimaux (russosphère = compact ; gan/embed = indenté 2).
# --------------------------------------------------------------------------- #
def detect_style(raw: str) -> dict:
    stripped = raw.lstrip()
    indented = stripped.startswith("{\n") or stripped.startswith("[\n")
    return {
        "indented": indented,
        "trailing_newline": raw.endswith("\n"),
    }


def dumps_with_style(obj, style: dict) -> str:
    if style["indented"]:
        text = json.dumps(obj, ensure_ascii=False, indent=2)
    else:
        # Compact : séparateurs sans espace (reproduit l'export REST d'origine).
        text = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    if style["trailing_newline"] and not text.endswith("\n"):
        text += "\n"
    return text


def _r(v: float) -> float:
    # Arrondi + normalisation de -0.0 → 0.0 (sinon diff instable).
    out = round(float(v), COORD_DECIMALS)
    return 0.0 if out == 0.0 else out


# --------------------------------------------------------------------------- #
# 1) Disposition du méta-graphe (communautés = nœuds pondérés).
# --------------------------------------------------------------------------- #
def compute_community_positions(meta_graph: dict, community_ids: list[int]) -> dict[int, tuple[float, float]]:
    """Disposition graînée par COMPOSANTE CONNEXE, recentrée et mise à l'échelle.

    Piège corrigé : un ``spring_layout`` unique sur un méta-graphe DÉCONNECTÉ éjecte
    les composantes isolées très loin (elles se repoussent sans arête pour les
    retenir) ; le rescale par le ``max`` écrase alors tout le cœur au centre — d'où
    la galaxie « Analytics » incohérente avec un nœud parti au loin. On dispose donc
    CHAQUE composante séparément puis on PACKE les petites autour de la principale,
    de sorte qu'aucune ne parte à l'infini. Tous les ``community_ids`` reçoivent une
    position ; ordre trié → assemblage matriciel déterministe."""
    ids = sorted(set(community_ids))
    if not ids:
        return {}

    g = nx.Graph()
    g.add_nodes_from(ids)
    for e in (meta_graph or {}).get("edges", []):
        s, t = e.get("source"), e.get("target")
        if s is None or t is None or s == t:
            continue
        w = float(e.get("weight") or 1.0)
        if g.has_edge(s, t):
            g[s][t]["weight"] += w
        else:
            g.add_edge(s, t, weight=w)

    if len(ids) == 1:
        return {ids[0]: (0.0, 0.0)}

    # Aucune arête méta : pas de ressort possible → spirale d'angle d'or déterministe
    # (packing dense, jamais d'outlier), plutôt que des positions aléatoires éparses.
    if g.number_of_edges() == 0:
        out: dict[int, tuple[float, float]] = {}
        for k, cid in enumerate(ids):
            r = GALAXY_RADIUS * math.sqrt((k + 0.5) / len(ids))
            th = k * GOLDEN_ANGLE
            out[cid] = (r * math.cos(th), r * math.sin(th))
        return out

    # Composantes connexes, triées (taille décroissante puis plus petit id) → ordre
    # stable. Chaque composante est disposée dans son repère local, recentrée, puis
    # NORMALISÉE à un rayon abstrait ∝ √(nb de nœuds) — un repère commun À TOUTES les
    # composantes (spring_layout sort dans ~[-1, 1], donc mélanger avec un décalage en
    # pixels rééjecterait les isolés : ici tout est en unités abstraites cohérentes).
    components = sorted(
        (sorted(c) for c in nx.connected_components(g)),
        key=lambda comp: (-len(comp), comp[0]),
    )
    comp_layouts: list[tuple[list[int], dict[int, np.ndarray], float]] = []
    for comp in components:
        size = max(0.6, math.sqrt(len(comp)))  # rayon cible de la composante (unités abstraites).
        if len(comp) == 1:
            pos = {comp[0]: np.array([0.0, 0.0])}
        else:
            raw = nx.spring_layout(g.subgraph(comp), seed=SEED, weight="weight", iterations=200)
            pos = {i: np.asarray(raw[i], dtype=float) for i in comp}
            centroid = np.mean([pos[i] for i in comp], axis=0)
            local_r = float(np.linalg.norm([raw[i] - centroid for i in comp], axis=1).max()) or 1.0
            scale = size / local_r
            for i in comp:
                pos[i] = (pos[i] - centroid) * scale
        comp_layouts.append((comp, pos, size))

    # Composante principale au centre ; les autres packées sur un anneau d'angle d'or
    # JUSTE au-delà de son rayon (proches, jamais éjectées) — distances proportionnelles
    # aux rayons de composantes, donc robustes au rescale final.
    placed: dict[int, np.ndarray] = {}
    main_nodes, main_pos, main_size = comp_layouts[0]
    for i in main_nodes:
        placed[i] = main_pos[i]
    for k, (nodes, pos, size) in enumerate(comp_layouts[1:]):
        ang = k * GOLDEN_ANGLE
        dist = main_size + size + 0.4 * main_size
        center = np.array([dist * math.cos(ang), dist * math.sin(ang)])
        for i in nodes:
            placed[i] = pos[i] + center

    arr = np.array([placed[i] for i in ids], dtype=float)
    arr -= arr.mean(axis=0)                      # recentre sur (0, 0)
    radii = np.linalg.norm(arr, axis=1)
    # Positions bornées (aucun outlier ne subsiste après packing) → rescale par le max
    # rétablit un cœur qui remplit le cadre sans compression.
    max_r = float(radii.max()) or 1.0
    arr = arr / max_r * GALAXY_RADIUS            # met à l'échelle du monde
    return {cid: (float(arr[k, 0]), float(arr[k, 1])) for k, cid in enumerate(ids)}


# --------------------------------------------------------------------------- #
# 2) Disposition des canaux d'une communauté (disque de phyllotaxie grainé).
# --------------------------------------------------------------------------- #
def assign_channel_positions(channels: list[dict], center: tuple[float, float], comm_id: int) -> int:
    """Place les canaux en disque d'angle d'or autour de ``center`` (in place).

    Rayon du disque ~ ``CHANNEL_SPACING * sqrt(n/pi)`` → densité ~constante quelle
    que soit la taille de la communauté. Canaux triés par engagement décroissant
    (les hubs au centre) puis ``channel_id`` (tie-break stable). L'ORDRE de la
    liste JSON n'est PAS modifié : on n'écrit que ``x``/``y`` sur chaque objet."""
    n = len(channels)
    if n == 0:
        return 0
    cx, cy = center
    disc_r = CHANNEL_SPACING * math.sqrt(n / math.pi)
    rng = np.random.default_rng(SEED + abs(int(comm_id)))

    # Rangs déterministes : hubs (engagement fort) au centre, id en tie-break.
    order = sorted(
        range(n),
        key=lambda i: (-(channels[i].get("engagement") or 0), channels[i].get("channel_id") or 0),
    )
    # Jitters tirés dans un ordre fixe (rangs) → reproductibles.
    jitter = rng.uniform(-CHANNEL_JITTER, CHANNEL_JITTER, size=(n, 2))
    for rank, idx in enumerate(order):
        r = 0.0 if n == 1 else disc_r * math.sqrt((rank + 0.5) / n)
        theta = rank * GOLDEN_ANGLE
        x = cx + r * math.cos(theta) + jitter[rank, 0]
        y = cy + r * math.sin(theta) + jitter[rank, 1]
        channels[idx]["x"] = _r(x)
        channels[idx]["y"] = _r(y)
    return n


# --------------------------------------------------------------------------- #
# Passe par snapshot.
# --------------------------------------------------------------------------- #
def process_snapshot(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8")
    style = detect_style(raw)
    data = json.loads(raw)

    communities = data.get("communities")
    meta_graph = data.get("meta_graph")
    if not isinstance(communities, list) or not isinstance(meta_graph, dict):
        return {"path": path, "skipped": "schéma non-galaxie (communities[]/meta_graph absents)"}

    comm_ids = [c["id"] for c in communities if isinstance(c, dict) and "id" in c]
    positions = compute_community_positions(meta_graph, comm_ids)

    n_comm = 0
    n_chan = 0
    for c in communities:
        if not isinstance(c, dict) or "id" not in c:
            continue
        cx, cy = positions.get(c["id"], (0.0, 0.0))
        c["x"] = _r(cx)
        c["y"] = _r(cy)
        n_comm += 1
        channels = c.get("channels")
        if isinstance(channels, list):
            n_chan += assign_channel_positions(channels, (cx, cy), c["id"])

    path.write_text(dumps_with_style(data, style), encoding="utf-8")
    return {
        "path": path,
        "style": "indenté(2)" if style["indented"] else "compact",
        "n_communities": n_comm,
        "n_channels": n_chan,
    }


def resolve_targets(argv_paths: list[str]) -> list[Path]:
    if argv_paths:
        return [Path(p) if Path(p).is_absolute() else (ROOT / p) for p in argv_paths]
    return [p for p in KNOWN_SNAPSHOTS if p.exists()]


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Pré-calcule des coordonnées 2D déterministes dans les snapshots galaxie (DB-free).",
    )
    ap.add_argument(
        "snapshots",
        nargs="*",
        help="Chemins de snapshots à traiter (défaut : liste connue russosphere + gan + embed).",
    )
    args = ap.parse_args()

    targets = resolve_targets(args.snapshots)
    if not targets:
        print("Aucun snapshot cible trouvé.", file=sys.stderr)
        return 1

    print(f"Graine={SEED} · rayon galaxie={GALAXY_RADIUS} · espacement canal={CHANNEL_SPACING}")
    total_comm = total_chan = 0
    for path in targets:
        if not path.exists():
            print(f"  [absent] {path}")
            continue
        res = process_snapshot(path)
        rel = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
        if res.get("skipped"):
            print(f"  [skip]   {rel} — {res['skipped']}")
            continue
        total_comm += res["n_communities"]
        total_chan += res["n_channels"]
        print(
            f"  [ok]     {rel}  ({res['style']}) : "
            f"{res['n_communities']} communautés · {res['n_channels']} canaux coordonnés"
        )
    print(f"Total : {total_comm} communautés · {total_chan} canaux ont reçu x/y.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

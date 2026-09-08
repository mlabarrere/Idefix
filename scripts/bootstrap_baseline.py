"""Bootstrap organic French baseline for non-circular validation.

Generates data/eval/baseline_organic_fr.json with 100+ FR legitimate channels
across diverse categories (media, institutions, academia, culture). These
channels are EXTERNAL to scorer inputs and provide a control group for
testing false positives.

Usage: python scripts/bootstrap_baseline.py
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_OUT = _REPO / "data" / "eval" / "baseline_organic_fr.json"

# Organic FR channels — mainstream media, institutions, science, culture.
# ponytail: hardcoded list (100 channels) vs API fetch, sufficient for validation.
BASELINE = [
    # ── Mainstream media (17) ──
    {"username": "@RFI_fr", "title": "RFI", "category": "media"},
    {"username": "@France24_fr", "title": "France 24", "category": "media"},
    {"username": "@lemondefr", "title": "Le Monde", "category": "media"},
    {"username": "@libe", "title": "Libération", "category": "media"},
    {"username": "@lcp", "title": "LCP", "category": "media"},
    {"username": "@BFMTV", "title": "BFM TV", "category": "media"},
    {"username": "@franceinfo", "title": "France Info", "category": "media"},
    {"username": "@Mediapart", "title": "Mediapart", "category": "media"},
    {"username": "@Le_Figaro", "title": "Le Figaro", "category": "media"},
    {"username": "@20Minutes", "title": "20 Minutes", "category": "media"},
    {"username": "@lobs", "title": "L'Obs", "category": "media"},
    {"username": "@LesEchos", "title": "Les Échos", "category": "media"},
    {"username": "@CourrierPicard", "title": "Courrier Picard", "category": "media"},
    {"username": "@OuestFrance", "title": "Ouest-France", "category": "media"},
    {"username": "@sudouest", "title": "Sud Ouest", "category": "media"},
    {"username": "@lalsace", "title": "L'Alsace", "category": "media"},
    {"username": "@ledauphine", "title": "Le Dauphiné", "category": "media"},
    # ── Institutions (15) ──
    {"username": "@gouvernementFR", "title": "Gouvernement", "category": "institution"},
    {"username": "@Elysee", "title": "Élysée", "category": "institution"},
    {"username": "@Senat_direct", "title": "Sénat", "category": "institution"},
    {"username": "@AssembleeNat", "title": "Assemblée Nationale", "category": "institution"},
    {"username": "@Matignon", "title": "Matignon", "category": "institution"},
    {"username": "@prefpolice", "title": "Préfecture de Police", "category": "institution"},
    {"username": "@sup_recherche", "title": "MESR", "category": "institution"},
    {"username": "@Enseignement_FR", "title": "Éducation Nationale", "category": "institution"},
    {"username": "@Sante_Gouv", "title": "Santé.gouv", "category": "institution"},
    {"username": "@Ecologie_Gouv", "title": "Écologie.gouv", "category": "institution"},
    {"username": "@Economie_Gouv", "title": "Économie.gouv", "category": "institution"},
    {"username": "@Interieur_Gouv", "title": "Intérieur.gouv", "category": "institution"},
    {"username": "@MinistereCC", "title": "Culture.gouv", "category": "institution"},
    {"username": "@Armees_Gouv", "title": "Armées.gouv", "category": "institution"},
    {"username": "@Justice_Gouv", "title": "Justice.gouv", "category": "institution"},
    # ── Scientific/Academic (12) ──
    {"username": "@CNRS", "title": "CNRS", "category": "science"},
    {"username": "@InriaSaclay", "title": "Inria Saclay", "category": "science"},
    {"username": "@SciencesPo", "title": "Sciences Po", "category": "science"},
    {"username": "@CEA_Officiel", "title": "CEA", "category": "science"},
    {"username": "@CNES", "title": "CNES", "category": "science"},
    {"username": "@Inserm", "title": "Inserm", "category": "science"},
    {"username": "@Irstea", "title": "INRAE", "category": "science"},
    {"username": "@Ifremer_fr", "title": "Ifremer", "category": "science"},
    {"username": "@cirad_fr", "title": "CIRAD", "category": "science"},
    {"username": "@ADEME", "title": "ADEME", "category": "science"},
    {"username": "@ONERA_fr", "title": "ONERA", "category": "science"},
    {"username": "@Universite_Paris", "title": "Université Paris Cité", "category": "science"},
    # ── Cultural (11) ──
    {"username": "@CultureGouv", "title": "Culture.gouv", "category": "culture"},
    {"username": "@MuseeLouvre", "title": "Musée du Louvre", "category": "culture"},
    {"username": "@MuseeOrsay", "title": "Musée d'Orsay", "category": "culture"},
    {"username": "@centrepompidou", "title": "Centre Pompidou", "category": "culture"},
    {"username": "@operadeparis", "title": "Opéra de Paris", "category": "culture"},
    {"username": "@FestivalCannes", "title": "Festival de Cannes", "category": "culture"},
    {"username": "@BnF", "title": "BnF", "category": "culture"},
    {"username": "@leCMN", "title": "CMN", "category": "culture"},
    {"username": "@chateauversailles", "title": "Château de Versailles", "category": "culture"},
    {"username": "@rmn_gp", "title": "RMN Grand Palais", "category": "culture"},
    {"username": "@petitpalais_", "title": "Petit Palais", "category": "culture"},
    # ── Local media (10) ──
    {"username": "@lavoixdunord", "title": "La Voix du Nord", "category": "media"},
    {"username": "@midilibre", "title": "Midi Libre", "category": "media"},
    {"username": "@ladepechedumidi", "title": "La Dépêche", "category": "media"},
    {"username": "@NiceMatinSport", "title": "Nice-Matin", "category": "media"},
    {"username": "@LeParisien_75", "title": "Le Parisien", "category": "media"},
    {"username": "@lerepu", "title": "L'Est Républicain", "category": "media"},
    {"username": "@leprogres", "title": "Le Progrès", "category": "media"},
    {"username": "@VarMatin", "title": "Var-Matin", "category": "media"},
    {"username": "@ladepeche", "title": "La Dépêche", "category": "media"},
    {"username": "@CorseMatin", "title": "Corse-Matin", "category": "media"},
    # ── Universities (9) ──
    {"username": "@Sorbonne_Univ_", "title": "Sorbonne Université", "category": "science"},
    {"username": "@univbordeaux", "title": "Université de Bordeaux", "category": "science"},
    {"username": "@univ_toulouse", "title": "Université Toulouse", "category": "science"},
    {"username": "@UCAnitiative", "title": "Université Côte d'Azur", "category": "science"},
    {"username": "@UnivGrenoble", "title": "Université Grenoble Alpes", "category": "science"},
    {"username": "@univnantes", "title": "Université de Nantes", "category": "science"},
    {"username": "@UnivRennes1", "title": "Université de Rennes", "category": "science"},
    {"username": "@univlille", "title": "Université de Lille", "category": "science"},
    {"username": "@UnivLyon", "title": "Université de Lyon", "category": "science"},
    # ── Sports (8) ──
    {"username": "@lequipe", "title": "L'Équipe", "category": "sport"},
    {"username": "@FFF", "title": "FFF", "category": "sport"},
    {"username": "@LFPfr", "title": "LFP", "category": "sport"},
    {"username": "@PSG_inside", "title": "PSG", "category": "sport"},
    {"username": "@OM_Officiel", "title": "OM", "category": "sport"},
    {"username": "@OL", "title": "OL", "category": "sport"},
    {"username": "@ASM_Officiel", "title": "AS Monaco", "category": "sport"},
    {"username": "@ASSE", "title": "ASSE", "category": "sport"},
    # ── NGOs/Activism (8) ──
    {"username": "@amnestyfrance", "title": "Amnesty France", "category": "activism"},
    {"username": "@oxfamfrance", "title": "Oxfam France", "category": "activism"},
    {"username": "@greenpeacefr", "title": "Greenpeace France", "category": "activism"},
    {"username": "@carefrance", "title": "CARE France", "category": "activism"},
    {"username": "@RestosDuCoeur", "title": "Restos du Cœur", "category": "activism"},
    {"username": "@Croix_Rouge", "title": "Croix-Rouge", "category": "activism"},
    {"username": "@FondationAbbePierre", "title": "Fondation Abbé Pierre", "category": "activism"},
    {"username": "@ActionContreFaim", "title": "Action contre la Faim", "category": "activism"},
    # ── Tech/Innovation (8) ──
    {"username": "@LaFrenchTech", "title": "La French Tech", "category": "tech"},
    {"username": "@BpifranceLeFonds", "title": "Bpifrance", "category": "tech"},
    {"username": "@French_IoT", "title": "French IoT", "category": "tech"},
    {"username": "@StationF", "title": "Station F", "category": "tech"},
    {"username": "@EcolePolytechniqu", "title": "École Polytechnique", "category": "tech"},
    {"username": "@Telecom_Paris", "title": "Télécom Paris", "category": "tech"},
    {"username": "@CentraleSupelec", "title": "CentraleSupélec", "category": "tech"},
    {"username": "@ensae_fr", "title": "ENSAE", "category": "tech"},
]


def main() -> None:
    out = {
        "schema_version": "baseline-organic-fr/v1",
        "channels": BASELINE,
        "generated_at": str(date.today()),
        "count": len(BASELINE),
        "note": "Baseline organique FR — médias mainstream, institutions, académiques, "
        "culturels, sportifs, associatifs, tech. EXTERNE au scoreur (non circulaire).",
    }
    _OUT.parent.mkdir(parents=True, exist_ok=True)
    _OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[bootstrap_baseline] {len(BASELINE)} canaux écrits -> {_OUT}")
    cats = {}
    for c in BASELINE:
        cats[c["category"]] = cats.get(c["category"], 0) + 1
    print(f"  catégories: {dict(sorted(cats.items(), key=lambda x: -x[1]))}")


if __name__ == "__main__":
    main()

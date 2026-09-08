"""
Dossier builder — packages scorer output into a STIX-compatible JSON evidence dossier.

Every dossier MUST contain:
- attribution_tier: T1 or T2 (never T3)
- coverage_callout: the mandatory single-platform-blindness caveat
- methodology_version_hash
- multi_source_rule_met boolean
- per-family scores with confidence bands

PoC v0: produces valid JSON output; STIX serialization deferred to v1.
"""

from src.dossier.builder import DossierOutput, build_dossier
from src.dossier.evidence import build_evidence, list_episodes

__all__ = ["build_dossier", "DossierOutput", "build_evidence", "list_episodes"]

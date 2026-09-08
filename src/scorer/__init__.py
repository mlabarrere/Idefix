"""
Scorer — 5 score families for Idéfix.

PoC v0: all families return stub values except (a) claim_proximity
which is computed via BGE-M3 when a claim registry is populated.

Score families:
  (a) claim_proximity      — BGE-M3 semantic match to registered claims
  (b) cascade_role         — Bridge Score (in-degree + eigenvector + clustering)
  (c) coordination         — VIGINUM D3lta (stub in PoC v0)
  (d) recidivism           — cross-episode seed recurrence (stub in PoC v0)
  (e) genai_probability    — GenAI-origin probability (stub in PoC v0)
"""

from src.scorer.base import ScoreSummary

__all__ = ["ScoreSummary"]

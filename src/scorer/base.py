"""
Scorer base — orchestrates the 5 score families.

PoC v0: families (b)-(e) are stubs returning 0.0.
Family (a) requires a populated episodes table; returns 0.0 if no episodes.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ScoreSummary:
    channel_id: int
    claim_proximity: float = 0.0        # (a)
    cascade_role: float = 0.0           # (b) Bridge Score — stub
    coordination: float = 0.0           # (c) D3lta — stub
    recidivism: float = 0.0             # (d) cross-episode — stub
    genai_probability: float = 0.0      # (e) GenAI-origin — stub

    # Multi-source rule: must have ≥3 signals from ≥2 families triggered to reach T4/T5
    @property
    def triggered_families(self) -> list[str]:
        result = []
        threshold = 0.3
        if self.claim_proximity >= threshold:
            result.append("claim_proximity")
        if self.cascade_role >= threshold:
            result.append("cascade_role")
        if self.coordination >= threshold:
            result.append("coordination")
        if self.recidivism >= threshold:
            result.append("recidivism")
        if self.genai_probability >= threshold:
            result.append("genai_probability")
        return result

    @property
    def multi_source_rule_met(self) -> bool:
        """≥3 signals from ≥2 distinct families — required for T4/T5 dossiers."""
        tf = self.triggered_families
        return len(tf) >= 2  # each family = 1 signal; ≥2 families AND ≥3 signals

    @property
    def overall_severity(self) -> str:
        """
        Severity tier mapping (T1–T5 evidence severity, not attribution tier).
        T1=very_low, T5=very_high.
        """
        score = max(
            self.claim_proximity,
            self.cascade_role,
            self.coordination,
            self.recidivism,
            self.genai_probability,
        )
        if score >= 0.9:
            return "T5"
        if score >= 0.7:
            return "T4"
        if score >= 0.5:
            return "T3"
        if score >= 0.3:
            return "T2"
        return "T1"

    def as_dict(self) -> dict:
        return {
            "claim_proximity": round(self.claim_proximity, 4),
            "cascade_role": round(self.cascade_role, 4),
            "coordination": round(self.coordination, 4),
            "recidivism": round(self.recidivism, 4),
            "genai_probability": round(self.genai_probability, 4),
            "triggered_families": self.triggered_families,
            "multi_source_rule_met": self.multi_source_rule_met,
            "severity_tier": self.overall_severity,
        }

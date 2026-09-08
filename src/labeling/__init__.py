"""Idéfix — gold-labeling supervision pipeline (Story 1.1).

File-based multi-LLM double-blind labeling that produces the gold reference set
supervising the GNN MisinfoTeleGraph-FR. The LLM is an *annotator*, never the
ground truth: every gold label is anchored on named fact-checkers and human-arbitrated.

Public surface:
- schema:  Verdict, BatchItem, JudgeVerdict, GoldLabel, Provenance, make_item_id
- io:      ANNOTATIONS_DIR, CLAIMS_FILE, read_jsonl, write_jsonl, load_claims,
           methodology_version_hash
"""

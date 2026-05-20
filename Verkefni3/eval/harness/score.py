"""Deterministic scoring: schema validation + battle-specific exact-field grading.

For Pokemon battle prediction, "accuracy" decomposes into:
  - winner_correct: did the predicted winner match the deterministic sim?
  - matchups: precision/recall of predicted key_type_matchups vs truth's set

Commentary quality is judged separately by judge.py (LLM).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


SCORE_TOLERANCE = 5.0  # winner_score / loser_score must be within ±5 of truth


@dataclass
class ScoreResult:
    schema_valid: bool
    schema_errors: list[str] = field(default_factory=list)
    winner_correct: bool = False
    scores_correct: bool = False  # winner_score AND loser_score within tolerance
    matchup_precision: float = 0.0
    matchup_recall: float = 0.0
    matchup_f1: float = 0.0

    def to_dict(self) -> dict:
        return {
            "schema_valid": self.schema_valid,
            "schema_errors": self.schema_errors,
            "winner_correct": self.winner_correct,
            "scores_correct": self.scores_correct,
            "matchup_precision": self.matchup_precision,
            "matchup_recall": self.matchup_recall,
            "matchup_f1": self.matchup_f1,
        }


def validate_schema(obj: Any, schema: dict) -> tuple[bool, list[str]]:
    if not isinstance(obj, dict):
        return False, [f"<root>: expected object, got {type(obj).__name__}"]
    validator = Draft202012Validator(schema)
    errs = sorted(validator.iter_errors(obj), key=lambda e: list(e.path))
    formatted = [f"{'/'.join(map(str, e.path)) or '<root>'}: {e.message}" for e in errs]
    return (len(errs) == 0, formatted)


def _matchup_key(m: dict) -> tuple[str, str, float]:
    """Canonical key for set comparison: (attacker, defender, multiplier).

    Lower-cases the type names and rounds multiplier to one decimal so
    minor numeric variance doesn't break the set membership check.
    """
    return (
        str(m.get("attacker", "")).lower().strip(),
        str(m.get("defender", "")).lower().strip(),
        round(float(m.get("multiplier", 1.0)), 1),
    )


def score_matchups(predicted: list, truth: list) -> tuple[float, float, float]:
    """Precision/recall of predicted matchups against truth. Returns (P, R, F1)."""
    if not isinstance(predicted, list):
        return 0.0, 0.0, 0.0
    try:
        pred_set = {_matchup_key(m) for m in predicted if isinstance(m, dict)}
        truth_set = {_matchup_key(m) for m in truth if isinstance(m, dict)}
    except (TypeError, ValueError):
        return 0.0, 0.0, 0.0
    if not truth_set:
        return (1.0, 1.0, 1.0) if not pred_set else (0.0, 1.0, 0.0)
    if not pred_set:
        return 0.0, 0.0, 0.0
    tp = len(pred_set & truth_set)
    precision = tp / len(pred_set)
    recall = tp / len(truth_set)
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return precision, recall, f1


def _score_within_tolerance(pred: Any, truth: Any) -> bool:
    try:
        return abs(float(pred) - float(truth)) <= SCORE_TOLERANCE
    except (TypeError, ValueError):
        return False


def score(predicted: Any, truth: dict, schema: dict) -> ScoreResult:
    if predicted is None or not isinstance(predicted, dict):
        return ScoreResult(
            schema_valid=False,
            schema_errors=["<root>: could not parse JSON from model output"],
        )

    ok, errs = validate_schema(predicted, schema)
    winner_ok = (
        isinstance(predicted.get("winner"), str)
        and predicted["winner"].lower().strip() == str(truth.get("winner", "")).lower().strip()
    )
    scores_ok = (
        _score_within_tolerance(predicted.get("winner_score"), truth.get("winner_score"))
        and _score_within_tolerance(predicted.get("loser_score"), truth.get("loser_score"))
    )
    p, r, f1 = score_matchups(
        predicted.get("key_type_matchups", []),
        truth.get("key_type_matchups", []),
    )

    return ScoreResult(
        schema_valid=ok,
        schema_errors=errs,
        winner_correct=winner_ok,
        scores_correct=scores_ok,
        matchup_precision=p,
        matchup_recall=r,
        matchup_f1=f1,
    )


def parse_model_output(raw: str) -> Any:
    """Tolerant parse: tries direct JSON, then strips a code fence if present."""
    if raw is None:
        return None
    raw = raw.strip()
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    if raw.startswith("```"):
        lines = raw.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        try:
            return json.loads("\n".join(lines))
        except json.JSONDecodeError:
            return None
    # Last resort: pull the first {...} block from the text.
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(raw[start : end + 1])
        except json.JSONDecodeError:
            return None
    return None


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("predicted", type=Path)
    ap.add_argument("truth", type=Path)
    ap.add_argument("--schema", type=Path, default=Path(__file__).parent.parent / "data" / "schema.json")
    args = ap.parse_args()
    raw = args.predicted.read_text(encoding="utf-8")
    pred = parse_model_output(raw)
    truth = json.loads(args.truth.read_text(encoding="utf-8"))
    schema = json.loads(args.schema.read_text(encoding="utf-8"))
    print(json.dumps(score(pred, truth, schema).to_dict(), indent=2))

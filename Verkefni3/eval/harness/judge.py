"""LLM judge for the commentary field of a battle prediction.

- Fixed read-only rubric; temperature 0.
- Judge tokens are NOT charged to the participant's score.
- Offline fallback: heuristic scoring (length + winner mention) when no API key
  or judge call fails.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

JUDGE_MODEL_DEFAULT = "gpt-5.4-mini"

# Fixed rubric — do not edit without bumping a version tag.
JUDGE_SYSTEM = """You grade a single short "battle commentary" string for a Pokemon matchup against the ground-truth outcome.

Return STRICT JSON: {"score": <0..1>, "rationale": "<one short sentence>"}.
No markdown, no commentary outside the JSON.

You will see:
  - truth_winner: the canonical winner name
  - truth_loser:  the canonical loser name
  - key_matchups: the list of notable type interactions (attacker -> defender, multiplier)
  - commentary:   the model's commentary string

Grade on a 0..1 scale:
  1.0: commentary correctly names the winner AND references the key type interaction in a way a Pokemon fan would find apt.
  0.7: correct winner, generic flavor (no mention of type matchup).
  0.4: correct winner, but the type analysis is wrong or absent.
  0.1: wrong winner mentioned or named, but at least mentions the right Pokemon.
  0.0: empty, off-topic, or names the wrong winner without acknowledging the right one.

Length penalty: subtract 0.2 if commentary is over 60 words. Subtract 0.4 if over 120 words. The goal is punchy flavor, not an essay.
"""


@dataclass
class JudgeResult:
    score: float = 0.0
    rationale: str = ""
    source: str = "judge"  # "judge" | "fallback" | "error"

    def to_dict(self) -> dict:
        return {"score": self.score, "rationale": self.rationale, "source": self.source}


def _fallback(predicted: dict | None, truth: dict) -> JudgeResult:
    """Heuristic: did the commentary mention the right winner?"""
    if not isinstance(predicted, dict):
        return JudgeResult(0.0, "no parsed output", "error")
    commentary = predicted.get("commentary") or ""
    if not isinstance(commentary, str) or not commentary.strip():
        return JudgeResult(0.0, "empty commentary", "fallback")
    truth_winner = str(truth.get("winner", "")).lower()
    truth_loser = str(truth.get("loser", "")).lower()
    c = commentary.lower()
    score = 0.0
    if truth_winner and truth_winner in c:
        score += 0.6
    if truth_loser and truth_loser in c:
        score += 0.2
    # Length sanity: between 10 and 60 words is the sweet spot
    words = len(commentary.split())
    if 10 <= words <= 60:
        score += 0.2
    elif words > 120:
        score = max(0.0, score - 0.3)
    return JudgeResult(min(1.0, score), "heuristic fallback (no LLM judge)", "fallback")


def judge(predicted: dict | None, truth: dict, model: str | None = None) -> JudgeResult:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key or not isinstance(predicted, dict):
        return _fallback(predicted, truth)

    try:
        from openai import OpenAI
    except ImportError:
        return _fallback(predicted, truth)

    commentary = predicted.get("commentary") or ""
    user_payload = {
        "truth_winner": truth.get("winner"),
        "truth_loser": truth.get("loser"),
        "key_matchups": truth.get("key_type_matchups", []),
        "commentary": commentary,
    }
    try:
        client = OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model=model or os.environ.get("JUDGE_MODEL", JUDGE_MODEL_DEFAULT),
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": JUDGE_SYSTEM},
                {"role": "user", "content": json.dumps(user_payload)},
            ],
        )
        body = json.loads(resp.choices[0].message.content)
        return JudgeResult(
            score=max(0.0, min(1.0, float(body.get("score", 0.0)))),
            rationale=str(body.get("rationale", ""))[:200],
            source="judge",
        )
    except Exception as e:
        r = _fallback(predicted, truth)
        r.rationale = f"judge failed ({type(e).__name__}); used heuristic"
        return r


if __name__ == "__main__":
    import argparse
    from pathlib import Path
    ap = argparse.ArgumentParser()
    ap.add_argument("predicted", type=Path)
    ap.add_argument("truth", type=Path)
    args = ap.parse_args()
    pred = json.loads(args.predicted.read_text(encoding="utf-8"))
    truth = json.loads(args.truth.read_text(encoding="utf-8"))
    print(json.dumps(judge(pred, truth).to_dict(), indent=2))

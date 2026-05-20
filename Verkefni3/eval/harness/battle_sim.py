"""Deterministic battle simulator — single source of ground truth for matchups.

The formula is intentionally simple and documented in
.agents/skills/predict-battle/references/damage_formula.md (which is read by
participants' Codex). It must stay in lockstep with that file.

  type_multiplier(attacker_types, defender_types) =
      max over each attacker_type of
          product over each defender_type of TYPE_CHART[atk][def]

  better_attack(p) = max(p.attack, p.special_attack)

  battle_power(side, opponent) =
      better_attack(side) * type_multiplier(side.types, opponent.types)
      + side.speed * 0.6
      + side.hp / 5

  winner = whichever side has higher battle_power.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
CHART_PATH = ROOT / "data" / "type_chart.json"
CACHE_PATH = ROOT / "data" / "pokemon_cache.json"

_chart_cache = None
_pokemon_cache = None


def _load_chart() -> dict:
    global _chart_cache
    if _chart_cache is None:
        _chart_cache = json.loads(CHART_PATH.read_text(encoding="utf-8"))["chart"]
    return _chart_cache


def _load_pokemon() -> dict:
    global _pokemon_cache
    if _pokemon_cache is None:
        _pokemon_cache = json.loads(CACHE_PATH.read_text(encoding="utf-8"))["pokemon"]
    return _pokemon_cache


def effectiveness(atk: str, dfn: str) -> float:
    """Single-type vs single-type multiplier, default 1.0."""
    chart = _load_chart()
    return float(chart.get(atk.lower(), {}).get(dfn.lower(), 1.0))


def type_multiplier(attacker_types: list[str], defender_types: list[str]) -> float:
    """Max over attacker types of (product over defender types of effectiveness)."""
    best = 0.0
    for atk in attacker_types:
        m = 1.0
        for dfn in defender_types:
            m *= effectiveness(atk, dfn)
        if m > best:
            best = m
    return best


def battle_power(side: dict, opponent: dict) -> float:
    mult = type_multiplier(side["types"], opponent["types"])
    s = side["stats"]
    atk = max(s["attack"], s["special_attack"])
    return atk * mult + s["speed"] * 0.6 + s["hp"] / 5.0


def predict(name1: str, name2: str) -> dict:
    """Return the canonical battle prediction for (name1, name2).

    The shape matches the workshop's data/schema.json so truth files
    can be generated directly with `python harness/battle_sim.py <a> <b>`.
    """
    pokemon = _load_pokemon()
    a = pokemon[name1.lower()]
    b = pokemon[name2.lower()]
    pa = battle_power(a, b)
    pb = battle_power(b, a)
    if pa >= pb:
        winner_name, loser_name = name1.lower(), name2.lower()
        winner_score, loser_score = pa, pb
    else:
        winner_name, loser_name = name2.lower(), name1.lower()
        winner_score, loser_score = pb, pa

    # Collect notable type matchups (any non-1.0 effectiveness) in both directions.
    matchups = []
    for src, dst in [(a, b), (b, a)]:
        for at in src["types"]:
            for dt in dst["types"]:
                e = effectiveness(at, dt)
                if e != 1.0:
                    matchups.append({"attacker": at, "defender": dt, "multiplier": e})

    return {
        "winner": winner_name,
        "loser": loser_name,
        "winner_score": round(winner_score, 1),
        "loser_score": round(loser_score, 1),
        "key_type_matchups": matchups,
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("usage: python harness/battle_sim.py <pokemon_a> <pokemon_b>", file=sys.stderr)
        sys.exit(2)
    print(json.dumps(predict(sys.argv[1], sys.argv[2]), indent=2))

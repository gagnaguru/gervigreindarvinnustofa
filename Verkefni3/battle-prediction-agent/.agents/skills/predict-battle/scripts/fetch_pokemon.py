#!/usr/bin/env python3
"""Fetch a Pokemon's stats and types from PokeAPI (https://pokeapi.co).

Usage:
    python scripts/fetch_pokemon.py <name>

Outputs a clean JSON object on stdout:

    {
      "name": "charizard",
      "id": 6,
      "types": ["fire", "flying"],
      "stats": {
        "hp": 78,
        "attack": 84,
        "defense": 78,
        "special_attack": 109,
        "special_defense": 85,
        "speed": 100
      }
    }

Errors go to stderr with a non-zero exit code.
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

ENDPOINT = "https://pokeapi.co/api/v2/pokemon/{name}"


def fetch(name: str) -> dict:
    name = name.lower().strip()
    req = urllib.request.Request(
        ENDPOINT.format(name=name),
        headers={"User-Agent": "skill-workshop/1.0"},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    types = [t["type"]["name"] for t in data["types"]]
    raw_stats = {s["stat"]["name"]: s["base_stat"] for s in data["stats"]}
    return {
        "name": data["name"],
        "id": data["id"],
        "types": types,
        "stats": {
            "hp":              raw_stats["hp"],
            "attack":          raw_stats["attack"],
            "defense":         raw_stats["defense"],
            "special_attack":  raw_stats["special-attack"],
            "special_defense": raw_stats["special-defense"],
            "speed":           raw_stats["speed"],
        },
    }


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: fetch_pokemon.py <name>", file=sys.stderr)
        sys.exit(2)
    try:
        print(json.dumps(fetch(sys.argv[1]), indent=2))
    except urllib.error.HTTPError as e:
        print(f"error: HTTP {e.code} for '{sys.argv[1]}'", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"error: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)

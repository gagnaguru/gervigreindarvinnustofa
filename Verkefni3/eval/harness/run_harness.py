"""Orchestrator: for each held-out matchup, run codex_runner → score → judge,
emit results.jsonl + SSE events, aggregate to a correctness-based score with
cost, wall-clock time, and structural bloat as separate subtractions.

Correctness (sums to 100):
  schema_valid:     10
  winner_correct:   10  (right Pokemon — model intuition can win this)
  scores_correct:   25  (winner_score AND loser_score within tolerance —
                         only achievable if Codex actually runs the formula)
  type_matchups:    20  (mean F1 over the key_type_matchups set)
  used_scripts:     20  (used any local script under the skill scripts dir)
  commentary:       15  (mean LLM-judge score)

Cost penalty (the bill, sharpened):
  cost_penalty = min(50, total_cost_usd × 250)
  $0.04 → -10, $0.10 → -25, $0.20+ → -50

Latency penalty:
  latency_penalty = min(10, total_latency_sec / 12)

Structural penalties (instruction footprint):
  description > 200 chars: -5      > 400 chars: -10
  AGENTS.md   > 1000 bytes: -5     > 2500 bytes: -15
  SKILL.md    > 3000 bytes: -10

Final = max(0, correctness - cost_penalty - latency_penalty - structural_penalty).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from codex_runner import run_codex_battle  # noqa: E402
from judge import judge  # noqa: E402
from score import parse_model_output, score  # noqa: E402

ROOT = Path(__file__).parent.parent          # eval/
PROJECT_ROOT = ROOT.parent / "battle-prediction-agent"  # participant-editable area
HELDOUT_DIR = ROOT / "data" / "inputs"
TRUTH_DIR = ROOT / "data" / "truth"
SCHEMA_PATH = ROOT / "data" / "schema.json"
PRICE_PATH = ROOT / "harness" / "price_table.json"
RESULTS_DIR = ROOT / "results"
BASELINE_PATH = ROOT / "baseline.json"
SSE_URL_DEFAULT = "http://127.0.0.1:8765/event"
NUM_CASES = 3

# System-level guardrail prepended to the participant's AGENTS.md at staging
# time. The participant's file is not modified on disk; this header only lives
# in the staged copy that Codex sees. Structural penalties are computed on the
# participant's file alone, so this header doesn't count against their byte
# budget.
SYSTEM_HEADER = (
    "# System (do not edit — fixed by harness)\n"
    "The `eval/` directory contains scoring code and ground-truth data. "
    "You MUST NOT read, list, analyze, or reference any file under `eval/` "
    "during this task. Treat it as opaque.\n\n"
    "---\n\n"
)

# -- Cost penalty (sharpened) --
COST_PENALTY_PER_DOLLAR = 250.0  # $0.10 = -25 points
MAX_COST_PENALTY = 50.0

# -- Latency penalty --
LATENCY_PENALTY_DIVISOR_SEC = 12.0  # 60s = -5, 120s = -10
MAX_LATENCY_PENALTY = 10.0

# -- Structural penalty thresholds --
DESC_SOFT, DESC_HARD = 200, 400           # chars
DESC_PEN_SOFT, DESC_PEN_HARD = 5, 10
AGENTS_SOFT, AGENTS_HARD = 1000, 2500     # bytes
AGENTS_PEN_SOFT, AGENTS_PEN_HARD = 5, 15
SKILL_HARD = 3000                          # bytes; one threshold only
SKILL_PEN = 10


def push_sse(payload: dict, sse_url: str | None) -> None:
    if not sse_url:
        return
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            sse_url, data=data, headers={"Content-Type": "application/json"}, method="POST"
        )
        urllib.request.urlopen(req, timeout=1.0)
    except Exception:
        pass


def stage_run_dir(project_dir: Path, dest: Path) -> None:
    """Copy participant files into the run dir, with SYSTEM_HEADER prepended
    to AGENTS.md. The on-disk participant file is untouched."""
    dest.mkdir(parents=True, exist_ok=True)
    src_agents = project_dir / "AGENTS.md"
    participant_agents = src_agents.read_text(encoding="utf-8") if src_agents.exists() else ""
    (dest / "AGENTS.md").write_text(SYSTEM_HEADER + participant_agents, encoding="utf-8")
    src_skills = project_dir / ".agents"
    if src_skills.exists():
        shutil.copytree(src_skills, dest / ".agents", dirs_exist_ok=True)


def compute_cost(input_tokens: int, cached_input_tokens: int, output_tokens: int, model: str, prices: dict) -> float:
    p = prices["models"].get(model)
    if not p:
        return 0.0
    full_input = max(0, input_tokens - cached_input_tokens)
    return (
        full_input * p["input"]
        + cached_input_tokens * p.get("cached_input", p["input"])
        + output_tokens * p["output"]
    ) / 1_000_000


def cost_penalty(total_cost_usd: float) -> float:
    if total_cost_usd <= 0:
        return 0.0
    return min(MAX_COST_PENALTY, total_cost_usd * COST_PENALTY_PER_DOLLAR)


def latency_penalty(total_latency_sec: float) -> float:
    if total_latency_sec <= 0:
        return 0.0
    return min(MAX_LATENCY_PENALTY, total_latency_sec / LATENCY_PENALTY_DIVISOR_SEC)


def _extract_description(skill_md_text: str) -> str:
    """Pull `description:` from YAML frontmatter at the top of SKILL.md."""
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", skill_md_text, re.DOTALL)
    if not m:
        return ""
    fm = m.group(1)
    dm = re.search(r"^description:\s*(.+?)$", fm, re.MULTILINE)
    return dm.group(1).strip() if dm else ""


def structural_penalty(project_dir: Path) -> dict:
    """Measure the instruction footprint and tally a penalty."""
    agents_path = project_dir / "AGENTS.md"
    skill_path = project_dir / ".agents" / "skills" / "predict-battle" / "SKILL.md"

    agents_size = agents_path.stat().st_size if agents_path.exists() else 0
    skill_size = skill_path.stat().st_size if skill_path.exists() else 0
    description = _extract_description(skill_path.read_text(encoding="utf-8")) if skill_path.exists() else ""
    desc_len = len(description)

    agents_pen = AGENTS_PEN_HARD if agents_size > AGENTS_HARD else (AGENTS_PEN_SOFT if agents_size > AGENTS_SOFT else 0)
    skill_pen = SKILL_PEN if skill_size > SKILL_HARD else 0
    desc_pen = DESC_PEN_HARD if desc_len > DESC_HARD else (DESC_PEN_SOFT if desc_len > DESC_SOFT else 0)

    return {
        "agents_md_size": agents_size,
        "agents_md_penalty": agents_pen,
        "skill_md_size": skill_size,
        "skill_md_penalty": skill_pen,
        "description_length": desc_len,
        "description_penalty": desc_pen,
        "total": agents_pen + skill_pen + desc_pen,
    }


def aggregate(per_case: list[dict], struct: dict) -> dict:
    n = len(per_case) or 1
    schema = sum(c["schema_valid"] for c in per_case) / n
    winner = sum(c["winner_correct"] for c in per_case) / n
    scores = sum(c["scores_correct"] for c in per_case) / n
    matchup_f1 = sum(c["matchup_f1"] for c in per_case) / n
    scripts_frac = sum(1.0 if c["scripts_used"] else 0.0 for c in per_case) / n
    commentary = sum(c["commentary_score"] for c in per_case) / n
    total_cost = sum(c["cost_usd"] for c in per_case)
    total_tokens = sum(c["total_tokens"] for c in per_case)
    total_latency = sum(c["latency_sec"] for c in per_case)
    skill_read_rate = sum(1.0 if c.get("skill_read") else 0.0 for c in per_case) / n
    reference_counts: dict[str, int] = {}
    for c in per_case:
        for ref in c.get("references_read", []):
            reference_counts[ref] = reference_counts.get(ref, 0) + 1

    axes = {
        "schema_valid":   {"raw": schema,       "points": 10 * schema,       "max": 10},
        "winner_correct": {"raw": winner,       "points": 10 * winner,       "max": 10},
        "scores_correct": {"raw": scores,       "points": 25 * scores,       "max": 25},
        "type_matchups":  {"raw": matchup_f1,   "points": 20 * matchup_f1,   "max": 20},
        "used_scripts":   {"raw": scripts_frac, "points": 20 * scripts_frac, "max": 20,
                           "scripts_per_case": scripts_frac},
        "commentary":     {"raw": commentary,   "points": 15 * commentary,   "max": 15},
    }
    correctness = sum(a["points"] for a in axes.values())
    cpen = cost_penalty(total_cost)
    lpen = latency_penalty(total_latency)
    spen = struct["total"]
    final = max(0.0, correctness - cpen - lpen - spen)
    return {
        "correctness": round(correctness, 1),
        "cost_penalty": round(cpen, 1),
        "latency_penalty": round(lpen, 1),
        "structural_penalty": spen,
        "structural_breakdown": struct,
        "total_points": round(final, 1),
        "axes": axes,
        "total_cost_usd": round(total_cost, 4),
        "total_tokens": total_tokens,
        "total_latency_sec": round(total_latency, 2),
        "skill_read_rate": round(skill_read_rate, 2),
        "references_read_counts": reference_counts,
    }


def generate_hints(summary: dict) -> list[dict]:
    """Create deterministic coaching hints for the dashboard."""
    axes = summary["axes"]
    struct = summary["structural_breakdown"]
    hints: list[dict] = []

    def add(title: str, body: str, severity: str = "info") -> None:
        hints.append({"title": title, "body": body, "severity": severity})

    if summary.get("skill_read_rate", 0.0) < 0.5:
        add(
            "Skill may not be triggering",
            "The run did not visibly read SKILL.md. Edit the `description:` field in the YAML frontmatter at the top of SKILL.md so it names the task explicitly — something like 'Predict the outcome of a 1-on-1 Pokemon battle and emit the BattlePrediction JSON.' Codex uses this string to decide whether to load the skill at all.",
            "warn",
        )

    if axes["used_scripts"]["points"] < axes["used_scripts"]["max"]:
        add(
            "Wire local tools",
            "Codex is not consistently invoking scripts. In SKILL.md, show the exact commands for fetch_pokemon.py and type_matchup.py.",
            "warn",
        )

    if axes["schema_valid"]["points"] < axes["schema_valid"]["max"]:
        add(
            "Fix output shape",
            "In SKILL.md, add an Output section showing the exact JSON shape with all six required keys (winner, loser, winner_score, loser_score, key_type_matchups, commentary) and instruct the agent to print only that JSON object — no ```json fences, no leading or trailing prose.",
            "warn",
        )

    if axes["scores_correct"]["points"] < axes["scores_correct"]["max"]:
        add(
            "Focus on the formula",
            "Winner can be right while scores are wrong. In SKILL.md, instruct the agent to read damage_formula.md and follow it exactly: use max(attack, special_attack) for the offensive stat, multiply by the type effectiveness from type_matchup.py, then factor in speed and HP as the formula prescribes. Do not approximate.",
            "warn",
        )

    if axes["type_matchups"]["points"] < axes["type_matchups"]["max"]:
        add(
            "Tune type matchup reporting",
            "In SKILL.md, spell out the key_type_matchups row format: each row is one single attacker type and one single defender type (e.g., 'water' / 'dragon', not 'water/flying' or 'fire,ice'), with the multiplier taken from type_matchup.py. Scoring is F1, so extra rows hurt precision and missing rows hurt recall — emit the matchups that actually decide the battle, nothing more.",
            "warn",
        )

    if axes["commentary"]["points"] < axes["commentary"]["max"]:
        add(
            "Improve commentary",
            "In SKILL.md, tell the agent that the `commentary` field must be one or two sentences, name the winner by name, and call out the decisive factor (the key stat advantage or the type matchup that swung it). No filler, no recaps of both Pokemon's full movesets.",
            "info",
        )

    if struct["agents_md_penalty"] or struct["skill_md_penalty"] or struct["description_penalty"]:
        add(
            "Trim instruction bloat",
            "Structural penalty is active. Shorten AGENTS.md first, then remove lore and repeated examples from SKILL.md.",
            "warn",
        )
    elif summary["cost_penalty"] >= 5:
        add(
            "Reduce cost",
            "Cost is now the biggest drag on the final score. In SKILL.md, drop any reference files the agent is reading that aren't load-bearing (check the references_read counts in the summary), and trim verbose prose down to short bullet instructions. If AGENTS.md is adding overhead too, shorten it.",
            "info",
        )

    refs = summary.get("references_read_counts", {})
    if refs.get("competitive_meta.md"):
        add(
            "Avoid competitive_meta.md",
            "The meta reference is lore-only for this task. If it is being read, update SKILL.md to ignore it.",
            "warn",
        )

    if not hints:
        add(
            "Strong run",
            "The main remaining wins are cost and latency. Look for shorter instructions or fewer tool calls without sacrificing correctness.",
            "ok",
        )
    return hints[:5]


def collect_cases() -> list[tuple[str, Path, Path]]:
    cases = []
    for txt in sorted(HELDOUT_DIR.glob("*.txt"))[:NUM_CASES]:
        truth = TRUTH_DIR / f"{txt.stem}.json"
        if not truth.exists():
            print(f"WARN: no truth for {txt.name}, skipping", file=sys.stderr)
            continue
        cases.append((txt.stem, txt, truth))
    return cases


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-dir", type=Path, default=PROJECT_ROOT,
                    help="Where AGENTS.md and .agents/ live (default: ./battle-prediction-agent)")
    ap.add_argument("--model", default=os.environ.get("MODEL"),
                    help="Codex model. Default: env MODEL or Codex's auto-pick.")
    ap.add_argument("--sse-url", default=os.environ.get("SSE_URL", SSE_URL_DEFAULT),
                    help="Where to POST per-case events (set empty to disable)")
    ap.add_argument("--save-as-baseline", action="store_true")
    ap.add_argument("--baseline", type=Path, default=BASELINE_PATH)
    args = ap.parse_args()

    sse_url = args.sse_url or None
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    prices = json.loads(PRICE_PATH.read_text(encoding="utf-8"))
    user_model = args.model
    billing_model = user_model or prices.get("default_model")
    baseline = json.loads(args.baseline.read_text(encoding="utf-8")) if args.baseline.exists() else None
    struct = structural_penalty(args.project_dir)

    cases = collect_cases()
    if not cases:
        print("No held-out cases found.", file=sys.stderr)
        return 2

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    run_root = RESULTS_DIR / stamp
    run_root.mkdir(parents=True, exist_ok=True)
    jsonl = (run_root / "results.jsonl").open("w", encoding="utf-8")

    push_sse({"type": "run.started", "stamp": stamp, "n_cases": len(cases),
              "model": user_model or f"auto ({billing_model} pricing)",
              "structural": struct}, sse_url)

    per_case: list[dict] = []
    for idx, (case_id, input_path, truth_path) in enumerate(cases, 1):
        push_sse({"type": "case.started", "case_id": case_id, "i": idx, "n": len(cases)}, sse_url)
        case_dir = run_root / f"case_{case_id}"
        stage_run_dir(args.project_dir, case_dir)

        doc = input_path.read_text(encoding="utf-8")
        truth = json.loads(truth_path.read_text(encoding="utf-8"))

        def progress_cb(activity: dict, _case_id=case_id, _i=idx, _n=len(cases)):
            push_sse({"type": "case.progress", "case_id": _case_id,
                      "i": _i, "n": _n, "activity": activity}, sse_url)

        run = run_codex_battle(doc, case_dir, model=user_model, on_activity=progress_cb)
        predicted = parse_model_output(run.raw_output)
        s = score(predicted, truth, schema)
        j = judge(predicted, truth)
        cost_usd = compute_cost(
            run.input_tokens, run.cached_input_tokens, run.output_tokens,
            billing_model, prices
        )

        case_record = {
            "case_id": case_id,
            "schema_valid": bool(s.schema_valid),
            "schema_errors": s.schema_errors,
            "winner_correct": bool(s.winner_correct),
            "scores_correct": bool(s.scores_correct),
            "matchup_precision": s.matchup_precision,
            "matchup_recall": s.matchup_recall,
            "matchup_f1": s.matchup_f1,
            "scripts_used": run.scripts_used,
            "files_read": run.files_read,
            "skill_read": run.skill_read,
            "references_read": run.references_read,
            "commentary_score": j.score,
            "commentary_rationale": j.rationale,
            "judge_source": j.source,
            "input_tokens": run.input_tokens,
            "output_tokens": run.output_tokens,
            "total_tokens": run.total_tokens,
            "cost_usd": round(cost_usd, 4),
            "latency_sec": round(run.latency_sec, 2),
            "thinking_sec": round(run.thinking_sec, 2),
            "script_sec": round(run.script_sec, 2),
            "message_sec": round(run.message_sec, 2),
            "exit_code": run.exit_code,
            "error": run.error,
            "raw_output_preview": (run.raw_output or "")[:500],
        }
        per_case.append(case_record)
        jsonl.write(json.dumps(case_record) + "\n")
        jsonl.flush()
        (case_dir / "result.json").write_text(json.dumps(case_record, indent=2), encoding="utf-8")
        (case_dir / "raw_output.txt").write_text(run.raw_output or "", encoding="utf-8")

        push_sse({"type": "case.completed", **case_record}, sse_url)
        print(f"[{idx}/{len(cases)}] {case_id}: schema={s.schema_valid} "
              f"winner={s.winner_correct} scores={s.scores_correct} "
              f"match_f1={s.matchup_f1:.2f} "
              f"scripts={'/'.join(run.scripts_used) or '-'} "
              f"cost=${cost_usd:.4f} latency={run.latency_sec:.1f}s")

    jsonl.close()
    summary = aggregate(per_case, struct)
    summary["model"] = user_model or f"auto ({billing_model} pricing)"
    summary["hints"] = generate_hints(summary)
    (run_root / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    summary_for_sse = {**summary, "delta_vs_baseline":
                       round(summary["total_points"] - baseline["total_points"], 1) if baseline else None}
    push_sse({"type": "run.completed", **summary_for_sse}, sse_url)

    print("\n=== Summary ===")
    print(f"Model: {summary['model']}")
    print(f"Correctness: {summary['correctness']} / 100")
    print(f"Cost penalty:       -{summary['cost_penalty']:>4}  (${summary['total_cost_usd']:.4f})")
    print(f"Latency penalty:    -{summary['latency_penalty']:>4}  ({summary['total_latency_sec']:.1f}s)")
    print(f"Structural penalty: -{summary['structural_penalty']:>4}  "
          f"(desc {struct['description_length']}c -{struct['description_penalty']}, "
          f"AGENTS {struct['agents_md_size']}b -{struct['agents_md_penalty']}, "
          f"SKILL {struct['skill_md_size']}b -{struct['skill_md_penalty']})")
    print(f"FINAL: {summary['total_points']} / 100")
    if baseline:
        delta = summary["total_points"] - baseline["total_points"]
        print(f"Delta vs baseline: {'+' if delta >= 0 else ''}{delta:.1f}  "
              f"(baseline: {baseline['total_points']}, model: {baseline.get('model', '?')})")
    print(f"Tokens: {summary['total_tokens']:,}   Wall: {summary['total_latency_sec']:.1f}s")
    for name, ax in summary["axes"].items():
        print(f"  {name:18s} {ax['points']:5.1f} / {ax['max']:>2}")
    if summary.get("hints"):
        print("\nHints:")
        for hint in summary["hints"]:
            print(f"  - {hint['title']}: {hint['body']}")

    if args.save_as_baseline:
        new_baseline = {
            "stamp": stamp,
            "model": summary["model"],
            "total_points": summary["total_points"],
            "total_cost_usd": summary["total_cost_usd"],
            "total_tokens": summary["total_tokens"],
            "total_latency_sec": summary["total_latency_sec"],
        }
        args.baseline.write_text(json.dumps(new_baseline, indent=2), encoding="utf-8")
        print(f"\nSaved baseline -> {args.baseline}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

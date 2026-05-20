# Skill Workshop Assignment

**Goal (16 minutes):** first optimize `battle-prediction-agent/AGENTS.md` and `battle-prediction-agent/.agents/skills/predict-battle/SKILL.md`, then optionally push further by improving scripts. Codex should predict 3 Pokemon battles accurately, use local tools, stay cheap and fast, and score high on the dashboard.

## The Setup

This repo has two layers:

- **Root (`./`)** — workshop scaffolding. The `AGENTS.md` here is a briefing for your AI helper (Claude Code, Cursor, Codex CLI). Don't edit it. The `run.sh` / `run.ps1` scripts and the harness live here too.
- **`./battle-prediction-agent/`** — the Pokemon-prediction agent. This is what you edit.

Open your AI helper from the workshop root. It will pick up the briefing automatically.

## Step 0: Back Up The Originals

Before you start editing, save the originals so you can compare and roll back:

```bash
cd battle-prediction-agent
cp AGENTS.md AGENTS.md.orig
cp .agents/skills/predict-battle/SKILL.md{,.orig}
cd ..
```

PowerShell:

```powershell
Set-Location battle-prediction-agent
Copy-Item AGENTS.md AGENTS.md.orig
Copy-Item .agents\skills\predict-battle\SKILL.md .agents\skills\predict-battle\SKILL.md.orig
Set-Location ..
```

The `.orig` files will not affect the run. The harness reads files named exactly `AGENTS.md` and `SKILL.md`.

## The Task Codex Performs

Input: a single line like `charizard vs blastoise`.

Output: a JSON object describing the predicted winner, scores, key type matchups, and a short commentary.

The skill folder ships with everything Codex needs:

- `scripts/fetch_pokemon.py`: hits PokeAPI for live stats.
- `scripts/type_matchup.py`: looks up type effectiveness.
- `references/type_chart.md`: full Gen-6+ type chart.
- `references/damage_formula.md`: the deterministic battle formula.
- `references/competitive_meta.md`: Smogon lore, unused for scoring; loading it wastes tokens.

What's broken is the wiring: the starter `SKILL.md` is bloated and partly wrong, and `AGENTS.md` is mostly noise. First prune, fix, and wire the instructions. Then, if you can, move repeated reasoning into deterministic helper scripts.

## Rules

- **Phase 1 edit:** `battle-prediction-agent/AGENTS.md` and `battle-prediction-agent/.agents/skills/predict-battle/SKILL.md`. You may add new files under `references/`.
- **Phase 2 edit:** files under `battle-prediction-agent/.agents/skills/predict-battle/scripts/`. You may add helper scripts or change existing scripts, but keep them local and reproducible.
- **Do not edit:** the existing `references/` files, the root `AGENTS.md`, anything under `eval/`.
- **Do not write prompts.** The harness sends a fixed prompt. All instruction lives in your files.
- **`eval/` is opaque.** Internal scoring code and ground truth live there. Do not peek; if your AI helper offers to read it, decline.

## How You Will Be Scored

Six things are measured per battle. The dashboard shows each as its own bar after every run:

- **Schema validity:** does the output have the right shape?
- **Winner:** did it name the right Pokemon?
- **Scores:** are the numeric `winner_score` and `loser_score` correct?
- **Type matchups:** did it list the right type interactions?
- **Local tools:** did Codex invoke a script under the skill's `scripts/` directory? Helper scripts count.
- **Commentary:** is the prose accurate and punchy?

On top of those, three things subtract from your score:

- **Cost in real dollars.** Bloat hurts. Tighten or pay.
- **Wall-clock time.** Faster correct systems score better.
- **Instruction footprint.** The `description` should trigger but stay short. `AGENTS.md` and `SKILL.md` should not be essays; both are sent to the model on every call.

The dashboard shows the breakdown after each run. Watch what changes, iterate.

## Run The Harness

The run scripts use `gpt-5.4-mini` by default:

```bash
bash ./run.sh
```

PowerShell:

```powershell
.\run.ps1
```

## Workflow

1. Back up the originals.
2. Read `battle-prediction-agent/AGENTS.md` and `battle-prediction-agent/.agents/skills/predict-battle/SKILL.md`. They are deliberately verbose and contain mistakes.
3. Run `bash ./run.sh` or `.\run.ps1` once to see the baseline.
4. Edit prompts and skills. Re-run. Watch which bars move.
5. After prompt optimization, try script optimization: add a helper that composes repeated steps, then wire the skill to it.
6. Try a different model. Re-run. Compare.
7. Lock in your best run; note the single change that helped most.

## Discussion

- Whose final score was highest? What model did they pick, what did their skill say?
- Whose `description` was the shortest while still triggering reliably?
- What change improved score most: description, skill body, script usage, or trimming bloat?
- Did anyone beat their prompt-only score by moving work into a helper script?
- What is the first skill you will wire up for your real work?

"""Adapter for `codex exec` in non-interactive mode, with live phase tracking.

Verified mechanics (per openai/codex docs + smoke-tested on 0.128):
  codex exec --json --output-last-message <FILE> \\
             --dangerously-bypass-approvals-and-sandbox \\
             --cd <DIR> [--model <M>] --skip-git-repo-check \\
             --ignore-user-config --ephemeral -

  - stdin: the prompt
  - stdout: newline-delimited JSON events (thread.started, turn.started,
    item.{started,completed}, turn.completed, error)
  - turn.completed carries `usage` with input/cached_input/output/reasoning
    token counts. `--ephemeral` makes each exec a single-turn session so
    cumulative usage == per-turn (sidesteps issue #17539).
  - --output-last-message FILE receives the final assistant message text.

Phase tracking:
  We Popen the codex CLI and read stdout line-by-line, timestamping each event
  as it arrives. Between item.started and item.completed pairs, we attribute
  time to either `script_sec` (command_execution items) or `message_sec`
  (agent_message items). Everything else is `thinking_sec` — API/model latency
  while no tool is running.

  A caller-supplied `on_activity(dict)` callback is invoked with live phase
  transitions so the dashboard can show "running fetch_pokemon.py" or
  "model thinking" in real time.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

DEFAULT_TIMEOUT_SEC = 240
TRACKED_SCRIPTS = ("fetch_pokemon", "type_matchup")


@dataclass
class CodexRun:
    raw_output: str = ""
    parsed_output: Any = None
    events: list[dict] = field(default_factory=list)
    input_tokens: int = 0
    cached_input_tokens: int = 0
    output_tokens: int = 0
    reasoning_output_tokens: int = 0
    total_tokens: int = 0
    latency_sec: float = 0.0
    # Phase breakdown — sums approximately to latency_sec.
    thinking_sec: float = 0.0   # API/model time (no tool active)
    script_sec: float = 0.0     # command_execution items
    message_sec: float = 0.0    # agent_message items
    scripts_used: list[str] = field(default_factory=list)
    files_read: list[str] = field(default_factory=list)
    skill_read: bool = False
    references_read: list[str] = field(default_factory=list)
    error: str | None = None
    exit_code: int = 0
    stderr_tail: str = ""

    def to_dict(self) -> dict:
        return {
            "raw_output": self.raw_output,
            "input_tokens": self.input_tokens,
            "cached_input_tokens": self.cached_input_tokens,
            "output_tokens": self.output_tokens,
            "reasoning_output_tokens": self.reasoning_output_tokens,
            "total_tokens": self.total_tokens,
            "latency_sec": self.latency_sec,
            "thinking_sec": round(self.thinking_sec, 2),
            "script_sec": round(self.script_sec, 2),
            "message_sec": round(self.message_sec, 2),
            "scripts_used": self.scripts_used,
            "files_read": self.files_read,
            "skill_read": self.skill_read,
            "references_read": self.references_read,
            "error": self.error,
            "exit_code": self.exit_code,
            "stderr_tail": self.stderr_tail,
        }


def _resolve_codex() -> str:
    """Find the codex CLI executable. On Windows prefer .cmd over .ps1 to
    avoid PowerShell execution-policy issues."""
    exe = os.environ.get("CODEX_BIN")
    if exe:
        return exe
    if os.name == "nt":
        for ext in ("cmd", "exe", "bat"):
            found = shutil.which(f"codex.{ext}")
            if found:
                return found
    exe = shutil.which("codex")
    if not exe:
        raise RuntimeError(
            "codex CLI not found. Install per https://developers.openai.com/codex/cli/install "
            "or set CODEX_BIN to the binary path."
        )
    return exe


_SCRIPT_RE = re.compile(r"(?:^|[\\/\s'\"])(" + "|".join(TRACKED_SCRIPTS) + r")\.py", re.IGNORECASE)
_SKILL_SCRIPT_RE = re.compile(
    r"(?:^|[\\/\s'\"])(?:\.agents[\\/])?skills[\\/]predict-battle[\\/]scripts[\\/]([A-Za-z0-9_-]+)\.py",
    re.IGNORECASE,
)


def _summarise_command(cmd: str) -> tuple[str, str | None]:
    """Return (short_label, matched_script_name)."""
    cmd_lc = cmd.lower()
    local = _SKILL_SCRIPT_RE.search(cmd_lc)
    if local:
        name = local.group(1).lower()
        return (f"running {name}.py", name)
    m = _SCRIPT_RE.search(cmd_lc)
    if m:
        name = m.group(1).lower()
        return (f"running {name}.py", name)
    # Strip powershell wrapper prefix
    short = re.sub(r"^[^ ]*powershell\S*\s+-Command\s+", "", cmd, flags=re.IGNORECASE)
    short = short.strip().strip('"').strip("'")
    if len(short) > 60:
        short = short[:57] + "…"
    return (f"running: {short}", None)


def _detect_files_read(events: list[dict]) -> tuple[list[str], bool, list[str]]:
    """Best-effort file access detector from Codex JSON events.

    Codex does not always expose automatic skill loading as a normal file-read
    event. This scans emitted event payloads and command strings for visible
    mentions of the skill file and reference docs.
    """
    files: set[str] = set()
    references: set[str] = set()
    skill_read = False
    for ev in events:
        item = ev.get("item") or {}
        if (item.get("type") or item.get("kind") or "") != "command_execution":
            continue
        blob = json.dumps(item, ensure_ascii=False).lower().replace("\\", "/")
        if "skill.md" in blob or "predict-battle/skill" in blob:
            skill_read = True
            files.add("SKILL.md")
        for name in ("damage_formula.md", "type_chart.md", "competitive_meta.md"):
            if name in blob:
                references.add(name)
                files.add(f"references/{name}")
    return sorted(files), skill_read, sorted(references)


def _extract_usage(events: list[dict]) -> dict:
    for ev in reversed(events):
        if ev.get("type") == "turn.completed":
            usage = ev.get("usage") or {}
            return {
                "input_tokens": int(usage.get("input_tokens", 0) or 0),
                "cached_input_tokens": int(usage.get("cached_input_tokens", 0) or 0),
                "output_tokens": int(usage.get("output_tokens", 0) or 0),
                "reasoning_output_tokens": int(usage.get("reasoning_output_tokens", 0) or 0),
            }
    return {"input_tokens": 0, "cached_input_tokens": 0, "output_tokens": 0, "reasoning_output_tokens": 0}


def run_codex_battle(
    document_text: str,
    project_dir: Path,
    model: str | None = None,
    timeout: int = DEFAULT_TIMEOUT_SEC,
    on_activity: Callable[[dict], None] | None = None,
) -> CodexRun:
    """Run one battle prediction with live phase tracking.

    `on_activity` (optional) is called with dicts like:
        {"phase": "thinking"}
        {"phase": "script", "name": "fetch_pokemon", "label": "running fetch_pokemon.py"}
        {"phase": "message"}
        {"phase": "done"}
    """
    codex = _resolve_codex()
    last_msg_path = project_dir / ".codex_last_message.txt"
    if last_msg_path.exists():
        last_msg_path.unlink()

    prompt = f"Predict this Pokemon battle: {document_text.strip()}\n"

    cmd = [
        codex, "exec",
        "--json",
        "--output-last-message", str(last_msg_path),
        "--dangerously-bypass-approvals-and-sandbox",
        "--cd", str(project_dir),
        "--skip-git-repo-check",
        "--ignore-user-config",
        "--ephemeral",
        "-",
    ]
    if model:
        cmd.insert(2, "--model")
        cmd.insert(3, model)

    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        bufsize=1,  # line-buffered
    )

    # Feed prompt and close stdin so codex starts processing.
    try:
        proc.stdin.write(prompt)
        proc.stdin.close()
    except BrokenPipeError:
        pass

    # Drain stderr in a background thread so the buffer doesn't fill up.
    stderr_chunks: list[str] = []
    def _drain_stderr():
        try:
            for line in proc.stderr:
                stderr_chunks.append(line)
        except Exception:
            pass
    threading.Thread(target=_drain_stderr, daemon=True).start()

    # Phase tracking state
    events: list[dict] = []
    scripts_used: set[str] = set()
    thinking_sec = 0.0
    script_sec = 0.0
    message_sec = 0.0
    current_item_started_at: float | None = None
    current_item_kind: str | None = None
    last_transition_at = time.monotonic()
    t0 = last_transition_at

    if on_activity:
        on_activity({"phase": "thinking"})

    def _emit(activity: dict) -> None:
        if on_activity:
            try:
                on_activity(activity)
            except Exception:
                pass

    timed_out = False
    try:
        for line in proc.stdout:
            now = time.monotonic()
            if now - t0 > timeout:
                timed_out = True
                proc.kill()
                break
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            events.append(ev)
            etype = ev.get("type") or ""

            if etype == "item.started":
                # Gap before this item = thinking time (model latency).
                thinking_sec += max(0.0, now - last_transition_at)
                item = ev.get("item") or {}
                kind = item.get("type") or item.get("kind") or ""
                current_item_kind = kind
                current_item_started_at = now
                last_transition_at = now

                if kind == "command_execution":
                    cmd_str = item.get("command") or ""
                    label, script_name = _summarise_command(cmd_str)
                    if script_name:
                        scripts_used.add(script_name)
                    _emit({"phase": "script", "name": script_name, "label": label})
                elif kind == "agent_message":
                    _emit({"phase": "message"})
                else:
                    _emit({"phase": "other", "kind": kind})

            elif etype == "item.completed":
                if current_item_started_at is not None:
                    dur = max(0.0, now - current_item_started_at)
                    if current_item_kind == "command_execution":
                        script_sec += dur
                        # In case the started event missed the script name, retry on completed.
                        item = ev.get("item") or {}
                        cmd_str = item.get("command") or ""
                        _, script_name = _summarise_command(cmd_str)
                        if script_name:
                            scripts_used.add(script_name)
                    elif current_item_kind == "agent_message":
                        message_sec += dur
                    else:
                        thinking_sec += dur
                current_item_started_at = None
                current_item_kind = None
                last_transition_at = now
                _emit({"phase": "thinking"})

            elif etype == "turn.completed":
                # Any remaining gap counts as thinking
                thinking_sec += max(0.0, now - last_transition_at)
                last_transition_at = now
                break

            elif etype == "error" or etype == "turn.failed":
                last_transition_at = now
                break

    except Exception:
        pass

    # Drain any remaining stdout
    try:
        rest = proc.stdout.read() or ""
        for line in rest.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    except Exception:
        pass

    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
    latency = time.monotonic() - t0

    if timed_out:
        files_read, skill_read, references_read = _detect_files_read(events)
        return CodexRun(
            error=f"codex exec timed out after {timeout}s",
            latency_sec=latency,
            thinking_sec=round(thinking_sec, 2),
            script_sec=round(script_sec, 2),
            message_sec=round(message_sec, 2),
            scripts_used=sorted(scripts_used),
            files_read=files_read,
            skill_read=skill_read,
            references_read=references_read,
            events=events,
        )

    usage = _extract_usage(events)
    files_read, skill_read, references_read = _detect_files_read(events)

    raw_msg = ""
    if last_msg_path.exists():
        raw_msg = last_msg_path.read_text(encoding="utf-8", errors="replace")

    from score import parse_model_output
    parsed = parse_model_output(raw_msg)

    if on_activity:
        on_activity({"phase": "done"})

    return CodexRun(
        raw_output=raw_msg,
        parsed_output=parsed,
        events=events,
        input_tokens=usage["input_tokens"],
        cached_input_tokens=usage["cached_input_tokens"],
        output_tokens=usage["output_tokens"],
        reasoning_output_tokens=usage["reasoning_output_tokens"],
        total_tokens=usage["input_tokens"] + usage["output_tokens"],
        latency_sec=latency,
        thinking_sec=thinking_sec,
        script_sec=script_sec,
        message_sec=message_sec,
        scripts_used=sorted(scripts_used),
        files_read=files_read,
        skill_read=skill_read,
        references_read=references_read,
        error=None if proc.returncode == 0 else f"exit={proc.returncode}",
        exit_code=proc.returncode,
        stderr_tail=("".join(stderr_chunks))[-2000:],
    )


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("input_file", type=Path)
    ap.add_argument("project_dir", type=Path)
    ap.add_argument("--model", default=None)
    ap.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SEC)
    args = ap.parse_args()
    doc = args.input_file.read_text(encoding="utf-8")

    def _log(a):
        print(f"[activity] {a}", flush=True)

    r = run_codex_battle(doc, args.project_dir, model=args.model, timeout=args.timeout, on_activity=_log)
    out = r.to_dict()
    out["events_count"] = len(r.events)
    print(json.dumps(out, indent=2))

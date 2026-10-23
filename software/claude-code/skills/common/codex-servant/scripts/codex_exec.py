#!/usr/bin/env -S uv run --quiet --no-project --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Run the Codex CLI as a stateless servant: it loads none of its own configuration and saves nothing but its answer.

Model, reasoning effort and sandbox come from roles.json for every call, never from Codex's config or
defaults. The context comes from the prompt alone: no AGENTS.md discovery, no memories, hooks, plugins,
skills, apps or MCP servers, unless a call asks for a named MCP server from roles.json.

When Codex reports a usage or rate limit, this script records it and answers `unavailable` without calling
Codex for the next 10 minutes, so callers fall back to Claude and check back later.

  codex_exec.py run --role <role> --cd <dir> (--prompt-file <file> | --prompt <text>) [--schema <file>] [--out <file>]
                    [--model <m>] [--effort <e>] [--network] [--mcp context7] [--add-dir <dir>]
  codex_exec.py doctor
  codex_exec.py probe

Prints one JSON object. Exit 0 ok, 1 error, 3 unavailable, 4 timeout.
"""

import argparse
import json
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path

ROLES_FILE = Path(__file__).resolve().parent / "roles.json"
STATE_DIR = Path.home() / ".local" / "state" / "codex-servant"
STATUS_FILE = STATE_DIR / "status.json"
MODELS_CACHE = Path.home() / ".codex" / "models_cache.json"
UNAVAILABLE_FOR = 600
EXHAUSTED = re.compile(r"usage limit|rate.?limit|\b429\b|quota|too many requests|exceeded your", re.IGNORECASE)


def emit(payload: dict, code: int) -> None:
    print(json.dumps(payload))
    sys.exit(code)


def load_status() -> dict:
    try:
        return json.loads(STATUS_FILE.read_text())
    except FileNotFoundError:
        return {}


def save_status(status: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    temporary = STATUS_FILE.with_suffix(".tmp")
    temporary.write_text(json.dumps(status, indent=2))
    temporary.replace(STATUS_FILE)


def command_for(*, roles: dict, role: dict, model: str, effort: str, cd: Path, network: bool, mcp: list[str], schema: str | None, out: Path, add_dirs: list[str]) -> list[str]:
    isolation = roles["isolation"]
    command = ["codex", "exec", *isolation["flags"]]
    for feature in isolation["disable"]:
        command += ["--disable", feature]
    for entry in isolation["config"]:
        command += ["-c", entry]
    if mcp:
        for name in mcp:
            for entry in roles["mcp"][name]:
                command += ["-c", entry]
    else:
        command += ["-c", "mcp_servers={}"]
    command += ["-m", model, "-c", f'model_reasoning_effort="{effort}"', "-s", role["sandbox"], "-C", str(cd), "-o", str(out)]
    if network and role["sandbox"] == "workspace-write":
        command += ["-c", "sandbox_workspace_write.network_access=true"]
    for directory in add_dirs:
        command += ["--add-dir", directory]
    if schema:
        command += ["--output-schema", schema]
    return command + ["-"]


def run(args: argparse.Namespace) -> None:
    roles = json.loads(ROLES_FILE.read_text())
    if args.role not in roles["roles"]:
        emit({"status": "error", "reason": f"unknown role {args.role}; roles: {sorted(roles['roles'])}"}, 1)
    role = roles["roles"][args.role]
    status = load_status()
    if args.role != "probe" and time.time() < status.get("unavailable_until", 0):
        emit({"status": "unavailable", "reason": status.get("reason", ""), "retry_after": status["unavailable_until"]}, 3)
    substitutes = status.get("model_substitutes", {})
    model = args.model or substitutes.get(role["model"], role["model"])
    effort = args.effort or role["effort"]
    prompt = Path(args.prompt_file).read_text() if args.prompt_file else args.prompt
    if not prompt:
        emit({"status": "error", "reason": "empty prompt"}, 1)
    out = Path(args.out) if args.out else STATE_DIR / f"last-{args.role}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    command = command_for(roles=roles, role=role, model=model, effort=effort, cd=Path(args.cd).resolve(), network=args.network, mcp=args.mcp, schema=args.schema, out=out, add_dirs=args.add_dir)
    started = time.monotonic()
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
    # Codex runs in its own process group, outside the caller's. Record it for a supervising job to reap, and
    # pass a termination on, so ending the caller never leaves codex editing files on its own.
    if run_dir := os.environ.get("NIGHT_SHIFT_RUN_DIR"):
        with (Path(run_dir) / "codex-pgids").open("a") as record:
            record.write(f"{process.pid}\n")

    def forward(signum: int, _frame: object) -> None:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        sys.exit(128 + signum)

    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(sig, forward)
    try:
        stdout, stderr = process.communicate(prompt, timeout=role["minutes"] * 60)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGTERM)
        try:
            stdout, stderr = process.communicate(timeout=30)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            stdout, stderr = process.communicate()
        emit({"status": "timeout", "role": args.role, "model": model, "effort": effort, "minutes": role["minutes"]}, 4)
    seconds = round(time.monotonic() - started)
    tokens = re.search(r"tokens used\s*\n\s*([\d,]+)", stdout + stderr)
    if process.returncode != 0:
        text = (stderr + stdout)[-2000:]
        if EXHAUSTED.search(text):
            save_status({**status, "unavailable_until": time.time() + UNAVAILABLE_FOR, "reason": text.strip().splitlines()[-1][:300]})
            emit({"status": "unavailable", "reason": text.strip().splitlines()[-1][:300]}, 3)
        emit({"status": "error", "role": args.role, "model": model, "returncode": process.returncode, "stderr_tail": text}, 1)
    if status.get("unavailable_until"):
        status.pop("unavailable_until", None)
        status.pop("reason", None)
        save_status(status)
    emit({"status": "ok", "role": args.role, "model": model, "effort": effort, "seconds": seconds, "tokens": tokens.group(1) if tokens else None, "last_message_file": str(out)}, 0)


def listed_models() -> list[str]:
    try:
        data = json.loads(MODELS_CACHE.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return []
    models = data.get("models", data)
    entries = models if isinstance(models, list) else list(models.values())
    return [entry.get("slug") for entry in entries if isinstance(entry, dict) and entry.get("visibility") == "list" and entry.get("slug")]


def doctor(_: argparse.Namespace) -> None:
    """Check that every flag, feature and model the recipe uses still exists; substitute a missing model."""
    roles = json.loads(ROLES_FILE.read_text())
    try:
        version = subprocess.run(["codex", "--version"], capture_output=True, text=True, timeout=30).stdout.strip()
        help_text = subprocess.run(["codex", "exec", "--help"], capture_output=True, text=True, timeout=30).stdout
        features = subprocess.run(["codex", "features", "list"], capture_output=True, text=True, timeout=60).stdout
    except FileNotFoundError:
        emit({"ok": False, "reason": "codex is not on PATH"}, 1)
    flags = [flag for flag in roles["isolation"]["flags"] if flag.startswith("--")]
    flags += ["--disable", "--output-schema", "--sandbox", "--cd", "--output-last-message", "--add-dir"]
    missing_flags = [flag for flag in flags if flag not in help_text]
    known_features = {line.split()[0] for line in features.splitlines() if line.strip()}
    missing_features = [name for name in roles["isolation"]["disable"] if name not in known_features]
    listed = listed_models()
    wanted = sorted({role["model"] for role in roles["roles"].values()})
    missing_models = [model for model in wanted if listed and model not in listed]
    newest_sol = sorted((model for model in listed if model.endswith("-sol")), reverse=True)
    substitutes = {model: newest_sol[0] for model in missing_models if newest_sol}
    status = load_status()
    status.update({"model_substitutes": substitutes, "doctor_at": time.time(), "version": version})
    save_status(status)
    ok = not missing_flags and not missing_features
    emit(
        {
            "ok": ok,
            "version": version,
            "recipe_verified_with": roles["codex_version"],
            "recipe_last_verified": roles["last_verified"],
            "missing_flags": missing_flags,
            "missing_features": missing_features,
            "missing_models": missing_models,
            "substitutes": substitutes,
            "listed_models": listed,
        },
        0 if ok else 1,
    )


def probe(_: argparse.Namespace) -> None:
    sys.argv = [sys.argv[0], "run", "--role", "probe", "--cd", str(Path.home()), "--prompt", "Reply with exactly: OK"]
    main()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="action", required=True)
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--role", required=True)
    run_parser.add_argument("--cd", required=True)
    run_parser.add_argument("--prompt-file")
    run_parser.add_argument("--prompt")
    run_parser.add_argument("--schema")
    run_parser.add_argument("--out")
    run_parser.add_argument("--model")
    run_parser.add_argument("--effort")
    run_parser.add_argument("--network", action="store_true")
    run_parser.add_argument("--mcp", action="append", default=[], choices=["context7"])
    run_parser.add_argument("--add-dir", action="append", default=[])
    run_parser.set_defaults(handler=run)
    sub.add_parser("doctor").set_defaults(handler=doctor)
    sub.add_parser("probe").set_defaults(handler=probe)
    args = parser.parse_args()
    args.handler(args)


if __name__ == "__main__":
    main()

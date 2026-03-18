#!/usr/bin/env python3

import argparse
import json
import os
import signal
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path


def skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def repo_root() -> Path:
    return skill_root().parent.parent


def default_runs_root() -> Path:
    return Path.cwd() / ".it-runs"


def timestamp_dir() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H%M")


def load_commands(run_dir: Path) -> dict:
    cmd_path = run_dir / "commands.json"
    if not cmd_path.exists():
        raise FileNotFoundError(f"commands.json not found: {cmd_path}")
    with cmd_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def merge_env(env: dict | None) -> dict:
    merged = os.environ.copy()
    if not env:
        return merged
    for k, v in env.items():
        merged[str(k)] = str(v)
    return merged


def resolve_env(env: dict | None, run_dir: Path) -> dict:
    resolved = {}
    if env:
        for k, v in env.items():
            value = str(v)
            if "<RUN_DIR>" in value:
                value = value.replace("<RUN_DIR>", str(run_dir))
            if k == "YOMO_PROVIDER_RECORD_PATH":
                if value == "" or value == "<RUN_DIR>/record.jsonl":
                    value = str(run_dir / "record.jsonl")
                elif not os.path.isabs(value):
                    value = str(run_dir / value)
            resolved[str(k)] = value
    if "YOMO_PROVIDER_RECORD_PATH" not in resolved:
        resolved["YOMO_PROVIDER_RECORD_PATH"] = str(run_dir / "record.jsonl")
    return resolved


def merge_env_dict(base: dict, override: dict) -> dict:
    merged = dict(base)
    merged.update(override)
    return merged


def start_process(
    command: str,
    workdir: str | None,
    env: dict | None,
    stdout_path: Path | None = None,
) -> subprocess.Popen:
    cwd = Path(workdir).expanduser() if workdir else None
    stdout_handle = None
    stderr_handle = None
    if stdout_path:
        stdout_handle = stdout_path.open("w", encoding="utf-8")
        stderr_handle = stdout_handle
    proc = subprocess.Popen(
        command,
        shell=True,
        cwd=str(cwd) if cwd else None,
        env=merge_env(env),
        stdout=stdout_handle,
        stderr=stderr_handle,
    )
    if stdout_handle:
        stdout_handle.close()
    return proc


def get_child_pid(parent_pid: int) -> int | None:
    try:
        result = subprocess.run(
            ["pgrep", "-P", str(parent_pid)],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return None
    if result.returncode != 0:
        return None
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if not lines:
        return None
    try:
        return int(lines[0])
    except ValueError:
        return None


def write_pids(run_dir: Path, data: dict) -> None:
    pid_path = run_dir / ".pids.json"
    with pid_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def read_pids(run_dir: Path) -> dict:
    pid_path = run_dir / ".pids.json"
    if not pid_path.exists():
        return {}
    with pid_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def send_sigint(pid: int) -> None:
    try:
        os.kill(pid, signal.SIGINT)
    except ProcessLookupError:
        return


def init_run(run_dir: Path | None) -> Path:
    runs_root = default_runs_root()
    runs_root.mkdir(parents=True, exist_ok=True)
    if run_dir is None:
        run_dir = runs_root / timestamp_dir()
    run_dir.mkdir(parents=True, exist_ok=True)

    (run_dir / "requests").mkdir(exist_ok=True)
    (run_dir / "responses").mkdir(exist_ok=True)

    template = skill_root() / "assets" / "commands.json"
    shutil.copyfile(template, run_dir / "commands.json")
    return run_dir


def read_server_config(config: dict) -> dict:
    server = config.get("server", {})
    if "start" in server:
        return server.get("start", {})
    return server


def start(run_dir: Path, only: str, wait_seconds: int) -> None:
    config = load_commands(run_dir)
    pid_record = read_pids(run_dir)
    if not pid_record:
        pid_record = {"server": None, "tools": []}
    if "tools" not in pid_record or pid_record["tools"] is None:
        pid_record["tools"] = []

    server = read_server_config(config)
    base_env = resolve_env(server.get("env") if server else None, run_dir)

    if only in ("all", "server"):
        if server and server.get("command"):
            log_path = run_dir / "server.log"
            proc = start_process(server["command"], server.get("workdir"), base_env, log_path)
            child_pid = get_child_pid(proc.pid)
            pid_record["server"] = {
                "pid": proc.pid,
                "child_pid": child_pid,
                "command": server["command"],
                "log": str(log_path),
            }
            print(f"started server pid={proc.pid}")
        else:
            print("no server.command found")
        if wait_seconds > 0:
            print(f"waiting {wait_seconds}s for server startup")
            time.sleep(wait_seconds)

    if only in ("all", "tools"):
        for tool in config.get("tools", []):
            start_cfg = tool.get("start", {})
            command = start_cfg.get("command")
            if not command:
                continue
            tool_env = resolve_env(start_cfg.get("env"), run_dir)
            merged_env = merge_env_dict(base_env, tool_env)
            tool_name = tool.get("name", "tool")
            log_path = run_dir / f"{tool_name}.log"
            proc = start_process(command, start_cfg.get("workdir"), merged_env, log_path)
            child_pid = get_child_pid(proc.pid)
            pid_record["tools"].append({
                "name": tool_name,
                "pid": proc.pid,
                "child_pid": child_pid,
                "command": command,
                "log": str(log_path),
            })
            print(f"started tool {tool_name} pid={proc.pid}")
        if wait_seconds > 0:
            print(f"waiting {wait_seconds}s for tools startup")
            time.sleep(wait_seconds)

    write_pids(run_dir, pid_record)
    print(f"pid file: {run_dir / '.pids.json'}")


def send_sigkill(pid: int) -> None:
    try:
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        return


def kill_by_port(port: int | None) -> None:
    if not port:
        return
    try:
        result = subprocess.run(
            ["lsof", "-ti", f":{port}"],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return
    pids = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    for pid in pids:
        send_sigkill(int(pid))


def stop(run_dir: Path, only: str) -> None:
    pids = read_pids(run_dir)
    config = load_commands(run_dir)
    if not pids:
        pids = {"server": None, "tools": []}

    if only in ("all", "server"):
        server = pids.get("server")
        server_cfg = read_server_config(config)
        kill_by_port(server_cfg.get("port"))
        if server and server.get("pid"):
            send_sigkill(int(server["pid"]))
            print(f"killed server pid={server['pid']}")
        if server and server.get("child_pid"):
            send_sigkill(int(server["child_pid"]))
            print(f"killed server child pid={server['child_pid']}")

    if only in ("all", "tools"):
        for tool in pids.get("tools", []):
            if tool.get("pid"):
                send_sigkill(int(tool["pid"]))
                print(f"killed tool {tool.get('name','tool')} pid={tool['pid']}")
            if tool.get("child_pid"):
                send_sigkill(int(tool["child_pid"]))
                print(f"killed tool {tool.get('name','tool')} child pid={tool['child_pid']}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Start/stop server and tools using commands.json")
    sub = parser.add_subparsers(dest="action", required=True)

    init_cmd = sub.add_parser("init", help="create run directory and copy commands.json")
    init_cmd.add_argument("--run-dir", default="", help="custom run directory path")

    start_cmd = sub.add_parser("start", help="start server/tools")
    start_cmd.add_argument("--run-dir", required=True, help="run directory path")
    start_cmd.add_argument("--only", choices=["all", "server", "tools"], default="all")
    start_cmd.add_argument("--wait", type=int, default=0, help="wait seconds after starting")

    stop_cmd = sub.add_parser("stop", help="stop server/tools")
    stop_cmd.add_argument("--run-dir", required=True, help="run directory path")
    stop_cmd.add_argument("--only", choices=["all", "server", "tools"], default="all")

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.action == "init":
        run_dir = Path(args.run_dir).expanduser() if args.run_dir else None
        created = init_run(run_dir)
        print(f"run dir: {created}")
        print("request/response file names:")
        print("- requests/no_tools_streaming.json | responses/no_tools_streaming.txt")
        print("- requests/no_tools_non_streaming.json | responses/no_tools_non_streaming.txt")
        print("- requests/client_tool_streaming.json | responses/client_tool_streaming.txt")
        print("- requests/client_tool_non_streaming.json | responses/client_tool_non_streaming.txt")
        print("- requests/server_tool_streaming.json | responses/server_tool_streaming.txt")
        print("- requests/server_tool_non_streaming.json | responses/server_tool_non_streaming.txt")
        print("- requests/mixed_streaming.json | responses/mixed_streaming.txt")
        print("- requests/mixed_non_streaming.json | responses/mixed_non_streaming.txt")
        return

    run_dir = Path(args.run_dir).expanduser()
    if args.action == "start":
        start(run_dir, args.only, args.wait)
        return
    if args.action == "stop":
        stop(run_dir, args.only)
        return


if __name__ == "__main__":
    main()

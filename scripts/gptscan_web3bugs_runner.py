from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GPTSCAN_SRC = REPO_ROOT / "GPTScan" / "src"
DEFAULT_GEMINI_ENV = REPO_ROOT / "demo" / ".env"
EXPECTED_WEB3BUGS_PROJECTS = 72


def main() -> int:
    args = parse_args()
    dataset_root = args.dataset_root.resolve()
    output_root = args.output_root.resolve()
    gptscan_src = args.gptscan_src.resolve()

    if not dataset_root.exists():
        print(f"Dataset root not found: {dataset_root}", file=sys.stderr)
        return 2
    if not (gptscan_src / "main.py").exists():
        print(f"GPTScan src/main.py not found: {gptscan_src}", file=sys.stderr)
        return 2

    projects = select_projects(discover_projects(dataset_root), args.limit)
    output_root.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    for index, project in enumerate(projects, start=1):
        print(f"[{index}/{len(projects)}] {project.name}")
        rows.append(run_project(project, output_root, gptscan_src, args))

    write_outputs(rows, output_root, args.backend, len(projects), args.expected_projects)
    print(f"Summary written to: {output_root}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run GPTScan over Web3Bugs-style project folders and collect metadata."
    )
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--backend", choices=("openai", "gemini"), default="gemini")
    parser.add_argument(
        "--limit",
        default="5",
        help="Number of projects, percentage such as 20%%, or all. Default: 5.",
    )
    parser.add_argument("--gptscan-src", type=Path, default=DEFAULT_GPTSCAN_SRC)
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--openai-key", default=os.getenv("OPENAI_API_KEY", ""))
    parser.add_argument("--gemini-env", type=Path, default=DEFAULT_GEMINI_ENV)
    parser.add_argument("--expected-projects", type=int, default=EXPECTED_WEB3BUGS_PROJECTS)
    parser.add_argument("--timeout-seconds", type=int, default=0)
    return parser.parse_args()


def discover_projects(dataset_root: Path) -> list[Path]:
    direct_solidity_files = list(dataset_root.glob("*.sol"))
    if direct_solidity_files:
        return [dataset_root]
    if looks_like_framework_project(dataset_root):
        return [dataset_root]

    projects = []
    for child in sorted(dataset_root.iterdir(), key=lambda path: path.name.lower()):
        if not child.is_dir() or child.name.startswith("."):
            continue
        if child.name.lower() in {"artifacts", "cache", "reports", "screenshots", "node_modules"}:
            continue
        try:
            if any(child.rglob("*.sol")):
                projects.append(child)
        except OSError:
            continue
    return projects


def select_projects(projects: list[Path], limit: str) -> list[Path]:
    normalized = limit.strip().lower()
    if normalized == "all":
        return projects
    if normalized.endswith("%"):
        percent = float(normalized[:-1])
        count = max(1, round(len(projects) * percent / 100))
        return projects[:count]
    count = int(normalized)
    return projects[:count]


def run_project(project: Path, output_root: Path, gptscan_src: Path, args: argparse.Namespace) -> dict[str, Any]:
    scan_source = resolve_scan_source(project)
    project_output = output_root / safe_name(project.name)
    project_output.mkdir(parents=True, exist_ok=True)
    output_json = project_output / "output.json"
    stdout_file = project_output / "stdout.log"
    stderr_file = project_output / "stderr.log"
    metadata_file = Path(str(output_json) + ".metadata.json")

    env = os.environ.copy()
    env["GPTSCAN_LLM_BACKEND"] = args.backend
    env["PYTHONIOENCODING"] = "utf-8"
    if args.backend == "gemini":
        env["GPTSCAN_GEMINI_ENV"] = str(args.gemini_env.resolve())
        key_arg = "GEMINI_BACKEND"
    else:
        key_arg = args.openai_key or "OPENAI_API_KEY_NOT_SET"

    command = [
        args.python,
        "main.py",
        "-s",
        str(scan_source.resolve()),
        "-o",
        str(output_json),
        "-k",
        key_arg,
    ]

    started_at = time.time()
    timeout = args.timeout_seconds if args.timeout_seconds > 0 else None
    timed_out = False
    try:
        completed = subprocess.run(
            command,
            cwd=gptscan_src,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        return_code = completed.returncode
        stdout = completed.stdout
        stderr = completed.stderr
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        return_code = 124
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""

    duration_seconds = time.time() - started_at
    stdout = stdout or ""
    stderr = stderr or ""
    stdout_file.write_text(stdout, encoding="utf-8", errors="replace")
    stderr_file.write_text(stderr, encoding="utf-8", errors="replace")

    metadata = read_json(metadata_file)
    status = classify_status(return_code, timed_out, stdout + "\n" + stderr, metadata_file, output_json)
    row = {
        "project": project.name,
        "project_path": str(project.resolve()),
        "scan_source": str(scan_source.resolve()),
        "backend": args.backend,
        "status": status,
        "return_code": return_code,
        "duration_seconds": round(duration_seconds, 3),
        "output_json": str(output_json),
        "metadata_json": str(metadata_file),
        "stdout_log": str(stdout_file),
        "stderr_log": str(stderr_file),
        "loc": metadata.get("loc"),
        "files": metadata.get("files"),
        "contracts": metadata.get("contracts"),
        "functions": metadata.get("functions"),
        "functions_after_filter": metadata.get("functions_after_filter"),
        "functions_after_step_1": metadata.get("functions_after_step_1"),
        "functions_after_step_2": metadata.get("functions_after_step_2"),
        "vul_before_static": metadata.get("vul_before_static"),
        "vul_after_static": metadata.get("vul_after_static"),
        "vul_after_merge": metadata.get("vul_after_merge"),
        "used_time": metadata.get("used_time"),
        "estimated_cost": metadata.get("estimated_cost"),
        "manual_tp": "",
        "manual_fp": "",
        "manual_fn": "",
        "manual_note": "",
    }
    return row


def resolve_scan_source(project: Path) -> Path:
    for candidate in [project, project / "contracts"]:
        if not candidate.is_dir():
            continue
        if looks_like_framework_project(candidate):
            return candidate

    direct_solidity_files = [path for path in project.glob("*.sol") if path.is_file()]
    if len(direct_solidity_files) == 1:
        return project

    nested_contracts = project / "contracts"
    if nested_contracts.is_dir() and any(nested_contracts.rglob("*.sol")):
        return nested_contracts

    return project


def looks_like_framework_project(path: Path) -> bool:
    framework_files = {
        "package.json",
        "hardhat.config.js",
        "hardhat.config.ts",
        "truffle-config.js",
        "truffle-config.ts",
        "truffle.js",
        "brownie-config.yaml",
        "foundry.toml",
    }
    return any((path / name).exists() for name in framework_files)


def classify_status(
    return_code: int,
    timed_out: bool,
    logs: str,
    metadata_file: Path,
    output_json: Path,
) -> str:
    lowered = logs.lower()
    if timed_out:
        return "llm_failed"
    if any(token in lowered for token in ("gemini", "openai", "api", "quota", "rate limit", "authentication")):
        return "llm_failed"
    if "compile failed" in lowered:
        return "compile_failed"
    if metadata_file.exists() and output_json.exists() and return_code == 0:
        return "completed"
    return "parse_failed"


def write_outputs(
    rows: list[dict[str, Any]],
    output_root: Path,
    backend: str,
    selected_count: int,
    expected_projects: int,
) -> None:
    summary = build_summary(rows, backend, selected_count, expected_projects)
    (output_root / "run_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    write_csv(rows, output_root / "run_summary.csv")
    (output_root / "run_summary.md").write_text(render_markdown(summary, rows), encoding="utf-8")


def build_summary(
    rows: list[dict[str, Any]],
    backend: str,
    selected_count: int,
    expected_projects: int,
) -> dict[str, Any]:
    status_counts: dict[str, int] = {}
    for row in rows:
        status_counts[row["status"]] = status_counts.get(row["status"], 0) + 1

    completed = status_counts.get("completed", 0)
    compile_failed = status_counts.get("compile_failed", 0)
    tried = len(rows)
    total_loc = sum(int(row["loc"] or 0) for row in rows)
    total_used_time = sum(float(row["used_time"] or 0) for row in rows)
    total_before_static = sum(int(row["vul_before_static"] or 0) for row in rows)
    total_after_static = sum(int(row["vul_after_static"] or 0) for row in rows)
    total_after_merge = sum(int(row["vul_after_merge"] or 0) for row in rows)
    kloc = total_loc / 1000 if total_loc else 0

    return {
        "backend": backend,
        "selected_projects": selected_count,
        "expected_web3bugs_projects": expected_projects,
        "status_counts": status_counts,
        "metrics": {
            "run_coverage": safe_ratio(completed, expected_projects),
            "compile_success_rate": safe_ratio(tried - compile_failed, tried),
            "completion_rate": safe_ratio(completed, tried),
            "total_loc": total_loc,
            "runtime_per_kloc": safe_ratio(total_used_time, kloc),
            "vul_before_static": total_before_static,
            "vul_after_static": total_after_static,
            "vul_after_merge": total_after_merge,
            "static_confirmation_reduction": safe_ratio(
                total_before_static - total_after_static,
                total_before_static,
            ),
        },
        "claim_policy": {
            "accuracy_claim_allowed": False,
            "reason": "Runner output lacks paper-equivalent ground truth mapping and manual TP/FP/FN labels by default.",
        },
    }


def render_markdown(summary: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    metrics = summary["metrics"]
    lines = [
        "# Reproduction Log - Web3Bugs",
        "",
        "The 57.14% value is paper-reported precision, not a result reproduced in this environment.",
        "A Gemini run is a backend-sensitivity check, not confirmation of the paper precision.",
        "Without ground-truth mapping or all 72 Web3Bugs projects, read the result only as pipeline observation.",
        "",
        "## Paper Baseline",
        "",
        "| Dataset | TP | TN | FP | FN | Sum | Precision | Recall | F1 |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        "| Web3Bugs | 40 | 154 | 30 | 8 | 232 | 57.14% | 83.33% | 67.8% |",
        "",
        "Static confirmation story: `647 -> 221` is a raw function count before merge, not final `TP + FP`.",
        "",
        "## Our Run Summary",
        "",
        f"- Backend: `{summary['backend']}`",
        f"- Selected projects: `{summary['selected_projects']}`",
        f"- Expected Web3Bugs projects: `{summary['expected_web3bugs_projects']}`",
        f"- Status counts: `{json.dumps(summary['status_counts'], ensure_ascii=False)}`",
        f"- Run coverage: `{metrics['run_coverage']}`",
        f"- Compile success rate: `{metrics['compile_success_rate']}`",
        f"- Completion rate: `{metrics['completion_rate']}`",
        f"- Runtime/KLoC: `{metrics['runtime_per_kloc']}`",
        f"- Pipeline reduction: `{metrics['vul_before_static']} -> {metrics['vul_after_static']} -> {metrics['vul_after_merge']}`",
        "",
        "## Project Rows",
        "",
        "| Project | Status | LoC | Runtime | Before static | After static | After merge | Output |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        lines.append(
            "| {project} | {status} | {loc} | {runtime} | {before} | {after} | {merge} | `{output}` |".format(
                project=row["project"],
                status=row["status"],
                loc=row["loc"] or "",
                runtime=row["used_time"] or row["duration_seconds"],
                before=row["vul_before_static"] or "",
                after=row["vul_after_static"] or "",
                merge=row["vul_after_merge"] or "",
                output=row["output_json"],
            )
        )
    lines.append("")
    return "\n".join(lines)


def write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def safe_ratio(numerator: float, denominator: float) -> float | None:
    if denominator == 0:
        return None
    return round(numerator / denominator, 6)


def safe_name(name: str) -> str:
    return "".join(char if char.isalnum() or char in "._-" else "_" for char in name)


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from gptscan_demo.confirm import confirm_finding
from gptscan_demo.filters import filter_candidates
from gptscan_demo.llm_client import LLMClientError, build_llm_client
from gptscan_demo.mock_gpt import MockLLMClient
from gptscan_demo.models import FindingResult, ScanResult
from gptscan_demo.parser import parse_solidity_file
from gptscan_demo.report import render_json, render_text
from gptscan_demo.scenarios import load_scenarios


DEMO_ROOT = Path(__file__).resolve().parent
DEFAULT_SAMPLE = DEMO_ROOT / "samples" / "vulnerable_gemini.sol"


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    input_file = Path(args.input_file).resolve()
    warnings: list[str] = []

    if not input_file.exists():
        print(f"Input file not found: {input_file}", file=sys.stderr)
        return 2

    scenarios = load_scenarios(DEMO_ROOT / "scenarios.json")
    functions = parse_solidity_file(input_file)
    candidates = filter_candidates(functions, scenarios)
    llm_client = build_llm_client(args.llm, DEMO_ROOT, warnings)
    mock_fallback = MockLLMClient()

    findings: list[FindingResult] = []
    llm_used_values: set[str] = set()
    for candidate in candidates:
        try:
            llm_findings = llm_client.analyze_candidate(candidate, scenarios)
        except LLMClientError as exc:
            warnings.append(
                f"{llm_client.name} failed on {candidate.function.name} ({exc}); using mock fallback."
            )
            llm_findings = mock_fallback.analyze_candidate(candidate, scenarios)

        for llm_finding in llm_findings:
            llm_used_values.add(llm_finding.llm_used)
            findings.append(
                FindingResult(
                    llm_finding=llm_finding,
                    confirmation=confirm_finding(llm_finding),
                )
            )

    llm_used = ", ".join(sorted(llm_used_values)) if llm_used_values else llm_client.name
    result = ScanResult(
        input_file=input_file,
        llm_requested=args.llm,
        llm_used=llm_used,
        function_count=len(functions),
        candidates=candidates,
        findings=findings,
        warnings=warnings,
    )

    print(render_json(result) if args.json else render_text(result))
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="GPTScan-inspired Solidity vulnerability pipeline demo."
    )
    parser.add_argument(
        "input_file",
        nargs="?",
        default=str(DEFAULT_SAMPLE),
        help="Solidity file to scan. Defaults to demo/samples/vulnerable_gemini.sol.",
    )
    parser.add_argument(
        "--llm",
        choices=("auto", "mock", "gemini"),
        default="auto",
        help="LLM backend. auto uses Gemini when GOOGLE_API_KEY is set, otherwise mock.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of the staged text report.",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())


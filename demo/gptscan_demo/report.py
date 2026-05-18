from __future__ import annotations

import json

from .models import FindingResult, ScanResult


def render_json(result: ScanResult) -> str:
    return json.dumps(result.to_dict(), indent=2)


def render_text(result: ScanResult) -> str:
    lines: list[str] = []
    lines.append("GPTScan-inspired Demo")
    lines.append("=" * 24)
    lines.append(f"Input: {result.input_file}")
    lines.append(f"LLM requested: {result.llm_requested}")
    lines.append(f"LLM used: {result.llm_used}")
    lines.append("")
    lines.append("[1] Parse")
    lines.append(f"- Functions discovered: {result.function_count}")
    lines.append("")
    lines.append("[2] Static filter")
    lines.append(f"- Candidate functions: {len(result.candidates)}")
    for candidate in result.candidates:
        line_range = f"{candidate.function.start_line}-{candidate.function.end_line}"
        vulns = ", ".join(candidate.possible_vulnerabilities)
        reasons = "; ".join(candidate.reasons)
        lines.append(f"  - {candidate.function.name} ({line_range}): {vulns}")
        lines.append(f"    reason: {reasons}")
    lines.append("")
    lines.append("[3] LLM matching + key extraction")
    lines.append(f"- Potential findings: {len(result.findings)}")
    lines.append("")
    lines.append("[4] Static confirmation")
    if not result.findings:
        lines.append("- No findings.")
    for item in result.findings:
        lines.extend(_render_finding(item))

    if result.warnings:
        lines.append("")
        lines.append("Warnings")
        for warning in result.warnings:
            lines.append(f"- {warning}")

    return "\n".join(lines)


def _render_finding(item: FindingResult) -> list[str]:
    finding = item.llm_finding
    confirmation = item.confirmation
    line_range = f"{finding.function.start_line}-{finding.function.end_line}"
    lines = [
        f"- {finding.vulnerability_type} in {finding.function.name} ({line_range})",
        f"  confidence: {finding.confidence:.2f} via {finding.llm_used}",
        f"  status: {confirmation.status}",
        f"  LLM: {finding.explanation}",
        f"  proof: {confirmation.proof}",
    ]
    if finding.key_variables:
        lines.append(f"  key variables: {', '.join(finding.key_variables)}")
    if confirmation.evidence:
        lines.append("  evidence:")
        for statement in confirmation.evidence:
            line = "?" if statement.line is None else str(statement.line)
            lines.append(f"    line {line} [{statement.role}]: {statement.code}")
    return lines


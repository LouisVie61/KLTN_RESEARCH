from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SolidityFunction:
    name: str
    signature: str
    source: str
    body: str
    start_line: int
    end_line: int
    file_path: Path

    def lines(self) -> list[tuple[int, str]]:
        return [
            (self.start_line + index, line)
            for index, line in enumerate(self.source.splitlines())
        ]


@dataclass(frozen=True)
class ScenarioDefinition:
    id: str
    name: str
    scenario: str
    property: str
    static_check: str
    filter_keywords: list[str] = field(default_factory=list)


@dataclass
class CandidateFunction:
    function: SolidityFunction
    possible_vulnerabilities: list[str]
    reasons: list[str]


@dataclass
class ScenarioMatch:
    vulnerability_type: str
    scenario_matched: bool
    property_matched: bool
    confidence: float
    explanation: str
    llm_used: str


@dataclass
class KeyStatement:
    line: int | None
    code: str
    role: str


@dataclass
class LLMFinding:
    function: SolidityFunction
    vulnerability_type: str
    scenario: str
    property: str
    confidence: float
    key_variables: list[str]
    key_statements: list[KeyStatement]
    explanation: str
    llm_used: str


@dataclass
class ConfirmationResult:
    status: str
    proof: str
    evidence: list[KeyStatement] = field(default_factory=list)


@dataclass
class FindingResult:
    llm_finding: LLMFinding
    confirmation: ConfirmationResult


@dataclass
class ScanResult:
    input_file: Path
    llm_requested: str
    llm_used: str
    function_count: int
    candidates: list[CandidateFunction]
    findings: list[FindingResult]
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "input_file": str(self.input_file),
            "llm_requested": self.llm_requested,
            "llm_used": self.llm_used,
            "function_count": self.function_count,
            "candidate_count": len(self.candidates),
            "candidates": [
                {
                    "function": candidate.function.name,
                    "line_range": [
                        candidate.function.start_line,
                        candidate.function.end_line,
                    ],
                    "possible_vulnerabilities": candidate.possible_vulnerabilities,
                    "reasons": candidate.reasons,
                }
                for candidate in self.candidates
            ],
            "findings": [
                {
                    "file": str(result.llm_finding.function.file_path),
                    "function": result.llm_finding.function.name,
                    "line_range": [
                        result.llm_finding.function.start_line,
                        result.llm_finding.function.end_line,
                    ],
                    "vulnerability_type": result.llm_finding.vulnerability_type,
                    "scenario": result.llm_finding.scenario,
                    "property": result.llm_finding.property,
                    "confidence": result.llm_finding.confidence,
                    "llm_used": result.llm_finding.llm_used,
                    "key_variables": result.llm_finding.key_variables,
                    "key_statements": [
                        {
                            "line": statement.line,
                            "role": statement.role,
                            "code": statement.code,
                        }
                        for statement in result.llm_finding.key_statements
                    ],
                    "llm_explanation": result.llm_finding.explanation,
                    "confirmation": {
                        "status": result.confirmation.status,
                        "proof": result.confirmation.proof,
                        "evidence": [
                            {
                                "line": statement.line,
                                "role": statement.role,
                                "code": statement.code,
                            }
                            for statement in result.confirmation.evidence
                        ],
                    },
                }
                for result in self.findings
            ],
            "warnings": self.warnings,
        }


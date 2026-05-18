from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from .llm_client import LLMClientError
from .models import CandidateFunction, KeyStatement, LLMFinding, ScenarioDefinition, ScenarioMatch


class GeminiLLMClient:
    name = "gemini"

    def __init__(self, demo_root: Path) -> None:
        try:
            from google import genai
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise LLMClientError("Install google-genai to use Gemini.") from exc

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise LLMClientError("GEMINI_API_KEY is not set.")

        self.model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self.client = genai.Client(api_key=api_key)
        self.match_prompt = (demo_root / "prompts" / "scenario_match.txt").read_text(encoding="utf-8")
        self.key_prompt = (demo_root / "prompts" / "key_location.txt").read_text(encoding="utf-8")

    def analyze_candidate(
        self,
        candidate: CandidateFunction,
        scenarios: dict[str, ScenarioDefinition],
    ) -> list[LLMFinding]:
        matches = self.match_candidate(candidate, scenarios)
        findings: list[LLMFinding] = []
        for match in matches:
            if not match.scenario_matched or not match.property_matched:
                continue
            findings.append(self.extract_keys(candidate, match, scenarios))
        return findings

    def match_candidate(
        self,
        candidate: CandidateFunction,
        scenarios: dict[str, ScenarioDefinition],
    ) -> list[ScenarioMatch]:
        scenario_payload = [
            {
                "id": scenario_id,
                "name": scenarios[scenario_id].name,
                "scenario": scenarios[scenario_id].scenario,
                "property": scenarios[scenario_id].property,
            }
            for scenario_id in candidate.possible_vulnerabilities
            if scenario_id in scenarios
        ]
        prompt = self.match_prompt.format(
            function_name=candidate.function.name,
            signature=candidate.function.signature,
            line_start=candidate.function.start_line,
            line_end=candidate.function.end_line,
            scenarios=json.dumps(scenario_payload, indent=2),
            code=candidate.function.source,
        )
        raw = self._generate_json(prompt)
        items = raw.get("matches", [])
        matches: list[ScenarioMatch] = []
        for item in items:
            vulnerability_type = str(item.get("vulnerability_type", "")).strip()
            if vulnerability_type not in scenarios:
                continue
            matches.append(
                ScenarioMatch(
                    vulnerability_type=vulnerability_type,
                    scenario_matched=bool(item.get("scenario_matched", False)),
                    property_matched=bool(item.get("property_matched", False)),
                    confidence=float(item.get("confidence", 0.0)),
                    explanation=str(item.get("explanation", "")),
                    llm_used=self.name,
                )
            )
        return matches

    def extract_keys(
        self,
        candidate: CandidateFunction,
        match: ScenarioMatch,
        scenarios: dict[str, ScenarioDefinition],
    ) -> LLMFinding:
        scenario = scenarios[match.vulnerability_type]
        prompt = self.key_prompt.format(
            function_name=candidate.function.name,
            vulnerability_type=match.vulnerability_type,
            scenario=scenario.scenario,
            property=scenario.property,
            line_start=candidate.function.start_line,
            line_end=candidate.function.end_line,
            code=candidate.function.source,
        )
        raw = self._generate_json(prompt)
        statements = [
            KeyStatement(
                line=_optional_int(item.get("line")),
                role=str(item.get("role", "unknown")),
                code=str(item.get("code", "")),
            )
            for item in raw.get("key_statements", [])
            if isinstance(item, dict)
        ]
        return LLMFinding(
            function=candidate.function,
            vulnerability_type=match.vulnerability_type,
            scenario=scenario.scenario,
            property=scenario.property,
            confidence=match.confidence,
            key_variables=[str(item) for item in raw.get("key_variables", [])],
            key_statements=statements,
            explanation=raw.get("explanation", match.explanation),
            llm_used=self.name,
        )

    def _generate_json(self, prompt: str) -> dict[str, Any]:
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
            )
        except Exception as exc:  # pragma: no cover - network/API dependent
            raise LLMClientError(f"Gemini request failed: {exc}") from exc

        text = getattr(response, "text", "") or ""
        try:
            return json.loads(_strip_json_fence(text))
        except json.JSONDecodeError as exc:
            raise LLMClientError(f"Gemini returned non-JSON response: {text[:200]}") from exc


def _strip_json_fence(text: str) -> str:
    stripped = text.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", stripped, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        return fenced.group(1).strip()
    return stripped


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


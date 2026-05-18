from __future__ import annotations

from .filters import has_access_control
from .models import CandidateFunction, KeyStatement, LLMFinding, ScenarioDefinition, ScenarioMatch


class MockLLMClient:
    name = "mock"

    def match_candidate(
        self,
        candidate: CandidateFunction,
        scenarios: dict[str, ScenarioDefinition],
    ) -> list[ScenarioMatch]:
        matches: list[ScenarioMatch] = []
        source = candidate.function.source.lower()

        for scenario_id in candidate.possible_vulnerabilities:
            confidence = 0.72
            explanation = "Mock semantic matcher found code-level scenario/property keywords."
            scenario_matched = True
            property_matched = True

            if scenario_id == "reentrancy_order_issue":
                confidence = 0.88 if ".call{" in source or ".call(" in source else 0.65
                explanation = "External call appears near balance/state update logic."
            elif scenario_id == "missing_access_control":
                confidence = 0.82
                if has_access_control(candidate.function):
                    confidence = 0.55
                    explanation = "Sensitive operation exists, but access-control text is also present."
                else:
                    explanation = "Sensitive operation appears in a public/external function."
            elif scenario_id == "risky_first_deposit":
                confidence = 0.86
                explanation = "Supply-zero branch appears near share minting logic."

            matches.append(
                ScenarioMatch(
                    vulnerability_type=scenario_id,
                    scenario_matched=scenario_matched,
                    property_matched=property_matched,
                    confidence=confidence,
                    explanation=explanation,
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
        key_variables = _guess_variables(candidate, match.vulnerability_type)
        key_statements = _guess_statements(candidate, match.vulnerability_type)
        return LLMFinding(
            function=candidate.function,
            vulnerability_type=match.vulnerability_type,
            scenario=scenario.scenario,
            property=scenario.property,
            confidence=match.confidence,
            key_variables=key_variables,
            key_statements=key_statements,
            explanation=match.explanation,
            llm_used=self.name,
        )

    def analyze_candidate(
        self,
        candidate: CandidateFunction,
        scenarios: dict[str, ScenarioDefinition],
    ) -> list[LLMFinding]:
        return [
            self.extract_keys(candidate, match, scenarios)
            for match in self.match_candidate(candidate, scenarios)
            if match.scenario_matched and match.property_matched
        ]


def _guess_variables(candidate: CandidateFunction, vulnerability_type: str) -> list[str]:
    source = candidate.function.source
    variables: list[str] = []
    for token in ("balances", "amount", "owner", "totalSupply", "shares", "_shares", "totalShares"):
        if token in source and token not in variables:
            variables.append(token)

    if vulnerability_type == "missing_access_control" and "owner" not in variables:
        variables.append("owner")
    return variables[:5]


def _guess_statements(candidate: CandidateFunction, vulnerability_type: str) -> list[KeyStatement]:
    statements: list[KeyStatement] = []
    for line, code in candidate.function.lines():
        normalized = code.lower()
        stripped = code.strip()
        role = None
        if vulnerability_type == "reentrancy_order_issue":
            if ".call{" in normalized or ".call(" in normalized:
                role = "external_call"
            elif "balance" in normalized and ("-=" in stripped or "+=" in stripped):
                role = "state_update"
        elif vulnerability_type == "missing_access_control":
            if "_mint(" in normalized or ".mint(" in normalized or "owner =" in normalized:
                role = "sensitive_operation"
        elif vulnerability_type == "risky_first_deposit":
            if "totalsupply" in normalized and "0" in normalized:
                role = "supply_zero_branch"
            elif "shares" in normalized or "_mint(" in normalized:
                role = "share_or_mint_logic"

        if role:
            statements.append(KeyStatement(line=line, code=stripped, role=role))

    return statements[:6]

from __future__ import annotations

import sys
import unittest
from pathlib import Path


DEMO_ROOT = Path(__file__).resolve().parents[1]
if str(DEMO_ROOT) not in sys.path:
    sys.path.insert(0, str(DEMO_ROOT))

from gptscan_demo.confirm import confirm_finding
from gptscan_demo.filters import filter_candidates
from gptscan_demo.mock_gpt import MockLLMClient
from gptscan_demo.models import LLMFinding
from gptscan_demo.parser import parse_functions
from gptscan_demo.scenarios import load_scenarios


SCENARIOS = load_scenarios(DEMO_ROOT / "scenarios.json")


class ComponentTests(unittest.TestCase):
    def test_parser_extracts_functions_and_lines(self) -> None:
        source = """pragma solidity ^0.8.20;

contract A {
    function one() public {
        uint256 x = 1;
    }

    function two(uint256 y) external returns (uint256) {
        return y;
    }
}
"""
        functions = parse_functions(source, Path("A.sol"))
        self.assertEqual([function.name for function in functions], ["one", "two"])
        self.assertEqual(functions[0].start_line, 4)
        self.assertEqual(functions[1].start_line, 8)
        self.assertIn("external returns", functions[1].signature)

    def test_filter_selects_expected_sample_candidates(self) -> None:
        sample = (DEMO_ROOT / "samples" / "vulnerable.sol").read_text(encoding="utf-8")
        functions = parse_functions(sample, DEMO_ROOT / "samples" / "vulnerable.sol")
        candidates = filter_candidates(functions, SCENARIOS)
        by_name = {candidate.function.name: candidate for candidate in candidates}

        self.assertIn("withdraw", by_name)
        self.assertIn("mintReward", by_name)
        self.assertIn("firstDeposit", by_name)
        self.assertIn("protectedMint", by_name)
        self.assertIn("reentrancy_order_issue", by_name["withdraw"].possible_vulnerabilities)
        self.assertIn("missing_access_control", by_name["mintReward"].possible_vulnerabilities)
        self.assertIn("risky_first_deposit", by_name["firstDeposit"].possible_vulnerabilities)

    def test_mock_llm_returns_deterministic_findings(self) -> None:
        sample = (DEMO_ROOT / "samples" / "vulnerable.sol").read_text(encoding="utf-8")
        functions = parse_functions(sample, DEMO_ROOT / "samples" / "vulnerable.sol")
        candidates = filter_candidates(functions, SCENARIOS)
        withdraw = next(candidate for candidate in candidates if candidate.function.name == "withdraw")

        findings = MockLLMClient().analyze_candidate(withdraw, SCENARIOS)

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].vulnerability_type, "reentrancy_order_issue")
        self.assertTrue(findings[0].key_statements)

    def test_confirmation_confirms_reentrancy_order(self) -> None:
        finding = _finding_for("withdraw", "reentrancy_order_issue")

        result = confirm_finding(finding)

        self.assertEqual(result.status, "confirmed")
        self.assertIn("external call before", result.proof)

    def test_confirmation_rejects_protected_access_control(self) -> None:
        finding = _finding_for("protectedMint", "missing_access_control")

        result = confirm_finding(finding)

        self.assertEqual(result.status, "rejected")
        self.assertIn("owner check", result.proof)

    def test_confirmation_confirms_risky_first_deposit(self) -> None:
        finding = _finding_for("firstDeposit", "risky_first_deposit")

        result = confirm_finding(finding)

        self.assertEqual(result.status, "confirmed")
        self.assertIn("Supply-zero", result.proof)


def _finding_for(function_name: str, vulnerability_type: str) -> LLMFinding:
    sample_path = DEMO_ROOT / "samples" / "vulnerable.sol"
    functions = parse_functions(sample_path.read_text(encoding="utf-8"), sample_path)
    function = next(item for item in functions if item.name == function_name)
    scenario = SCENARIOS[vulnerability_type]
    return LLMFinding(
        function=function,
        vulnerability_type=vulnerability_type,
        scenario=scenario.scenario,
        property=scenario.property,
        confidence=0.9,
        key_variables=[],
        key_statements=[],
        explanation="test",
        llm_used="mock",
    )


if __name__ == "__main__":
    unittest.main()


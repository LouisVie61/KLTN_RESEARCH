from __future__ import annotations

import re

from .filters import EXTERNAL_CALL_PATTERNS, has_access_control
from .models import ConfirmationResult, KeyStatement, LLMFinding, SolidityFunction


def confirm_finding(finding: LLMFinding) -> ConfirmationResult:
    checkers = {
        "reentrancy_order_issue": _confirm_reentrancy_order,
        "missing_access_control": _confirm_missing_access_control,
        "risky_first_deposit": _confirm_risky_first_deposit,
    }
    checker = checkers.get(finding.vulnerability_type)
    if checker is None:
        return ConfirmationResult(
            status="needs_review",
            proof="No static confirmation rule is registered for this finding.",
        )
    return checker(finding.function)


def _confirm_reentrancy_order(function: SolidityFunction) -> ConfirmationResult:
    lines = function.lines()
    external_calls = [
        KeyStatement(line, code.strip(), "external_call")
        for line, code in lines
        if _is_external_call(code)
    ]
    state_updates = [
        KeyStatement(line, code.strip(), "state_update")
        for line, code in lines
        if _is_state_update(code)
    ]

    for call in external_calls:
        later_updates = [
            update for update in state_updates if update.line is not None and call.line is not None and update.line > call.line
        ]
        if later_updates:
            first_update = later_updates[0]
            return ConfirmationResult(
                status="confirmed",
                proof=(
                    "Static order check found an external call before a state/balance "
                    f"update at lines {call.line} -> {first_update.line}."
                ),
                evidence=[call, first_update],
            )

    if external_calls:
        return ConfirmationResult(
            status="rejected",
            proof="External call exists, but no later state/balance update was found.",
            evidence=external_calls[:1],
        )
    return ConfirmationResult(
        status="rejected",
        proof="No low-level or ETH transfer-style external call was found.",
    )


def _confirm_missing_access_control(function: SolidityFunction) -> ConfirmationResult:
    sensitive_statements = [
        KeyStatement(line, code.strip(), "sensitive_operation")
        for line, code in function.lines()
        if _is_sensitive_operation(function, code)
    ]

    if not sensitive_statements:
        return ConfirmationResult(
            status="rejected",
            proof="No owner/admin/mint-style sensitive operation was found.",
        )

    if has_access_control(function):
        return ConfirmationResult(
            status="rejected",
            proof="Sensitive operation exists, but an owner check or onlyOwner modifier is present.",
            evidence=sensitive_statements[:1],
        )

    return ConfirmationResult(
        status="confirmed",
        proof="Sensitive operation is reachable from a public/external function with no obvious owner check.",
        evidence=sensitive_statements[:2],
    )


def _confirm_risky_first_deposit(function: SolidityFunction) -> ConfirmationResult:
    supply_zero = [
        KeyStatement(line, code.strip(), "supply_zero_branch")
        for line, code in function.lines()
        if re.search(r"(totalSupply\s*\(\s*\)|totalSupply|supply)\s*(==|<=)\s*0", code, re.IGNORECASE)
    ]
    direct_share = [
        KeyStatement(line, code.strip(), "direct_initial_share")
        for line, code in function.lines()
        if re.search(r"shares?\s*=\s*_?amount\b|_shares\s*=\s*_?amount\b|_mint\s*\([^,]+,\s*_?amount\s*\)", code, re.IGNORECASE)
    ]
    mint_lines = [
        KeyStatement(line, code.strip(), "mint_share")
        for line, code in function.lines()
        if "_mint(" in code or ".mint(" in code
    ]

    if supply_zero and (direct_share or mint_lines):
        return ConfirmationResult(
            status="confirmed",
            proof="Supply-zero branch mints or assigns initial shares directly from the deposit amount.",
            evidence=(supply_zero[:1] + direct_share[:1] + mint_lines[:1])[:3],
        )

    if supply_zero:
        return ConfirmationResult(
            status="needs_review",
            proof="Supply-zero branch exists, but direct share minting was not proven by the heuristic.",
            evidence=supply_zero[:1],
        )
    return ConfirmationResult(
        status="rejected",
        proof="No totalSupply/supply zero branch was found.",
    )


def _is_external_call(code: str) -> bool:
    normalized = code.lower()
    return any(pattern in normalized for pattern in EXTERNAL_CALL_PATTERNS)


def _is_state_update(code: str) -> bool:
    stripped = code.strip()
    normalized = stripped.lower()
    if stripped.startswith("//"):
        return False
    if not any(token in normalized for token in ("balance", "balances", "shares", "supply", "locked")):
        return False
    return bool(re.search(r"\+=|-=|(?<![!<>=])=(?!=)", stripped))


def _is_sensitive_operation(function: SolidityFunction, code: str) -> bool:
    normalized = code.lower()
    if "_mint(" in normalized or ".mint(" in normalized:
        return True
    if re.search(r"\bowner\s*=", normalized):
        return True
    if "selfdestruct" in normalized:
        return True
    if any(token in normalized for token in ("_pause(", "_unpause(", "sweep(")):
        return True
    return False

from __future__ import annotations

import re

from .models import CandidateFunction, ScenarioDefinition, SolidityFunction


EXTERNAL_CALL_PATTERNS = (".call{", ".call(", ".send(", ".transfer(")
ACCESS_CONTROL_PATTERNS = (
    "onlyowner",
    "require(msg.sender == owner",
    "require(owner == msg.sender",
    "require(_msgsender() == owner",
    "_checkowner()",
)


def filter_candidates(
    functions: list[SolidityFunction],
    scenarios: dict[str, ScenarioDefinition],
) -> list[CandidateFunction]:
    candidates: list[CandidateFunction] = []
    for function in functions:
        possible: list[str] = []
        reasons: list[str] = []

        if _looks_reentrancy_candidate(function):
            possible.append("reentrancy_order_issue")
            reasons.append("external call and later state/balance update keywords")

        if _looks_access_control_candidate(function):
            possible.append("missing_access_control")
            reasons.append("public/external sensitive operation without relying on compilation")

        if _looks_risky_first_deposit_candidate(function):
            possible.append("risky_first_deposit")
            reasons.append("supply-zero branch combined with mint/share logic")

        possible = [item for item in possible if item in scenarios]
        if possible:
            candidates.append(
                CandidateFunction(
                    function=function,
                    possible_vulnerabilities=possible,
                    reasons=reasons,
                )
            )

    return candidates


def has_access_control(function: SolidityFunction) -> bool:
    normalized = _compact(function.signature + "\n" + function.body)
    return any(pattern in normalized for pattern in ACCESS_CONTROL_PATTERNS)


def _looks_reentrancy_candidate(function: SolidityFunction) -> bool:
    normalized = function.source.lower()
    if not any(pattern in normalized for pattern in EXTERNAL_CALL_PATTERNS):
        return False
    return bool(re.search(r"\b(balance|balances|shares|supply|locked)\b", normalized))


def _looks_access_control_candidate(function: SolidityFunction) -> bool:
    if not _is_public_entrypoint(function):
        return False

    normalized = function.source.lower()
    signature = function.signature.lower()
    sensitive_name = any(
        keyword in function.name.lower()
        for keyword in ("mint", "owner", "admin", "pause", "sweep")
    )
    sensitive_body = any(
        pattern in normalized
        for pattern in ("_mint(", "owner =", "selfdestruct", ".mint(")
    )
    withdraw_admin_like = "withdraw" in signature and "balances[msg.sender]" not in normalized
    return sensitive_name or sensitive_body or withdraw_admin_like


def _looks_risky_first_deposit_candidate(function: SolidityFunction) -> bool:
    normalized = function.source.lower()
    has_supply_zero = bool(
        re.search(r"(totalsupply\s*\(\s*\)|totalsupply|supply)\s*(==|<=)\s*0", normalized)
    )
    has_mint_or_share = any(
        token in normalized for token in ("_mint(", ".mint(", "shares", "_shares")
    )
    has_deposit_context = any(
        token in normalized for token in ("deposit", "liquidity", "share", "amount")
    )
    return has_supply_zero and has_mint_or_share and has_deposit_context


def _is_public_entrypoint(function: SolidityFunction) -> bool:
    signature = function.signature.lower()
    return " public" in signature or " external" in signature


def _compact(value: str) -> str:
    return re.sub(r"\s+", "", value.lower())


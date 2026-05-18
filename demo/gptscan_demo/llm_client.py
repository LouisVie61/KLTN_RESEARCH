from __future__ import annotations

import os
from pathlib import Path
from typing import Protocol

from .mock_gpt import MockLLMClient
from .models import CandidateFunction, LLMFinding, ScenarioDefinition


class LLMClient(Protocol):
    name: str

    def analyze_candidate(
        self,
        candidate: CandidateFunction,
        scenarios: dict[str, ScenarioDefinition],
    ) -> list[LLMFinding]:
        ...


class LLMClientError(RuntimeError):
    pass


def load_env(demo_root: Path) -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return

    load_dotenv(demo_root / ".env")
    load_dotenv()


def build_llm_client(mode: str, demo_root: Path, warnings: list[str]) -> LLMClient:
    load_env(demo_root)

    if mode == "mock":
        return MockLLMClient()

    if mode == "auto" and not os.getenv("GEMINI_API_KEY"):
        warnings.append("GEMINI_API_KEY is not set; using mock LLM.")
        return MockLLMClient()

    if mode in {"auto", "gemini"}:
        if not os.getenv("GEMINI_API_KEY"):
            warnings.append("GEMINI_API_KEY is not set; falling back to mock LLM.")
            return MockLLMClient()
        try:
            from .gemini_client import GeminiLLMClient

            return GeminiLLMClient(demo_root=demo_root)
        except Exception as exc:  # pragma: no cover - depends on optional SDK install
            warnings.append(f"Gemini client is unavailable ({exc}); falling back to mock LLM.")
            return MockLLMClient()

    raise ValueError(f"Unsupported LLM mode: {mode}")


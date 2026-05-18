from __future__ import annotations

import json
from pathlib import Path

from .models import ScenarioDefinition


def load_scenarios(path: Path) -> dict[str, ScenarioDefinition]:
    with path.open("r", encoding="utf-8") as handle:
        raw_items = json.load(handle)

    scenarios: dict[str, ScenarioDefinition] = {}
    for item in raw_items:
        scenario = ScenarioDefinition(
            id=item["id"],
            name=item["name"],
            scenario=item["scenario"],
            property=item["property"],
            static_check=item["static_check"],
            filter_keywords=list(item.get("filter_keywords", [])),
        )
        scenarios[scenario.id] = scenario
    return scenarios


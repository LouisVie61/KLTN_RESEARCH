from __future__ import annotations

import bisect
import re
from pathlib import Path

from .models import SolidityFunction


FUNCTION_RE = re.compile(r"\bfunction\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(")


def parse_solidity_file(path: Path) -> list[SolidityFunction]:
    source = path.read_text(encoding="utf-8")
    return parse_functions(source, path)


def parse_functions(source: str, file_path: Path) -> list[SolidityFunction]:
    line_offsets = _line_offsets(source)
    functions: list[SolidityFunction] = []

    for match in FUNCTION_RE.finditer(source):
        brace_index = source.find("{", match.end())
        semicolon_index = source.find(";", match.end())
        if brace_index == -1:
            continue
        if semicolon_index != -1 and semicolon_index < brace_index:
            continue

        end_index = _find_matching_brace(source, brace_index)
        if end_index is None:
            continue

        signature = source[match.start() : brace_index].strip()
        function_source = source[match.start() : end_index + 1]
        body = source[brace_index : end_index + 1]
        start_line = _line_number(line_offsets, match.start())
        end_line = _line_number(line_offsets, end_index)

        functions.append(
            SolidityFunction(
                name=match.group(1),
                signature=signature,
                source=function_source,
                body=body,
                start_line=start_line,
                end_line=end_line,
                file_path=file_path,
            )
        )

    return functions


def _line_offsets(source: str) -> list[int]:
    offsets = [0]
    for index, char in enumerate(source):
        if char == "\n":
            offsets.append(index + 1)
    return offsets


def _line_number(line_offsets: list[int], char_index: int) -> int:
    return bisect.bisect_right(line_offsets, char_index)


def _find_matching_brace(source: str, open_index: int) -> int | None:
    depth = 0
    index = open_index
    state = "code"

    while index < len(source):
        char = source[index]
        next_char = source[index + 1] if index + 1 < len(source) else ""

        if state == "line_comment":
            if char == "\n":
                state = "code"
            index += 1
            continue

        if state == "block_comment":
            if char == "*" and next_char == "/":
                state = "code"
                index += 2
                continue
            index += 1
            continue

        if state == "string":
            if char == "\\":
                index += 2
                continue
            if char == '"':
                state = "code"
            index += 1
            continue

        if state == "single_quote":
            if char == "\\":
                index += 2
                continue
            if char == "'":
                state = "code"
            index += 1
            continue

        if char == "/" and next_char == "/":
            state = "line_comment"
            index += 2
            continue
        if char == "/" and next_char == "*":
            state = "block_comment"
            index += 2
            continue
        if char == '"':
            state = "string"
            index += 1
            continue
        if char == "'":
            state = "single_quote"
            index += 1
            continue

        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index
        index += 1

    return None


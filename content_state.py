"""Persistent, monotonic allocation of generated post and reel IDs."""

import json
import os
import re
import tempfile

STATE_FILENAME = "content_state.json"
PATTERNS = {"post": re.compile(r"post_(\d+)$", re.IGNORECASE), "reel": re.compile(r"reel_(\d+)$", re.IGNORECASE)}


def _number_from_id(value, kind):
    if isinstance(value, int) and value > 0:
        return value
    if not isinstance(value, str):
        return None
    match = PATTERNS[kind].fullmatch(value.strip())
    if not match:
        return None
    number = int(match.group(1))
    return number if number > 0 else None


def _numbers_from_queue(path, kind):
    try:
        with open(path, "r", encoding="utf-8") as queue_file: queue = json.load(queue_file)
    except (OSError, json.JSONDecodeError): return []
    if not isinstance(queue, list): return []
    return [number for item in queue if isinstance(item, dict) for number in [_number_from_id(item.get("id"), kind)] if number]


def _numbers_from_artifacts(directory, kind):
    try: names = os.listdir(directory)
    except OSError: return []
    extensions = {".jpg", ".jpeg", ".png", ".webp", ".jfif", ".txt"} if kind == "post" else {".mp4", ".txt"}
    numbers = []
    for name in names:
        stem, extension = os.path.splitext(name)
        number = _number_from_id(stem, kind) if extension.lower() in extensions else None
        if number: numbers.append(number)
    return numbers


def _read_state(path):
    try:
        with open(path, "r", encoding="utf-8") as state_file: data = json.load(state_file)
    except (OSError, json.JSONDecodeError): return {}
    return data if isinstance(data, dict) else {}


def _write_state(path, state):
    directory = os.path.dirname(os.path.abspath(path)) or "."
    fd, temporary_path = tempfile.mkstemp(prefix="content-state-", suffix=".json", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as state_file:
            json.dump(state, state_file, indent=2); state_file.write("\n")
        os.replace(temporary_path, path)
    finally:
        if os.path.exists(temporary_path): os.unlink(temporary_path)


def allocate_next(kind, *, state_path, queue_path, artifact_directories):
    state = _read_state(state_path)
    candidates = [_number_from_id(state.get(f"last_{kind}_number"), kind)]
    candidates += _numbers_from_queue(queue_path, kind)
    for directory in artifact_directories: candidates += _numbers_from_artifacts(directory, kind)
    return max((number for number in candidates if number), default=0) + 1


def persist_allocated(kind, number, *, state_path):
    state = _read_state(state_path)
    key = f"last_{kind}_number"; current = state.get(key, 0)
    if not isinstance(current, int) or current < 0: current = 0
    state[key] = max(current, number)
    _write_state(state_path, state)

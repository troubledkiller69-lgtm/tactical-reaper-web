import json
import logging
import os
import tempfile
from datetime import datetime

logger = logging.getLogger(__name__)

HISTORY_FILE = "history.json"


class HistoryManager:
    def __init__(self) -> None:
        self.history: dict[str, list] = self._load()

    def _load(self) -> dict[str, list]:
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict) and "past" in data and "current" in data:
                        return data
            except (json.JSONDecodeError, IOError) as e:
                logger.warning("Failed to load history file: %s", e)
        return {"past": [], "current": []}

    def _save(self) -> None:
        dir_name = os.path.dirname(os.path.abspath(HISTORY_FILE))
        tmp_path = None
        try:
            fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(self.history, f, indent=4)
            os.replace(tmp_path, HISTORY_FILE)
        except IOError as e:
            logger.error("Failed to save history: %s", e)
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)

    def add_to_past(self, target: str, reason: str) -> None:
        entry = {
            "target": target,
            "reason": reason,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        self.history["past"].append(entry)
        self._save()

    def add_to_current(self, target: str, reason: str) -> None:
        entry = {
            "target": target,
            "reason": reason,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        self.history["current"].append(entry)
        self._save()

    def clear_current(self, target: str) -> None:
        self.history["current"] = [r for r in self.history["current"] if r["target"] != target]
        self._save()

    def get_past(self, limit: int = 10) -> list[dict]:
        return self.history["past"][-limit:]

    def get_current(self) -> list[dict]:
        return self.history["current"]

import json
import os
import sys
import logging

logger = logging.getLogger(__name__)

class SettingsManager:
    """Manages persistent settings for PyDM."""

    def __init__(self):
        if sys.platform == "win32":
            base = os.environ.get("APPDATA", os.path.expanduser("~"))
            self.config_dir = os.path.join(base, "pydm")
        else:
            self.config_dir = os.path.expanduser("~/.config/pydm")
        self.config_file = os.path.join(self.config_dir, "settings.json")
        self._settings = self._load()

    def _load(self) -> dict:
        """Load settings from the JSON file."""
        if not os.path.exists(self.config_file):
            return {}
        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load settings from {self.config_file}: {e}")
            return {}

    def _save(self):
        """Save current settings to the JSON file."""
        try:
            os.makedirs(self.config_dir, exist_ok=True)
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self._settings, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save settings to {self.config_file}: {e}")

    def get(self, key: str, default=None):
        """Get a setting by key."""
        return self._settings.get(key, default)

    def set(self, key: str, value):
        """Set a setting and save it immediately."""
        self._settings[key] = value
        self._save()

    def get_category_path(self, category_name: str) -> str | None:
        """Get the custom path defined for a specific category, if any."""
        category_paths = self.get("category_paths", {})
        return category_paths.get(category_name)

    def set_category_path(self, category_name: str, path: str):
        """Set a custom path for a specific category and save."""
        category_paths = self.get("category_paths", {})
        category_paths[category_name] = path
        self.set("category_paths", category_paths)

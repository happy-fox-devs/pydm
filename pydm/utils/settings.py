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

    # ── Autostart helpers ────────────────────────────────────────────

    def get_autostart(self) -> bool:
        """Check if PyDM is set to start with the OS."""
        if sys.platform == "win32":
            return self._win_get_autostart()
        else:
            return self._linux_get_autostart()

    def set_autostart(self, enabled: bool):
        """Enable or disable autostart with the OS."""
        if sys.platform == "win32":
            self._win_set_autostart(enabled)
        else:
            self._linux_set_autostart(enabled)

    def _win_get_autostart(self) -> bool:
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_READ,
            )
            try:
                winreg.QueryValueEx(key, "PyDM")
                return True
            except FileNotFoundError:
                return False
            finally:
                winreg.CloseKey(key)
        except Exception:
            return False

    def _win_set_autostart(self, enabled: bool):
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_SET_VALUE,
            )
            if enabled:
                python_exe = self.get_python_executable()
                cmd = f'"{python_exe}" -m pydm.main'
                winreg.SetValueEx(key, "PyDM", 0, winreg.REG_SZ, cmd)
                logger.info("Autostart enabled: %s", cmd)
            else:
                try:
                    winreg.DeleteValue(key, "PyDM")
                    logger.info("Autostart disabled")
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
        except Exception as e:
            logger.error("Failed to set autostart: %s", e)

    def _linux_get_autostart(self) -> bool:
        desktop_file = os.path.expanduser("~/.config/autostart/pydm.desktop")
        return os.path.exists(desktop_file)

    def _linux_set_autostart(self, enabled: bool):
        desktop_file = os.path.expanduser("~/.config/autostart/pydm.desktop")
        if enabled:
            os.makedirs(os.path.dirname(desktop_file), exist_ok=True)
            python_exe = self.get_python_executable()
            content = (
                "[Desktop Entry]\n"
                "Name=PyDM\n"
                "Comment=Python Download Manager\n"
                f"Exec={python_exe} -m pydm.main\n"
                "Terminal=false\n"
                "Type=Application\n"
                "X-GNOME-Autostart-enabled=true\n"
            )
            with open(desktop_file, "w") as f:
                f.write(content)
            logger.info("Autostart enabled: %s", desktop_file)
        else:
            if os.path.exists(desktop_file):
                os.remove(desktop_file)
                logger.info("Autostart disabled")

    # ── Python executable helpers ────────────────────────────────────

    def get_python_executable(self) -> str:
        """Get the Python executable path, using pythonw on Windows when console is hidden."""
        if sys.platform == "win32":
            python_dir = os.path.dirname(sys.executable)
            show_console = self.get("show_console", False)
            if show_console:
                exe = os.path.join(python_dir, "python.exe")
            else:
                exe = os.path.join(python_dir, "pythonw.exe")
            if os.path.exists(exe):
                return exe
        return sys.executable


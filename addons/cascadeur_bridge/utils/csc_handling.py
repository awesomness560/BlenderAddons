import subprocess
import platform
import os
import shutil

from . import file_handling
import bpy
from ..addon_info import PACKAGE_NAME


def get_default_csc_exe_path() -> str:
    """
    Returns the default Cascadeur executable path based on the operating system.

    :return str: Default Cascadeur executable path, or an empty string if not found.
    """
    system = platform.system()

    if system == "Linux":
        # Prefer PATH if user installed it via AUR/script/AppImage wrapper.
        which = shutil.which("cascadeur")
        if which and file_handling.file_exists(which) and os.access(which, os.X_OK):
            return which

        # Common locations for extracted archives / manual installs.
        candidates = [
            "/opt/cascadeur/cascadeur",
            "/opt/cascadeur-linux/cascadeur",
            "/opt/cascadeur-linux/Cascadeur",
            "/opt/Cascadeur/cascadeur",
            "/usr/local/bin/cascadeur",
            "/usr/bin/cascadeur",
        ]
        for p in candidates:
            if file_handling.file_exists(p) and os.access(p, os.X_OK):
                return p
        return ""

    csc_path = {
        "Windows": r"C:\Program Files\Cascadeur\cascadeur.exe",
        "Darwin": r"/Applications/Cascadeur.app",
    }
    default = csc_path.get(system, "")
    return default if default and file_handling.file_exists(default) else ""


class CascadeurHandler:
    def _require_valid_cascadeur_path(self) -> str:
        csc_path = self.csc_exe_path_addon_preference
        if not csc_path:
            raise FileNotFoundError(
                "Cascadeur executable path is empty. Set it in Edit → Preferences → Add-ons → Cascadeur Bridge."
            )
        if not file_handling.file_exists(csc_path):
            raise FileNotFoundError(
                f"Cascadeur executable was not found at: {csc_path}. Update the add-on preference to point to the Cascadeur binary."
            )
        # On Linux/macOS we need the executable bit; on Windows `os.X_OK` is less meaningful.
        if platform.system() != "Windows" and not os.access(csc_path, os.X_OK):
            raise PermissionError(
                f"Cascadeur executable is not marked as runnable: {csc_path}. On Linux run: chmod +x '{csc_path}'"
            )
        return csc_path

    @property
    def csc_exe_path_addon_preference(self) -> str:
        """
        Get the set Cascadeur executable path from the addon's preferences.

        :return str: Cascadeur executable path stored in the addon's preferences.
        """
        preferences = bpy.context.preferences
        addon_prefs = preferences.addons[PACKAGE_NAME].preferences
        return addon_prefs.csc_exe_path

    @property
    def csc_dir(self) -> str:
        """
        Get the root directory of Cascadeur installation.

        :return str: Directory path as a string.
        """
        if self.is_csc_exe_path_valid:
            return (
                self.csc_exe_path_addon_preference
                if platform.system() == "Darwin"
                else os.path.dirname(self.csc_exe_path_addon_preference)
            )

    @property
    def is_csc_exe_path_valid(self) -> bool:
        """
        Check if the Cascadeur executable path is valid.

        :return bool: True if file exists, False otherwise.
        """
        csc_path = self.csc_exe_path_addon_preference
        if not csc_path or not file_handling.file_exists(csc_path):
            return False
        if platform.system() != "Windows" and not os.access(csc_path, os.X_OK):
            return False
        return True

    @property
    def commands_path(self) -> str:
        """
        Get the path to the Cascadeur commands directory.

        :return str: Directory path as a string.
        """
        resources_dir = (
            os.path.join(self.csc_dir, "Contents", "MacOS", "resources")
            if platform.system() == "Darwin"
            else os.path.join(self.csc_dir, "resources")
        )
        return os.path.join(resources_dir, "scripts", "python", "commands")

    def start_cascadeur(self) -> None:
        """
        Start Cascadeur using the specified executable path.

        :return: None
        """
        csc_path = self._require_valid_cascadeur_path()
        self._sync_external_commands()
        subprocess.Popen([csc_path], env=self._cascadeur_env())

    def execute_csc_command(self, command: str) -> None:
        """
        Execute a Cascadeur command using the specified executable path.

        :param command str: Cascadeur command to execute.
        :return: None
        """
        csc_path = self._require_valid_cascadeur_path()
        self._sync_external_commands()
        subprocess.Popen([csc_path, "--run-script", command], env=self._cascadeur_env())

    def _cascadeur_env(self) -> dict:
        """
        Build a safer environment for launching Cascadeur from Blender.

        Some setups (notably Wayland sessions) may default to a Qt platform that
        Cascadeur doesn't ship a plugin for, which causes confusing startup errors.
        """
        env = os.environ.copy()

        # If FONTCONFIG_* are explicitly set to empty, fontconfig treats it as "null".
        # Unset them so the system defaults can be used.
        for k in ("FONTCONFIG_FILE", "FONTCONFIG_PATH"):
            if env.get(k, None) == "":
                env.pop(k, None)

        # Match a known-good shell launch on Linux, e.g.:
        #   env QT_QPA_PLATFORM=xcb QT_SCALE_FACTOR=1.80 /opt/cascadeur-linux/cascadeur
        # Scaling often only applies as expected with xcb; only forcing on Wayland was not enough.
        if platform.system() == "Linux":
            env["QT_QPA_PLATFORM"] = "xcb"
            env["QT_SCALE_FACTOR"] = "1.80"

        return env

    def _sync_external_commands(self) -> None:
        """
        During development, keep the Cascadeur-side bridge scripts in sync.

        This copies the add-on's `csc_files/externals/*` into Cascadeur's
        `commands/externals` folder on every launch/run-script call, overwriting
        existing files.
        """
        # Only attempt if Cascadeur path is valid (also ensures csc_dir/commands_path exist).
        if not self.is_csc_exe_path_valid:
            return

        from .. import addon_info

        src_dir = os.path.join(addon_info.ADDON_PATH, "csc_files", "externals")
        dst_dir = os.path.join(self.commands_path, "externals")

        if not os.path.isdir(src_dir):
            return

        # Copy everything from src to dst, overwriting.
        file_list = [f for f in os.listdir(src_dir) if os.path.isfile(os.path.join(src_dir, f))]
        ok = file_handling.copy_files(src_dir, dst_dir, file_list, overwrite=True)
        if ok:
            print(f"[cascadeur_bridge] Synced {len(file_list)} external command files to: {dst_dir}")
        else:
            print(
                "[cascadeur_bridge] Failed to sync external command files. "
                "Check permissions for the Cascadeur scripts folder."
            )

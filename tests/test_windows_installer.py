"""Regression checks for the per-user Windows installer."""

from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INSTALLER_SCRIPT = PROJECT_ROOT / "packaging" / "windows" / "JobCompass.nsi"


class WindowsInstallerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.script = INSTALLER_SCRIPT.read_text(encoding="utf-8")

    def test_installer_uses_current_users_shell_folders(self) -> None:
        self.assertIn("Function .onInit", self.script)
        self.assertIn("SetShellVarContext current", self.script)

    def test_installer_creates_desktop_shortcut(self) -> None:
        self.assertIn(
            'CreateShortcut "$DESKTOP\\${DESKTOP_LINK}" "$INSTDIR\\${APP_EXE}"',
            self.script,
        )

    def test_uninstaller_removes_desktop_shortcut(self) -> None:
        self.assertIn('Delete "$DESKTOP\\${DESKTOP_LINK}"', self.script)


if __name__ == "__main__":
    unittest.main()

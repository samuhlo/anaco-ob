import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "native"))
from installer import default_state, install, uninstall, HOST_NAME, EXTENSION_ID


class FakeRegistry:
    def __init__(self):
        self.values = {}

    def set(self, key, value):
        self.values[key] = value

    def delete(self, key):
        self.values.pop(key, None)


class InstallerTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name) / "home"
        self.home.mkdir()
        self.state = Path(self.temp.name) / "state"

    def tearDown(self):
        self.temp.cleanup()

    def test_state_folder_follows_each_system_and_keeps_the_linux_path(self):
        self.assertEqual(default_state("linux", self.home, {}), self.home / ".local/share/anaco-ob")
        self.assertEqual(default_state("linux", self.home, {"XDG_DATA_HOME": "/datos"}), Path("/datos/anaco-ob"))
        self.assertEqual(default_state("darwin", self.home, {}), self.home / "Library/Application Support/anaco-ob")
        self.assertEqual(default_state("win32", self.home, {"APPDATA": "C:/Users/a/AppData/Roaming"}), Path("C:/Users/a/AppData/Roaming/anaco-ob"))

    def check_manifest(self, path, launcher):
        manifest = json.loads(path.read_text())
        self.assertEqual(manifest["name"], HOST_NAME)
        self.assertEqual(manifest["allowed_extensions"], [EXTENSION_ID])
        # macOS resolves /tmp to /private/tmp: compare resolved paths.
        self.assertEqual(Path(manifest["path"]).resolve(), launcher.resolve())

    def test_linux_registers_firefox_and_zen(self):
        result = install(self.state, platform="linux", home=self.home)
        launcher = self.state / "native-host"
        self.assertIn('exec "', launcher.read_text())
        if os.name != "nt":
            self.assertTrue(launcher.stat().st_mode & 0o100)
        for folder in (".mozilla/native-messaging-hosts", ".config/zen/native-messaging-hosts"):
            self.check_manifest(self.home / folder / f"{HOST_NAME}.json", launcher)
        self.assertEqual(len(result["registered"]), 2)

    def test_macos_registers_mozilla_and_zen_folders(self):
        install(self.state, platform="darwin", home=self.home)
        for folder in ("Library/Application Support/Mozilla/NativeMessagingHosts", "Library/Application Support/zen/NativeMessagingHosts"):
            self.check_manifest(self.home / folder / f"{HOST_NAME}.json", self.state / "native-host")

    def test_windows_uses_a_batch_launcher_and_the_user_registry(self):
        registry = FakeRegistry()
        result = install(self.state, platform="win32", home=self.home, registry=registry)
        launcher = self.state / "native-host.bat"
        self.assertIn("ANACO_OB_STATE", launcher.read_text())
        manifest = self.state / f"{HOST_NAME}.json"
        self.check_manifest(manifest, launcher)
        self.assertEqual(registry.values[rf"Software\Mozilla\NativeMessagingHosts\{HOST_NAME}"], str(manifest))
        self.assertIn(rf"HKCU\Software\Mozilla\NativeMessagingHosts\{HOST_NAME}", result["registered"])

    def test_uninstall_removes_registrations_and_keeps_data_unless_purged(self):
        registry = FakeRegistry()
        for platform in ("linux", "darwin", "win32"):
            install(self.state, platform=platform, home=self.home, registry=registry)
            (self.state / "config.json").write_text("{}")
            removed = uninstall(self.state, platform=platform, home=self.home, registry=registry)
            self.assertTrue(removed["removed"], platform)
            self.assertFalse(list(self.home.rglob(f"{HOST_NAME}.json")), platform)
            self.assertFalse(registry.values, platform)
            self.assertTrue((self.state / "config.json").exists(), platform)
        uninstall(self.state, platform="linux", home=self.home, purge=True)
        self.assertFalse(self.state.exists())


if __name__ == "__main__":
    unittest.main()

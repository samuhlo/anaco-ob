import json
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "native"))


class ReleaseTest(unittest.TestCase):
    def test_every_part_carries_the_same_version(self):
        # The panel warns when the extension and the service differ, so a release must bump them together.
        from core import VERSION
        manifest = json.loads((ROOT / "extension/manifest.json").read_text())["version"]
        package = json.loads((ROOT / "package.json").read_text())["version"]
        project = re.search(r'^version = "([^"]+)"', (ROOT / "pyproject.toml").read_text(), re.M)[1]
        self.assertEqual({manifest, package, project, VERSION}, {VERSION})


if __name__ == "__main__":
    unittest.main()

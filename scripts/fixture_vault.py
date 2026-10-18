"""Shared setup for smoke scripts: temporary vaults use the classic profile."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLASSIC = ROOT / "tests/fixtures/profile-classic.json"


def classic_profile(app):
    from vault_profile import install
    return install(app, json.loads(CLASSIC.read_text()), "99_Recursos/anaco/perfil.json")

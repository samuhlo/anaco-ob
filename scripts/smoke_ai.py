#!/usr/bin/env python3
"""Real subscribed Codex inference with synthetic notes only; leaves reproducible evidence."""
import argparse
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "native"))
from core import App
from fixture_vault import classic_profile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / ".test-artifacts/ai")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    vault = args.output.resolve() / "Vault"
    folder = vault / "02_Cerebro/Modelos_Mentales"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "recuperacion_activa.md").write_text("# Recuperación activa\n\nIntentar recordar sin mirar fortalece la memoria. Las pruebas sin apuntes ayudan a detectar lagunas y corregir errores.\n")
    (folder / "redes_de_ordenadores.md").write_text("# Redes de ordenadores\n\nLa recuperación de paquetes perdidos utiliza retransmisión. Un router conecta redes y transmite datos entre equipos.\n")
    app = App(args.output / "state")
    app.set_config({"vault":str(vault), "provider":"codex"});classic_profile(app)
    capture = app.stage({"kind":"article", "url":"https://example.org/aprender", "title":"Aprender recordando", "text":"La recuperación activa mejora el aprendizaje. Intentar recordar una explicación sin mirar permite comprobar qué sabemos. Después de estudiar, cierra los apuntes y explica el concepto con tus propias palabras. Revisa los errores y repite la prueba otro día. Combinar recuperación activa y repetición espaciada ayuda a conservar conceptos a largo plazo."})
    result = app.draft(capture["id"],"Quiero estudiar mejor y entender cómo repasar.",provider="codex")
    paths = [r["path"] for r in result["draft"]["relations"]]
    assert any(p.endswith("recuperacion_activa.md") for p in paths), "No encontró la relación positiva"
    assert not any(p.endswith("redes_de_ordenadores.md") for p in paths), "Propuso una coincidencia léxica incorrecta"
    saved = app.save(capture["id"], {"relations":paths})
    report = {"model":result["draft"]["model"],"relations":result["draft"]["relations"],"note":saved["path"],"passed":True}
    (args.output / "result.json").write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__ == "__main__":
    main()

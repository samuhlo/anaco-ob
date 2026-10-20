#!/usr/bin/env python3
"""Compose the addons.mozilla.org screenshots (1280×800) from the README captures.

  .venv/bin/python scripts/amo_shots.py   # writes docs/amo/*.png with headless Zen
"""
from pathlib import Path
import tempfile

from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "docs/assets"
OUT = ROOT / "docs/amo"
SHOTS = {
    "1-resaltado": ["recursos.png", "resaltado.png"],
    "2-revision": ["revision.png"],
    "3-panel-perfil": ["panel.png", "perfil.png"],
    # The welcome screenshots have empty space below: show only their top part.
    "4-bienvenida": ["bienvenida-por-que.png:560", "bienvenida.png:560"],
}
PAGE = """<!doctype html><meta charset="utf-8"><style>
html,body{{margin:0;width:1280px;height:800px;overflow:hidden}}
body{{display:flex;gap:32px;align-items:center;justify-content:center;background:radial-gradient(circle at 15% 10%,#ffe8a8,#fff8e6 45%,#f4f1ea)}}
img{{max-height:740px;max-width:{width}px;border-radius:14px;box-shadow:0 18px 50px rgba(12,0,17,.18)}}
.crop{{overflow:hidden;border-radius:14px;box-shadow:0 18px 50px rgba(12,0,17,.18)}}.crop img{{display:block;max-height:none;border-radius:0;box-shadow:none}}
</style>{images}"""


def image(spec, width):
    """An <img>, or a <div> showing only its top «height» pixels for «file:height»."""
    name, _, height = spec.partition(":")
    tag = f'<img src="{(ASSETS / name).as_uri()}">'
    return f'<div class="crop" style="height:{height}px;width:{width}px">{tag}</div>' if height else tag


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    options = Options()
    options.binary_location = "/opt/zen-browser-bin/zen"
    options.add_argument("-headless")
    driver = webdriver.Firefox(options=options, service=Service(executable_path=str(ROOT / ".test-artifacts/bin/geckodriver")))
    # Larger than the page, so the body keeps its exact 1280×800.
    driver.set_window_size(1500, 1100)
    try:
        with tempfile.TemporaryDirectory() as temp:
            for name, files in SHOTS.items():
                images = "".join(image(f, 1180 // len(files)) for f in files)
                page = Path(temp) / f"{name}.html"
                page.write_text(PAGE.format(width=1180 // len(files), images=images), encoding="utf-8")
                driver.get(page.as_uri())
                driver.find_element("tag name", "body").screenshot(str(OUT / f"{name}.png"))
                print(OUT / f"{name}.png")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()

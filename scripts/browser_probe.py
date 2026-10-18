#!/usr/bin/env python3
"""Launch a separate headless Zen for development tests. Does not use personal profiles."""
from pathlib import Path
import json
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service

options = Options()
options.binary_location = "/opt/zen-browser-bin/zen"
options.add_argument("-headless")
options.set_preference("zen.welcome-screen.seen", True)
options.set_preference("browser.shell.checkDefaultBrowser", False)
driver = webdriver.Firefox(options=options, service=Service(executable_path=str(Path(__file__).resolve().parent.parent / ".test-artifacts/bin/geckodriver"), service_args=["--allow-system-access"]))
try:
    driver.get("data:text/html,<title>Zen test</title><h1>Browser ready</h1>")
    print(json.dumps({"title":driver.title,"browser":driver.capabilities.get("browserVersion"),"driver":driver.capabilities.get("moz:geckodriverVersion")}))
finally:
    driver.quit()

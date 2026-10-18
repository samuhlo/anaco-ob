#!/usr/bin/env python3
"""Cache the public regression article in an isolated Zen profile for code QA."""
import json
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support.ui import WebDriverWait

ROOT=Path(__file__).resolve().parents[1]
URL='https://tympanus.net/codrops/2026/10/13/scroll-driven-ghost-trails/'


def main():
    out=ROOT/'.test-artifacts/codrops-code';out.mkdir(parents=True,exist_ok=True)
    options=Options();options.binary_location='/opt/zen-browser-bin/zen';options.add_argument('-headless')
    options.set_preference('zen.welcome-screen.seen',True)
    driver=webdriver.Firefox(options=options,service=Service(executable_path=str(ROOT/'.test-artifacts/bin/geckodriver'),log_output=str(out/'fetch.log')))
    try:
        driver.set_page_load_timeout(40);driver.get(URL)
        WebDriverWait(driver,20).until(lambda d:d.execute_script('return document.querySelectorAll("article pre").length>0'))
        source=driver.execute_script('return {url:location.href,title:document.title,html:document.querySelector("article").outerHTML,code:[...document.querySelectorAll("article pre")].map(n=>n.textContent)}')
        (out/'source.json').write_text(json.dumps(source,ensure_ascii=False,indent=2))
        print(json.dumps({'source':URL,'code_blocks':len(source['code']),'cached':str(out/'source.json')}))
    finally:driver.quit()


if __name__=='__main__':main()

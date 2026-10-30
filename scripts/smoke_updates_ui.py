#!/usr/bin/env python3
"""Exercise update controls in an isolated headless Zen profile (Linux)."""
import json
import os
from pathlib import Path
import sys
import tempfile

from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support.ui import WebDriverWait

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'native'))
from core import App
import installer


def main():
    out = ROOT / '.test-artifacts' / 'updates'
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='anaco-update-ui-') as temp:
        home = Path(temp)
        state, vault = home / 'state', home / 'vault'
        vault.mkdir()
        app = App(state)
        app.set_config({'vault': str(vault), 'vault_mode': 'manual', 'provider': 'manual'})
        app.db.close()
        installer.install(state, home=home)
        options = Options()
        options.binary_location = '/opt/zen-browser-bin/zen'
        options.add_argument('-headless')
        options.set_preference('zen.welcome-screen.seen', True)
        options.set_preference('browser.shell.checkDefaultBrowser', False)
        driver = webdriver.Firefox(options=options, service=Service(
            executable_path=str(ROOT / '.test-artifacts/bin/geckodriver'),
            service_args=['--allow-system-access'], env={**os.environ, 'HOME': str(home)},
            log_output=str(out / 'geckodriver.log')))
        wait = WebDriverWait(driver, 40)
        try:
            driver.set_window_size(1100, 1100)
            addon = driver.install_addon(str(ROOT / 'dist/anaco-ob-1.3.2.zip'), temporary=True)
            driver.set_context('chrome')
            uuid = json.loads(driver.execute_script('return Services.prefs.getStringPref("extensions.webextensions.uuids")'))[addon]
            driver.set_context('content')
            base = f'moz-extension://{uuid}/'
            driver.get(base + 'options.html')
            driver.execute_script('localStorage.setItem("anaco-ob:lang","es")')
            driver.refresh()
            # Let the real startup check finish, then use deterministic release metadata.
            driver.execute_async_script('const done=arguments[0];browser.runtime.sendMessage({type:"checkUpdates",force:true}).then(done,e=>done({error:e.message}));')
            driver.execute_script('''browser.runtime.getBackgroundPage().then(bg=>{bg.fetch=async()=>({ok:true,json:async()=>({guid:'anaco-ob@samuhlo',current_version:{version:'1.4.0',file:{status:'public'}},tag_name:'v1.4.0'})});});''')
            driver.find_element('id', 'checkUpdates').click()
            wait.until(lambda d: d.find_element('id', 'updateService').is_displayed())
            assert driver.find_element('id', 'updateExtension').is_displayed()
            assert '1.3.2' in driver.find_element('id', 'serviceVersion').text
            assert '1.4.0' in driver.find_element('id', 'serviceVersion').text
            driver.find_element('id', 'updatesCard').screenshot(str(out / 'options-updates.png'))
            driver.find_element('id', 'autoUpdateCheck').click()
            assert driver.execute_async_script('const done=arguments[0];browser.storage.local.get("autoUpdateCheck").then(v=>done(v.autoUpdateCheck));') is False
            driver.refresh()
            assert not driver.find_element('id', 'autoUpdateCheck').is_selected()
            driver.get(base + 'panel.html')
            wait.until(lambda d: d.find_element('id', 'updateNotice').is_displayed())
            driver.set_window_size(420, 950)
            assert driver.execute_script('return document.documentElement.scrollWidth <= innerWidth')
            driver.find_element('id', 'updateNotice').screenshot(str(out / 'panel-update.png'))
            driver.get(base + 'options.html')
            driver.execute_script('browser.runtime.getBackgroundPage().then(bg=>{bg.fetch=async()=>{throw Error("offline fixture")}})')
            driver.find_element('id', 'checkUpdates').click()
            wait.until(lambda d: 'No se pudo comprobar' in d.find_element('id', 'extensionVersion').text)
            print(json.dumps({'passed': True, 'real_native_connection': True, 'manual_check': True, 'opt_out_persisted': True, 'sidebar_notice': True, 'offline_error': True, 'narrow_layout': True}))
        finally:
            driver.quit()


if __name__ == '__main__':
    main()

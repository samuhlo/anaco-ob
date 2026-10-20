const $ = id => document.getElementById(id);
const call = message => browser.runtime.sendMessage({type: "native", message});
const configKeys = ["vault", "vault_mode", "note_structure", "note_language", "provider", "api_base", "api_model", "api_vision_model", "model", "vision_model", "vision_policy", "reader_batch_pages", "pdf_page_limit", "pdf_visual_pages", "video_minutes", "video_frames", "asr_model"];
let manualPath = "", savedPath = "", savedAvailable = false, detecting = false;
const draftKey = 'optionsDraft';
let loaded = false, dirty = false;

function rememberDraft() {
  if (!loaded) return;
  dirty = true;
  localStorage.setItem(draftKey, JSON.stringify({
    values: Object.fromEntries(configKeys.map(k => [k, $(k).value])), manualPath
  }));
  $('options-draft-status').textContent = tx('options_cambios_sin_guardar_se_conservan_al_volv');
}

async function returnToCapture(event) {
  event.preventDefault();
  if (dirty) rememberDraft();
  try {
    if (await browser.runtime.sendMessage({type: 'returnFromOptions'})) return;
  } catch { /* The source tab may have been closed. Keep a usable capture page. */ }
  location.href = browser.runtime.getURL('panel.html');
}

function notice(text, error = false) {
  $("message").textContent = text;
  $("message").hidden = false;
  $("message").className = "notice " + (error ? "error" : "success");
}

function applyMode() {
  const automatic = $("vault_mode").value === "auto";
  $("vault-discovery").hidden = !automatic;
  $("vault").readOnly = automatic;
  $("vault").value = automatic ? $("detected-vault").value : manualPath;
  $("settings").querySelector('[type="submit"]').disabled = automatic && detecting;
  $('save-and-back').disabled = automatic && detecting;
  if ($('vault').value && $('vault').value !== savedPath) {
    notice(tx('options_vault_seleccionado_1_aun_no_esta_en_uso_',[$('vault').value]));
  }
}

async function detectVaults(preferred = $("detected-vault").value || savedPath) {
  if (detecting) return;
  detecting = true;
  $("detect-vaults").disabled = true;
  $("vault-help").textContent = tx('options_buscando_en_el_registro_de_obsidian_y_ca');
  applyMode();
  try {
    const {vaults} = await call({action: "discover_vaults"});
    const select = $("detected-vault");
    select.replaceChildren(new Option(tx('options_selecciona_un_vault'), ""));
    for (const vault of vaults) {
      select.add(new Option(`${vault.name} · ${vault.path} · ${vault.source}`, vault.path));
    }
    // Keep an already saved, available vault even outside the search locations.
    if (savedAvailable && !vaults.some(v => v.path === savedPath)) {
      select.add(new Option(`${savedPath} · ${tx('options_ruta_guardada')}`, savedPath));
    }
    const paths = [...select.options].map(o => o.value).filter(Boolean);
    select.value = paths.includes(preferred) ? preferred : paths.length === 1 ? paths[0] : "";
    $("vault-help").textContent = paths.length === 0
      ? tx('options_no_se_han_encontrado_vaults_puedes_intro')
      : paths.length === 1
        ? tx('options_vault_localizado_revisa_la_ruta_y_pulsa_')
        : tx('options_hay_varios_vaults_elige_el_que_quieres_u');
  } catch (error) {
    $("vault-help").textContent = tx('options_no_se_pudo_completar_la_busqueda_1', [error.message]);
  } finally {
    detecting = false;
    $("detect-vaults").disabled = false;
    applyMode();
    if (dirty) rememberDraft();
  }
}

async function load() {
  loaded = false;
  try {
    // Settings remain accessible when a vault was moved.
    const s = await call({action: "settings"});
    for (const k of configKeys) $(k).value = s.config[k];
    savedPath = manualPath = s.config.vault;
    savedAvailable = s.vault_available;
    if (!s.config.describe_images) $("vision_policy").value = "metadata";
    // The key never comes back from the service: only whether one is stored.
    $("api_key").value = "";
    $("api_key").placeholder = s.config.api_key_set ? tx('options_clave_guardada_escribe_otra_para_cambiar') : tx('options_vacia_para_modelos_locales');
    applyProvider();
    let draft;
    try { draft = JSON.parse(localStorage.getItem(draftKey)); } catch { localStorage.removeItem(draftKey); }
    if (draft?.values) {
      for (const k of configKeys) if (typeof draft.values[k] === 'string') $(k).value = draft.values[k];
      manualPath = draft.manualPath ?? draft.values.vault;
      dirty = true;
      $('options-draft-status').textContent = tx('options_cambios_sin_guardar_se_conservan_al_volv');
    }
    notice(savedAvailable ? tx('options_servicio_conectado_vault_configurado_dis') : tx('options_servicio_conectado_localiza_tu_vault_par'));
    applyMode();
    applyProvider();
    if ($("vault_mode").value === "auto") await detectVaults(draft?.values?.vault || savedPath);
    loaded = true;
  } catch (e) { notice(e.message, true); }
}

$("vault_mode").onchange = () => {
  if ($("vault_mode").value === "auto") {
    manualPath = $("vault").value;
    applyMode();
    detectVaults();
  } else applyMode();
};
// [UI] Choosing a service by name fills its address and a suggested model.
function serviceHint() {
  const service = AnacoObProviders.find($("api_service").value);
  $("api_key_link").hidden = !service?.keys;
  $("api_local_note").hidden = !service?.local;
  if (service?.keys) { $("api_key_link").href = service.keys; $("api_key_link").textContent = tx('options_consigue_tu_clave_de_1', [service.name]); }
}
$("api_service").addEventListener("change", () => {
  const service = AnacoObProviders.find($("api_service").value);
  if (service) {
    $("api_base").value = service.base;
    $("api_model").value = service.model;
    $("api_vision_model").value = "";
    // Programmatic values fire no events: let the draft see them.
    $("api_base").dispatchEvent(new Event("input", {bubbles: true}));
  }
  serviceHint();
});
$("api_base").addEventListener("input", event => { if (event.isTrusted) { $("api_service").value = AnacoObProviders.match($("api_base").value); serviceHint(); } });
function applyProvider() {
  $("api_service").value = AnacoObProviders.match($("api_base").value);
  serviceHint();
  $("openai-settings").hidden = $("provider").value !== "openai";
  // Codex models only matter with Codex; the other provider has its own fields.
  for (const block of document.querySelectorAll(".codex-only")) block.hidden = $("provider").value !== "codex";
}
$("provider").addEventListener("change", applyProvider);
$("vault").oninput = () => { if ($("vault_mode").value === "manual") manualPath = $("vault").value; };
$("detected-vault").onchange = applyMode;
$("detect-vaults").onclick = () => detectVaults();
$("settings").onsubmit = async event => {
  event.preventDefault();
  if (!$("vault").value.trim()) {
    notice(tx('options_selecciona_un_vault_detectado_o_introduc'), true);
    return;
  }
  const submit = $("settings").querySelector('[type="submit"]');
  submit.disabled = $('save-and-back').disabled = true;
  try {
    const values = Object.fromEntries(configKeys.map(k => [k, $(k).value]));
    for (const k of ["reader_batch_pages", "pdf_page_limit", "pdf_visual_pages", "video_minutes", "video_frames"]) values[k] = Number(values[k]);
    values.describe_images = values.vision_policy !== "metadata";
    if ($("api_key").value.trim()) values.api_key = $("api_key").value.trim();
    else if ($("api_key_clear").checked) values.api_key = null;
    const config = await call({action: "configure", values});
    savedPath = config.vault;
    $("api_key").value = "";$("api_key_clear").checked = false;
    $("api_key").placeholder = config.api_key_set ? tx('options_clave_guardada_escribe_otra_para_cambiar') : tx('options_vacia_para_modelos_locales');
    savedAvailable = true;
    $("vault").value = savedPath;
    if (config.vault_mode === "manual") manualPath = savedPath;
    localStorage.removeItem(draftKey);
    dirty = false;
    $('options-draft-status').textContent = tx('options_opciones_guardadas');
    await browser.storage.local.set({currentCapture: null, draftResult: null, editorFields: null, operationError: "", settingsRevision: crypto.randomUUID()});
    notice(tx('options_opciones_guardadas_las_capturas_pendient'));
    globalThis.AnacoObProfileCard?.refresh();
    if (event.submitter?.id === 'save-and-back') await returnToCapture(event);
  } catch (e) { notice(e.message, true); }
  finally { submit.disabled = $('save-and-back').disabled = false; }
};
$("check").onclick = load;
$('back-to-capture').onclick = returnToCapture;
$('settings').addEventListener('input', rememberDraft);
$('settings').addEventListener('change', rememberDraft);
load();

// The interface language lives in this browser, not in the local service.
const uiLanguage=document.getElementById('ui_language');
uiLanguage.value=AnacoObI18n.chosen();
uiLanguage.addEventListener('change',()=>{AnacoObI18n.set(uiLanguage.value);location.reload();});

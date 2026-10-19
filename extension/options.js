const $ = id => document.getElementById(id);
const call = message => browser.runtime.sendMessage({type: "native", message});
const configKeys = ["vault", "vault_mode", "note_structure", "provider", "api_base", "api_model", "api_vision_model", "model", "vision_model", "vision_policy", "reader_batch_pages", "pdf_page_limit", "pdf_visual_pages", "video_minutes", "video_frames", "asr_model"];
let manualPath = "", savedPath = "", savedAvailable = false, detecting = false;
const draftKey = 'optionsDraft';
let loaded = false, dirty = false;

function rememberDraft() {
  if (!loaded) return;
  dirty = true;
  localStorage.setItem(draftKey, JSON.stringify({
    values: Object.fromEntries(configKeys.map(k => [k, $(k).value])), manualPath
  }));
  $('options-draft-status').textContent = 'Cambios sin guardar · se conservan al volver';
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
    notice(`Vault seleccionado: ${$('vault').value}\nAún no está en uso. Pulsa Guardar y volver para aplicarlo.`);
  }
}

async function detectVaults(preferred = $("detected-vault").value || savedPath) {
  if (detecting) return;
  detecting = true;
  $("detect-vaults").disabled = true;
  $("vault-help").textContent = "Buscando en el registro de Obsidian y carpetas habituales…";
  applyMode();
  try {
    const {vaults} = await call({action: "discover_vaults"});
    const select = $("detected-vault");
    select.replaceChildren(new Option("Selecciona un vault", ""));
    for (const vault of vaults) {
      select.add(new Option(`${vault.name} · ${vault.path} · ${vault.source}`, vault.path));
    }
    // Keep an already saved, available vault even outside the search locations.
    if (savedAvailable && !vaults.some(v => v.path === savedPath)) {
      select.add(new Option(`${savedPath} · Ruta guardada`, savedPath));
    }
    const paths = [...select.options].map(o => o.value).filter(Boolean);
    select.value = paths.includes(preferred) ? preferred : paths.length === 1 ? paths[0] : "";
    $("vault-help").textContent = paths.length === 0
      ? "No se han encontrado vaults. Puedes introducir la ruta manualmente arriba."
      : paths.length === 1
        ? "Vault localizado. Revisa la ruta y pulsa Guardar opciones para usarlo."
        : "Hay varios vaults. Elige el que quieres usar y pulsa Guardar opciones.";
  } catch (error) {
    $("vault-help").textContent = "No se pudo completar la búsqueda: " + error.message + ". Puedes introducir la ruta manualmente.";
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
    $("api_key").placeholder = s.config.api_key_set ? "Clave guardada · escribe otra para cambiarla" : "Vacía para modelos locales";
    applyProvider();
    let draft;
    try { draft = JSON.parse(localStorage.getItem(draftKey)); } catch { localStorage.removeItem(draftKey); }
    if (draft?.values) {
      for (const k of configKeys) if (typeof draft.values[k] === 'string') $(k).value = draft.values[k];
      manualPath = draft.manualPath ?? draft.values.vault;
      dirty = true;
      $('options-draft-status').textContent = 'Cambios sin guardar · se conservan al volver';
    }
    notice(savedAvailable ? "Servicio conectado · vault configurado disponible." : "Servicio conectado. Localiza tu vault para empezar.");
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
function applyProvider() {
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
    notice("Selecciona un vault detectado o introduce su ruta manualmente.", true);
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
    $("api_key").placeholder = config.api_key_set ? "Clave guardada · escribe otra para cambiarla" : "Vacía para modelos locales";
    savedAvailable = true;
    $("vault").value = savedPath;
    if (config.vault_mode === "manual") manualPath = savedPath;
    localStorage.removeItem(draftKey);
    dirty = false;
    $('options-draft-status').textContent = 'Opciones guardadas';
    await browser.storage.local.set({currentCapture: null, draftResult: null, editorFields: null, operationError: "", settingsRevision: crypto.randomUUID()});
    notice("Opciones guardadas. Las capturas pendientes siguen disponibles desde su vault de origen.");
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

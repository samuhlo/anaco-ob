/* Vault profile card in Options: scan, choose what the model may read, review
   each rule next to its evidence and confirm. The form edits one draft object. */
globalThis.AnacoObProfileCard = (() => {
  const $ = id => document.getElementById(id);
  const call = message => browser.runtime.sendMessage({type: "native", message});
  const ORIGINS = {type: "Tipo de nota", constant: "Valor fijo", folder_map: "Según la carpeta", path_segment: "Nombre de una carpeta de la ruta",
    tags: "Etiquetas propuestas", context: "Contexto", title: "Título", created: "Fecha de creación", today: "Fecha de guardado",
    url: "URL de la fuente", author: "Autor de la fuente", source_format: "Formato de la fuente", assisted: "Asistido por IA",
    model: "Modelo de IA", relations: "Relaciones aceptadas"};
  const SECTIONS = {summary: "Resumen", intent: "Intención personal", quote: "Cita", quote_context: "Contexto de la cita",
    relations: "Notas relacionadas", resources: "Recursos de la fuente", source: "Fuente", warning: "Alcance de la captura"};
  let scanned = null, draft = null, evidence = {}, provider = "manual";

  const el = (tag, props = {}, ...children) => {
    const node = document.createElement(tag);
    for (const [key, value] of Object.entries(props)) key.includes("-") ? node.setAttribute(key, value) : node[key] = value;
    node.append(...children.filter(c => c !== null && c !== undefined && c !== ""));
    return node;
  };
  const hint = text => text ? el("small", {className: "profile-evidence", textContent: text}) : null;
  const message = (text, error = false) => { const box = $("message"); box.textContent = text; box.hidden = false; box.className = "notice " + (error ? "error" : "success"); box.scrollIntoView({block: "nearest"}); };
  const busy = (button, label) => { const previous = button.textContent; button.disabled = true; button.textContent = label; return () => { button.disabled = false; button.textContent = previous; }; };

  async function refresh() {
    try {
      const [current, settings] = await Promise.all([call({action: "profile_get"}), call({action: "settings"})]);
      provider = settings.config.provider;
      $("profileInterpret").hidden = provider !== "codex";
      if (current.missing) {
        $("profileStatus").textContent = "Este vault aún no tiene perfil. Escanéalo para que Anaco sepa dónde y cómo guardar.";
        $("profileProblems").hidden = true;
        return;
      }
      $("profileStatus").textContent = `Perfil confirmado en ${current.path} · ${current.folders.length} carpetas de destino.`;
      $("profilePath").value = current.path;
      $("profileProblems").hidden = !current.problems.length;
      $("profileProblems").textContent = current.problems.length ? "Revisa el perfil:\n" + current.problems.join("\n") : "";
      $("profileScan").textContent = "Volver a escanear";
    } catch (error) { $("profileStatus").textContent = error.message; }
  }

  async function scan() {
    const done = busy($("profileScan"), "Escaneando…");
    try {
      scanned = await call({action: "profile_scan"});
      $("profileDocList").replaceChildren();
      const labels = {instructions: "Instrucciones", skill: "Skill", guide: "Guía", template: "Plantilla"};
      for (const doc of scanned.documents) {
        const box = el("input", {type: "checkbox", value: doc.path, checked: doc.suggested});
        $("profileDocList").append(el("label", {className: "profile-option"}, box, " ", el("span", {textContent: doc.path}), el("small", {textContent: ` · ${labels[doc.kind] || doc.kind}`})));
      }
      if (!scanned.documents.length) $("profileDocList").append(el("p", {className: "muted", textContent: "No se han encontrado instrucciones ni plantillas en el vault."}));
      $("profileDocs").hidden = false;
      $("profilePath").value = $("profilePath").value || scanned.suggested_path;
      $("profileDocs").scrollIntoView({block: "nearest"});
    } catch (error) { message(error.message, true); }
    finally { done(); }
  }

  async function interpret(useModel) {
    const button = useModel ? $("profileInterpret") : $("profileAutomatic");
    const done = busy(button, useModel ? "La IA está leyendo tus instrucciones…" : "Preparando…");
    try {
      const documents = [...$("profileDocList").querySelectorAll("input:checked")].map(i => i.value);
      const result = useModel ? await call({action: "profile_interpret", documents}) : {...scanned.proposal, assisted: false, warnings: []};
      draft = structuredClone(result.profile);
      evidence = result.evidence || {};
      $("profileWarnings").hidden = !result.warnings?.length;
      $("profileWarnings").textContent = (result.warnings || []).join("\n");
      render();
      $("profileReview").hidden = false;
      $("profileReview").scrollIntoView({block: "start"});
    } catch (error) { message(error.message, true); }
    finally { done(); }
  }

  // ===========================================================================
  // [UI] REVIEW FORM
  // ===========================================================================
  function section(title, intro, ...rows) {
    return el("fieldset", {className: "profile-section"}, el("legend", {textContent: title}), intro ? el("p", {className: "muted"}, el("small", {textContent: intro})) : null, ...rows);
  }

  function render() {
    const form = $("profileForm");
    form.replaceChildren();
    const typeKeys = Object.keys(draft.types);
    const destinations = draft.destinations.map((rule, index) => {
      const include = el("input", {type: "checkbox", checked: !rule.disabled, title: "Usar este destino"});
      include.onchange = () => { rule.disabled = !include.checked; sync(); };
      const types = el("input", {value: rule.types.join(", "), "aria-label": "Tipos en " + rule.pattern});
      types.onchange = () => { rule.types = types.value.split(",").map(t => t.trim()).filter(Boolean); render(); };
      const select = el("select", {"aria-label": "Tipo predeterminado en " + rule.pattern});
      for (const type of rule.types) select.add(new Option(type, type, false, type === rule.default));
      select.onchange = () => { rule.default = select.value; sync(); };
      return el("div", {className: "profile-row"}, el("label", {className: "profile-head"}, include, " ", el("strong", {textContent: rule.pattern})),
        el("div", {className: "profile-fields"}, el("span", {textContent: "Tipos"}), types, el("span", {textContent: "Por defecto"}), select), hint(evidence["destination:" + rule.pattern]));
    });
    const types = typeKeys.map(key => {
      const label = el("input", {value: draft.types[key].label, "aria-label": "Nombre visible de " + key});
      label.onchange = () => { draft.types[key].label = label.value; sync(); };
      const pattern = el("input", {value: draft.types[key].filename, "aria-label": "Nombre de archivo de " + key});
      pattern.onchange = () => { draft.types[key].filename = pattern.value; sync(); };
      return el("div", {className: "profile-row"}, el("strong", {textContent: key}),
        el("div", {className: "profile-fields"}, el("span", {textContent: "Nombre"}), label, el("span", {textContent: "Archivo"}), pattern), hint(evidence["filename:" + key]));
    });
    const fields = draft.frontmatter.map((spec, index) => {
      const include = el("input", {type: "checkbox", checked: !spec.disabled, title: "Incluir este campo"});
      include.onchange = () => { spec.disabled = !include.checked; sync(); };
      const origin = el("select", {"aria-label": "Origen de " + spec.key});
      for (const [value, label] of Object.entries(ORIGINS)) origin.add(new Option(label, value, false, value === spec.from));
      origin.onchange = () => { spec.from = origin.value; render(); };
      let detail = null;
      if (spec.from === "constant") { detail = el("input", {value: spec.value ?? "", "aria-label": "Valor de " + spec.key}); detail.onchange = () => { spec.value = detail.value; sync(); }; }
      if (spec.from === "folder_map") detail = el("small", {textContent: Object.entries(spec.values || {}).map(([folder, value]) => `${folder} → ${value}`).join(" · ") || "Sin valores: edítalos en el JSON."});
      if (spec.from === "path_segment") detail = el("small", {textContent: `Carpeta n.º ${spec.index + 1} de la ruta, sin el prefijo numérico.`});
      const when = spec.when ? [spec.when.types && "solo tipos " + spec.when.types.join(", "), spec.when.folders && "solo en " + spec.when.folders.join(", "), spec.when.assisted !== undefined && (spec.when.assisted ? "solo con IA" : "solo sin IA")].filter(Boolean).join(" · ") : "";
      return el("div", {className: "profile-row"}, el("label", {className: "profile-head"}, include, " ", el("strong", {textContent: spec.key})),
        el("div", {className: "profile-fields"}, el("span", {textContent: "Origen"}), origin, detail ? el("span", {textContent: "Detalle"}) : null, detail), hint([when, evidence["field:" + spec.key] || evidence["frontmatter:" + spec.key]].filter(Boolean).join(" · ")));
    });
    const attachments = el("input", {value: draft.attachments, "aria-label": "Carpeta de adjuntos"});
    attachments.onchange = () => { draft.attachments = attachments.value.trim(); sync(); };
    const tops = [...new Set((scanned?.folders || []).map(f => f.split("/")[0]))];
    const roots = tops.map(top => {
      const box = el("input", {type: "checkbox", checked: draft.relation_roots.includes(top)});
      box.onchange = () => { draft.relation_roots = box.checked ? [...draft.relation_roots, top] : draft.relation_roots.filter(r => r !== top); sync(); };
      return el("label", {className: "profile-option"}, box, " " + top);
    });
    const documents = (scanned?.documents || []).map(doc => {
      const box = el("input", {type: "checkbox", checked: draft.instructions.includes(doc.path)});
      box.onchange = () => { draft.instructions = box.checked ? [...draft.instructions, doc.path] : draft.instructions.filter(p => p !== doc.path); sync(); };
      return el("label", {className: "profile-option"}, box, " " + doc.path);
    });
    const headings = Object.entries(SECTIONS).map(([key, fallback]) => {
      const input = el("input", {value: draft.sections?.[key] || "", placeholder: fallback, "aria-label": "Encabezado: " + fallback});
      input.onchange = () => { draft.sections = {...draft.sections, [key]: input.value.trim()}; if (!input.value.trim()) delete draft.sections[key]; sync(); };
      return el("div", {className: "profile-fields"}, el("span", {textContent: fallback}), input);
    });
    const notes = Object.entries(evidence).filter(([key]) => !/^(destination|filename|field|frontmatter):/.test(key)).map(([key, text]) => el("li", {}, el("strong", {textContent: key + ": "}), text));
    form.append(
      notes.length ? section("Por qué se propone así", "", el("ul", {className: "profile-notes"}, ...notes)) : "",
      section("Destinos", "Carpetas donde Anaco puede guardar notas y los tipos que admite cada una.", ...destinations),
      section("Tipos y nombres de archivo", "Admite {date}, {slug_}, {slug-}, {title}, {type} y {variant}.", ...types),
      section("Frontmatter", "Cada campo dice de dónde sale su valor. Las relaciones solo incluyen las que aceptes al revisar.", ...fields),
      section("Adjuntos y relaciones", "", el("label", {textContent: "Carpeta de adjuntos"}), attachments, el("p", {className: "muted"}, el("small", {textContent: "Carpetas donde buscar notas relacionadas:"})), ...roots),
      section("Documentos para la IA al redactar", "Las instrucciones del vault mandan sobre el estilo y la estructura de las notas.", ...documents),
      section("Encabezados que añade Anaco", "Vacío: se usa el encabezado por defecto.", ...headings));
    sync();
  }

  // The JSON mirrors the form; disabled rows are left out of the saved profile.
  function finalProfile() {
    const profile = structuredClone(draft);
    profile.destinations = profile.destinations.filter(r => !r.disabled).map(({disabled, ...rule}) => rule);
    profile.frontmatter = profile.frontmatter.filter(f => !f.disabled).map(({disabled, ...field}) => field);
    return profile;
  }
  function sync() { $("profileJson").value = JSON.stringify(finalProfile(), null, 2); }

  function applyJson() {
    try { draft = JSON.parse($("profileJson").value); render(); message("JSON aplicado al formulario. Revísalo y confirma."); }
    catch (error) { message("El JSON no es válido: " + error.message, true); }
  }

  async function save() {
    const done = busy($("profileSave"), "Guardando…");
    try {
      const result = await call({action: "profile_save", profile: finalProfile(), path: $("profilePath").value.trim()});
      message(`Perfil guardado en ${result.path}. Las notas nuevas seguirán estas reglas; las existentes no se modifican.`);
      await browser.storage.local.set({currentCapture: null, draftResult: null, settingsRevision: crypto.randomUUID()});
      $("profileReview").hidden = $("profileDocs").hidden = true;
      await refresh();
    } catch (error) { message(error.message, true); }
    finally { done(); }
  }

  $("profileScan").onclick = scan;
  $("profileInterpret").onclick = () => interpret(true);
  $("profileAutomatic").onclick = () => interpret(false);
  $("profileApplyJson").onclick = applyJson;
  $("profileSave").onclick = save;
  refresh();
  return {refresh};
})();

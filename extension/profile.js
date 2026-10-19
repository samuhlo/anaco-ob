/* Vault profile card in Options: scan, choose what the model may read, review
   each rule next to its evidence and confirm. The form edits one draft object. */
globalThis.AnacoObProfileCard = (() => {
  const $ = id => document.getElementById(id);
  const call = message => browser.runtime.sendMessage({type: "native", message});
  const ORIGINS = {type: tx('review_tipo_de_nota'), constant: tx('profile_valor_fijo'), folder_map: tx('profile_segun_la_carpeta'), path_segment: tx('profile_nombre_de_una_carpeta_de_la_ruta'),
    tags: tx('profile_etiquetas_propuestas'), context: tx('review_contexto'), title: tx('review_titulo'), created: tx('profile_fecha_de_creacion'), today: tx('profile_fecha_de_guardado'),
    url: tx('profile_url_de_la_fuente'), author: tx('profile_autor_de_la_fuente'), source_format: tx('profile_formato_de_la_fuente'), assisted: tx('profile_asistido_por_ia'),
    model: tx('profile_modelo_de_ia'), relations: tx('profile_relaciones_aceptadas')};
  // Default headings written into notes: the service gives them in the note language.
  let SECTIONS = {summary: "Resumen", intent: "Intención personal", quote: "Cita", quote_context: "Contexto de la cita",
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
      if (settings.default_sections) SECTIONS = settings.default_sections;
      $("profileInterpret").hidden = provider !== "codex";
      if (current.missing) {
        // A broken file is not a missing profile: show its own error.
        $("profileStatus").textContent = current.path ? current.message : tx('profile_este_vault_aun_no_tiene_perfil_escanealo');
        $("profileProblems").hidden = true;
        return;
      }
      $("profileStatus").textContent = tx('profile_perfil_confirmado_en_1_2_carpetas_de_des',[current.path,current.folders.length]);
      $("profilePath").value = current.path;
      $("profileProblems").hidden = !current.problems.length;
      $("profileProblems").textContent = current.problems.length ? tx('profile_revisa_el_perfil') + current.problems.join("\n") : "";
      $("profileScan").textContent = tx('profile_volver_a_escanear');
    } catch (error) { $("profileStatus").textContent = error.message; }
  }

  async function scan() {
    const done = busy($("profileScan"), tx('profile_escaneando'));
    try {
      scanned = await call({action: "profile_scan"});
      $("profileDocList").replaceChildren();
      // Grouped by kind; long groups stay folded with their count.
      const groups = [[tx('profile_instrucciones_y_skills'), ["instructions", "skill"], true], [tx('profile_guias'), ["guide"], false], [tx('profile_plantillas'), ["template"], false]];
      for (const [title, kinds, open] of groups) {
        const docs = scanned.documents.filter(d => kinds.includes(d.kind));
        if (!docs.length) continue;
        const marked = docs.filter(d => d.suggested).length;
        const boxes = docs.sort((a, b) => b.suggested - a.suggested || a.path.localeCompare(b.path)).map(doc =>
          el("label", {className: "profile-option"}, el("input", {type: "checkbox", value: doc.path, checked: doc.suggested}), " ", el("span", {textContent: doc.path})));
        $("profileDocList").append(el("details", {className: "profile-group", open: open || docs.length <= 3},
          el("summary", {textContent: tx('profile_1_2_de_3_marcadas', [title, marked, docs.length])}), ...boxes));
      }
      if (!scanned.documents.length) $("profileDocList").append(el("p", {className: "muted", textContent: tx('profile_no_se_han_encontrado_instrucciones_ni_pl')}));
      $("profileDocs").hidden = false;
      $("profilePath").value = $("profilePath").value || scanned.suggested_path;
      $("profileDocs").scrollIntoView({block: "nearest"});
    } catch (error) { message(error.message, true); }
    finally { done(); }
  }

  async function interpret(useModel) {
    const button = useModel ? $("profileInterpret") : $("profileAutomatic");
    const done = busy(button, useModel ? tx('profile_la_ia_esta_leyendo_tus_instrucciones') : tx('profile_preparando'));
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
  const opened = new Set();
  // Folded by default; a section stays open across re-renders once opened.
  function section(title, intro, ...rows) {
    const node = el("details", {className: "profile-section", open: opened.has(title)}, el("summary", {textContent: title}), intro ? el("p", {className: "muted"}, el("small", {textContent: intro})) : null, ...rows);
    node.ontoggle = () => node.open ? opened.add(title) : opened.delete(title);
    return node;
  }
  // Same glob as native/vault_profile.py: * is one segment, ** any number.
  function matches(pattern, folder) {
    const walk = (p, f) => !p.length ? !f.length : p[0] === "**" ? f.map((_, i) => i).concat(f.length).some(i => walk(p.slice(1), f.slice(i))) : f.length > 0 && (p[0] === "*" || p[0] === f[0]) && walk(p.slice(1), f.slice(1));
    return walk(pattern.split("/"), folder ? folder.split("/") : []);
  }
  function summary(profile) {
    const folders = scanned?.folders || [];
    const covered = rule => folders.filter(f => matches(rule.pattern, f) && !(rule.exclude || []).some(e => f === e || f.startsWith(e + "/"))).length;
    const fields = profile.frontmatter.map(f => f.key);
    const lines = [
      [tx('profile_guarda_en'), profile.destinations.map(r => `${r.pattern.replace(/\/\*.*$/, "")} (${covered(r)} carpeta${covered(r) === 1 ? "" : "s"})`).join(" · ")],
      [tx('profile_tipo_por_defecto'), profile.destinations.map(r => `${r.default} en ${r.pattern.replace(/\/\*.*$/, "")}`).join(" · ")],
      [tx('profile_metadatos'), fields.slice(0, 7).join(", ") + (fields.length > 7 ? tx('profile_y_1_mas',[fields.length - 7]) : "")],
      [tx('profile_adjuntos'), profile.attachments],
      [tx('profile_la_ia_redacta_con'), profile.instructions.length === 1 ? tx('profile_1_documento_de_tu_vault', [1]) : tx('profile_1_documentos_de_tu_vault', [profile.instructions.length])]];
    return el("div", {className: "profile-summary"}, el("h4", {textContent: tx('profile_lo_que_hara_anaco')}),
      el("ul", {}, ...lines.map(([label, text]) => el("li", {}, el("strong", {textContent: label + ": "}), text || "—"))),
      el("p", {className: "muted"}, el("small", {textContent: tx('profile_si_te_encaja_confirmalo_puedes_ajustar_c')})));
  }

  function render() {
    const form = $("profileForm");
    form.replaceChildren();
    const typeKeys = Object.keys(draft.types);
    const destinations = draft.destinations.map((rule, index) => {
      const include = el("input", {type: "checkbox", checked: !rule.disabled, title: tx('profile_usar_este_destino')});
      include.onchange = () => { rule.disabled = !include.checked; sync(); };
      const types = el("input", {value: rule.types.join(", "), "aria-label": tx('profile_tipos_en') + rule.pattern});
      types.onchange = () => { rule.types = types.value.split(",").map(t => t.trim()).filter(Boolean); render(); };
      const select = el("select", {"aria-label": tx('profile_tipo_predeterminado_en') + rule.pattern});
      for (const type of rule.types) select.add(new Option(type, type, false, type === rule.default));
      select.onchange = () => { rule.default = select.value; sync(); };
      return el("div", {className: "profile-row"}, el("label", {className: "profile-head"}, include, " ", el("strong", {textContent: rule.pattern})),
        el("div", {className: "profile-fields"}, el("span", {textContent: tx('profile_tipos')}), types, el("span", {textContent: tx('profile_por_defecto')}), select), hint(evidence["destination:" + rule.pattern]));
    });
    const types = typeKeys.map(key => {
      const label = el("input", {value: draft.types[key].label, "aria-label": tx('profile_nombre_visible_de') + key});
      label.onchange = () => { draft.types[key].label = label.value; sync(); };
      const pattern = el("input", {value: draft.types[key].filename, "aria-label": tx('profile_nombre_de_archivo_de') + key});
      pattern.onchange = () => { draft.types[key].filename = pattern.value; sync(); };
      return el("div", {className: "profile-row"}, el("strong", {textContent: key}),
        el("div", {className: "profile-fields"}, el("span", {textContent: tx('profile_nombre')}), label, el("span", {textContent: tx('profile_archivo')}), pattern), hint(evidence["filename:" + key]));
    });
    const fields = draft.frontmatter.map((spec, index) => {
      const include = el("input", {type: "checkbox", checked: !spec.disabled, title: tx('profile_incluir_este_campo')});
      include.onchange = () => { spec.disabled = !include.checked; sync(); };
      const origin = el("select", {"aria-label": tx('profile_origen_de') + spec.key});
      for (const [value, label] of Object.entries(ORIGINS)) origin.add(new Option(label, value, false, value === spec.from));
      origin.onchange = () => { spec.from = origin.value; render(); };
      let detail = null;
      if (spec.from === "constant") { detail = el("input", {value: spec.value ?? "", "aria-label": tx('profile_valor_de') + spec.key}); detail.onchange = () => { spec.value = detail.value; sync(); }; }
      if (spec.from === "folder_map") detail = el("small", {textContent: Object.entries(spec.values || {}).map(([folder, value]) => `${folder} → ${value}`).join(" · ") || tx('profile_sin_valores_editalos_en_el_json')});
      if (spec.from === "path_segment") detail = el("small", {textContent: tx('profile_carpeta_n_o_1_de_la_ruta_sin_el_prefijo_',[spec.index + 1])});
      const when = spec.when ? [spec.when.types && tx('profile_solo_tipos_1', [spec.when.types.join(", ")]), spec.when.folders && tx('profile_solo_en_1', [spec.when.folders.join(", ")]), spec.when.assisted !== undefined && (spec.when.assisted ? tx('profile_solo_con_ia') : tx('profile_solo_sin_ia'))].filter(Boolean).join(" · ") : "";
      return el("div", {className: "profile-row"}, el("label", {className: "profile-head"}, include, " ", el("strong", {textContent: spec.key})),
        el("div", {className: "profile-fields"}, el("span", {textContent: tx('profile_origen')}), origin, detail ? el("span", {textContent: tx('profile_detalle')}) : null, detail), hint([when, evidence["field:" + spec.key] || evidence["frontmatter:" + spec.key]].filter(Boolean).join(" · ")));
    });
    const attachments = el("input", {value: draft.attachments, "aria-label": tx('profile_carpeta_de_adjuntos')});
    attachments.onchange = () => { draft.attachments = attachments.value.trim(); sync(); };
    const tops = [...new Set((scanned?.folders || []).map(f => f.split("/")[0]))];
    const roots = tops.map(top => {
      const box = el("input", {type: "checkbox", checked: draft.relation_roots.includes(top)});
      box.onchange = () => { draft.relation_roots = box.checked ? [...draft.relation_roots, top] : draft.relation_roots.filter(r => r !== top); sync(); };
      return el("label", {className: "profile-option"}, box, " " + top);
    });
    const docOption = path => {
      const box = el("input", {type: "checkbox", checked: draft.instructions.includes(path)});
      box.onchange = () => { draft.instructions = box.checked ? [...draft.instructions, path] : draft.instructions.filter(p => p !== path); sync(); };
      return el("label", {className: "profile-option"}, box, " " + path);
    };
    const known = (scanned?.documents || []).map(d => d.path);
    const main = [...new Set([...draft.instructions, ...(scanned?.documents || []).filter(d => d.suggested).map(d => d.path)])];
    const others = known.filter(p => !main.includes(p));
    const documents = [...main.map(docOption), others.length ? el("details", {className: "profile-group"}, el("summary", {textContent: tx('profile_otros_documentos_1',[others.length])}), ...others.map(docOption)) : null];
    const headings = Object.entries(SECTIONS).map(([key, fallback]) => {
      const input = el("input", {value: draft.sections?.[key] || "", placeholder: fallback, "aria-label": tx('profile_encabezado_1', [fallback])});
      input.onchange = () => { draft.sections = {...draft.sections, [key]: input.value.trim()}; if (!input.value.trim()) delete draft.sections[key]; sync(); };
      return el("div", {className: "profile-fields"}, el("span", {textContent: fallback}), input);
    });
    const notes = Object.entries(evidence).filter(([key]) => !/^(destination|filename|field|frontmatter):/.test(key)).map(([key, text]) => el("li", {}, el("strong", {textContent: key + ": "}), text));
    form.append(summary(finalProfile()),
      section(tx('profile_ajustar_destinos_1',[destinations.length]), tx('profile_zonas_donde_anaco_puede_guardar_notas_co'), ...destinations),
      section(tx('profile_ajustar_tipos_y_nombres_de_archivo_1',[types.length]), tx('profile_admite_variables'), ...types),
      section(tx('profile_ajustar_metadatos_1',[fields.length]), tx('profile_cada_campo_dice_de_donde_sale_su_valor_l'), ...fields),
      section(tx('profile_ajustar_adjuntos_y_relaciones'), "", el("label", {textContent: tx('profile_carpeta_de_adjuntos')}), attachments, el("p", {className: "muted"}, el("small", {textContent: tx('profile_carpetas_donde_buscar_notas_relacionadas')})), ...roots),
      section(tx('profile_ajustar_documentos_para_la_ia_1',[draft.instructions.length]), tx('profile_las_instrucciones_del_vault_mandan_sobre'), ...documents),
      section(tx('profile_ajustar_encabezados'), tx('profile_vacio_se_usa_el_encabezado_por_defecto'), ...headings),
      notes.length ? section(tx('profile_por_que_se_propone_asi'), "", el("ul", {className: "profile-notes"}, ...notes)) : "");
    sync();
  }

  // The JSON mirrors the form; disabled rows are left out of the saved profile.
  function finalProfile() {
    const profile = structuredClone(draft);
    profile.destinations = profile.destinations.filter(r => !r.disabled).map(({disabled, ...rule}) => rule);
    profile.frontmatter = profile.frontmatter.filter(f => !f.disabled).map(({disabled, ...field}) => field);
    return profile;
  }
  function sync() {
    $("profileJson").value = JSON.stringify(finalProfile(), null, 2);
    const current = $("profileForm").querySelector(".profile-summary");
    if (current) current.replaceWith(summary(finalProfile()));
  }

  function applyJson() {
    try { draft = JSON.parse($("profileJson").value); render(); message(tx('profile_json_aplicado_al_formulario_revisalo_y_c')); }
    catch (error) { message(tx('profile_el_json_no_es_valido') + error.message, true); }
  }

  async function save() {
    const done = busy($("profileSave"), tx('profile_guardando'));
    try {
      const result = await call({action: "profile_save", profile: finalProfile(), path: $("profilePath").value.trim()});
      message(tx('profile_perfil_guardado_en_1_las_notas_nuevas_se',[result.path]));
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

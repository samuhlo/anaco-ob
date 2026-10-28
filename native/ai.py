"""OpenAI-compatible provider: OpenAI, Claude, Gemini, MiniMax, Qwen, OpenRouter,
Ollama, LM Studio and similar.

One request per call to {api_base}/chat/completions, asking for JSON that follows
the given schema. The schema also travels in the prompt, because some endpoints
(Claude's) ignore response_format; servers that reject it get plain JSON mode.
"""
import json
import re
import urllib.error
from translation import t
import urllib.request
from core import UserError, image_bytes, api_endpoint

TIMEOUT = 300
MIME = {".png": "image/png", ".jpg": "image/jpeg", ".gif": "image/gif", ".webp": "image/webp"}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """A configured API URL is the only destination authorized for this request."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def request(cfg, body):
    url = api_endpoint(cfg['api_base']) + '/chat/completions'
    headers = {"Content-Type": "application/json"}
    if cfg.get("api_key"):
        headers["Authorization"] = "Bearer " + cfg["api_key"]
    data = json.dumps(body, ensure_ascii=False).encode()
    try:
        opener = urllib.request.build_opener(NoRedirect())
        with opener.open(urllib.request.Request(url, data=data, headers=headers, method="POST"), timeout=TIMEOUT) as response:
            return 200, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        if exc.code in (301, 302, 303, 307, 308):
            exc.close()
            raise UserError('El servidor de IA ha redirigido la petición. Configura su URL base final en Opciones; no se han reenviado la clave ni el contenido.') from exc
        try:
            detail = json.loads(exc.read())
        except ValueError:
            detail = {}
        finally:
            exc.close()
        return exc.code, detail
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise UserError("No responde el servidor de IA en {url}. Comprueba la URL en Opciones y que el servidor esté en marcha. La captura sigue pendiente.", url=cfg['api_base']) from exc


def message(detail):
    error = detail.get("error") if isinstance(detail, dict) else None
    return str(error.get("message") if isinstance(error, dict) else error or "")[:300]


def parse(content):
    """The answer text as JSON, tolerating a fenced block or a sentence around the object."""
    text = (content or "").strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fenced:
        text = fenced.group(1)
    elif not text.startswith("{") and "{" in text:
        text = text[text.index("{"):text.rindex("}") + 1]
    try:
        return json.loads(text)
    except ValueError as exc:
        raise UserError("La IA no devolvió una propuesta válida; la captura sigue pendiente.") from exc


def openai_json(cfg, prompt, spec, images=None):
    model = (cfg.get("api_vision_model") or cfg["api_model"]) if images else cfg["api_model"]
    parts = [{"type": "text", "text": prompt + "\n\nDevuelve un único objeto JSON que cumpla este esquema:\n" + json.dumps(spec, ensure_ascii=False)}]
    for image in images or []:
        raw, ext = image_bytes(image)
        import base64
        parts.append({"type": "image_url", "image_url": {"url": f"data:{MIME[ext]};base64,{base64.b64encode(raw).decode()}"}})
    messages = [{"role": "system", "content": "Respondes solo con un objeto JSON válido que cumple el esquema pedido."}, {"role": "user", "content": parts}]
    # No temperature: recent Claude and reasoning models reject anything but their default.
    body = {"model": model, "messages": messages,
            "response_format": {"type": "json_schema", "json_schema": {"name": "anaco", "schema": spec, "strict": True}}}
    status, detail = request(cfg, body)
    if status == 400 and re.search(r"response_format|json_schema|schema", message(detail), re.I):
        # GUARD -> Some local servers reject schemas: the prompt already carries it, ask for plain JSON.
        body = {**body, "response_format": {"type": "json_object"}}
        status, detail = request(cfg, body)
    if status in (401, 403):
        raise UserError("El servidor de IA rechaza la clave API. Revísala en Opciones. La captura sigue pendiente.")
    if status == 404:
        raise UserError("El servidor de IA no encuentra el modelo o la ruta: {detail}. Revisa la URL base y el modelo en Opciones.", detail=message(detail) or cfg['api_model'])
    if status != 200:
        raise UserError("El servidor de IA respondió con un error ({status}): {detail}. La captura sigue pendiente.", status=status, detail=message(detail) or t("sin detalle"))
    try:
        content = detail["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise UserError("La respuesta del servidor de IA no tiene el formato de OpenAI.") from exc
    result = parse(content)
    if not isinstance(result, dict):
        raise UserError("La IA no devolvió una propuesta válida; la captura sigue pendiente.")
    result["_model"] = model
    return result

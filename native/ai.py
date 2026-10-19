"""OpenAI-compatible provider: OpenAI, OpenRouter, Ollama, LM Studio and similar.

One request per call to {api_base}/chat/completions, asking for JSON that follows
the given schema. Servers without schema support get plain JSON mode instead.
"""
import json
import re
import urllib.error
import urllib.request
from core import UserError, image_bytes

TIMEOUT = 300
MIME = {".png": "image/png", ".jpg": "image/jpeg", ".gif": "image/gif", ".webp": "image/webp"}


def request(cfg, body):
    url = cfg["api_base"].rstrip("/") + "/chat/completions"
    headers = {"Content-Type": "application/json"}
    if cfg.get("api_key"):
        headers["Authorization"] = "Bearer " + cfg["api_key"]
    data = json.dumps(body, ensure_ascii=False).encode()
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=headers, method="POST"), timeout=TIMEOUT) as response:
            return 200, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        try:
            detail = json.loads(exc.read())
        except ValueError:
            detail = {}
        return exc.code, detail
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise UserError(f"No responde el servidor de IA en {cfg['api_base']}. Comprueba la URL en Opciones y que el servidor esté en marcha. La captura sigue pendiente.") from exc


def message(detail):
    error = detail.get("error") if isinstance(detail, dict) else None
    return str(error.get("message") if isinstance(error, dict) else error or "")[:300]


def parse(content):
    """The answer text as JSON, tolerating a fenced block from plain JSON mode."""
    text = (content or "").strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    try:
        return json.loads(fenced.group(1) if fenced else text)
    except ValueError as exc:
        raise UserError("La IA no devolvió una propuesta válida; la captura sigue pendiente.") from exc


def openai_json(cfg, prompt, spec, images=None):
    model = (cfg.get("api_vision_model") or cfg["api_model"]) if images else cfg["api_model"]
    parts = [{"type": "text", "text": prompt}]
    for image in images or []:
        raw, ext = image_bytes(image)
        import base64
        parts.append({"type": "image_url", "image_url": {"url": f"data:{MIME[ext]};base64,{base64.b64encode(raw).decode()}"}})
    messages = [{"role": "system", "content": "Respondes solo con un objeto JSON válido que cumple el esquema pedido."}, {"role": "user", "content": parts}]
    body = {"model": model, "messages": messages, "temperature": 0.2,
            "response_format": {"type": "json_schema", "json_schema": {"name": "anaco", "schema": spec, "strict": True}}}
    status, detail = request(cfg, body)
    if status == 400 and re.search(r"response_format|json_schema|schema", message(detail), re.I):
        # GUARD -> Some local servers reject schemas: send the schema in the prompt instead.
        plain = [{"type": "text", "text": prompt + "\n\nDevuelve un único objeto JSON que cumpla este esquema:\n" + json.dumps(spec, ensure_ascii=False)}] + parts[1:]
        body = {**body, "messages": [messages[0], {"role": "user", "content": plain}], "response_format": {"type": "json_object"}}
        status, detail = request(cfg, body)
    if status in (401, 403):
        raise UserError("El servidor de IA rechaza la clave API. Revísala en Opciones. La captura sigue pendiente.")
    if status == 404:
        raise UserError(f"El servidor de IA no encuentra el modelo o la ruta: {message(detail) or cfg['api_model']}. Revisa la URL base y el modelo en Opciones.")
    if status != 200:
        raise UserError(f"El servidor de IA respondió con un error ({status}): {message(detail) or 'sin detalle'}. La captura sigue pendiente.")
    try:
        content = detail["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise UserError("La respuesta del servidor de IA no tiene el formato de OpenAI.") from exc
    result = parse(content)
    if not isinstance(result, dict):
        raise UserError("La IA no devolvió una propuesta válida; la captura sigue pendiente.")
    result["_model"] = model
    return result

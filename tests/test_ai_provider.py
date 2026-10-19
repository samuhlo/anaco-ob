import base64
import http.server
import json
from pathlib import Path
import sys
import threading
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "native"))
from core import UserError
import test_core as core_tests


class FakeOpenAI(http.server.BaseHTTPRequestHandler):
    """A /v1/chat/completions server that records requests and answers with JSON."""
    requests, reject_schema, status = [], False, 200

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        type(self).requests.append({"path": self.path, "auth": self.headers.get("Authorization"), "body": body})
        if type(self).status != 200:
            self.reply(type(self).status, {"error": {"message": "invalid api key"}})
            return
        if type(self).reject_schema and body.get("response_format", {}).get("type") == "json_schema":
            self.reply(400, {"error": {"message": "response_format json_schema is not supported"}})
            return
        answer = {"title": "Recuperación activa", "context": "Estudiar recordando", "body": "## Idea\n\nRecordar fortalece la memoria.",
                  "folder": "02_Cerebro/Modelos_Mentales", "tags": ["memoria"], "relations": [], "image_captions": [],
                  "note_type": "nota_atomica", "strategy": "concept", "rationale": "Un concepto.", "source_format": "articulo", "notes": []}
        content = json.dumps(answer, ensure_ascii=False)
        if body.get("response_format", {}).get("type") == "json_object":
            content = "```json\n" + content + "\n```"
        self.reply(200, {"choices": [{"message": {"role": "assistant", "content": content}}]})

    def reply(self, status, value):
        raw = json.dumps(value).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, *args):
        pass


class OpenAIProviderTest(unittest.TestCase):
    setUp_core = core_tests.CoreTest.setUp
    tearDown_core = core_tests.CoreTest.tearDown
    capture = core_tests.CoreTest.capture

    def setUp(self):
        self.setUp_core()
        FakeOpenAI.requests, FakeOpenAI.reject_schema, FakeOpenAI.status = [], False, 200
        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), FakeOpenAI)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.app.set_config({"provider": "openai", "api_base": f"http://127.0.0.1:{self.server.server_port}/v1",
                             "api_model": "llama3.1:8b", "api_vision_model": "llava:13b", "api_key": "sk-prueba"})

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.tearDown_core()

    def test_a_note_is_prepared_with_an_openai_compatible_server(self):
        c = self.capture()
        result = self.app.draft(c["id"], provider="openai")
        self.assertEqual(result["draft"]["title"], "Recuperación activa")
        self.assertTrue(result["draft"]["assisted"])
        self.assertEqual(result["draft"]["model"], "llama3.1:8b")
        sent = FakeOpenAI.requests[0]
        self.assertEqual(sent["path"], "/v1/chat/completions")
        self.assertEqual(sent["auth"], "Bearer sk-prueba")
        self.assertEqual(sent["body"]["model"], "llama3.1:8b")
        self.assertEqual(sent["body"]["response_format"]["type"], "json_schema")
        self.assertIn("La recuperación activa mejora el aprendizaje", json.dumps(sent["body"], ensure_ascii=False))

    def test_servers_without_schemas_fall_back_to_plain_json(self):
        FakeOpenAI.reject_schema = True
        c = self.capture()
        self.assertEqual(self.app.draft(c["id"], provider="openai")["draft"]["title"], "Recuperación activa")
        self.assertEqual([r["body"]["response_format"]["type"] for r in FakeOpenAI.requests], ["json_schema", "json_object"])
        self.assertIn('"required"', FakeOpenAI.requests[1]["body"]["messages"][-1]["content"][0]["text"])

    def test_images_use_the_vision_model_as_data_urls(self):
        from ai import openai_json
        image = {"data": base64.b64encode(core_tests.PNG).decode()}
        openai_json(self.app.config(), "Describe", {"type": "object", "properties": {}, "required": [], "additionalProperties": False}, [image])
        content = FakeOpenAI.requests[0]["body"]["messages"][-1]["content"]
        self.assertEqual(FakeOpenAI.requests[0]["body"]["model"], "llava:13b")
        self.assertTrue(content[1]["image_url"]["url"].startswith("data:image/png;base64,"))

    def test_a_wrong_key_says_so(self):
        FakeOpenAI.status = 401
        c = self.capture()
        with self.assertRaisesRegex(UserError, "clave"):
            self.app.draft(c["id"], provider="openai")

    def test_the_key_never_goes_back_to_the_extension(self):
        for action in ("settings", "status"):
            config = self.app.handle({"action": action})["config"]
            self.assertNotIn("api_key", config)
            self.assertTrue(config["api_key_set"])
        # An empty key from the form keeps the stored one; null removes it.
        self.app.set_config({"api_key": ""})
        self.assertEqual(self.app.config()["api_key"], "sk-prueba")
        self.app.set_config({"api_key": None})
        self.assertFalse(self.app.handle({"action": "settings"})["config"]["api_key_set"])

    def test_codex_stays_the_default_and_untouched(self):
        fresh = core_tests.App(self.root / "otro-estado")
        self.addCleanup(fresh.db.close)
        self.assertEqual(fresh.config()["provider"], "codex")
        with self.assertRaises(UserError):
            self.app.set_config({"api_base": "ftp://servidor"})


if __name__ == "__main__":
    unittest.main()

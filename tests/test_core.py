import base64
import io
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "native"))
from core import App, UserError, image_bytes, normalized_url, safe_path
from host import read_exact
from vault_profile import install

CLASSIC = Path(__file__).resolve().parent / "fixtures/profile-classic.json"

PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a3i8AAAAASUVORK5CYII=")


class CoreTest(unittest.TestCase):
    def test_codex_quality_defaults_and_selected_effort_reach_every_call(self):
        cfg=self.app.config()
        self.assertEqual(cfg['model'],'gpt-6.1-sol');self.assertEqual(cfg['vision_model'],'gpt-6.1-sol')
        self.assertEqual(cfg['reading_model'], 'gpt-6-luna')
        self.assertEqual(cfg['reasoning_effort'],'medium')
        commands=[]
        def fake(command,**kwargs):
            commands.append(command)
            Path(command[command.index('--output-last-message')+1]).write_text('{}')
            return subprocess.CompletedProcess(command,0)
        with patch('core.subprocess.run',side_effect=fake):
            self.app.codex_json('Fixture',{'type':'object'})
            self.app.codex_json('Vision fixture',{'type':'object'},cfg['vision_model'],[{'data':base64.b64encode(PNG).decode()}])
            self.app.set_config({'reasoning_effort':'high'})
            self.app.codex_json('Fixture',{'type':'object'})
        for command in commands[:2]:
            self.assertIn('model_reasoning_effort="medium"',command)
            self.assertEqual(command[command.index('--model')+1],'gpt-6.1-sol')
        self.assertIn('model_reasoning_effort="high"',commands[-1])
        with self.assertRaises(UserError):self.app.set_config({'reasoning_effort':'invalid'})
        with self.assertRaises(UserError):self.app.set_config({'reading_model':'bad/model'})

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.vault = self.root / "Vault"
        for folder in ("02_Cerebro/Tech_&_Codigo", "02_Cerebro/Modelos_Mentales", "03_Proyectos/App", "07_Clases/01_Curso/01_Tema", "99_Recursos"):
            (self.vault / folder).mkdir(parents=True, exist_ok=True)
        self.app = App(self.root / "state")
        self.app.set_config({"vault": str(self.vault), "provider": "manual"})
        # The previous built-in conventions, now expressed as a vault profile.
        install(self.app, json.loads(CLASSIC.read_text()), "99_Recursos/anaco/perfil.json")

    def tearDown(self):
        self.app.db.close()
        self.temp.cleanup()

    def capture(self, **kwargs):
        c = {"kind":"article", "url":"https://example.org/lesson?utm_source=test", "title":"Recuperación activa", "text":"La recuperación activa mejora el aprendizaje. Repetir pruebas permite recordar conceptos."}
        c.update(kwargs)
        return self.app.stage(c)

    def prepared(self, **kwargs):
        c = self.capture(**kwargs)
        return c, self.app.draft(c["id"], provider="manual")

    def test_manual_capture_has_no_ai_attribution(self):
        c, _ = self.prepared()
        result = self.app.save(c["id"], {})
        note = Path(result["path"]).read_text()
        self.assertIn('llm_asistido: false', note)
        self.assertNotIn('llm_modelo:', note)
        # Without accepted relations there is no empty relations section.
        self.assertNotIn('## Notas relacionadas', note)
        self.assertTrue(result["obsidian_url"].startswith("obsidian://open?"))

    def test_quote_is_literal_and_context_retained(self):
        quote = '«Una idea — con signos, ** y tildes.»\nSegunda línea.'
        c, _ = self.prepared(kind="quote",text=quote,context="Contexto antes y después.")
        rendered = self.app.preview(c["id"], {})["markdown"]
        self.assertIn("> «Una idea — con signos, ** y tildes.»\n> Segunda línea.", rendered)
        self.assertIn("Contexto antes y después.", rendered)
        self.assertNotIn("fuente_autor:", rendered)

    def test_images_local_and_exact(self):
        im = {"url":"https://example.org/temporary.png", "alt":"Diagrama", "data":base64.b64encode(PNG).decode()}
        c, _ = self.prepared(kind="image",text="Diagrama",images=[im])
        result = self.app.save(c["id"], {})
        image = next((self.vault / "99_Recursos").rglob("*.png"))
        self.assertEqual(image.read_bytes(), PNG)
        self.assertIn("![[99_Recursos/adjuntos/anaco-ob/", Path(result["path"]).read_text())

    def test_duplicate_blocked_different_selection_allowed(self):
        c, _ = self.prepared(kind="quote")
        self.app.save(c["id"], {})
        other, _ = self.prepared(kind="quote")
        with self.assertRaises(UserError): self.app.save(other["id"], {})
        third, _ = self.prepared(kind="quote",text="Otra selección de la misma página.")
        self.assertIsNone(self.app.duplicate(self.app.load(third["id"])))

    def test_collision_preserves_existing_note(self):
        c, d = self.prepared()
        target = self.vault / d["draft"]["folder"] / d["draft"]["filename"]
        target.write_text("MIS APUNTES")
        with self.assertRaises(UserError): self.app.save(c["id"], {})
        self.assertEqual(target.read_text(), "MIS APUNTES")

    def test_path_escape_and_symlink_blocked(self):
        with self.assertRaises(UserError): safe_path(self.vault,"../fuera.md")
        with self.assertRaises(UserError): safe_path(self.vault,"/tmp/fuera.md")
        (self.vault / "99_Recursos/escape").symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(UserError): safe_path(self.vault,"99_Recursos/escape/fuera.md")

    def test_save_rejects_invalid_folder_and_name(self):
        c, _ = self.prepared()
        for fields in ({"folder":"00_Sistema"},{"filename":"../../fuera.md"},{"folder":"02_Cerebro/nueva"}):
            with self.assertRaises(UserError): self.app.save(c["id"],fields)

    def test_class_frontmatter(self):
        c, d = self.prepared()
        folder = "07_Clases/01_Curso/01_Tema"
        result = self.app.preview(c["id"], {"folder":folder,"filename":self.app.filename(self.app.load(c["id"]),"Tema",folder)})
        self.assertIn('tipo: "resumen"',result["markdown"])
        self.assertIn('curso: "Curso"',result["markdown"])
        self.assertIn('asignatura: "Tema"',result["markdown"])

    def test_relation_evidence_and_existing_path(self):
        rel_path = "02_Cerebro/Modelos_Mentales/recuerdo.md"
        evidence = "Intentar recordar sin mirar fortalece la memoria."
        (self.vault / rel_path).write_text("# Recuerdo\n\n" + evidence)
        c = self.capture()
        response = {"title":"Aprender", "context":"Estudio", "body":"Un resumen útil.","folder":"02_Cerebro/Modelos_Mentales", "tags":["aprendizaje"],
                    "relations":[{"path":rel_path,"reason":"Explica el mecanismo de recuperación.","source_evidence":"La recuperación activa mejora el aprendizaje.","note_evidence":evidence},
                                 {"path":"inventada.md","reason":"No existe","source_evidence":"No existe evidencia","note_evidence":"Tampoco existe"}]}
        with patch.object(self.app,"codex_generate",return_value=response): d=self.app.draft(c["id"],provider="codex")
        self.assertEqual(len(d["draft"]["relations"]),1)
        self.assertFalse(d["draft"]["relations"][0]["accepted"])
        self.assertNotIn("[[02_Cerebro/",self.app.preview(c["id"],{})["markdown"])
        note=self.app.preview(c["id"],{"relations":[rel_path]})["markdown"]
        self.assertIn("[[02_Cerebro/Modelos_Mentales/recuerdo]]",note)
        (self.vault / rel_path).rename(self.vault / "renombrada.md")
        with self.assertRaises(UserError):self.app.save(c["id"],{"relations":[rel_path]})

    def test_false_evidence_removed(self):
        rel="02_Cerebro/Tech_&_Codigo/red.md"
        (self.vault/rel).write_text("# Redes\n\nUna red conecta ordenadores, no memorias personales.")
        c=self.capture()
        answer={"title":"Tema","context":"Tema","body":"Texto [[enlace_falso]].","folder":"02_Cerebro/Tech_&_Codigo","tags":[],
                "relations":[{"path":rel,"reason":"Palabras parecidas","source_evidence":"La recuperación activa mejora el aprendizaje.","note_evidence":"Evidencia inventada completamente."}]}
        with patch.object(self.app,"codex_generate",return_value=answer):d=self.app.draft(c["id"],provider="codex")
        self.assertEqual(d["draft"]["relations"],[])
        self.assertNotIn("[[",d["draft"]["body"])

    def test_ai_failure_keeps_pending(self):
        c=self.capture()
        with patch.object(self.app,"codex_generate",side_effect=UserError("Sin conexión")):
            with self.assertRaises(UserError):self.app.draft(c["id"],"Para estudiar",provider="codex")
        self.assertEqual(self.app.pending()[0]["id"],c["id"])
        self.assertEqual(self.app.load(c["id"])["intent"],"Para estudiar")

    def test_cross_vault_capture_blocked(self):
        c,_=self.prepared()
        other=self.root/"Other";other.mkdir()
        self.app.set_config({"vault":str(other)})
        with self.assertRaises(UserError):self.app.load(c["id"])
        self.assertEqual(self.app.pending(),[])

    def test_attachment_failure_does_not_create_note(self):
        im={"data":base64.b64encode(PNG).decode()}
        c,d=self.prepared(kind="image",text="Diagrama",images=[im])
        (self.vault/"99_Recursos/adjuntos").symlink_to(self.root,target_is_directory=True)
        with self.assertRaises(UserError):self.app.save(c["id"],{})
        self.assertFalse((self.vault/d["draft"]["folder"]/d["draft"]["filename"]).exists())

    def test_invalid_images_and_urls(self):
        with self.assertRaises(UserError):image_bytes({"data":base64.b64encode(b"<script>bad</script>").decode()})
        with self.assertRaises(UserError):self.capture(url="file:///etc/passwd")
        self.assertEqual(normalized_url("https://example.org/p?utm_source=a&x=1#foo"),"https://example.org/p?x=1")

    def test_failed_publish_leaves_no_partial_note(self):
        c,d=self.prepared()
        with patch("core.os.link",side_effect=OSError("Disco lleno")):
            with self.assertRaises(OSError):self.app.save(c["id"],{})
        self.assertFalse((self.vault/d["draft"]["folder"]/d["draft"]["filename"]).exists())
        self.assertFalse(list(self.vault.rglob(".anaco-ob-*")))
        self.assertEqual(self.app.load(c["id"])["status"],"draft")

    def test_discard_removes_pending_without_creating_note(self):
        c,_=self.prepared()
        self.assertTrue(self.app.handle({"action":"discard","id":c["id"]})["discarded"])
        self.assertEqual(self.app.pending(),[])
        self.assertEqual(self.app.load(c["id"])["status"],"discarded")
        self.assertFalse(list(self.vault.rglob("fuente_*.md")))
        with self.assertRaises(UserError):self.app.save(c["id"],{})
        with self.assertRaises(UserError):self.app.draft(c["id"],provider="manual")

    def test_discard_cannot_delete_saved_note(self):
        c,_=self.prepared()
        saved=self.app.save(c["id"],{})
        with self.assertRaises(UserError):self.app.handle({"action":"discard","id":c["id"]})
        self.assertTrue(Path(saved["path"]).exists())

    def test_preview_image_chunks_are_bounded_and_exact(self):
        im={"data":base64.b64encode(PNG).decode()}
        c,_=self.prepared(kind="image",text="Diagrama",images=[im])
        result=self.app.handle({"action":"image_chunk","id":c["id"],"index":0,"offset":0})
        self.assertEqual(base64.b64decode(result["data"]),PNG)
        self.assertEqual(result["mime"],"image/png")
        self.assertLessEqual(len(result["data"]),262144)
        for index,offset in [(99,0),(0,-1),(False,0),(0,"bad")]:
            with self.assertRaises(UserError):self.app.handle({"action":"image_chunk","id":c["id"],"index":index,"offset":offset})

    def test_native_protocol(self):
        import os
        packet=json.dumps({"action":"status","requestId":"test"}).encode()
        process=subprocess.run([sys.executable,str(Path(__file__).resolve().parents[1]/"native/host.py")],input=struct.pack("=I",len(packet))+packet,
                               capture_output=True,env={**os.environ,"ANACO_OB_STATE":str(self.root/"state")})
        size=struct.unpack("=I",process.stdout[:4])[0]
        result=json.loads(process.stdout[4:4+size])
        self.assertTrue(result["ok"])
        self.assertEqual(result["requestId"],"test")

    def test_short_stream_reads(self):
        class Short(io.BytesIO):
            def read(self,n):return super().read(min(n,2))
        self.assertEqual(read_exact(Short(b"abcdef"),6),b"abcdef")


if __name__ == "__main__":
    unittest.main()

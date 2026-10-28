"""Credentials must stay with their configured endpoint, including redirects."""
import http.server
import sys
import threading
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'native'))
import ai
from core import UserError
import test_core as core_tests


class CredentialScopeTest(unittest.TestCase):
    setUp = core_tests.CoreTest.setUp
    tearDown = core_tests.CoreTest.tearDown

    def test_changing_endpoint_does_not_reuse_a_stored_key(self):
        original = 'https://first.invalid/v1'
        for destination in ('https://second.invalid/v1', 'http://localhost:11434/v1',
                            'https://first.invalid:8443/v1', 'https://first.invalid/other'):
            with self.subTest(destination=destination):
                self.app.set_config({'api_base': original, 'api_key': 'audit-fake-key'})
                public = self.app.set_config({'api_base': destination, 'api_key': ''})
                self.assertFalse(public['api_key_set'])
                self.assertNotIn('api_key', self.app.config())

    def test_equivalent_endpoint_keeps_key_and_new_key_is_explicit(self):
        self.app.set_config({'api_base': 'https://first.invalid/v1', 'api_key': 'original'})
        self.app.set_config({'api_base': 'HTTPS://FIRST.INVALID:443/v1/'})
        self.assertEqual(self.app.config()['api_key'], 'original')
        self.app.set_config({'api_base': 'https://second.invalid/v1', 'api_key': 'replacement'})
        self.assertEqual(self.app.config()['api_key'], 'replacement')
        self.assertNotIn('api_key', self.app.handle({'action': 'settings'})['config'])

    def test_invalid_endpoint_does_not_change_saved_configuration(self):
        self.app.set_config({'api_base': 'https://first.invalid/v1', 'api_key': 'original'})
        before = self.app.config()
        for address in ('https://user:secret@example.org/v1', 'https://example.org/v1?key=secret',
                        'https://example.org/v1#fragment', 'http://', 'https://example.org:bad/v1'):
            with self.subTest(address=address), self.assertRaises(UserError):
                self.app.set_config({'api_base': address})
            self.assertEqual(self.app.config(), before)


class RedirectHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        self.rfile.read(int(self.headers.get('Content-Length', 0)))
        self.server.requests.append((self.path, self.headers.get('Authorization')))
        self.send_response(self.server.redirect_status)
        self.send_header('Location', self.server.destination)
        self.end_headers()

    def do_GET(self):
        self.server.requests.append((self.path, self.headers.get('Authorization')))
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'{}')

    def log_message(self, *args):
        pass


class RedirectSecurityTest(unittest.TestCase):
    def server(self):
        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), RedirectHandler)
        server.requests = []
        server.redirect_status = 302
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        return server

    def test_redirect_never_receives_credentials_or_prompt(self):
        source, target = self.server(), self.server()
        for status in (301, 302, 303, 307, 308):
            with self.subTest(status=status):
                source.redirect_status = status
                source.destination = f'http://127.0.0.1:{target.server_port}/sink'
                with self.assertRaises(UserError):
                    ai.request({'api_base': f'http://127.0.0.1:{source.server_port}/v1',
                                'api_key': 'audit-fake-key'}, {'prompt': 'private fixture'})
                self.assertEqual(target.requests, [])
                self.assertEqual(source.requests[-1][1], 'Bearer audit-fake-key')

    def test_same_origin_redirect_also_requires_the_final_url(self):
        source = self.server()
        source.destination = f'http://127.0.0.1:{source.server_port}/sink'
        with self.assertRaises(UserError):
            ai.request({'api_base': f'http://127.0.0.1:{source.server_port}/v1'}, {})
        self.assertEqual([path for path, _ in source.requests], ['/v1/chat/completions'])

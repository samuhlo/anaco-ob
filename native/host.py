#!/usr/bin/env python3
"""Firefox native messaging: one long-lived connection, request IDs preserved."""
import json
import struct
import sys
import signal
from core import App, UserError

MAX_IN = 8_000_000
MAX_OUT = 900_000


def read_exact(stream, size):
    result = bytearray()
    while len(result) < size:
        data = stream.read(size - len(result))
        if not data:
            if not result:
                return None
            raise ValueError("Mensaje nativo incompleto")
        result.extend(data)
    return bytes(result)


def send(response):
    encoded = json.dumps(response, ensure_ascii=False).encode()
    if len(encoded) > MAX_OUT:
        encoded = json.dumps({'requestId': response.get('requestId'), 'ok': False,
                              'error': 'La propuesta es demasiado grande para el panel.'}).encode()
    sys.stdout.buffer.write(struct.pack('=I', len(encoded)) + encoded)
    sys.stdout.buffer.flush()


def main():
    signal.signal(signal.SIGTERM,lambda *_:sys.exit(143))
    app = App()
    while True:
        header = read_exact(sys.stdin.buffer, 4)
        if header is None:
            return
        size = struct.unpack("=I", header)[0]
        if size > MAX_IN:
            return
        data = read_exact(sys.stdin.buffer, size)
        request_id = None
        job=None
        try:
            message = json.loads(data)
            request_id = message.get("requestId")
            app.job_id=message.get('task') if message.get('action') in ('upload_begin','upload_chunk','upload_finish','video_url','subtitles','draft','revise','propose_split','refresh_links','capture') or str(message.get('action','')).startswith('reader_') else None
            if app.job_id:
                from jobs import Job
                job=Job(app,app.job_id);job.start(message);app.check_cancel=job.check
            else:app.check_cancel=lambda:None
            def progress(text):
                app.check_cancel();send({'requestId':request_id,'progress':text})
            app.progress = progress
            response = {"requestId": request_id, "ok": True, "result": app.handle(message)}
        except UserError as exc:
            if app.job_id and job:
                from jobs import Cancelled
                job.update(status='cancelled' if isinstance(exc,Cancelled) else 'failed')
            response = {"requestId": request_id, "ok": False, "error": str(exc)}
        except Exception as exc:
            if job:job.update(status='failed')
            print(type(exc).__name__, file=sys.stderr)
            response = {"requestId": request_id, "ok": False, "error": "No se ha completado la operación. La captura puede recuperarse desde Pendientes."}
        send(response)


if __name__ == "__main__":
    main()

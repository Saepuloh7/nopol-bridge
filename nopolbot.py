#!/usr/bin/env python
"""Jembatan @nopol_robot -> HTTP lokal (userbot wrapper).

GET /health           -> status koneksi
GET /send?text=...    -> kirim teks ke bot, kembalikan balasan

Login pertama: jalankan di terminal yang terlihat, isi nomor (+62...),
kode dari Telegram, 2FA bila ada. Sesi tersimpan di nopol_session.session.

Self-check tanpa jaringan: python nopolbot.py --selfcheck
"""
import asyncio
import json
import os
import sys
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from telethon import TelegramClient, events

API_ID = int(os.environ.get("TG_API_ID", "0"))
API_HASH = os.environ.get("TG_API_HASH", "")
BOT = "nopol_robot"
TIMEOUT = int(os.environ.get("TG_TIMEOUT", "60"))
PORT = int(os.environ.get("NOPOL_PORT", "8765"))

queue: asyncio.Queue = asyncio.Queue()

# ponytail: antrean serial, satu request per waktu.
# Bot tidak membalas dengan ID korelasi; paralel = risiko balasan tertukar.
# Upgrade: inline query / korelasi isi pesan bila bot mendukung.
inflight = {"event": asyncio.Event(), "text": None}


class State:
    def __init__(self):
        self.loop = None
        self.done = threading.Event()
        self.result = None


state = State()


# ponytail: hanya teks/caption diambil. Balasan murni foto/media -> reply null.
# Upgrade: download media ke temp, kembalikan path.
async def on_reply(event):
    m = event.message
    if not inflight["event"].is_set():
        inflight["text"] = m.text or m.message
        inflight["event"].set()


async def worker():
    while True:
        text = await queue.get()
        inflight["event"].clear()
        inflight["text"] = None
        try:
            await client.send_message(BOT, text)
            try:
                await asyncio.wait_for(inflight["event"].wait(), TIMEOUT)
                result = {"ok": True, "reply": inflight["text"]}
            except asyncio.TimeoutError:
                result = {"ok": False, "error": f"timeout {TIMEOUT}s: bot tidak membalas"}
        except Exception as e:
            result = {"ok": False, "error": f"{type(e).__name__}: {e}"}
        state.result = result
        state.done.set()
        queue.task_done()


# perintah bot (@nopol_robot) -> (perintah, nama parameter query)
COMMANDS = {
    "/nopul": ("/nopul", "nopol"),
    "/noka": ("/noka", "rangka"),
    "/nosin": ("/nosin", "mesin"),
    "/nik": ("/nik", "nik"),
    "/nama": ("/nama", "nama"),
}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        q = urllib.parse.urlparse(self.path)
        if q.path == "/health":
            return self._json(200, {"ok": True, "connected": client.is_connected()})
        if q.path in COMMANDS:
            cmd, param = COMMANDS[q.path]
            val = urllib.parse.parse_qs(q.query).get(param, [""])[0].strip()
            if not val:
                return self._json(400, {"ok": False, "error": f"parameter {param} wajib"})
            if q.path == "/nik" and (not val.isdigit() or len(val) != 16):
                return self._json(400, {"ok": False, "error": "nik harus 16 digit"})
            text = f"{cmd} {val}"
            return self._handle(text)
        if q.path != "/send":
            return self._json(
                404,
                {"ok": False, "error": "endpoint: /send /nopul /noka /nosin /nik /nama"},
            )
        text = urllib.parse.parse_qs(q.query).get("text", [""])[0]
        if not text:
            return self._json(400, {"ok": False, "error": "parameter text wajib"})
        return self._handle(text)

    def _handle(self, text):
        state.done.clear()
        state.loop.call_soon_threadsafe(queue.put_nowait, text)
        if not state.done.wait(TIMEOUT + 5):
            return self._json(504, {"ok": False, "error": "upstream timeout"})
        self._json(200 if state.result["ok"] else 502, state.result)

    def _json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass  # sunyi


async def main():
    await client.start()  # prompt interaktif: nomor, kode, 2FA
    me = await client.get_me()
    print(f"login: {me.username or me.phone} | bot: @{BOT}")
    state.loop = asyncio.get_running_loop()
    asyncio.create_task(worker())
    try:
        ent = await client.get_entity(BOT)
        print(f"bot ditemukan: @{ent.username}")
    except Exception as e:
        print(f"peringatan: bot @{BOT} tidak ditemukan ({e})")
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    print(f"http://127.0.0.1:{PORT}/send?text=...")
    await client.run_until_disconnected()


if __name__ == "__main__":
    if "--selfcheck" in sys.argv:
        import time
        import urllib.request

        class FakeClient:
            def add_event_handler(self, *a, **k):
                pass

            async def start(self):
                pass

            async def get_me(self):
                class Me:
                    username = "selftest"
                return Me()

            async def get_entity(self, bot):
                class E:
                    username = bot
                return E()

            async def send_message(self, bot, text):
                await asyncio.sleep(0.01)
                inflight["text"] = "REPLY:" + text
                inflight["event"].set()

            async def run_until_disconnected(self):
                await asyncio.Event().wait()

            def is_connected(self):
                return True

        client = FakeClient()
        client.add_event_handler(on_reply, events.NewMessage(from_users=BOT))
        threading.Thread(target=lambda: asyncio.run(main()), daemon=True).start()
        time.sleep(1.0)
        try:
            body = urllib.request.urlopen(
                f"http://127.0.0.1:{PORT}/send?text=tes", timeout=10
            ).read()
            data = json.loads(body)
            assert data["ok"] is True and data["reply"] == "REPLY:tes", data
            h = urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=10)
            assert json.loads(h.read())["connected"] is True
            body = urllib.request.urlopen(
                f"http://127.0.0.1:{PORT}/nopul?nopol=AD1337AD", timeout=10
            ).read()
            data = json.loads(body)
            assert data["ok"] is True and data["reply"] == "REPLY:/nopul AD1337AD", data
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{PORT}/nik?nik=123", timeout=10)
                raise AssertionError("harusnya 400 untuk nik 3 digit")
            except urllib.error.HTTPError as e:
                assert e.code == 400, e.code
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{PORT}/send", timeout=10)
                raise AssertionError("harusnya 400 tanpa text")
            except urllib.error.HTTPError as e:
                assert e.code == 400, e.code
            print("SELFCHECK PASS", flush=True)
            os._exit(0)
        except Exception as e:
            print("SELFCHECK FAIL:", e, flush=True)
            os._exit(1)

    if not API_ID or not API_HASH:
        sys.exit("set TG_API_ID dan TG_API_HASH (dari my.telegram.org) sebelum jalan")

    client = TelegramClient("nopol_session", API_ID, API_HASH)
    client.add_event_handler(on_reply, events.NewMessage(from_users=BOT))
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

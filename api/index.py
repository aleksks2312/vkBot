import json
import os
import random
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler

VK_API_URL = "https://api.vk.com/method/"
VK_API_VERSION = "5.199"

VK_TOKEN = os.environ.get("VK_TOKEN", "")
VK_CONFIRMATION = os.environ.get("VK_CONFIRMATION") or "4809e6d1"
VK_SECRET = os.environ.get("VK_SECRET", "")
VK_GROUP_ID = os.environ.get("VK_GROUP_ID") or "241266471"


def vk_call(method, **params):
    params.update({"access_token": VK_TOKEN, "v": VK_API_VERSION})
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(VK_API_URL + method, data=data)
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode())


def send_message(peer_id, text):
    vk_call(
        "messages.send",
        peer_id=peer_id,
        message=text,
        random_id=random.randint(1, 2**31 - 1),
    )


def handle_command(text, from_id):
    cmd = text.strip().lower()

    if cmd in ("/start", "начать", "start"):
        return "Привет! Я бот на Vercel 🚀\nНапиши /help, чтобы увидеть список команд."

    if cmd in ("/help", "помощь", "help"):
        return (
            "Доступные команды:\n"
            "/start — приветствие\n"
            "/help — эта справка\n"
            "/id — твой ID ВКонтакте\n"
            "/ping — проверка, что бот жив\n"
            "Любой другой текст я повторю (эхо)."
        )

    if cmd == "/id":
        return f"Твой ID: {from_id}"

    if cmd == "/ping":
        return "pong 🏓"

    return f"Ты написал: {text}"


def handle_event(event):
    event_type = event.get("type")

    if event_type == "confirmation":
        return VK_CONFIRMATION

    if event_type == "message_new":
        message = event.get("object", {}).get("message", {})
        text = message.get("text", "")
        peer_id = message.get("peer_id")
        from_id = message.get("from_id")
        if peer_id and text:
            send_message(peer_id, handle_command(text, from_id))

    return "ok"


class handler(BaseHTTPRequestHandler):
    def _send(self, status, body):
        payload = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        self._send(200, "VK bot is running")

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b""

        try:
            event = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self._send(400, "bad request")
            return

        # При подтверждении адреса ВК секрет не присылает — не проверяем
        if (
            VK_SECRET
            and event.get("type") != "confirmation"
            and event.get("secret") != VK_SECRET
        ):
            self._send(403, "forbidden")
            return

        if VK_GROUP_ID and str(event.get("group_id")) != str(VK_GROUP_ID):
            self._send(403, "forbidden")
            return

        try:
            body = handle_event(event)
        except Exception as exc:
            print(f"Error handling event: {exc}")
            body = "ok"

        self._send(200, body)

    def log_message(self, *args):
        pass

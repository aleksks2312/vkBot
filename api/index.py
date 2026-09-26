"""
VK бот на Vercel (Python Serverless Function) через Callback API.

ВК присылает POST-запросы с событиями на этот endpoint.
Настройки берутся из переменных окружения (см. .env.example).
"""

import json
import os
import random
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler

VK_API_URL = "https://api.vk.com/method/"
VK_API_VERSION = "5.199"

VK_TOKEN = os.environ.get("VK_TOKEN", "")
VK_CONFIRMATION = os.environ.get("VK_CONFIRMATION", "")
VK_SECRET = os.environ.get("VK_SECRET", "")
VK_GROUP_ID = os.environ.get("VK_GROUP_ID", "")


# ---------------------------------------------------------------------------
# Работа с VK API
# ---------------------------------------------------------------------------

def vk_call(method: str, **params) -> dict:
    """Вызов метода VK API."""
    params.update({"access_token": VK_TOKEN, "v": VK_API_VERSION})
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(VK_API_URL + method, data=data)
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode())


def send_message(peer_id: int, text: str) -> None:
    vk_call(
        "messages.send",
        peer_id=peer_id,
        message=text,
        random_id=random.randint(1, 2**31 - 1),
    )


# ---------------------------------------------------------------------------
# Логика бота
# ---------------------------------------------------------------------------

def handle_command(text: str, from_id: int) -> str:
    """Возвращает текст ответа на входящее сообщение."""
    cmd = text.strip().lower()

    if cmd in ("/start", "начать", "start"):
        return (
            "Привет! Я бот на Vercel 🚀\n"
            "Напиши /help, чтобы увидеть список команд."
        )

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


def handle_event(event: dict) -> str:
    """Обрабатывает событие Callback API. Возвращает тело HTTP-ответа."""
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

    # На все остальные события ВК ждёт просто "ok"
    return "ok"


# ---------------------------------------------------------------------------
# HTTP handler (формат Vercel Python Runtime)
# ---------------------------------------------------------------------------

class handler(BaseHTTPRequestHandler):  # noqa: N801 — имя требуется Vercel
    def _send(self, status: int, body: str) -> None:
        payload = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):  # noqa: N802
        self._send(200, "VK bot is running")

    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b""

        try:
            event = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self._send(400, "bad request")
            return

        # Проверка секретного ключа, если он задан
        if VK_SECRET and event.get("secret") != VK_SECRET:
            self._send(403, "forbidden")
            return

        # Проверка ID группы, если он задан
        if VK_GROUP_ID and str(event.get("group_id")) != str(VK_GROUP_ID):
            self._send(403, "forbidden")
            return

        try:
            body = handle_event(event)
        except Exception as exc:  # noqa: BLE001
            # Отвечаем "ok", иначе ВК будет бесконечно повторять событие
            print(f"Error handling event: {exc}")
            body = "ok"

        self._send(200, body)

    def log_message(self, *args):  # тише в логах Vercel
        pass

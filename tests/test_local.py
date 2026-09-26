"""Локальная проверка Callback API без обращения к VK и OpenRouter."""
import json
import os
import sys
import threading
import urllib.request
from http.server import HTTPServer

os.environ.update(VK_CONFIRMATION="conf123", VK_SECRET="s3cret", VK_GROUP_ID="1")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "api"))
import index  # noqa: E402

sent = []
typing = []
index.send_message = lambda peer, text: sent.append((peer, text))
index.show_typing = lambda peer: typing.append(peer)
index.get_dialog_history = lambda peer, user: ([{"role": "user", "content": "привет"}], 1)
index.ask_openrouter = lambda history, turns: "Привет 🙂 Как день проходит?"

server = HTTPServer(("127.0.0.1", 0), index.handler)
port = server.server_address[1]
threading.Thread(target=server.serve_forever, daemon=True).start()


def post(payload):
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/", data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as response:
            return response.status, response.read().decode()
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode()


# Confirmation must succeed without checking the callback secret.
assert post({"type": "confirmation", "group_id": 1, "secret": "wrong"}) == (200, "conf123")
assert post({"type": "message_new", "group_id": 1, "secret": "wrong",
             "object": {"message": {"text": "/ping", "peer_id": 42, "from_id": 42}}})[0] == 403
assert post({"type": "message_new", "group_id": 1, "secret": "s3cret",
             "object": {"message": {"text": "/ping", "peer_id": 42, "from_id": 42}}}) == (200, "ok")
assert sent == [(42, "На связи 🙂")], sent
assert post({"type": "message_new", "group_id": 1, "secret": "s3cret",
             "object": {"message": {"text": "привет", "peer_id": 42, "from_id": 42}}}) == (200, "ok")
assert sent[-1] == (42, "Привет 🙂 Как день проходит?")
assert typing == [42]
assert post({"type": "message_reply", "group_id": 1, "secret": "s3cret", "object": {}}) == (200, "ok")
server.shutdown()
print("Все проверки пройдены ✅")

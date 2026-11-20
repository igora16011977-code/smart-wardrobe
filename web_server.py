"""
Backend API для вебверсії / Telegram Mini App проєкту «Шо одіти?».

Поточний етап: автономний тест модуля.
- Не змінює bot.py.
- Локальний запуск за замовчуванням: http://127.0.0.1:8765
- GET /health — перевірка працездатності без звернення до БД.
- GET /api/wardrobe — захищений список речей користувача.
- GET /api/photo/<id> — захищене отримання фото через Telegram Bot API.

Для інтеграції на Render модуль потрібно буде під'єднати до вже наявного
HTTP-сервера bot.py, а не запускати другий сервер на тому самому PORT.
"""

import hashlib
from io import BytesIO
import hmac
import json
import logging
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qsl, urlparse

import requests
from PIL import Image, UnidentifiedImageError

import config
import database


LOG = logging.getLogger("wardrobe_web")
TELEGRAM_API = "https://api.telegram.org"
TELEGRAM_FILE_API = "https://api.telegram.org/file"
DEFAULT_PORT = 8765
MAX_INIT_DATA_AGE = 24 * 60 * 60  # 24 години


def _json_bytes(payload):
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def _detect_image_content_type(data):
    """Визначає MIME-тип за сигнатурою байтів, а не лише HTTP-заголовком."""
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if data.startswith(b"BM"):
        return "image/bmp"
    if data.startswith((b"II*\x00", b"MM\x00*")):
        return "image/tiff"
    return None


def validate_telegram_init_data(init_data, bot_token):
    """
    Перевіряє підпис Telegram Mini App initData.
    Повертає словник параметрів або None, якщо підпис/час некоректні.
    """
    if not init_data or not bot_token:
        return None

    try:
        pairs = parse_qsl(init_data, keep_blank_values=True, strict_parsing=True)
        data = dict(pairs)
        received_hash = data.pop("hash", None)
        if not received_hash:
            return None

        data_check_string = "\n".join(
            f"{key}={value}" for key, value in sorted(data.items())
        )

        secret_key = hmac.new(
            key=b"WebAppData",
            msg=bot_token.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()

        calculated_hash = hmac.new(
            key=secret_key,
            msg=data_check_string.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(calculated_hash, received_hash):
            return None

        auth_date = int(data.get("auth_date", "0"))
        now = int(time.time())
        if auth_date <= 0 or auth_date > now + 60:
            return None
        if now - auth_date > MAX_INIT_DATA_AGE:
            return None

        user = json.loads(data.get("user", "{}"))
        if not isinstance(user, dict) or not user.get("id"):
            return None

        data["user"] = user
        return data
    except (ValueError, TypeError, json.JSONDecodeError):
        return None


def _allowed_origin():
    return (os.getenv("WEB_APP_URL") or "").strip().rstrip("/")


class WardrobeWebHandler(BaseHTTPRequestHandler):
    """HTTP handler для Mini App API."""

    server_version = "WardrobeWeb/0.1"

    def _cors_headers(self):
        origin = self.headers.get("Origin", "")
        allowed = _allowed_origin()
        if allowed and origin == allowed:
            self.send_header("Access-Control-Allow-Origin", allowed)
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
            self.send_header("Access-Control-Allow-Methods", "GET, PUT, DELETE, OPTIONS")
            self.send_header("Access-Control-Max-Age", "600")

    def _send_bytes(self, status, body, content_type="application/json; charset=utf-8"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self._cors_headers()
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _send_json(self, status, payload):
        self._send_bytes(status, _json_bytes(payload))

    def _get_authenticated_user(self):
        authorization = self.headers.get("Authorization", "")
        if not authorization.startswith("tma "):
            return None

        init_data = authorization[4:].strip()
        verified = validate_telegram_init_data(init_data, config.TELEGRAM_TOKEN)
        if not verified:
            return None

        return int(verified["user"]["id"])

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors_headers()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"

        # Зберігаємо стару поведінку кореневого URL для Render/UptimeRobot.
        if path in ("/", "/health"):
            self._send_bytes(200, b"OK", "text/plain; charset=utf-8")
            return

        if path == "/api/wardrobe":
            self._handle_wardrobe(parsed)
            return

        if path.startswith("/api/photo/"):
            self._handle_photo(path.rsplit("/", 1)[-1])
            return

        self._send_json(404, {"error": "not_found"})

    def do_PUT(self):
        parsed = urlparse(self.path)
        match = __import__("re").fullmatch(r"/api/wardrobe/(\d+)", parsed.path.rstrip("/"))
        if not match:
            self._send_json(404, {"error": "not_found"})
            return
        self._handle_update_item(int(match.group(1)))

    def do_DELETE(self):
        parsed = urlparse(self.path)
        match = __import__("re").fullmatch(r"/api/wardrobe/(\d+)", parsed.path.rstrip("/"))
        if not match:
            self._send_json(404, {"error": "not_found"})
            return
        self._handle_delete_item(int(match.group(1)))

    def do_HEAD(self):
        parsed = urlparse(self.path)
        if parsed.path.rstrip("/") in ("", "/health"):
            self._send_bytes(200, b"OK", "text/plain; charset=utf-8")
        else:
            self._send_json(404, {"error": "not_found"})

    def _handle_wardrobe(self, parsed):
        user_id = self._get_authenticated_user()
        if user_id is None:
            self._send_json(401, {"error": "unauthorized"})
            return

        query = dict(parse_qsl(parsed.query, keep_blank_values=True))
        category = (query.get("category") or "все").strip().casefold()
        allowed_categories = {"все", "верх", "низ", "взуття", "аксесуари"}
        if category not in allowed_categories:
            self._send_json(400, {"error": "invalid_category"})
            return

        try:
            rows = database.get_user_wardrobe_details(user_id, category)
            items = [
                {
                    "id": int(row[0]),
                    "title": row[1] or row[2] or "",
                    "description": row[2] or "",
                    "category": row[3] or "",
                    "color": row[4] or "",
                    "material": row[5] or "",
                    "style": row[6] or "",
                    "photo_url": f"/api/photo/{int(row[0])}",
                }
                for row in rows
            ]
            self._send_json(200, {"items": items, "count": len(items)})
        except Exception:
            LOG.exception("Помилка отримання гардероба")
            self._send_json(500, {"error": "server_error"})

    def _read_json_body(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 16_384:
                return None
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            return payload if isinstance(payload, dict) else None
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
            return None

    def _handle_update_item(self, item_id):
        user_id = self._get_authenticated_user()
        if user_id is None:
            self._send_json(401, {"error": "unauthorized"})
            return
        payload = self._read_json_body()
        if payload is None:
            self._send_json(400, {"error": "invalid_json"})
            return
        try:
            updated = database.update_clothing_details(
                item_id=item_id,
                user_id=user_id,
                title=payload.get("title", ""),
                description=payload.get("description", ""),
                category=payload.get("category", ""),
                color=payload.get("color", ""),
                material=payload.get("material", ""),
                style=payload.get("style", ""),
            )
            if not updated:
                self._send_json(404, {"error": "item_not_found"})
                return
            self._send_json(200, {"ok": True})
        except ValueError as exc:
            self._send_json(400, {"error": str(exc)})
        except Exception:
            LOG.exception("Помилка оновлення речі")
            self._send_json(500, {"error": "server_error"})

    def _handle_delete_item(self, item_id):
        user_id = self._get_authenticated_user()
        if user_id is None:
            self._send_json(401, {"error": "unauthorized"})
            return
        try:
            deleted = database.delete_clothing(item_id, user_id)
            if not deleted:
                self._send_json(404, {"error": "item_not_found"})
                return
            self._send_json(200, {"ok": True})
        except Exception:
            LOG.exception("Помилка видалення речі")
            self._send_json(500, {"error": "server_error"})

    def _handle_photo(self, item_id_text):
        user_id = self._get_authenticated_user()
        if user_id is None:
            self._send_json(401, {"error": "unauthorized"})
            return

        try:
            item_id = int(item_id_text)
            if item_id <= 0:
                raise ValueError
        except ValueError:
            self._send_json(400, {"error": "invalid_item_id"})
            return

        try:
            # get_user_wardrobe повертає тільки записи цього користувача.
            rows = database.get_user_wardrobe(user_id, "все")
            matching = next((row for row in rows if int(row[2]) == item_id), None)
            if matching is None:
                self._send_json(404, {"error": "photo_not_found"})
                return

            file_id = matching[0]
            api_response = requests.get(
                f"{TELEGRAM_API}/bot{config.TELEGRAM_TOKEN}/getFile",
                params={"file_id": file_id},
                timeout=20,
            )
            api_response.raise_for_status()
            result = api_response.json()
            if not result.get("ok") or not result.get("result", {}).get("file_path"):
                self._send_json(502, {"error": "telegram_file_unavailable"})
                return

            file_path = result["result"]["file_path"]
            photo_response = requests.get(
                f"{TELEGRAM_FILE_API}/bot{config.TELEGRAM_TOKEN}/{file_path}",
                timeout=30,
            )
            photo_response.raise_for_status()
            photo_bytes = photo_response.content
            header_type = (
                photo_response.headers.get("Content-Type", "")
                .split(";", 1)[0]
                .strip()
                .lower()
            )
            detected_type = _detect_image_content_type(photo_bytes)

            # Діагностика: фіксуємо метадані та сигнатуру, але не самі фото
            # і не Telegram file_id / токени.
            LOG.info(
                "Фото від Telegram: item_id=%s, status=%s, bytes=%s, "
                "header_type=%r, detected_type=%r, first_bytes_hex=%s",
                item_id,
                photo_response.status_code,
                len(photo_bytes),
                header_type,
                detected_type,
                photo_bytes[:16].hex(),
            )

            if not photo_bytes:
                LOG.error("Telegram повернув порожній файл для item_id=%s", item_id)
                self._send_json(502, {"error": "empty_photo_file"})
                return

            # Спочатку перевіряємо сигнатуру, а потім повністю декодуємо
            # зображення через Pillow. Це відрізняє справний JPEG від даних,
            # які лише починаються з JPEG-сигнатури.
            if not detected_type:
                LOG.error(
                    "Невідома сигнатура фото: item_id=%s, header_type=%r, "
                    "first_bytes_hex=%s",
                    item_id,
                    header_type,
                    photo_bytes[:32].hex(),
                )
                self._send_json(502, {"error": "invalid_photo_signature"})
                return

            try:
                with Image.open(BytesIO(photo_bytes)) as image:
                    image_format = image.format
                    image_size = image.size
                    image.verify()
                # verify() перевіряє структуру, але не декодує всі пікселі;
                # тому повторно відкриваємо файл і виконуємо повне завантаження.
                with Image.open(BytesIO(photo_bytes)) as image:
                    image.load()
                    image_format = image.format
                    image_size = image.size
            except (UnidentifiedImageError, OSError, ValueError) as exc:
                LOG.exception(
                    "Pillow не зміг декодувати фото: item_id=%s, "
                    "detected_type=%s, bytes=%s, error=%s",
                    item_id,
                    detected_type,
                    len(photo_bytes),
                    exc,
                )
                self._send_json(502, {"error": "image_decode_failed"})
                return

            LOG.info(
                "Фото успішно декодовано: item_id=%s, format=%s, size=%s, bytes=%s",
                item_id,
                image_format,
                image_size,
                len(photo_bytes),
            )
            self._send_bytes(200, photo_bytes, detected_type)
        except requests.RequestException:
            LOG.exception("Помилка отримання фото з Telegram")
            self._send_json(502, {"error": "photo_service_error"})
        except Exception:
            LOG.exception("Помилка обробки фото")
            self._send_json(500, {"error": "server_error"})

    def log_message(self, fmt, *args):
        # Не записуємо заголовок Authorization/initData до журналу.
        LOG.info("HTTP %s - %s", self.address_string(), fmt % args)


def run_local_test_server():
    """Запуск лише для локальної перевірки; не для паралельного запуску на Render."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    port = int(os.getenv("WEB_TEST_PORT", str(DEFAULT_PORT)))
    server = ThreadingHTTPServer(("127.0.0.1", port), WardrobeWebHandler)
    LOG.info("Локальний тестовий сервер: http://127.0.0.1:%s", port)
    LOG.info("Перевірка: http://127.0.0.1:%s/health", port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        LOG.info("Зупинка локального тестового сервера")
    finally:
        server.server_close()


if __name__ == "__main__":
    run_local_test_server()

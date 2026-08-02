"""
Сохранение загружаемых файлов (картинки для новостей/FAQ, дистрибутивы VPN-клиентов).

Файлы кладутся внутрь app/static/, поэтому раздаются nginx'ом напрямую —
никакой дополнительной настройки веб-сервера не требуется.
"""

import re
import uuid
from pathlib import Path

from fastapi import UploadFile

UPLOAD_DIR = Path("app/static/uploads")
DOWNLOAD_DIR = Path("app/static/downloads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_IMAGE_BYTES = 8 * 1024 * 1024        # 8 МБ на картинку
MAX_DOWNLOAD_BYTES = 250 * 1024 * 1024   # 250 МБ на файл дистрибутива — учитывай общий объём диска (15 ГБ)


class UploadTooLarge(Exception):
    pass


def _safe_ext(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    return ext if re.match(r"^\.[a-z0-9]{1,8}$", ext) else ""


def save_image(file: UploadFile | None) -> str | None:
    """Сохраняет картинку, возвращает путь относительно app/static/ (например 'uploads/xxx.png')."""
    if not file or not file.filename:
        return None

    ext = _safe_ext(file.filename)
    name = f"{uuid.uuid4().hex}{ext}"
    dest = UPLOAD_DIR / name

    data = file.file.read(MAX_IMAGE_BYTES + 1)
    if len(data) > MAX_IMAGE_BYTES:
        raise UploadTooLarge(f"Изображение слишком большое (максимум {MAX_IMAGE_BYTES // (1024*1024)} МБ)")

    dest.write_bytes(data)
    return f"uploads/{name}"


def save_download_file(file: UploadFile) -> tuple[str, str]:
    """Сохраняет файл дистрибутива потоково. Возвращает (stored_filename, original_filename)."""
    ext = _safe_ext(file.filename or "")
    stored_name = f"{uuid.uuid4().hex}{ext}"
    dest = DOWNLOAD_DIR / stored_name

    total = 0
    with dest.open("wb") as out:
        while True:
            chunk = file.file.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_DOWNLOAD_BYTES:
                out.close()
                dest.unlink(missing_ok=True)
                raise UploadTooLarge(f"Файл слишком большой (максимум {MAX_DOWNLOAD_BYTES // (1024*1024)} МБ)")
            out.write(chunk)

    return stored_name, (file.filename or stored_name)


def delete_file_quiet(relative_or_stored_path: str, base_dir: Path = DOWNLOAD_DIR) -> None:
    """Удаляет файл с диска, не поднимая исключение, если файла уже нет."""
    try:
        (base_dir / Path(relative_or_stored_path).name).unlink(missing_ok=True)
    except Exception:
        pass


def delete_upload_quiet(relative_path: str) -> None:
    """Удаляет картинку по пути вида 'uploads/xxx.png'."""
    if not relative_path:
        return
    try:
        (Path("app/static") / relative_path).unlink(missing_ok=True)
    except Exception:
        pass

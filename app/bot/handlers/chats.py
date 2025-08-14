# app/bot/handlers/user_chats.py
from __future__ import annotations
import io
import os
from dataclasses import dataclass
from typing import Literal, Optional, Tuple, cast

from PIL import Image, ImageOps, ImageEnhance, ImageFilter
from aiogram import Bot, F, Router
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    BufferedInputFile,
    InputMediaPhoto,
)

from app.db import stats as stats_db
from app.db import state as state_db

DEFAULT_DPI = int(os.getenv("DEFAULT_DPI", 300))
MAX_PREVIEW_WIDTH = int(os.getenv("MAX_PREVIEW_WIDTH", 1024))

# Размеры форматов A4 и A3 в мм
A_SERIES_MM = {
    "A4": (210, 297),
    "A3": (297, 420),
}

# Политика масштабирования: "fit" — вписывать с полями, "fill" — обрезать по краям
FIT_POLICY: Literal["fit", "fill"] = "fit"

# Совместимость с разными версиями Pillow: берём корректный фильтр ресемплинга
RESAMPLE = getattr(getattr(Image, "Resampling", Image), "LANCZOS")

# Диапазоны/варианты для отображения пользователю
BRIGHTNESS_MIN, BRIGHTNESS_MAX = 0.1, 3.0
CONTRAST_MIN,   CONTRAST_MAX   = 0.1, 3.0
GAMMA_MIN,      GAMMA_MAX      = 0.2, 5.0
SHARP_MIN,      SHARP_MAX      = 0.0, 5.0
BLUR_MIN,       BLUR_MAX       = 0.0, 2.0
DPI_CHOICES = [203, 300, 406, 600]
DITHER_CHOICES = ["fs", "ordered", "none"]
DENOISE_CHOICES = [0, 3, 5]

# ---------------------- Состояние пользователя ----------------------
@dataclass
class ProcState:
    brightness: float = 1.0   # Яркость (1.0 — исходная)
    contrast: float = 1.0     # Контраст (1.0 — исходный)
    gamma: float = 1.0        # Гамма (1.0 — исходная)
    sharpness: float = 2.0    # Резкость (1.0 — исходная)
    invert: bool = False      # Инверсия (ч/б меняются местами)
    dither: Literal["fs", "ordered", "none"] = "fs"  # Тип дизеринга
    dpi: int = DEFAULT_DPI    # Выходной DPI для финального изображения
    last_image_bytes: Optional[bytes] = None  # Оригинал, присланный пользователем
    denoise_size: int = 0       # 0 = выкл, 3 или 5 = медианный фильтр
    blur_radius: float = 0.0    # 0.0 = выкл; 0.3–1.5 = лёгкое сглаживание
    out_format: Literal["bmp", "png", "tiff", "jpg"] = "bmp"  # формат итогового файла

def build_caption(st: ProcState) -> str:
    """Текст под превью: текущие значения + их диапазоны/варианты."""
    lines = [
        "Предпросмотр. Подкрути и выбери размер.",
        "",
        f"Яркость:  {st.brightness:.2f}  (мин {BRIGHTNESS_MIN}, макс {BRIGHTNESS_MAX})",
        f"Контраст: {st.contrast:.2f}    (мин {CONTRAST_MIN},   макс {CONTRAST_MAX})",
        f"Гамма:    {st.gamma:.2f}       (мин {GAMMA_MIN},      макс {GAMMA_MAX})",
        f"Резкость: {st.sharpness:.2f}   (мин {SHARP_MIN},      макс {SHARP_MAX})",
        f"Шум-фильтр: {st.denoise_size}  (варианты: {', '.join(map(str, DENOISE_CHOICES))})",
        f"Сглаживание: {st.blur_radius:.2f} (мин {BLUR_MIN}, макс {BLUR_MAX})",
        f"Инверсия: {'вкл' if st.invert else 'выкл'}",
        f"Дизеринг: {st.dither}  (варианты: {', '.join(DITHER_CHOICES)})",
        f"DPI: {st.dpi}  (варианты: {', '.join(map(str, DPI_CHOICES))})",
        f"Формат: {st.out_format.upper()}  (варианты: BMP, PNG, TIFF, JPG)",
    ]
    return "\n".join(lines)

def _st_from_db(rec: dict) -> ProcState:
    return ProcState(
        brightness=rec["brightness"],
        contrast=rec["contrast"],
        gamma=rec["gamma"],
        sharpness=rec["sharpness"],
        invert=rec["invert"],
        dither=cast(Literal["fs","ordered","none"], rec["dither"]),
        dpi=rec["dpi"],
        last_image_bytes=rec["last_image_bytes"],
        denoise_size=rec["denoise_size"],
        blur_radius=rec["blur_radius"],
        out_format=cast(Literal["bmp","png","tiff"], (rec.get("out_format") or "bmp")),
    )

def _save_to_db(uid: int, st: ProcState) -> None:
    state_db.save_state(
        uid,
        brightness=st.brightness,
        contrast=st.contrast,
        gamma=st.gamma,
        sharpness=st.sharpness,
        invert=st.invert,
        dither=st.dither,
        dpi=st.dpi,
        denoise_size=st.denoise_size,
        blur_radius=st.blur_radius,
        last_image_bytes=st.last_image_bytes,
        out_format=st.out_format,
    )

# Роутер этого модуля
router = Router()

# ---------------------- Вспомогательные функции обработки ----------------------

def _ensure_rgb(img: Image.Image) -> Image.Image:
    """Гарантируем режим RGB для предсказуемых преобразований."""
    if img.mode in ("RGB", "RGBA"):
        return img.convert("RGB")
    return img.convert("RGB")

def adjust_image_base(img: Image.Image, st: ProcState) -> Image.Image:
    """Базовая обработка: перевод в серый → яркость/контраст → гамма → резкость → опциональная инверсия.
    Возвращает 8-бит изображение в режиме 'L'.
    """
    gray = ImageOps.grayscale(_ensure_rgb(img))  # режим L

    # Яркость / Контраст
    if abs(st.brightness - 1.0) > 1e-3:
        gray = ImageEnhance.Brightness(gray).enhance(st.brightness)
    if abs(st.contrast - 1.0) > 1e-3:
        gray = ImageEnhance.Contrast(gray).enhance(st.contrast)

    # Гамма-коррекция (на 8-бит L)
    if abs(st.gamma - 1.0) > 1e-3:
        inv_gamma = 1.0 / st.gamma
        lut = [int((i / 255.0) ** inv_gamma * 255 + 0.5) for i in range(256)]
        gray = gray.point(lut * 1)

    # Резкость
    if abs(st.sharpness - 1.0) > 1e-3:
        gray = ImageEnhance.Sharpness(gray).enhance(st.sharpness)

    # Удаление «песка» медианным фильтром
    if st.denoise_size in (3, 5):
        gray = gray.filter(ImageFilter.MedianFilter(size=st.denoise_size))

    # Мягкое сглаживание (убирает «лесенку», полезно до дизеринга)
    if st.blur_radius > 1e-3:
        gray = gray.filter(ImageFilter.GaussianBlur(radius=st.blur_radius))

    # Инверсия
    if st.invert:
        gray = ImageOps.invert(gray)

    return gray

# Упорядоченный (Bayer) дизеринг 8×8
_BAYER_8x8 = [
    [0, 48, 12, 60, 3, 51, 15, 63],
    [32, 16, 44, 28, 35, 19, 47, 31],
    [8, 56, 4, 52, 11, 59, 7, 55],
    [40, 24, 36, 20, 43, 27, 39, 23],
    [2, 50, 14, 62, 1, 49, 13, 61],
    [34, 18, 46, 30, 33, 17, 45, 29],
    [10, 58, 6, 54, 9, 57, 5, 53],
    [42, 26, 38, 22, 41, 25, 37, 21],
]

def ordered_dither(img_gray: Image.Image) -> Image.Image:
    """Вернуть 1-бит изображение через упорядоченный (Bayer) дизеринг 8×8."""
    w, h = img_gray.size
    src = img_gray
    dst = Image.new("1", (w, h))
    src_px = src.load()
    dst_px = dst.load()
    for y in range(h):
        for x in range(w):
            t = _BAYER_8x8[y % 8][x % 8]
            # Преобразуем порог из [0..63] в [0..255]
            threshold = (t + 0.5) * 4
            dst_px[x, y] = 255 if src_px[x, y] > threshold else 0
    return dst

def apply_dither(img_gray: Image.Image, kind: Literal["fs", "ordered", "none"]) -> Image.Image:
    """Применить выбранный тип дизеринга к серому изображению (режим 'L')."""
    if kind == "fs":
        # Стандартный Floyd–Steinberg из Pillow при convert('1')
        return img_gray.convert("1")
    elif kind == "ordered":
        return ordered_dither(img_gray)
    elif kind == "none":
        # Простой порог на 128
        return img_gray.point(lambda p: 255 if p >= 128 else 0, mode="1")
    else:
        return img_gray.convert("1")

def a_series_pixels(size: Literal["A4", "A3"], dpi: int) -> Tuple[int, int]:
    """Посчитать размеры в пикселях для заданного формата и DPI (портрет)."""
    mm_w, mm_h = A_SERIES_MM[size]
    inch_w, inch_h = mm_w / 25.4, mm_h / 25.4
    return int(round(inch_w * dpi)), int(round(inch_h * dpi))

def a_series_pixels_oriented(size: Literal["A4","A3"], dpi: int, landscape: bool) -> Tuple[int,int]:
    """Размеры листа с учётом ориентации. landscape=True — альбомная (поворот на 90°)."""
    w, h = a_series_pixels(size, dpi)
    return (h, w) if landscape else (w, h)

def fit_to_aspect(img: Image.Image, target_wh: Tuple[int, int], policy: Literal["fit", "fill"] = FIT_POLICY) -> Image.Image:
    """Подогнать под целевое соотношение сторон: вписать с полями (fit) или обрезать (fill)."""
    tw, th = target_wh
    target_ratio = tw / th
    w, h = img.size
    src_ratio = w / h

    if policy == "fill":
        # Обрезаем так, чтобы заполнить всё поле
        if src_ratio > target_ratio:
            # Слишком широкое изображение → обрезаем по ширине
            new_w = int(h * target_ratio)
            x0 = (w - new_w) // 2
            crop = img.crop((x0, 0, x0 + new_w, h))
            return crop.resize((tw, th), RESAMPLE)
        else:
            # Слишком высокое изображение → обрезаем по высоте
            new_h = int(w / target_ratio)
            y0 = (h - new_h) // 2
            crop = img.crop((0, y0, w, y0 + new_h))
            return crop.resize((tw, th), RESAMPLE)
    else:
        # Вписываем с белыми полями
        img_resized = img.copy()
        img_resized.thumbnail((tw, th), RESAMPLE)
        canvas = Image.new("L", (tw, th), 255)
        cx = (tw - img_resized.width) // 2
        cy = (th - img_resized.height) // 2
        canvas.paste(img_resized, (cx, cy))
        return canvas

def build_preview(img: Image.Image, st: ProcState) -> bytes:
    """Собрать предпросмотр для Telegram: уменьшаем, дизерим, сохраняем как JPEG-байты."""
    base = adjust_image_base(img, st)  # L
    # Масштаб предпросмотра под чат
    w = min(MAX_PREVIEW_WIDTH, base.width)
    h = int(round(base.height * (w / base.width)))
    base = base.resize((w, h), RESAMPLE)
    bw = apply_dither(base, st.dither)  # режим '1'
    # Для экономии трафика отправим JPEG (нужно вернуться в L перед сохранением)
    jpg = ImageOps.grayscale(bw.convert("L"))
    bio = io.BytesIO()
    jpg.save(bio, format="JPEG", quality=90)
    return bio.getvalue()

def build_final(img: Image.Image, st: ProcState, size: Literal["A4", "A3"]) -> Tuple[bytes, str]:
    """Собрать финальный 1-бит файл под выбранный лист и DPI.
    ВАЖНО: всегда 'fill' (обрезка), авто-альбомная ориентация для горизонтальных фото.
    """
    base = adjust_image_base(img, st)  # L
    # если фото горизонтальное — используем альбомную ориентацию листа
    landscape = base.width > base.height
    target_wh = a_series_pixels_oriented(size, st.dpi, landscape)
    # финал всегда с обрезанием (fill), без растяжения
    fitted = fit_to_aspect(base, target_wh, "fill")  # L
    bw = apply_dither(fitted, st.dither)  # 1-бит

    bio = io.BytesIO()
    fmt = st.out_format.lower()

    if fmt == "jpg":
        out = ImageOps.grayscale(bw.convert("L"))  # JPEG не поддерживает 1-бит
        out.save(bio, format="JPEG", quality=95, optimize=True, dpi=(st.dpi, st.dpi))
        filename = f"pyro_{size}_{st.dpi}dpi.jpg"
    else:
        pil_fmt = "BMP" if fmt == "bmp" else ("PNG" if fmt == "png" else "TIFF")
        # Сохраняем 1-битный bw и тоже проставляем DPI
        bw.save(bio, format=pil_fmt, dpi=(st.dpi, st.dpi))
        filename = f"pyro_{size}_{st.dpi}dpi.{('tiff' if fmt=='tiff' else fmt)}"

    return bio.getvalue(), filename

def load_image_from_bytes(data: bytes) -> Image.Image:
    """Открыть изображение из bytes в режиме RGB."""
    return Image.open(io.BytesIO(data)).convert("RGB")

# ---------------------- Клавиатура управления ----------------------

def kb_controls(st: ProcState) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()

    # --- все кнопки КРОМЕ размеров ---
    b.button(text="Темнее",   callback_data="adj:brightness:-0.3")
    b.button(text="Светлее",  callback_data="adj:brightness:+0.3")
    b.button(text="Контраст↑", callback_data="adj:contrast:+0.3")
    b.button(text="Контраст↓", callback_data="adj:contrast:-0.3")
    b.button(text="Гамма↑",   callback_data="adj:gamma:+0.5")
    b.button(text="Гамма↓",   callback_data="adj:gamma:-0.5")
    b.button(text="Резкость↑", callback_data="adj:sharpness:+0.5")
    b.button(text="Резкость↓", callback_data="adj:sharpness:-0.5")
    b.button(text="Сглажив.↑", callback_data="adj:blur:+0.2")
    b.button(text="Сглажив.↓", callback_data="adj:blur:-0.2")
    b.button(text=("Инверт: Вкл" if not st.invert else "Инверт: Выкл"), callback_data="toggle:invert")
    b.button(text=f"Дизер: {st.dither.upper()}", callback_data="cycle:dither")
    b.button(text=f"DPI: {st.dpi}", callback_data="cycle:dpi")
    denoise_label = f"Шум: {st.denoise_size or '0'}"
    b.button(text=denoise_label, callback_data="cycle:denoise")
    b.button(text=f"Формат: {st.out_format.upper()}", callback_data="cycle:outfmt")
    b.button(text="Сброс", callback_data="reset")

    # Разложим все выше по 2 в ряд
    b.adjust(2)

    # --- последняя строка: A4 и A3 всегда рядом ---
    b.row(
        InlineKeyboardButton(text="A4", callback_data="size:A4"),
        InlineKeyboardButton(text="A3", callback_data="size:A3"),
        width=2
    )

    return b.as_markup()

# ---------------------- Хендлеры ----------------------

@router.message(CommandStart())
async def on_start(m: Message):
    """Приветственное сообщение и инициализация состояния пользователя."""
    state_db.ensure_user(m.from_user.id)
    await m.answer(
        "Привет! Пришли фото (как фото или как документ). Я подготовлю Ч/Б предпросмотр для пиропечати. "
        "После — подкрути параметры, выбери формат файла (BMP/PNG/TIFF) и размер A4/A3. "
        "Финал: 1-бит без растяжения, с обрезанием под лист и автоориентацией."
    )

@router.message(Command("help"))
async def on_help(m: Message):
    """Краткая справка по кнопкам и процессу."""
    await m.answer(
        "Отправь фото. Кнопками регулируй яркость/контраст/гамму/резкость, можно инвертировать, сменить дизеринг и DPI. "
        "Выбери формат (BMP/PNG/TIFF) и затем A4 или A3 — пришлю 1-бит файл. "
        "Финальный кадр заполняет лист (обрезка), ориентация подстраивается под фото."
    )

async def _handle_new_image(m: Message, file_id: str):
    """Скачать файл по file_id, сохранить в состояние и отправить предпросмотр с клавиатурой."""
    uid = m.from_user.id
    bot: Bot = m.bot
    f = await bot.get_file(file_id)
    bio = io.BytesIO()
    await bot.download_file(f.file_path, bio)
    # сохраняем оригинал сразу в БД
    state_db.update_fields(uid, last_image_bytes=bio.getvalue())
    # читаем состояние из БД (со всеми полями)
    st = _st_from_db(state_db.get_state(uid))
    img = load_image_from_bytes(st.last_image_bytes)
    preview_bytes = build_preview(img, st)
    await m.answer_photo(
        BufferedInputFile(preview_bytes, filename="preview.jpg"),
        caption=build_caption(st),
        reply_markup=kb_controls(st),
    )

@router.message(F.photo)
async def on_photo(m: Message):
    """Обработчик присланной фотографии (берём самый большой размер)."""
    await _handle_new_image(m, m.photo[-1].file_id)

@router.message(F.document)
async def on_document(m: Message):
    """Обработчик присланного документа-изображения (PNG/JPG/BMP)."""
    doc = m.document
    if not doc:
        return
    if (doc.mime_type or "").lower() in {"image/png", "image/jpeg", "image/bmp"} or (doc.file_name or "").lower().endswith((".png", ".jpg", ".jpeg", ".bmp")):
        await _handle_new_image(m, doc.file_id)
    else:
        await m.reply("Пришли изображение (PNG/JPG/BMP), пожалуйста.")

@router.callback_query(F.data.startswith("adj:"))
async def on_adjust(cb: CallbackQuery):
    """Кнопки изменения параметров: яркость/контраст/гамма/резкость."""
    uid = cb.from_user.id
    rec = state_db.get_state(uid)
    if not rec.get("last_image_bytes"):
        await cb.answer("Сначала пришли фото", show_alert=True)
        return
    st = _st_from_db(rec)
    _, name, delta = cb.data.split(":")
    val = float(delta)
    if name == "brightness":
        st.brightness = round(max(0.1, min(3.0, st.brightness + val)), 2)
    elif name == "contrast":
        st.contrast = round(max(0.1, min(3.0, st.contrast + val)), 2)
    elif name == "gamma":
        st.gamma = round(max(0.2, min(5.0, st.gamma + val)), 2)
    elif name == "sharpness":
        st.sharpness = round(max(0.0, min(5.0, st.sharpness + val)), 2)
    elif name == "blur":
        st.blur_radius = round(max(0.0, min(2.0, st.blur_radius + val)), 2)

    stats_db.record_setting_change(uid)
    _save_to_db(uid, st)
    img = load_image_from_bytes(st.last_image_bytes)
    preview_bytes = build_preview(img, st)
    await cb.message.edit_media(
        media=InputMediaPhoto(
            media=BufferedInputFile(preview_bytes, filename="preview.jpg"),
            caption=build_caption(st),
        ),
        reply_markup=kb_controls(st),
    )
    await cb.answer("Обновлено")

@router.callback_query(F.data == "cycle:denoise")
async def on_cycle_denoise(cb: CallbackQuery):
    uid = cb.from_user.id
    rec = state_db.get_state(uid)
    if not rec.get("last_image_bytes"):
        await cb.answer("Сначала пришли фото", show_alert=True)
        return
    st = _st_from_db(rec)
    # Цикл: 0 → 3 → 5 → 0
    options = [0, 3, 5]
    idx = options.index(st.denoise_size) if st.denoise_size in options else 0
    st.denoise_size = options[(idx + 1) % len(options)]
    _save_to_db(uid, st)
    img = load_image_from_bytes(st.last_image_bytes)
    preview_bytes = build_preview(img, st)
    stats_db.record_setting_change(cb.from_user.id)
    await cb.message.edit_media(
        media=InputMediaPhoto(
            media=BufferedInputFile(preview_bytes, filename="preview.jpg"),
            caption=build_caption(st),
        ),
        reply_markup=kb_controls(st),
    )
    await cb.answer(f"Шум: {st.denoise_size}")

@router.callback_query(F.data == "toggle:invert")
async def on_toggle_invert(cb: CallbackQuery):
    """Переключение инверсии цветов."""
    uid = cb.from_user.id
    rec = state_db.get_state(uid)
    if not rec.get("last_image_bytes"):
        await cb.answer("Сначала пришли фото", show_alert=True)
        return
    st = _st_from_db(rec)
    st.invert = not st.invert
    _save_to_db(uid, st)
    img = load_image_from_bytes(st.last_image_bytes)
    preview_bytes = build_preview(img, st)
    stats_db.record_setting_change(cb.from_user.id)
    await cb.message.edit_media(
        media=InputMediaPhoto(
            media=BufferedInputFile(preview_bytes, filename="preview.jpg"),
            caption=build_caption(st),
        ),
        reply_markup=kb_controls(st),
    )
    await cb.answer("Инверсия переключена")

@router.callback_query(F.data == "cycle:dither")
async def on_cycle_dither(cb: CallbackQuery):
    """Циклическая смена типа дизеринга: fs → ordered → none → ..."""
    uid = cb.from_user.id
    rec = state_db.get_state(uid)
    if not rec.get("last_image_bytes"):
        await cb.answer("Сначала пришли фото", show_alert=True)
        return
    st = _st_from_db(rec)
    order = ["fs", "ordered", "none"]
    st.dither = cast(Literal["fs", "ordered", "none"], order[(order.index(st.dither) + 1) % len(order)])
    _save_to_db(uid, st)
    img = load_image_from_bytes(st.last_image_bytes)
    preview_bytes = build_preview(img, st)
    stats_db.record_setting_change(cb.from_user.id)
    await cb.message.edit_media(
        media=InputMediaPhoto(
            media=BufferedInputFile(preview_bytes, filename="preview.jpg"),
            caption=build_caption(st),
        ),
        reply_markup=kb_controls(st),
    )
    await cb.answer(f"Дизеринг: {st.dither}")

@router.callback_query(F.data == "cycle:dpi")
async def on_cycle_dpi(cb: CallbackQuery):
    """Циклическая смена DPI из набора типичных значений."""
    uid = cb.from_user.id
    rec = state_db.get_state(uid)
    if not rec.get("last_image_bytes"):
        await cb.answer("Сначала пришли фото", show_alert=True)
        return
    st = _st_from_db(rec)
    choices = [203, 300, 406, 600]
    st.dpi = choices[(choices.index(st.dpi) + 1) % len(choices)] if st.dpi in choices else DEFAULT_DPI
    if st.last_image_bytes:
        _save_to_db(uid, st)
        img = load_image_from_bytes(st.last_image_bytes)
        preview_bytes = build_preview(img, st)
        await cb.message.edit_media(
            media=InputMediaPhoto(media=BufferedInputFile(preview_bytes, filename="preview.jpg")),
            reply_markup=kb_controls(st),
        )
    else:
        await cb.message.edit_reply_markup(reply_markup=kb_controls(st))
    await cb.answer(f"DPI: {st.dpi}")

@router.callback_query(F.data == "cycle:outfmt")
async def on_cycle_outfmt(cb: CallbackQuery):
    """Цикл формата итогового файла: BMP → PNG → TIFF → ... (разрешено менять и без фото)."""
    uid = cb.from_user.id
    rec = state_db.get_state(uid)
    current = (rec.get("out_format") or "bmp").lower()
    order = ["bmp", "png", "tiff", "jpg"]
    try:
        new_fmt = order[(order.index(current) + 1) % len(order)]
    except ValueError:
        new_fmt = "bmp"
    state_db.update_fields(uid, out_format=new_fmt)
    # обновим UI
    new_st = _st_from_db(state_db.get_state(uid))
    if rec.get("last_image_bytes"):
        img = load_image_from_bytes(rec["last_image_bytes"])
        preview_bytes = build_preview(img, new_st)
        await cb.message.edit_media(
            media=InputMediaPhoto(
                media=BufferedInputFile(preview_bytes, filename="preview.jpg"),
                caption=build_caption(new_st),
            ),
            reply_markup=kb_controls(new_st),
        )
    else:
        await cb.message.edit_reply_markup(reply_markup=kb_controls(new_st))
    await cb.answer(f"Формат: {new_fmt.upper()}")

@router.callback_query(F.data == "reset")
async def on_reset(cb: CallbackQuery):
    """Сброс параметров к значениям по умолчанию (фото сохраняем, если было). Формат сохраняем."""
    uid = cb.from_user.id
    rec = state_db.get_state(uid)
    new_st = ProcState()
    new_st.last_image_bytes = rec.get("last_image_bytes")
    # сохраняем выбранный пользователем формат при сбросе
    new_st.out_format = cast(Literal["bmp","png","tiff"], (rec.get("out_format") or "bmp"))
    _save_to_db(uid, new_st)
    if not new_st.last_image_bytes:
        await cb.message.edit_reply_markup(reply_markup=kb_controls(new_st))
        await cb.answer("Сброшено")
        return
    img = load_image_from_bytes(new_st.last_image_bytes)
    preview_bytes = build_preview(img, new_st)
    stats_db.record_setting_change(uid)
    await cb.message.edit_media(
        media=InputMediaPhoto(media=BufferedInputFile(preview_bytes, filename="preview.jpg")),
        reply_markup=kb_controls(new_st),
    )
    await cb.answer("Сброшено")

@router.callback_query(F.data.startswith("size:"))
async def on_size(cb: CallbackQuery):
    uid = cb.from_user.id
    rec = state_db.get_state(uid)
    if not rec.get("last_image_bytes"):
        await cb.answer("Сначала пришли фото", show_alert=True)
        return
    st = _st_from_db(rec)
    size = cb.data.split(":")[1]
    if size not in ("A4", "A3"):
        await cb.answer("Неизвестный размер", show_alert=True)
        return
    img = load_image_from_bytes(st.last_image_bytes)
    data, fname = build_final(img, st, cast(Literal["A4","A3"], size))
    stats_db.record_output(uid)
    await cb.message.reply_document(
        document=BufferedInputFile(data, filename=fname),
        caption=f"Финал: {size}, {st.dpi} DPI, {st.dither}, {st.out_format.upper()}",
    )
    await cb.answer("Готово")

@router.message(Command("stats"))
async def on_my_stats(m: Message):
    s = stats_db.get_user_stats(m.from_user.id)
    await m.answer(
        f"Твоя статистика:\n"
        f"— финальных файлов: {s['outputs_count']}\n"
        f"— изменений настроек: {s['settings_changes_count']}\n"
        f"— первый раз: {s['first_seen']}\n"
        f"— обновлено: {s['last_seen']}"
    )

@router.message(Command("status"))
async def on_status(m: Message):
    rec = state_db.get_state(m.from_user.id)
    st = _st_from_db(rec)
    await m.answer(build_caption(st))

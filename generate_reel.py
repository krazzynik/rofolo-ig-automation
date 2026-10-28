"""Generate readable, paced Instagram reels with a final follow card."""
import json
import os
import random
import re
import time

import numpy as np
from PIL import Image, ImageDraw, ImageFont
try:
    from moviepy.editor import VideoClip
except ImportError:
    from moviepy import VideoClip
from google import genai
from google.genai import types

from content_state import allocate_next, persist_allocated
from content_style import CONTENT_BUCKETS, build_prompt, choose_bucket

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BRANDING_DIR = os.path.join(BASE_DIR, "branding")
REELS_DIR = os.path.join(BASE_DIR, "reels")
CONTENT_DIR = os.path.join(BASE_DIR, "content")
REELS_QUEUE_FILE = os.path.join(BASE_DIR, "scheduled_reels_queue.json")
STATE_FILE = os.path.join(BASE_DIR, "content_state.json")
BACKGROUND_PATH = os.path.join(BASE_DIR, os.environ.get("ROFOLO_BACKGROUND", "branding/background.jpg"))
FONT_PATH = os.path.join(BRANDING_DIR, "font.ttf")
TOPICS = CONTENT_BUCKETS
MODELS_TO_TRY = ["gemini-3.5-flash", "gemini-3.6-flash", "gemini-3.4-flash"]
os.makedirs(REELS_DIR, exist_ok=True)
os.makedirs(CONTENT_DIR, exist_ok=True)

# A card stays completely still long enough to read; no character-by-character crawl.
SECONDS_PER_CARD = float(os.environ.get("ROFOLO_SECONDS_PER_CARD", "4.0"))
CTA_SECONDS = float(os.environ.get("ROFOLO_CTA_SECONDS", "2.5"))
FOLLOW_TEXT = os.environ.get("ROFOLO_FOLLOW_TEXT", "Follow @rofolo for more ✨")


def get_next_reel_id():
    number = allocate_next("reel", state_path=STATE_FILE, queue_path=REELS_QUEUE_FILE,
                           artifact_directories=(REELS_DIR, CONTENT_DIR))
    return f"reel_{number:03d}"


def generate_hinglish_quote_and_caption():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY is missing!")
        return None, None
    bucket = choose_bucket(random)
    client = genai.Client(api_key=api_key)
    for model_name in MODELS_TO_TRY:
        try:
            response = client.models.generate_content(
                model=model_name, contents=build_prompt(bucket, reel=True),
                config=types.GenerateContentConfig(response_mime_type="application/json", temperature=1.0))
            data = json.loads(response.text.strip())
            return data.get("quote"), data.get("caption")
        except Exception:
            time.sleep(3)
    return None, None


def split_into_cards(quote, max_words=14, max_cards=5):
    """Prefer intentional model line breaks, then split long lines at sentence boundaries."""
    lines = [line.strip(" -•\t") for line in str(quote).splitlines() if line.strip()]
    if len(lines) <= 1:
        lines = [part.strip() for part in re.split(r"(?<=[.!?])\s+", str(quote)) if part.strip()]
    cards = []
    for line in lines:
        words = line.split()
        for offset in range(0, len(words), max_words):
            cards.append(" ".join(words[offset:offset + max_words]))
    if len(cards) > max_cards:
        # Keep the entire quote rather than silently losing its ending.
        cards = cards[:max_cards - 1] + [" ".join(cards[max_cards - 1:])]
    return cards or [str(quote).strip()]


def wrap_to_width(text, draw, font, max_width):
    """Measure actual glyph widths, so long Hinglish words do not overflow the frame."""
    rows = []
    for paragraph in text.splitlines():
        line = ""
        for word in paragraph.split():
            candidate = f"{line} {word}".strip()
            if line and draw.textbbox((0, 0), candidate, font=font)[2] > max_width:
                rows.append(line)
                line = word
            else:
                line = candidate
        rows.append(line)
    return "\n".join(rows)


def render_card(background, text, *, cta=False):
    image = background.copy()
    width, height = image.size
    draw = ImageDraw.Draw(image, "RGBA")
    # Dark overlay keeps white text readable on both bright and detailed photography.
    draw.rectangle((0, 0, width, height), fill=(0, 0, 0, 115))
    max_width = int(width * 0.83)
    for scale in (0.066, 0.060, 0.054, 0.048, 0.042, 0.036):
        try:
            font = ImageFont.truetype(FONT_PATH, max(20, int(width * scale)))
        except OSError:
            font = ImageFont.load_default()
        wrapped = wrap_to_width(text, draw, font, max_width)
        spacing = max(8, int(width * 0.014))
        bounds = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=spacing,
                                         align="center", stroke_width=2)
        text_height = bounds[3] - bounds[1]
        if text_height <= height * 0.65:
            break
    x = width / 2
    y = (height - text_height) / 2 - bounds[1]
    draw.multiline_text((x, y), wrapped, font=font, anchor="ma", align="center",
                        spacing=spacing, fill=(255, 255, 255, 255),
                        stroke_width=2, stroke_fill=(0, 0, 0, 210))
    if cta:
        draw.rectangle((int(width * .30), int(height * .69),
                        int(width * .70), int(height * .695)), fill=(255, 205, 85, 255))
    return np.asarray(image.convert("RGB"))


def create_typing_reel():
    reel_id = get_next_reel_id()
    quote_text, caption_text = generate_hinglish_quote_and_caption()
    if not quote_text or not caption_text or not os.path.exists(BACKGROUND_PATH):
        return False
    background = Image.open(BACKGROUND_PATH).convert("RGB")
    cards = split_into_cards(quote_text)
    frames = [render_card(background, card) for card in cards]
    frames.append(render_card(background, FOLLOW_TEXT, cta=True))
    card_seconds = max(2.0, SECONDS_PER_CARD)
    cta_seconds = max(1.5, CTA_SECONDS)
    total_duration = len(cards) * card_seconds + cta_seconds

    def make_frame(t):
        index = min(int(t / card_seconds), len(cards))
        return frames[index]

    video_rel_path = f"reels/{reel_id}.mp4"
    clip = VideoClip(make_frame, duration=total_duration)
    try:
        clip.write_videofile(os.path.join(BASE_DIR, video_rel_path), fps=24,
                             codec="libx264", audio=False, preset="fast")
    finally:
        clip.close()

    with open(os.path.join(CONTENT_DIR, f"{reel_id}.txt"), "w", encoding="utf-8") as file:
        file.write(f"[CAPTION]\n{caption_text}")
    try:
        with open(REELS_QUEUE_FILE, "r", encoding="utf-8") as file:
            queue = json.load(file)
    except (OSError, json.JSONDecodeError):
        queue = []
    queue.append({"id": reel_id, "video_path": video_rel_path, "caption": caption_text,
                  "status": "pending", "created_at": time.strftime("%Y-%m-%d %H:%M:%S")})
    with open(REELS_QUEUE_FILE, "w", encoding="utf-8") as file:
        json.dump(queue, file, indent=2, ensure_ascii=False)
    persist_allocated("reel", int(reel_id.split("_")[1]), state_path=STATE_FILE)
    return True


if __name__ == "__main__":
    create_typing_reel()

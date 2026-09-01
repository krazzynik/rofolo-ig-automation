import json
import os
import random
import re
import textwrap
import time

import numpy as np
from PIL import Image, ImageDraw, ImageFont
try:
    from moviepy.editor import VideoClip
except ImportError:
    from moviepy import VideoClip
from google import genai
from google.genai import types

from content_style import CONTENT_BUCKETS, build_prompt, choose_bucket

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BRANDING_DIR = os.path.join(BASE_DIR, "branding")
REELS_DIR = os.path.join(BASE_DIR, "reels")
CONTENT_DIR = os.path.join(BASE_DIR, "content")
REELS_QUEUE_FILE = os.path.join(BASE_DIR, "scheduled_reels_queue.json")
BACKGROUND_PATH = os.path.join(BRANDING_DIR, "background.jpg")
FONT_PATH = os.path.join(BRANDING_DIR, "font.ttf")
TOPICS = CONTENT_BUCKETS
MODELS_TO_TRY = ["gemini-3.5-flash", "gemini-3.6-flash", "gemini-3.4-flash"]
os.makedirs(REELS_DIR, exist_ok=True)
os.makedirs(CONTENT_DIR, exist_ok=True)


def get_next_reel_id():
    numbers = [int(match.group(1)) for name in os.listdir(REELS_DIR) if (match := re.match(r"reel_(\d+)\.mp4", name, re.I))]
    return f"reel_{max(numbers) + 1 if numbers else 1:03d}"


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
                config=types.GenerateContentConfig(response_mime_type="application/json", temperature=1.0),
            )
            data = json.loads(response.text.strip())
            return data.get("quote"), data.get("caption")
        except Exception:
            time.sleep(3)
    return None, None


def create_typing_reel():
    reel_id = get_next_reel_id()
    quote_text, caption_text = generate_hinglish_quote_and_caption()
    if not quote_text or not caption_text or not os.path.exists(BACKGROUND_PATH):
        return False
    background = Image.open(BACKGROUND_PATH).convert("RGB")
    font_size = int(background.width * 0.055)
    try: font = ImageFont.truetype(FONT_PATH, font_size)
    except Exception: font = ImageFont.load_default()
    full_text = "\n".join(textwrap.wrap(quote_text, width=22))
    bbox = ImageDraw.Draw(background).multiline_textbbox((0, 0), full_text, font=font)
    start_x = (background.width - (bbox[2] - bbox[0])) / 2
    start_y = background.height - (bbox[3] - bbox[1]) - int(background.height * 0.12)
    typing_duration, hold_duration = 4.0, 3.5

    def make_frame(t):
        visible = len(quote_text) if t >= typing_duration else int(len(quote_text) * t / typing_duration)
        image = background.copy()
        ImageDraw.Draw(image).multiline_text((start_x, start_y), "\n".join(textwrap.wrap(quote_text[:visible], width=22)), fill=(255, 255, 255), font=font)
        return np.array(image)

    video_rel_path = f"reels/{reel_id}.mp4"
    VideoClip(make_frame, duration=typing_duration + hold_duration).write_videofile(os.path.join(BASE_DIR, video_rel_path), fps=24, codec="libx264", audio=False, preset="fast")
    with open(os.path.join(CONTENT_DIR, f"{reel_id}.txt"), "w", encoding="utf-8") as file: file.write(f"[CAPTION]\n{caption_text}")
    queue = []
    if os.path.exists(REELS_QUEUE_FILE):
        try:
            with open(REELS_QUEUE_FILE, "r", encoding="utf-8") as file: queue = json.load(file)
        except json.JSONDecodeError: pass
    queue.append({"id": reel_id, "video_path": video_rel_path, "caption": caption_text, "status": "pending", "created_at": time.strftime("%Y-%m-%d %H:%M:%S")})
    with open(REELS_QUEUE_FILE, "w", encoding="utf-8") as file: json.dump(queue, file, indent=2, ensure_ascii=False)
    return True


if __name__ == "__main__":
    create_typing_reel()

import json
import os
import random
import re
import textwrap
import time
from google import genai
from google.genai import types
from PIL import Image, ImageDraw, ImageFont
from content_state import allocate_next, persist_allocated
from content_style import CONTENT_BUCKETS, build_prompt, choose_bucket

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BRANDING_DIR = os.path.join(BASE_DIR, "branding"); IMAGES_DIR = os.path.join(BASE_DIR, "images"); CONTENT_DIR = os.path.join(BASE_DIR, "content")
QUEUE_FILE = os.path.join(BASE_DIR, "scheduled_queue.json"); STATE_FILE = os.path.join(BASE_DIR, "content_state.json")
BACKGROUND_PATH = os.path.join(BRANDING_DIR, "background.jpg"); FONT_PATH = os.path.join(BRANDING_DIR, "font.ttf")
TOPICS = CONTENT_BUCKETS; MODELS_TO_TRY = ["gemini-3.5-flash", "gemini-3.6-flash", "gemini-3.4-flash"]
os.makedirs(IMAGES_DIR, exist_ok=True); os.makedirs(CONTENT_DIR, exist_ok=True)


def get_next_post_id():
    number = allocate_next("post", state_path=STATE_FILE, queue_path=QUEUE_FILE, artifact_directories=(IMAGES_DIR, CONTENT_DIR))
    return f"post_{number:02d}"


def generate_hinglish_quote_and_caption():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key: print("ERROR: GEMINI_API_KEY environment variable is missing or empty!"); return None, None
    bucket = choose_bucket(random); print(f"Today's Topic Focus: {bucket}"); client = genai.Client(api_key=api_key); prompt = build_prompt(bucket)
    for model_name in MODELS_TO_TRY:
        for attempt in range(1, 4):
            try:
                response = client.models.generate_content(model=model_name, contents=prompt, config=types.GenerateContentConfig(response_mime_type="application/json", temperature=1.0))
                data = json.loads(response.text.strip()); return data.get("quote"), data.get("caption")
            except Exception as exc:
                if any(code in str(exc) for code in ("503", "UNAVAILABLE", "429")) and attempt < 3: time.sleep(5)
                else: break
    print("All content-generation models failed."); return None, None


def create_post():
    post_id = get_next_post_id(); quote_text, caption_text = generate_hinglish_quote_and_caption()
    if not quote_text or not caption_text or not os.path.exists(BACKGROUND_PATH) or not os.path.exists(FONT_PATH): return False
    image = Image.open(BACKGROUND_PATH).convert("RGB"); draw = ImageDraw.Draw(image); font_size = int(image.width * 0.055)
    try: font = ImageFont.truetype(FONT_PATH, font_size)
    except Exception: font = ImageFont.load_default()
    text = "\n".join(textwrap.wrap(quote_text, width=22)); bbox = draw.multiline_textbbox((0, 0), text, font=font, align="center")
    x = (image.width - (bbox[2] - bbox[0])) / 2; y = image.height - (bbox[3] - bbox[1]) - int(image.height * 0.12)
    draw.multiline_text((x, y), text, fill=(255, 255, 255), font=font, align="center")
    image.save(os.path.join(IMAGES_DIR, f"{post_id}.jpg"), "JPEG", quality=95)
    with open(os.path.join(CONTENT_DIR, f"{post_id}.txt"), "w", encoding="utf-8") as file: file.write(f"[CAPTION]\n{caption_text}\n\n[USER_TAGS]")
    try:
        with open(QUEUE_FILE, "r", encoding="utf-8") as file: queue = json.load(file)
    except (OSError, json.JSONDecodeError): queue = []
    queue.append({"id": post_id, "status": "pending"})
    with open(QUEUE_FILE, "w", encoding="utf-8") as file: json.dump(queue, file, indent=2)
    persist_allocated("post", int(post_id.split("_")[1]), state_path=STATE_FILE)
    return True


if __name__ == "__main__": create_post()

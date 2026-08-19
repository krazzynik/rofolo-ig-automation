import os
import re
import json
import random
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

# ==========================================
# DIRECTORY & FILE PATHS
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BRANDING_DIR = os.path.join(BASE_DIR, "branding")
REELS_DIR = os.path.join(BASE_DIR, "reels")
CONTENT_DIR = os.path.join(BASE_DIR, "content")
REELS_QUEUE_FILE = os.path.join(BASE_DIR, "scheduled_reels_queue.json")

BACKGROUND_PATH = os.path.join(BRANDING_DIR, "background.jpg")
FONT_PATH = os.path.join(BRANDING_DIR, "font.ttf")

os.makedirs(REELS_DIR, exist_ok=True)
os.makedirs(CONTENT_DIR, exist_ok=True)

TOPICS = [
    "being called rude just for speaking facts and not sugarcoating",
    "taking no crap from toxic relatives, in-laws, or nosy neighbours",
    "prioritizing peace, sleep, and self-respect over social validation",
    "giving unfiltered reality checks to hypocrites and drama queens",
    "living life on own terms while people call it 'attitude problem'",
    "workplace drama and dealing with people who talk behind your back"
]

MODELS_TO_TRY = ['gemini-3.5-flash', 'gemini-3.6-flash', 'gemini-3.4-flash']

# ==========================================
# INCREMENTAL REEL ID (e.g. reel_001)
# ==========================================
def get_next_reel_id():
    existing_files = os.listdir(REELS_DIR) if os.path.exists(REELS_DIR) else []
    numbers = []
    for filename in existing_files:
        match = re.match(r"reel_(\d+)\.mp4", filename, re.IGNORECASE)
        if match:
            numbers.append(int(match.group(1)))
    next_num = max(numbers) + 1 if numbers else 1
    return f"reel_{next_num:03d}"

# ==========================================
# GEMINI AI CONTENT GENERATOR
# ==========================================
def generate_hinglish_quote_and_caption():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("❌ ERROR: GEMINI_API_KEY is missing!")
        return None, None

    selected_topic = random.choice(TOPICS)
    client = genai.Client(api_key=api_key)

    prompt = f"""
    Write viral content for an Instagram Reel persona.
    TODAY'S SUB-TOPIC: {selected_topic}
    
    QUOTE RULES:
    1. Must be 1 to 2 short lines max (Under 14 words total).
    2. Sassy, witty, sarcastic Hinglish quote.
    3. NO emojis in quote text.

    CAPTION RULES:
    - Include sarcastic follow-up, emojis (🤪, 👻, 💅, 💣), call-to-action, and 5 hashtags.

    OUTPUT FORMAT: Strictly JSON with "quote" and "caption".
    """

    for model_name in MODELS_TO_TRY:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=1.0
                )
            )
            data = json.loads(response.text.strip())
            return data.get("quote"), data.get("caption")
        except Exception as e:
            print(f"⚠️ {model_name} failed: {e}")
            time.sleep(3)

    return None, None

# ==========================================
# REEL VIDEO ANIMATOR
# ==========================================
def create_typing_reel():
    reel_id = get_next_reel_id()
    print(f"\n🚀 Creating Reel Post: {reel_id}")

    quote_text, caption_text = generate_hinglish_quote_and_caption()
    if not quote_text or not caption_text:
        print("❌ Content generation failed.")
        return False

    base_bg = Image.open(BACKGROUND_PATH).convert("RGB")
    img_w, img_h = base_bg.size

    font_size = int(img_w * 0.055)
    try:
        font = ImageFont.truetype(FONT_PATH, font_size)
    except Exception:
        font = ImageFont.load_default()

    # Pre-wrap full text so layout coordinates stay anchored during typing animation
    wrapped_lines = textwrap.wrap(quote_text, width=22)
    full_text = "\n".join(wrapped_lines)

    # Compute target bounding box for the FULL completed text
    dummy_draw = ImageDraw.Draw(base_bg)
    bbox = dummy_draw.multiline_textbbox((0, 0), full_text, font=font, align="left")
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    # Anchor to the fixed LEFT coordinate so text types naturally from left-to-right
    start_x = (img_w - text_w) / 2
    bottom_padding = int(img_h * 0.12)
    start_y = img_h - text_h - bottom_padding

    # Video Timing Settings (Slower typing speed for readability)
    TYPING_DURATION = 4.0  # Increased from 2.5s -> 4.0s for comfortable reading speed
    HOLD_DURATION = 3.5    # Hold full quote static before video ends
    TOTAL_DURATION = TYPING_DURATION + HOLD_DURATION

    # Frame generator function called by MoviePy
    def make_frame(t):
        if t < TYPING_DURATION:
            progress = t / TYPING_DURATION
            visible_chars = int(len(quote_text) * progress)
        else:
            visible_chars = len(quote_text)

        # Truncate raw string and wrap
        current_raw = quote_text[:visible_chars]
        current_wrapped = "\n".join(textwrap.wrap(current_raw, width=22))

        # Render frame anchored at static start_x, start_y using left alignment
        frame_img = base_bg.copy()
        draw = ImageDraw.Draw(frame_img)
        draw.multiline_text(
            (start_x, start_y), 
            current_wrapped, 
            fill=(255, 255, 255), 
            font=font, 
            align="left"  # <--- CRITICAL: Keeps left margin locked in place
        )

        return np.array(frame_img)

    print("🎬 Rendering typing animation MP4...")
    clip = VideoClip(make_frame, duration=TOTAL_DURATION)
    
    video_rel_path = f"reels/{reel_id}.mp4"
    video_output_path = os.path.join(BASE_DIR, video_rel_path)
    
    clip.write_videofile(
        video_output_path, 
        fps=24, 
        codec="libx264", 
        audio=False, 
        preset="fast"
    )
    print(f"✅ Reel saved: {video_rel_path}")

    # Save caption text file
    txt_output_path = os.path.join(CONTENT_DIR, f"{reel_id}.txt")
    with open(txt_output_path, "w", encoding="utf-8") as f:
        f.write(f"[CAPTION]\n{caption_text}")
    print(f"✅ Caption saved: content/{reel_id}.txt")

    # Update Reels Queue
    queue = []
    if os.path.exists(REELS_QUEUE_FILE):
        with open(REELS_QUEUE_FILE, "r", encoding="utf-8") as f:
            try:
                queue = json.load(f)
            except json.JSONDecodeError:
                queue = []

    queue.append({
        "id": reel_id,
        "video_path": video_rel_path,
        "caption": caption_text,
        "status": "pending",
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
    })

    with open(REELS_QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(queue, f, indent=2, ensure_ascii=False)

    print(f"✅ scheduled_reels_queue.json updated: {reel_id} added.")
    return True

if __name__ == "__main__":
    create_typing_reel()
import os
import re
import json
import random
import textwrap
from google import genai
from google.genai import types
from PIL import Image, ImageDraw, ImageFont
import time

# ==========================================
# DIRECTORY & FILE PATHS
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BRANDING_DIR = os.path.join(BASE_DIR, "branding")
IMAGES_DIR = os.path.join(BASE_DIR, "images")
CONTENT_DIR = os.path.join(BASE_DIR, "content")
QUEUE_FILE = os.path.join(BASE_DIR, "scheduled_queue.json")

BACKGROUND_PATH = os.path.join(BRANDING_DIR, "background.jpg")
FONT_PATH = os.path.join(BRANDING_DIR, "font.ttf")

os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs(CONTENT_DIR, exist_ok=True)

# List of topics to force unique responses on every run
TOPICS = [
    "being called rude just for speaking facts and not sugarcoating",
    "taking no crap from toxic relatives, in-laws, or nosy neighbours",
    "prioritizing peace, sleep, and self-respect over social validation",
    "giving unfiltered reality checks to hypocrites and drama queens",
    "living life on own terms while people call it 'attitude problem'",
    "workplace drama and dealing with people who talk behind your back"
]

# ==========================================
# INCREMENTAL POST ID CALCULATOR
# ==========================================
def get_next_post_id():
    """Scans images/ folder and returns the next incremental post ID (e.g. post_05)."""
    existing_files = os.listdir(IMAGES_DIR) if os.path.exists(IMAGES_DIR) else []
    numbers = []
    
    for filename in existing_files:
        match = re.match(r"post_(\d+)\.jpg", filename, re.IGNORECASE)
        if match:
            numbers.append(int(match.group(1)))
            
    next_num = max(numbers) + 1 if numbers else 1
    return f"post_{next_num:02d}"

# ==========================================
# GEMINI AI CONTENT GENERATOR
# ==========================================
# List of models to try in order of preference
MODELS_TO_TRY = ['gemini-3.5-flash', 'gemini-3.6-flash', 'gemini-3.4-flash']

def generate_hinglish_quote_and_caption():
    """Calls Gemini API with retries and model fallbacks for 503 high-demand errors."""
    api_key = os.environ.get("GEMINI_API_KEY")
    
    if not api_key:
        print("❌ ERROR: GEMINI_API_KEY environment variable is missing or empty!")
        print("👉 Run: set GEMINI_API_KEY=your_actual_key_here before running this script.")
        return None, None

    selected_topic = random.choice(TOPICS)
    print(f"🎯 Today's Topic Focus: {selected_topic}")

    client = genai.Client(api_key=api_key)

    prompt = f"""
    You are an expert social media growth strategist writing content for a viral relatable Instagram character persona.
    
    TODAY'S SPECIFIC SUB-TOPIC: {selected_topic}

    CHARACTER PERSONA PROFILE:
    - Vibe: Sassy, high-energy, childishly dramatic, lovable, but totally UPFRONT & unfiltered!
    - Tone: Witty, sarcastic, savage, but cute (uses emojis like 🤪, 👻, 🎀, 💅, 💣).
    - Language: Modern Hinglish (Hindi in English script mixed with witty English).

    QUOTE STYLE & RULES:
    1. Must be 1 to 2 short lines max (Under 14 words total).
    2. Must be punchy, relatable, and contain a unexpected sarcastic/sassy twist.
    3. Examples of desired tone and formatting:
       - "It’s unfair that I have to manage my anger just because other people can’t manage their stupidity 👻"
       - "I am not lazy. I’m on power-saving mode because life keeps running too many background apps 🔋"
       - "Blocking isn’t enough. We need options like: Mute forever or Send to Mars 🤪"
       - "Shakal se hu main cute and pyari,\\nPar dimaag se poori aatankwadi 🎀💣"
       - "Mai rude nahi hu, bas mujhse fake smile aur sugarcoating nahi hoti 🙅‍♀️"
    
    CAPTION RULES:
    - First line MUST be a punchy follow-up joke or reality check.
    - Include an engaging call-to-action (e.g., "Tag someone who...", "Send this to...").
    - End with 5 highly targeted hashtags.

    OUTPUT FORMAT:
    Return strictly valid JSON with keys "quote" and "caption". No extra markdown or commentary.
    """

    # Retry loop across multiple models
    for model_name in MODELS_TO_TRY:
        for attempt in range(1, 4):  # Try each model up to 3 times
            try:
                print(f"🔄 Requesting API using {model_name} (Attempt {attempt})...")
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
                err_str = str(e)
                if "503" in err_str or "UNAVAILABLE" in err_str or "429" in err_str:
                    print(f"⚠️ {model_name} busy (503/429). Waiting 5 seconds before retrying...")
                    time.sleep(5)
                else:
                    print(f"⚠️ Error with {model_name}: {e}")
                    break  # Try next model if it's a non-transient error

    print("❌ All models and retry attempts failed due to high server load.")
    return None, None
        
# ==========================================
# IMAGE CREATOR & QUEUE UPDATER
# ==========================================
def create_post():
    post_id = get_next_post_id()
    print(f"\n🚀 Creating new incremental post: {post_id}")

    # 1. Fetch Dynamic Content
    quote_text, caption_text = generate_hinglish_quote_and_caption()
    
    if not quote_text or not caption_text:
        print("❌ Generation aborted because API failed or key was missing.")
        return False

    print(f"✍️ Generated Quote: \"{quote_text}\"")

    # 2. Open Canvas
    if not os.path.exists(BACKGROUND_PATH) or not os.path.exists(FONT_PATH):
        print("❌ Error: Missing background.jpg or font.ttf in branding folder!")
        return False

    img = Image.open(BACKGROUND_PATH).convert("RGB")
    draw = ImageDraw.Draw(img)
    img_w, img_h = img.size

    # 3. Typography & Wrapping
    font_size = int(img_w * 0.055)
    try:
        font = ImageFont.truetype(FONT_PATH, font_size)
    except Exception as e:
        font = ImageFont.load_default()

    wrapped_lines = textwrap.wrap(quote_text, width=22)
    text_to_draw = "\n".join(wrapped_lines)

    # 4. Bottom Alignment Coordinates
    bbox = draw.multiline_textbbox((0, 0), text_to_draw, font=font, align="center")
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    # Center horizontally
    x = (img_w - text_w) / 2

    # Align to bottom with padding (12% of total height from the bottom)
    bottom_padding = int(img_h * 0.12)
    y = img_h - text_h - bottom_padding

    draw.multiline_text((x, y), text_to_draw, fill=(255, 255, 255), font=font, align="center")
    
    # 5. Save Image File
    image_output_path = os.path.join(IMAGES_DIR, f"{post_id}.jpg")
    img.save(image_output_path, "JPEG", quality=95)
    print(f"✅ Image saved: images/{post_id}.jpg")

    # 6. Save Content File
    txt_output_path = os.path.join(CONTENT_DIR, f"{post_id}.txt")
    with open(txt_output_path, "w", encoding="utf-8") as f:
        f.write(f"[CAPTION]\n{caption_text}\n\n[USER_TAGS]")
    print(f"✅ Caption saved: content/{post_id}.txt")

    # 7. Append to Queue
    queue = []
    if os.path.exists(QUEUE_FILE):
        with open(QUEUE_FILE, "r", encoding="utf-8") as f:
            try:
                queue = json.load(f)
            except json.JSONDecodeError:
                queue = []

    queue.append({"id": post_id, "status": "pending"})

    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(queue, f, indent=2)
    print(f"✅ Queue updated: {post_id} added as pending.")
    return True

if __name__ == "__main__":
    create_post()
import os
import json
import tempfile
import requests
from PIL import Image

# ==========================================
# CONFIGURATION
# ==========================================
IG_USER_ID = os.environ.get("IG_USER_ID")
ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN")

QUEUE_FILE = "scheduled_queue.json"
IMAGES_DIR = "images"
CONTENT_DIR = "content"

# GitHub Repo Details for Raw Image URLs
GITHUB_REPO = os.environ.get("GITHUB_REPOSITORY", "krazzynik/rofolo-ig-automation")
GITHUB_BRANCH = "main"

# ==========================================
# HELPER FUNCTIONS
# ==========================================
def parse_txt_file(txt_path):
    """Parses CAPTION and USER_TAGS from text file."""
    with open(txt_path, "r", encoding="utf-8") as f:
        content = f.read()

    caption = ""
    user_tags = []

    parts = content.split("[USER_TAGS]")
    caption = parts[0].replace("[CAPTION]", "").strip()

    if len(parts) > 1:
        tags_raw = parts[1].strip().split("\n")
        for line in tags_raw:
            if line.strip():
                items = [i.strip() for i in line.split(",")]
                if len(items) == 3:
                    user_tags.append({
                        "username": items[0],
                        "x": float(items[1]),
                        "y": float(items[2])
                    })

    return caption, user_tags


def find_image_file(post_id):
    """Locates the image matching post_id regardless of extension."""
    for ext in [".jpg", ".jpeg", ".png", ".webp", ".jfif"]:
        path = os.path.join(IMAGES_DIR, f"{post_id}{ext}")
        if os.path.exists(path):
            return path, f"{post_id}{ext}"
    return None, None


def get_github_raw_url(filename):
    """Generates direct, raw HTTPS GitHub URL for Meta to download."""
    raw_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/{GITHUB_BRANCH}/{IMAGES_DIR}/{filename}"
    print(f"Generated Public GitHub Image URL: {raw_url}")
    return raw_url


# ==========================================
# EXECUTION FLOW
# ==========================================
if not os.path.exists(QUEUE_FILE):
    print("ERROR: scheduled_queue.json not found.")
    exit()

with open(QUEUE_FILE, "r", encoding="utf-8") as f:
    queue = json.load(f)

# Find next pending item
next_item = None
for item in queue:
    if item.get("status") == "pending":
        next_item = item
        break

if not next_item:
    print("No pending posts found in queue. All done!")
    exit()

post_id = next_item["id"]
image_path, filename = find_image_file(post_id)
txt_path = os.path.join(CONTENT_DIR, f"{post_id}.txt")

if not image_path or not os.path.exists(txt_path):
    print(f"ERROR: Missing image or text file for post ID '{post_id}'")
    exit()

caption, user_tags = parse_txt_file(txt_path)

# Construct direct raw GitHub URL
public_url = get_github_raw_url(filename)

print(f"\nCreating Meta Container for {post_id}...")
container_params = {
    "image_url": public_url,
    "caption": caption,
    "user_tags": json.dumps(user_tags),
    "access_token": ACCESS_TOKEN,
}

container_res = requests.post(
    f"https://graph.facebook.com/v21.0/{IG_USER_ID}/media",
    params=container_params,
).json()

creation_id = container_res.get("id")

if creation_id:
    print("Publishing to Instagram...")
    publish_res = requests.post(
        f"https://graph.facebook.com/v21.0/{IG_USER_ID}/media_publish",
        params={
            "creation_id": creation_id,
            "access_token": ACCESS_TOKEN
        },
    ).json()

    if "id" in publish_res:
        print(f"🎉 SUCCESS! {post_id} published! Post ID:", publish_res.get("id"))
        
        # Update status in queue file
        next_item["status"] = "published"
        with open(QUEUE_FILE, "w", encoding="utf-8") as f:
            json.dump(queue, f, indent=2)
    else:
        print("Publish failed:", publish_res)
else:
    print("Container creation failed:", container_res)
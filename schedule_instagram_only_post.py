import json
import os
import sys
from instagram_only_common import (InstagramOnlyError, api_base_url, cleanup_artifacts, compact_queue, load_queue, mark_failed, mark_published, mark_publishing, post, public_asset_url, publish_container, require_credentials, save_queue)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
QUEUE_FILE = os.path.join(BASE_DIR, "scheduled_queue.json")
IMAGES_DIR = os.path.join(BASE_DIR, "images")
CONTENT_DIR = os.path.join(BASE_DIR, "content")

def parse_caption(path):
    with open(path, "r", encoding="utf-8") as content_file:
        return content_file.read().split("[USER_TAGS]", 1)[0].replace("[CAPTION]", "").strip()

def find_image(post_id):
    for extension in (".jpg", ".jpeg", ".png", ".webp", ".jfif"):
        filename = f"{post_id}{extension}"; path = os.path.join(IMAGES_DIR, filename)
        if os.path.exists(path): return filename, path
    return None, None

def main():
    queue = load_queue(QUEUE_FILE)
    item = next((entry for entry in queue if entry.get("status") == "pending" and not entry.get("instagram_media_id")), None)
    if not item:
        print("No pending Instagram-only posts found."); return 0
    user_id, access_token = require_credentials(); mark_publishing(item); save_queue(QUEUE_FILE, queue)
    try:
        post_id = item["id"]; filename, image_path = find_image(post_id); caption_path = os.path.join(CONTENT_DIR, f"{post_id}.txt")
        if not image_path or not os.path.exists(caption_path): raise InstagramOnlyError(f"Missing image or caption for {post_id}.")
        creation_id = item.get("instagram_creation_id")
        if not creation_id:
            creation_id = post(f"{api_base_url()}/{user_id}/media", access_token, {"image_url": public_asset_url("images", filename), "caption": parse_caption(caption_path)}).get("id")
            if not creation_id: raise InstagramOnlyError("Instagram container response did not include an id.")
            item["instagram_creation_id"] = creation_id; save_queue(QUEUE_FILE, queue)
        media_id = publish_container(user_id, access_token, creation_id)
        mark_published(item, media_id); save_queue(QUEUE_FILE, queue)
        cleanup_artifacts(((image_path, "images"), (caption_path, "content")), base_dir=os.path.dirname(IMAGES_DIR))
        save_queue(QUEUE_FILE, compact_queue(queue)); print(f"Published Instagram-only post {post_id} (media id {media_id})."); return 0
    except (InstagramOnlyError, KeyError, OSError, json.JSONDecodeError) as exc:
        mark_failed(item, exc); save_queue(QUEUE_FILE, queue); print(f"Instagram-only post failed: {exc}"); return 1

if __name__ == "__main__": sys.exit(main())

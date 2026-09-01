import os
import sys
from instagram_only_common import (InstagramOnlyError, api_base_url, cleanup_artifacts, compact_queue, load_queue, mark_failed, mark_published, mark_publishing, post, public_asset_url, publish_container, require_credentials, save_queue)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
QUEUE_FILE = os.path.join(BASE_DIR, "scheduled_reels_queue.json")

def main():
    queue = load_queue(QUEUE_FILE)
    item = next((entry for entry in queue if entry.get("status") == "pending" and not entry.get("instagram_media_id")), None)
    if not item:
        print("No pending Instagram-only reels found."); return 0
    user_id, access_token = require_credentials(); mark_publishing(item); save_queue(QUEUE_FILE, queue)
    try:
        reel_id = item["id"]; filename = os.path.basename(item.get("video_path") or f"{reel_id}.mp4"); video_path = os.path.join(BASE_DIR, "reels", filename)
        if not os.path.exists(video_path): raise InstagramOnlyError(f"Missing reel video for {reel_id}.")
        creation_id = item.get("instagram_creation_id")
        if not creation_id:
            creation_id = post(f"{api_base_url()}/{user_id}/media", access_token, {"media_type": "REELS", "video_url": public_asset_url("reels", filename), "caption": item.get("caption", "")}).get("id")
            if not creation_id: raise InstagramOnlyError("Instagram reel container response did not include an id.")
            item["instagram_creation_id"] = creation_id; save_queue(QUEUE_FILE, queue)
        media_id = publish_container(user_id, access_token, creation_id)
        mark_published(item, media_id); save_queue(QUEUE_FILE, queue)
        cleanup_artifacts(((video_path, "reels"),), base_dir=os.path.dirname(os.path.dirname(video_path)))
        save_queue(QUEUE_FILE, compact_queue(queue)); print(f"Published Instagram-only reel {reel_id} (media id {media_id})."); return 0
    except (InstagramOnlyError, KeyError, OSError) as exc:
        mark_failed(item, exc); save_queue(QUEUE_FILE, queue); print(f"Instagram-only reel failed: {exc}"); return 1

if __name__ == "__main__": sys.exit(main())

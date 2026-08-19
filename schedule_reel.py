import os
import json
import requests
import time

IG_ACCOUNT_ID = os.getenv("INSTAGRAM_ACCOUNT_ID")
ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN")
RAW_BASE_URL = os.getenv("RAW_IMAGE_BASE_URL")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REELS_QUEUE_FILE = os.path.join(BASE_DIR, "scheduled_reels_queue.json")

def load_reels_queue():
    if os.path.exists(REELS_QUEUE_FILE):
        with open(REELS_QUEUE_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []

def save_reels_queue(queue):
    with open(REELS_QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(queue, f, indent=2, ensure_ascii=False)

def publish_reel_to_instagram(video_url, caption):
    print("🎬 Uploading Reel to Meta Graph API...")
    container_url = f"https://graph.facebook.com/v20.0/{IG_ACCOUNT_ID}/media"
    payload = {
        'media_type': 'REELS',
        'video_url': video_url,
        'caption': caption,
        'access_token': ACCESS_TOKEN
    }
    
    r1 = requests.post(container_url, data=payload)
    res1 = r1.json()
    
    if "id" not in res1:
        print(f"❌ Container Error: {res1}")
        return False

    creation_id = res1["id"]
    print(f"📦 Reel Container ID: {creation_id}. Waiting 30s for encoding...")
    time.sleep(30)

    publish_url = f"https://graph.facebook.com/v20.0/{IG_ACCOUNT_ID}/media_publish"
    r2 = requests.post(publish_url, data={'creation_id': creation_id, 'access_token': ACCESS_TOKEN})
    res2 = r2.json()

    if "id" in res2:
        print(f"🎉 Reel published! Instagram Media ID: {res2['id']}")
        return True
    else:
        print(f"❌ Publish Error: {res2}")
        return False

def main():
    if not IG_ACCOUNT_ID or not ACCESS_TOKEN or not RAW_BASE_URL:
        print("❌ Missing Meta credentials environment variables.")
        return

    queue = load_reels_queue()
    pending_item = next((item for item in queue if item.get("status") == "pending"), None)

    if not pending_item:
        print("ℹ️ No pending reels found in scheduled_reels_queue.json.")
        return

    reel_id = pending_item["id"]
    video_rel_path = pending_item["video_path"]
    public_video_url = f"{RAW_BASE_URL.rstrip('/')}/{video_rel_path}"
    caption = pending_item.get("caption", "")

    print(f"\n🚀 Processing Reel: {reel_id}")
    print(f"🔗 Public URL: {public_video_url}")

    if publish_reel_to_instagram(public_video_url, caption):
        pending_item["status"] = "posted"
        pending_item["posted_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        save_reels_queue(queue)
        print("✅ scheduled_reels_queue.json updated to 'posted'.")

if __name__ == "__main__":
    main()
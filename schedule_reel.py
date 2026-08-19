import os
import json
import time
import requests

# ==========================================
# CONFIGURATION (Matching image publisher setup)
# ==========================================
IG_USER_ID = os.environ.get("IG_USER_ID") or os.environ.get("INSTAGRAM_ACCOUNT_ID")
ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN") or os.environ.get("INSTAGRAM_ACCESS_TOKEN")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REELS_QUEUE_FILE = os.path.join(BASE_DIR, "scheduled_reels_queue.json")
REELS_DIR = "reels"

# Automatically infer repository URL without needing RAW_IMAGE_BASE_URL secret
GITHUB_REPO = os.environ.get("GITHUB_REPOSITORY", "krazzynik/rofolo-ig-automation")
GITHUB_BRANCH = "main"

# ==========================================
# HELPER FUNCTIONS
# ==========================================
def get_github_raw_url(filename):
    """Generates direct, raw HTTPS GitHub URL for Meta to download the reel video."""
    raw_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/{GITHUB_BRANCH}/{REELS_DIR}/{filename}"
    print(f"🔗 Generated Public GitHub Reel URL: {raw_url}")
    return raw_url

def wait_for_container_ready(creation_id, max_attempts=15, delay=10):
    """Polls Meta Graph API until the Reel video container finishes processing/encoding."""
    print(f"⏳ Waiting for Meta container {creation_id} to finish encoding...")
    status_url = f"https://graph.facebook.com/v21.0/{creation_id}"
    
    for attempt in range(1, max_attempts + 1):
        time.sleep(delay)
        try:
            res = requests.get(
                status_url,
                params={
                    "fields": "status_code",
                    "access_token": ACCESS_TOKEN
                }
            ).json()
            
            status_code = res.get("status_code")
            print(f"Attempt {attempt}/{max_attempts}: Container status = {status_code}")
            
            if status_code == "FINISHED":
                return True
            elif status_code == "ERROR":
                print("❌ Container processing failed on Meta's end:", res)
                return False
        except Exception as e:
            print(f"⚠️ Error checking status: {e}")

    print("❌ Timed out waiting for Meta Reel container to be ready.")
    return False

# ==========================================
# EXECUTION FLOW
# ==========================================
def main():
    if not IG_USER_ID or not ACCESS_TOKEN:
        print("❌ Missing Meta credentials. Ensure IG_USER_ID and ACCESS_TOKEN are set.")
        exit(1)

    if not os.path.exists(REELS_QUEUE_FILE):
        print("❌ ERROR: scheduled_reels_queue.json not found.")
        exit(1)

    with open(REELS_QUEUE_FILE, "r", encoding="utf-8") as f:
        queue = json.load(f)

    # Find next pending reel
    pending_item = next((item for item in queue if item.get("status") == "pending"), None)

    if not pending_item:
        print("ℹ️ No pending reels found in scheduled_reels_queue.json. All done!")
        exit(0)

    reel_id = pending_item["id"]
    filename = f"{reel_id}.mp4"
    public_video_url = get_github_raw_url(filename)
    caption = pending_item.get("caption", "")

    print(f"\n🚀 Creating Meta Reel Container for {reel_id}...")
    container_params = {
        "media_type": "REELS",
        "video_url": public_video_url,
        "caption": caption,
        "access_token": ACCESS_TOKEN
    }

    container_res = requests.post(
        f"https://graph.facebook.com/v21.0/{IG_USER_ID}/media",
        data=container_params
    ).json()

    creation_id = container_res.get("id")

    if creation_id:
        # Wait for Meta to finish video processing & encoding
        if wait_for_container_ready(creation_id):
            print("🎬 Publishing Reel to Instagram...")
            publish_res = requests.post(
                f"https://graph.facebook.com/v21.0/{IG_USER_ID}/media_publish",
                data={
                    "creation_id": creation_id,
                    "access_token": ACCESS_TOKEN
                }
            ).json()

            if "id" in publish_res:
                print(f"🎉 SUCCESS! Reel {reel_id} published! Instagram Media ID:", publish_res.get("id"))
                
                # Update queue status
                pending_item["status"] = "posted"
                pending_item["posted_at"] = time.strftime("%Y-%m-%d %H:%M:%S")

                with open(REELS_QUEUE_FILE, "w", encoding="utf-8") as f:
                    json.dump(queue, f, indent=2, ensure_ascii=False)
                
                print("✅ scheduled_reels_queue.json updated to 'posted'.")
            else:
                print("❌ Publish failed:", publish_res)
                exit(1)
        else:
            print("❌ Aborting publish: Container was not ready in time.")
            exit(1)
    else:
        print("❌ Container creation failed:", container_res)
        exit(1)

if __name__ == "__main__":
    main()
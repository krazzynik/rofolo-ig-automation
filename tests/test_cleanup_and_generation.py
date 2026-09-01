import json
import os
import tempfile
import unittest
from unittest.mock import patch

import instagram_only_common as common
import schedule_instagram_only_post as post
import schedule_instagram_only_reel as reel
from content_style import CONTENT_BUCKETS, build_prompt


class CleanupAndGenerationTests(unittest.TestCase):
    def setUp(self):
        os.environ.update(INSTAGRAM_ONLY_USER_ID="user", INSTAGRAM_ONLY_ACCESS_TOKEN="secret")

    def tearDown(self):
        for key in ("INSTAGRAM_ONLY_USER_ID", "INSTAGRAM_ONLY_ACCESS_TOKEN", "INSTAGRAM_ONLY_PUBLISHED_RETENTION"):
            os.environ.pop(key, None)

    def test_style_prompt_and_category_variety(self):
        prompt = build_prompt("desi family")
        self.assertIn("punchline", prompt); self.assertIn("natural Hinglish", prompt); self.assertIn("spammy block", prompt)
        self.assertGreaterEqual(len(CONTENT_BUCKETS), 10); self.assertNotIn("Tag someone who", prompt)

    def test_post_success_deletes_only_generated_files(self):
        with tempfile.TemporaryDirectory() as directory:
            images, content = os.path.join(directory, "images"), os.path.join(directory, "content")
            os.mkdir(images); os.mkdir(content)
            image, caption, other = [os.path.join(folder, name) for folder, name in ((images, "post_01.jpg"), (content, "post_01.txt"), (images, "keep.jpg"))]
            for path in (image, caption, other): open(path, "w").close()
            queue_path = os.path.join(directory, "queue.json")
            with open(queue_path, "w") as file: json.dump([{"id": "post_01", "status": "pending"}], file)
            post.QUEUE_FILE, post.IMAGES_DIR, post.CONTENT_DIR = queue_path, images, content
            def fake(method, url, **kwargs):
                if method == "GET": return {"status_code": "FINISHED"}
                return {"id": "creation"} if url.endswith("/media") else {"id": "media"}
            with patch("instagram_only_common.request", side_effect=fake): self.assertEqual(post.main(), 0)
            self.assertFalse(os.path.exists(image)); self.assertFalse(os.path.exists(caption)); self.assertTrue(os.path.exists(other))
            record = json.load(open(queue_path))[0]
            self.assertEqual(record["instagram_media_id"], "media"); self.assertEqual(record["instagram_creation_id"], "creation")

    def test_failed_publish_keeps_files_and_cleanup_is_confined(self):
        with tempfile.TemporaryDirectory() as directory:
            approved = os.path.join(directory, "images"); os.mkdir(approved)
            inside, outside = os.path.join(approved, "post.jpg"), os.path.join(directory, "outside.txt")
            open(inside, "w").close(); open(outside, "w").close()
            with self.assertRaises(common.InstagramOnlyError): common.safe_remove_artifact(outside, "images", base_dir=directory)
            self.assertTrue(os.path.exists(outside)); self.assertTrue(os.path.exists(inside))

    def test_reel_cleanup_deletes_video_and_keeps_record(self):
        with tempfile.TemporaryDirectory() as directory:
            reels = os.path.join(directory, "reels"); os.mkdir(reels)
            video = os.path.join(reels, "reel_01.mp4"); open(video, "w").close()
            queue_path = os.path.join(directory, "queue.json")
            with open(queue_path, "w") as file: json.dump([{"id": "reel_01", "video_path": "reels/reel_01.mp4", "status": "pending"}], file)
            reel.QUEUE_FILE, reel.BASE_DIR = queue_path, directory
            def fake(method, url, **kwargs):
                if method == "GET": return {"status_code": "FINISHED"}
                return {"id": "creation"} if url.endswith("/media") else {"id": "media"}
            with patch("instagram_only_common.request", side_effect=fake): self.assertEqual(reel.main(), 0)
            self.assertFalse(os.path.exists(video)); self.assertEqual(json.load(open(queue_path))[0]["status"], "published")

    def test_compaction_never_prunes_pending_or_failed(self):
        os.environ["INSTAGRAM_ONLY_PUBLISHED_RETENTION"] = "1"
        queue = [{"id": "old", "status": "published", "publisher": "instagram_only", "instagram_media_id": "1"}, {"id": "pending", "status": "pending"}, {"id": "failed", "status": "failed"}, {"id": "new", "status": "published", "publisher": "instagram_only", "instagram_media_id": "2"}]
        self.assertEqual([item["id"] for item in common.compact_queue(queue)], ["pending", "failed", "new"])


if __name__ == "__main__": unittest.main()

import json
import os
import tempfile
import unittest
from unittest.mock import patch


class InstagramOnlyTests(unittest.TestCase):
    def setUp(self):
        os.environ.update(INSTAGRAM_ONLY_USER_ID="user-1", INSTAGRAM_ONLY_ACCESS_TOKEN="secret", INSTAGRAM_GRAPH_API_VERSION="v23.0", GITHUB_REPOSITORY="owner/repo", GITHUB_REF_NAME="dev")

    def tearDown(self):
        for key in ("INSTAGRAM_ONLY_USER_ID", "INSTAGRAM_ONLY_ACCESS_TOKEN", "INSTAGRAM_GRAPH_API_VERSION", "GITHUB_REPOSITORY", "GITHUB_REF_NAME"):
            os.environ.pop(key, None)

    def test_post_flow_and_queue_ids(self):
        import schedule_instagram_only_post as module
        with tempfile.TemporaryDirectory() as directory:
            image_dir, content_dir = os.path.join(directory, "images"), os.path.join(directory, "content")
            os.mkdir(image_dir); os.mkdir(content_dir)
            open(os.path.join(image_dir, "post_01.jpg"), "wb").close()
            with open(os.path.join(content_dir, "post_01.txt"), "w", encoding="utf-8") as file: file.write("[CAPTION]\nHello")
            queue_path = os.path.join(directory, "queue.json")
            with open(queue_path, "w", encoding="utf-8") as file: json.dump([{"id": "post_01", "status": "pending"}], file)
            module.QUEUE_FILE, module.IMAGES_DIR, module.CONTENT_DIR = queue_path, image_dir, content_dir
            def fake(method, url, **kwargs):
                if method == "GET": return {"status_code": "FINISHED"}
                if url.endswith("/media"): return {"id": "creation-1"}
                return {"id": "media-1"}
            with patch("instagram_only_common.request", side_effect=fake): self.assertEqual(module.main(), 0)
            saved = json.load(open(queue_path, encoding="utf-8"))[0]
            self.assertEqual((saved["status"], saved["instagram_creation_id"], saved["instagram_media_id"]), ("published", "creation-1", "media-1"))

    def test_missing_secret_and_published_skip(self):
        import instagram_only_common as common
        os.environ.pop("INSTAGRAM_ONLY_ACCESS_TOKEN")
        with self.assertRaises(common.InstagramOnlyError): common.require_credentials()
        os.environ["INSTAGRAM_ONLY_ACCESS_TOKEN"] = "secret"
        import schedule_instagram_only_reel as reel
        with tempfile.TemporaryDirectory() as directory:
            queue_path = os.path.join(directory, "queue.json")
            with open(queue_path, "w", encoding="utf-8") as file: json.dump([{"id": "reel_01", "status": "published", "instagram_media_id": "media-1"}], file)
            reel.QUEUE_FILE = queue_path
            with patch("instagram_only_common.request") as request: self.assertEqual(reel.main(), 0); request.assert_not_called()


if __name__ == "__main__": unittest.main()

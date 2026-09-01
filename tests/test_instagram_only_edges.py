import json
import os
import tempfile
import unittest
from unittest.mock import patch

import instagram_only_common as common
import schedule_instagram_only_reel as reel


class Response:
    def __init__(self, payload, status_code):
        self.payload, self.status_code = payload, status_code
        self.text = json.dumps(payload)

    def json(self):
        return self.payload


class InstagramOnlyEdgeTests(unittest.TestCase):
    def setUp(self):
        os.environ.update(INSTAGRAM_ONLY_USER_ID="user", INSTAGRAM_ONLY_ACCESS_TOKEN="secret")

    def tearDown(self):
        os.environ.pop("INSTAGRAM_ONLY_USER_ID", None)
        os.environ.pop("INSTAGRAM_ONLY_ACCESS_TOKEN", None)

    def test_reel_polls_until_finished_and_publishes(self):
        with tempfile.TemporaryDirectory() as directory:
            reels_dir = os.path.join(directory, "reels")
            os.mkdir(reels_dir)
            open(os.path.join(reels_dir, "reel_01.mp4"), "wb").close()
            queue_path = os.path.join(directory, "queue.json")
            with open(queue_path, "w", encoding="utf-8") as file:
                json.dump([{"id": "reel_01", "video_path": "reels/reel_01.mp4", "status": "pending"}], file)
            reel.QUEUE_FILE = queue_path
            reel.BASE_DIR = directory
            calls = []
            def fake(method, url, **kwargs):
                calls.append((method, url, kwargs))
                if method == "GET": return {"status_code": "IN_PROGRESS" if len(calls) == 3 else "FINISHED"}
                if url.endswith("/media"): return {"id": "creation"}
                return {"id": "media"}
            with patch("instagram_only_common.request", side_effect=fake), patch("instagram_only_common.time.sleep"):
                self.assertEqual(reel.main(), 0)
            self.assertTrue(any(call[0] == "GET" for call in calls))
            self.assertEqual(json.load(open(queue_path, encoding="utf-8"))[0]["status"], "published")

    def test_api_failure_marks_queue_failed_and_retries_transient_status(self):
        responses = [Response({"error": {"message": "busy"}}, 503), Response({"error": {"message": "bad request"}}, 400)]
        with patch("instagram_only_common.time.sleep"), patch("instagram_only_common.requests.request", side_effect=responses) as request:
            with self.assertRaises(common.InstagramOnlyError):
                common.request("POST", "https://graph.instagram.com/v23.0/user/media", params=None, data={"access_token": "secret"})
        self.assertEqual(request.call_count, 2)


if __name__ == "__main__":
    unittest.main()

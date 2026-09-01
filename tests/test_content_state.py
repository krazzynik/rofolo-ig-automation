import json
import os
import tempfile
import unittest

from content_state import allocate_next, persist_allocated


class ContentStateTests(unittest.TestCase):
    def setup_paths(self, directory):
        state = os.path.join(directory, "content_state.json")
        post_queue = os.path.join(directory, "scheduled_queue.json")
        reel_queue = os.path.join(directory, "scheduled_reels_queue.json")
        images = os.path.join(directory, "images"); reels = os.path.join(directory, "reels"); content = os.path.join(directory, "content")
        for path in (images, reels, content): os.mkdir(path)
        with open(post_queue, "w") as file: json.dump([], file)
        with open(reel_queue, "w") as file: json.dump([], file)
        return state, post_queue, reel_queue, images, reels, content

    def test_post_id_survives_deleted_image_and_queue_compaction(self):
        with tempfile.TemporaryDirectory() as directory:
            state, queue, _, images, _, content = self.setup_paths(directory)
            with open(queue, "w") as file: json.dump([{"id": "post_7", "status": "published"}], file)
            persist_allocated("post", 7, state_path=state)
            self.assertEqual(allocate_next("post", state_path=state, queue_path=queue, artifact_directories=(images, content)), 8)
            os.remove(queue)
            with open(queue, "w") as file: json.dump([], file)
            self.assertEqual(allocate_next("post", state_path=state, queue_path=queue, artifact_directories=(images, content)), 8)

    def test_reel_id_survives_deleted_video(self):
        with tempfile.TemporaryDirectory() as directory:
            state, _, queue, _, reels, content = self.setup_paths(directory)
            with open(queue, "w") as file: json.dump([{"id": "reel_9", "status": "published"}], file)
            persist_allocated("reel", 9, state_path=state)
            self.assertEqual(allocate_next("reel", state_path=state, queue_path=queue, artifact_directories=(reels, content)), 10)
            os.remove(queue)
            with open(queue, "w") as file: json.dump([], file)
            self.assertEqual(allocate_next("reel", state_path=state, queue_path=queue, artifact_directories=(reels, content)), 10)

    def test_migration_uses_historical_queue_and_artifact_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            state, queue, _, images, _, content = self.setup_paths(directory)
            with open(queue, "w") as file: json.dump([{"id": "post_41"}, {"id": "not-a-post"}, {"id": "post_bad"}], file)
            open(os.path.join(images, "post_43.jpg"), "w").close(); open(os.path.join(content, "post_42.txt"), "w").close()
            self.assertEqual(allocate_next("post", state_path=state, queue_path=queue, artifact_directories=(images, content)), 44)

    def test_ids_remain_monotonic_and_malformed_state_is_ignored(self):
        with tempfile.TemporaryDirectory() as directory:
            state, queue, _, images, _, content = self.setup_paths(directory)
            with open(state, "w") as file: file.write('{"last_post_number": "bad"}')
            with open(queue, "w") as file: json.dump([{"id": "post_3"}, {"id": "post_100x"}], file)
            self.assertEqual(allocate_next("post", state_path=state, queue_path=queue, artifact_directories=(images, content)), 4)
            persist_allocated("post", 4, state_path=state)
            persist_allocated("post", 2, state_path=state)
            with open(state) as file: saved = json.load(file)
            self.assertEqual(saved["last_post_number"], 4)


if __name__ == "__main__": unittest.main()

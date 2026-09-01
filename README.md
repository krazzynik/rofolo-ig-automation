# Rofolo Instagram Automation

The repository has two publishing paths. The legacy FB + Instagram scripts are `schedule_fb_instagram_post.py` and `schedule_fb_instagram_reel.py`. The Instagram-only scripts are `schedule_instagram_only_post.py` and `schedule_instagram_only_reel.py`; they use only `INSTAGRAM_ONLY_USER_ID` and `INSTAGRAM_ONLY_ACCESS_TOKEN` with `https://graph.instagram.com`.

Generation uses shared guidance in `content_style.py`. Posts and reels rotate across desi family, relationships, relatives, workplace chaos, food, money, friendship, laziness, self-respect, social media, bad luck, and other daily-life buckets. Prompts favor short punchlines, natural Hinglish, concise complementary captions, limited hashtags, and occasional CTAs instead of repetitive attitude lectures or tag-a-friend blocks.

Generated IDs are monotonic and persisted in `content_state.json`. Each generator takes the next number from the persistent counter, queue history, and existing artifacts, then updates the counter after a successful generation. If the state file is missing or malformed, queue and artifact history safely migrate the maximum seen ID. This prevents ID reuse after publishing cleanup or queue compaction.

Instagram-only workflows are manual-only and do not have cron schedules. They use the invoking branch, publish content, update the queue, remove the successfully published generated artifacts, and commit those changes back with the built-in GitHub token. No credentials are printed.

Posts use `scheduled_queue.json`, `content/<id>.txt`, and `images/`; reels use `scheduled_reels_queue.json` and `reels/<filename>`. Cleanup rejects absolute, traversal, symlink, and out-of-directory paths and never runs until a final Instagram media ID has been stored. Failed publication retains all artifacts. A cleanup error is logged but does not mark an already-published item as failed.

Published Instagram-only records are compacted after success. By default the newest 100 Instagram-only published records are retained; set `INSTAGRAM_ONLY_PUBLISHED_RETENTION` to a larger value when needed. Pending, publishing, failed, and legacy records are never pruned automatically.

Checks:

```text
python -m compileall .
python -m unittest discover -s tests
```

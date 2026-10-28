# Rofolo Instagram Automation

The repository has two publishing paths. The legacy FB + Instagram scripts are `schedule_fb_instagram_post.py` and `schedule_fb_instagram_reel.py`. The Instagram-only scripts are `schedule_instagram_only_post.py` and `schedule_instagram_only_reel.py`; they use only `INSTAGRAM_ONLY_USER_ID` and `INSTAGRAM_ONLY_ACCESS_TOKEN` with `https://graph.instagram.com`.

## Creative direction and readable reels

Generation uses shared guidance in `content_style.py`, now focused on inclusive, funny motivation: getting back up after bad days, self-worth, work and money stress, unfair expectations, setbacks, healing, courage, and celebrating small wins. The voice is human, defiant, cheeky, sometimes mildly sweary, and avoids targeting any gender or mocking hardship.

Reels use **stationary, centered text cards**, not fast character-by-character typing. Gemini is asked for 2–4 short newline-separated beats. Each beat displays for 4 seconds by default, followed by a separate 2.5-second follow card. Long lines are wrapped to the actual image width, and a translucent dark overlay improves contrast. The generated MP4 has no audio, as before.

Optional environment variables for the reel generation workflow:

| Variable | Default | Purpose |
| --- | --- | --- |
| `ROFOLO_SECONDS_PER_CARD` | `4.0` | Seconds each quote card remains on screen (minimum 2). Try `5.0` for slower reading. |
| `ROFOLO_CTA_SECONDS` | `2.5` | Final follow card duration (minimum 1.5). |
| `ROFOLO_FOLLOW_TEXT` | `Follow @rofolo for more ✨` | Final card wording; use a handle that matches your real Instagram account. |
| `ROFOLO_BACKGROUND` | `branding/background.jpg` | A path relative to the repository root, used for both reels and static posts. |

### Change the background image

The easiest route is to replace `branding/background.jpg` in GitHub with a new JPEG **of the same filename**. New posts and reels will pick it up on their next generation run; already-rendered or queued media will not retroactively change. For a different filename, upload it to `branding/` and set `ROFOLO_BACKGROUND` to its relative path (for example `branding/sunset.jpg`) in the generation workflow's environment. A portrait 9:16 image, ideally 1080×1920, with an uncluttered center works best. Keep ownership or usage rights for any art.

Suggested visual direction: modern cinematic lifestyle photography or textured gradients, subtle warm/cool color, generous negative space for text. Avoid busy imagery or tiny characters behind the center quote.

## Queues and publishing

Generated IDs are monotonic and persisted in `content_state.json`. Each generator takes the next number from the persistent counter, queue history, and existing artifacts, then updates the counter after a successful generation. If the state file is missing or malformed, queue and artifact history safely migrate the maximum seen ID. This prevents ID reuse after publishing cleanup or queue compaction.

Instagram-only workflows are manual-only and do not have cron schedules. They use the invoking branch, publish content, update the queue, remove the successfully published generated artifacts, and commit those changes back with the built-in GitHub token. No credentials are printed.

Posts use `scheduled_queue.json`, `content/<id>.txt`, and `images/`; reels use `scheduled_reels_queue.json` and `reels/<filename>`. Cleanup rejects absolute, traversal, symlink, and out-of-directory paths and never runs until a final Instagram media ID has been stored. Failed publication retains all artifacts. A cleanup error is logged but does not mark an already-published item as failed.

Published Instagram-only records are compacted after success. By default the newest 100 Instagram-only published records are retained; set `INSTAGRAM_ONLY_PUBLISHED_RETENTION` to a larger value when needed. Pending, publishing, failed, and legacy records are never pruned automatically.

Checks:

```text
python -m compileall .
python -m unittest discover -s tests
```

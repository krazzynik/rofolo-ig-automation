# Rofolo Instagram Automation

This repository contains two explicit publishing paths. The legacy FB + Instagram path is `schedule_fb_instagram_post.py` and `schedule_fb_instagram_reel.py`; it retains `IG_USER_ID` and `ACCESS_TOKEN`. The Instagram-only path is `schedule_instagram_only_post.py` and `schedule_instagram_only_reel.py`; it uses only `INSTAGRAM_ONLY_USER_ID` and `INSTAGRAM_ONLY_ACCESS_TOKEN` with `https://graph.instagram.com`.

The Instagram-only workflows are `workflow_dispatch` only, with no cron. Configure both Instagram-only repository secrets, then run the appropriate workflow manually. The workflow sets `INSTAGRAM_GRAPH_API_VERSION` to `v23.0`.

Posts use `scheduled_queue.json`, `content/<id>.txt`, and `images/`; reels use `scheduled_reels_queue.json` and `reels/`. Public raw GitHub URLs use `GITHUB_REPOSITORY` and `GITHUB_REF_NAME`, falling back to `krazzynik/rofolo-ig-automation` and `main`.

Instagram-only queue entries use `pending`, `publishing`, `published`, and `failed`. A creation ID is saved before publishing for safe recovery, and existing `instagram_media_id` entries are skipped. Successful entries store the media ID, timestamp, and publisher; failures store the error and timestamp. Requests have timeouts, bounded retries for transient HTTP errors, and never log access tokens.

Checks: `python -m compileall .` and `python -m unittest discover -s tests`.

import json
import os
import tempfile
import time
from datetime import datetime, timezone

import requests


DEFAULT_REPOSITORY = "krazzynik/rofolo-ig-automation"
DEFAULT_BRANCH = "main"
DEFAULT_API_VERSION = "v23.0"
API_RETRY_STATUSES = {429, 500, 502, 503, 504}


class InstagramOnlyError(RuntimeError):
    """An expected, user-facing Instagram publishing error."""


def now_utc():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def api_base_url():
    version = os.environ.get("INSTAGRAM_GRAPH_API_VERSION", DEFAULT_API_VERSION)
    return f"https://graph.instagram.com/{version}"


def public_asset_url(directory, filename):
    repository = os.environ.get("GITHUB_REPOSITORY", DEFAULT_REPOSITORY)
    branch = os.environ.get("GITHUB_REF_NAME", DEFAULT_BRANCH)
    return f"https://raw.githubusercontent.com/{repository}/{branch}/{directory}/{filename}"


def require_credentials():
    user_id = os.environ.get("INSTAGRAM_ONLY_USER_ID")
    access_token = os.environ.get("INSTAGRAM_ONLY_ACCESS_TOKEN")
    if not user_id or not access_token:
        raise InstagramOnlyError(
            "Missing Instagram-only credentials: set INSTAGRAM_ONLY_USER_ID "
            "and INSTAGRAM_ONLY_ACCESS_TOKEN."
        )
    return user_id, access_token


def _safe_error(response):
    try:
        payload = response.json()
    except ValueError:
        payload = {"message": response.text[:300]}
    if isinstance(payload, dict) and payload.get("error"):
        error = payload["error"]
        if isinstance(error, dict):
            return error.get("message") or error.get("type") or "Meta API error"
    if isinstance(payload, dict):
        return payload.get("message") or "Meta API request failed"
    return "Meta API request failed"


def request(method, url, *, params, data=None, timeout=30, session=requests):
    """Call Meta with bounded retries while never logging credential-bearing data."""
    for attempt in range(4):
        try:
            response = session.request(
                method,
                url,
                params=params if method == "GET" else None,
                data=data if method != "GET" else None,
                timeout=timeout,
            )
        except requests.RequestException as exc:
            raise InstagramOnlyError(f"Meta API request failed: {exc.__class__.__name__}") from exc

        if response.status_code in API_RETRY_STATUSES and attempt < 3:
            time.sleep(2 ** attempt)
            continue
        try:
            payload = response.json()
        except ValueError as exc:
            raise InstagramOnlyError("Meta API returned invalid JSON.") from exc
        if response.status_code >= 400 or (isinstance(payload, dict) and payload.get("error")):
            raise InstagramOnlyError(_safe_error(response))
        return payload
    raise InstagramOnlyError("Meta API request failed after retries.")


def post(url, access_token, values):
    values = dict(values)
    values["access_token"] = access_token
    return request("POST", url, params=None, data=values)


def get(url, access_token, values):
    values = dict(values)
    values["access_token"] = access_token
    return request("GET", url, params=values)


def load_queue(path):
    with open(path, "r", encoding="utf-8") as queue_file:
        queue = json.load(queue_file)
    if not isinstance(queue, list):
        raise InstagramOnlyError(f"Queue must contain a JSON list: {path}")
    return queue


def save_queue(path, queue):
    directory = os.path.dirname(os.path.abspath(path)) or "."
    fd, temporary_path = tempfile.mkstemp(prefix="queue-", suffix=".json", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as queue_file:
            json.dump(queue, queue_file, indent=2, ensure_ascii=False)
            queue_file.write("\n")
        os.replace(temporary_path, path)
    finally:
        if os.path.exists(temporary_path):
            os.unlink(temporary_path)


def mark_publishing(item):
    item.update({
        "status": "publishing",
        "publisher": "instagram_only",
        "publishing_started_at": now_utc(),
    })


def mark_failed(item, error):
    item.update({
        "status": "failed",
        "last_error": str(error)[:500],
        "failed_at": now_utc(),
        "publisher": "instagram_only",
    })


def mark_published(item, media_id):
    item.update({
        "status": "published",
        "instagram_media_id": media_id,
        "published_at": now_utc(),
        "publisher": "instagram_only",
    })


def wait_for_container(creation_id, access_token, *, max_attempts=15, delay=10):
    url = f"{api_base_url()}/{creation_id}"
    for attempt in range(max_attempts):
        if attempt:
            time.sleep(delay)
        payload = get(url, access_token, {"fields": "status_code"})
        status_code = payload.get("status_code")
        if status_code == "FINISHED":
            return
        if status_code in {"ERROR", "EXPIRED"}:
            raise InstagramOnlyError(f"Container processing failed with status {status_code}.")
    raise InstagramOnlyError("Timed out waiting for Instagram container processing.")


def publish_container(user_id, access_token, creation_id, *, wait=True):
    if wait:
        wait_for_container(creation_id, access_token)
    payload = post(
        f"{api_base_url()}/{user_id}/media_publish",
        access_token,
        {"creation_id": creation_id},
    )
    media_id = payload.get("id")
    if not media_id:
        raise InstagramOnlyError("Instagram publish response did not include a media id.")
    return media_id

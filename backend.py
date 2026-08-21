"""Standalone Douyin API and 1080p-first downloader for the ComfyUI node."""

import os
import re
from datetime import datetime
from urllib.parse import parse_qs, quote, unquote, urlencode, urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)
TARGET_VIDEO_HEIGHT = 1080
QUALITY_HEIGHTS = {"480p": 480, "720p": 720, "1080p": 1080}
PAGE_SIZE = 50
_RESOLUTION_RE = re.compile(r"(?<!\d)(\d{3,5})p\b", re.IGNORECASE)


def _as_int(value):
    try:
        return max(0, int(float(value)))
    except (TypeError, ValueError):
        return 0


def _resolution_from_text(value):
    match = _RESOLUTION_RE.search(str(value or ""))
    return _as_int(match.group(1)) if match else 0


def _candidate_resolution(rate_info, url):
    rate_info = rate_info if isinstance(rate_info, dict) else {}
    width = _as_int(rate_info.get("width"))
    height = _as_int(rate_info.get("height"))
    pixels = width * height
    resolution = min(width, height) if width and height else width or height

    if not resolution:
        for key in ("quality", "quality_name", "gear_name", "ratio", "definition"):
            resolution = _resolution_from_text(rate_info.get(key))
            if resolution:
                break

    if not resolution:
        ratio = parse_qs(urlparse(url).query).get("ratio", [""])[0]
        resolution = _resolution_from_text(ratio)

    return resolution, pixels


def get_video_url_candidates(video_info, target_resolution=None):
    """Return video URLs ordered by quality, optionally preferring an exact tier.

    When an exact 480p/720p/1080p tier exists, it is returned first. If the
    requested tier is absent, the complete list remains ordered from the
    highest available resolution down, which implements the requested
    automatic fallback behavior.
    """
    if not isinstance(video_info, dict):
        return []

    rates = video_info.get("bit_rate") or []
    candidates = []
    for rate_index, rate_info in enumerate(rates):
        if not isinstance(rate_info, dict):
            continue
        url_list = (rate_info.get("play_addr") or {}).get("url_list") or []
        for url_index, url in enumerate(url_list):
            if not url:
                continue
            resolution, pixels = _candidate_resolution(rate_info, url)
            score = (
                int(resolution >= TARGET_VIDEO_HEIGHT),
                resolution,
                pixels,
                _as_int(rate_info.get("bit_rate")),
                -rate_index,
                -url_index,
            )
            candidates.append((score, str(url), resolution))

    # Some API responses omit bit_rate. Keep the generic sources as a fallback.
    for source_index, source in enumerate(
        (video_info.get("play_addr"), video_info.get("download_addr"))
    ):
        if not isinstance(source, dict):
            continue
        for url_index, url in enumerate(source.get("url_list") or []):
            if not url:
                continue
            resolution, pixels = _candidate_resolution(video_info, url)
            score = (
                int(resolution >= TARGET_VIDEO_HEIGHT),
                resolution,
                pixels,
                _as_int(video_info.get("bit_rate")),
                -(len(rates) + source_index),
                -url_index,
            )
            candidates.append((score, str(url), resolution))

    candidates.sort(key=lambda item: item[0], reverse=True)
    ordered = candidates
    if target_resolution:
        exact = [item for item in candidates if item[2] == int(target_resolution)]
        if exact:
            ordered = exact + [item for item in candidates if item[2] != int(target_resolution)]

    result = []
    seen = set()
    for _, url, _ in ordered:
        if url not in seen:
            seen.add(url)
            result.append(url)
    return result


def extract_aweme_id(url):
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    for key in ("aweme_id", "item_id", "modal_id"):
        query_id = query.get(key, [""])[0]
        if query_id:
            return query_id
    match = re.search(r"/(?:video|note)/(\d+)", parsed.path)
    return match.group(1) if match else None


def extract_aweme_id_from_text(text):
    """Extract an embedded work ID from a short-link landing page."""
    text = str(text or "")
    patterns = (
        r"(?:aweme_id|awemeId|modal_id|item_id)\s*[\"'=:]+\s*[\"']?(\d{8,})",
        r"/(?:video|note)/(\d{8,})",
    )
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return None


def extract_sec_user_id(url):
    patterns = (
        r"/user/([A-Za-z0-9_.\-]+)",
        r"sec_user_id=([A-Za-z0-9_.\-]+)",
        r"(MS4wLjAB[A-Za-z0-9_-]+)",
    )
    for pattern in patterns:
        match = re.search(pattern, url or "")
        if match:
            return match.group(1)
    return None


def create_session(cookie=""):
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Referer": "https://www.douyin.com/"})
    if cookie.strip():
        session.headers["Cookie"] = cookie.strip()
    retry = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(("GET",)),
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=20)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def _signed_url(base_url, params, abogus):
    signed_params = dict(params)
    signed_params["a_bogus"] = quote(abogus.get_value(signed_params), safe="")
    return f"{base_url}?{urlencode(signed_params)}"


def _get_json(session, url, timeout=30):
    response = session.get(url, timeout=timeout)
    response.raise_for_status()
    data = response.json()
    status_code = data.get("status_code")
    if status_code not in (None, 0):
        raise RuntimeError(
            f"Douyin API error: status_code={status_code}, "
            f"message={data.get('status_msg', '')}"
        )
    return data


def _detail_params(aweme_id):
    return {
        "device_platform": "webapp",
        "aid": "6383",
        "channel": "channel_pc_web",
        "pc_client_type": "1",
        "version_code": "190500",
        "version_name": "19.5.0",
        "cookie_enabled": "true",
        "browser_language": "zh-CN",
        "browser_platform": "Win32",
        "browser_name": "Chrome",
        "browser_online": "true",
        "engine_name": "Blink",
        "os_name": "Windows",
        "platform": "PC",
        "screen_width": "1920",
        "screen_height": "1080",
        "browser_version": "122.0.0.0",
        "engine_version": "122.0.0.0",
        "cpu_core_num": "12",
        "device_memory": "8",
        "aweme_id": aweme_id,
    }


def _post_params(sec_user_id, max_cursor, is_first_page):
    return {
        "device_platform": "webapp",
        "aid": "6383",
        "channel": "channel_pc_web",
        "sec_user_id": sec_user_id,
        "max_cursor": max_cursor,
        "count": PAGE_SIZE,
        "locate_query": "false",
        "show_live_replay_strategy": "1",
        "need_time_list": "1" if is_first_page else "0",
        "publish_video_strategy_type": "2",
        "from_user_page": "1",
        "update_version_code": "170400",
    }


def _fetch_aweme_detail(session, aweme_id, abogus):
    base_url = "https://www.douyin.com/aweme/v1/web/aweme/detail/"
    data = _get_json(session, _signed_url(base_url, _detail_params(aweme_id), abogus))
    aweme = data.get("aweme_detail")
    if not isinstance(aweme, dict):
        raise RuntimeError("未从链接中获取到作品信息，请检查 Cookie 或链接")
    return aweme


def fetch_aweme(source_url, cookie, video_index=0, max_pages=10):
    try:
        # Load the signer only when a download is actually queued.  This lets
        # ComfyUI register and display the node even when gmssl was installed
        # into a different Python environment; execution then reports the
        # actionable dependency error instead of hiding the whole node.
        from .abogus import ABogus
    except ImportError as exc:
        raise RuntimeError(
            "ComfyUI 节点缺少 gmssl，请使用 ComfyUI 实际运行的 Python 安装 "
            "comfyui_douyin_downloader/requirements.txt"
        ) from exc

    session = create_session(cookie)
    source_url = source_url.strip()
    abogus = ABogus()

    aweme_id = extract_aweme_id(source_url)
    if aweme_id:
        return session, _fetch_aweme_detail(session, aweme_id, abogus)

    landing_text = ""
    try:
        response = session.get(source_url, allow_redirects=True, timeout=20)
        resolved_url = response.url
        # Some short-link responses end at a generic page but embed the work
        # ID in JSON/HTML instead of exposing it in the final URL.
        landing_text = getattr(response, "text", "")
    except requests.RequestException:
        resolved_url = source_url

    # Short video share links usually redirect to /video/<aweme_id>.  Handle
    # that before trying to interpret the URL as a user homepage.
    resolved_aweme_id = extract_aweme_id(resolved_url) or extract_aweme_id_from_text(
        landing_text
    )
    if resolved_aweme_id:
        return session, _fetch_aweme_detail(session, resolved_aweme_id, abogus)

    sec_user_id = extract_sec_user_id(resolved_url) or extract_sec_user_id(source_url)
    if not sec_user_id:
        raise RuntimeError(
            "无法从链接中解析视频 ID 或 sec_user_id，请输入抖音视频链接、主页链接或分享链接"
        )

    base_url = "https://www.douyin.com/aweme/v1/web/aweme/post/"
    cursor = 0
    selected_index = 0
    for page in range(max(1, max_pages)):
        params = _post_params(sec_user_id, cursor, page == 0)
        data = _get_json(session, _signed_url(base_url, params, abogus))
        aweme_list = data.get("aweme_list") or []
        for aweme in aweme_list:
            if get_video_url_candidates(aweme.get("video")):
                if selected_index == max(0, video_index):
                    return session, aweme
                selected_index += 1

        if data.get("has_more") != 1 or not aweme_list:
            break
        cursor = data.get("max_cursor", 0)

    raise RuntimeError(f"未找到第 {video_index} 个视频，已检查 {selected_index} 个视频")


def _safe_filename(value):
    value = unquote(str(value or "")).strip()
    value = re.sub(r'[\\/*?:"<>|#\x00-\x1f]', "_", value)
    value = re.sub(r"\s+", " ", value).strip(" .")
    return (value or "douyin_video")[:150]


def download_aweme(
    session,
    aweme,
    output_dir,
    filename="",
    refresh=False,
    quality="1080p",
):
    target_resolution = QUALITY_HEIGHTS.get(str(quality).lower())
    candidates = get_video_url_candidates(
        aweme.get("video"), target_resolution=target_resolution
    )
    if not candidates:
        raise RuntimeError("该作品没有可用的视频源")

    os.makedirs(output_dir, exist_ok=True)
    if not filename.strip():
        create_time = aweme.get("create_time")
        date_text = ""
        if create_time:
            try:
                date_text = datetime.fromtimestamp(create_time).strftime("%Y-%m-%d_")
            except (TypeError, ValueError, OSError):
                pass
        filename = f"{date_text}{aweme.get('desc') or aweme.get('aweme_id') or 'douyin_video'}"
    filename = _safe_filename(filename)
    if not filename.lower().endswith(".mp4"):
        filename += ".mp4"
    path = os.path.abspath(os.path.join(output_dir, filename))

    if os.path.exists(path) and not refresh:
        return path, candidates[0]
    tmp_path = path + ".tmp"
    last_error = None

    for candidate_index, url in enumerate(candidates[:8]):
        if candidate_index > 0 and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass
        if refresh and candidate_index == 0 and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass

        headers = {}
        existing_size = os.path.getsize(tmp_path) if os.path.exists(tmp_path) else 0
        if existing_size:
            headers["Range"] = f"bytes={existing_size}-"

        try:
            with session.get(url, headers=headers, stream=True, timeout=(15, 120)) as response:
                if response.status_code == 416 and existing_size:
                    os.replace(tmp_path, path)
                    return path, url
                if response.status_code not in (200, 206):
                    response.raise_for_status()

                mode = "ab" if response.status_code == 206 and existing_size else "wb"
                with open(tmp_path, mode) as handle:
                    for chunk in response.iter_content(1024 * 512):
                        if chunk:
                            handle.write(chunk)
            os.replace(tmp_path, path)
            return path, url
        except Exception as exc:
            last_error = exc

    raise RuntimeError(f"视频下载失败: {last_error}")

"""ComfyUI node entry points for the standalone Music Note downloader."""

import os

from .backend import download_aweme, fetch_aweme
from .media import load_media_outputs

try:
    import folder_paths

    DEFAULT_OUTPUT_DIR = os.path.join(folder_paths.get_output_directory(), "douyin")
except ImportError:
    DEFAULT_OUTPUT_DIR = os.path.join(os.getcwd(), "output", "douyin")

try:
    # ComfyUI 0.31+ native VIDEO values are lazy file-backed objects.  A raw
    # path is only a STRING and cannot be connected to the native SaveVideo
    # node.
    from comfy_api.latest import InputImpl
except ImportError:
    InputImpl = None


class DouyinDownload1080P:
    """Download a target-platform video and expose native video, frames, audio and FPS."""

    CATEGORY = "video/音符"
    FUNCTION = "download"
    # ComfyUI 0.31+ accepts the file-backed native VIDEO object returned by
    # InputImpl.VideoFromFile.  This can connect directly to SaveVideo.
    RETURN_TYPES = ("VIDEO", "IMAGE", "AUDIO", "FLOAT")
    RETURN_NAMES = ("video", "image", "audio", "fps")
    # The download is a side effect.  Marking this as an output node makes a
    # workflow containing only this node executable from the ComfyUI queue.
    OUTPUT_NODE = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "source_url": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": False,
                        "placeholder": "音符视频链接",
                    },
                ),
                "cookie": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": True,
                        "placeholder": "可选：从浏览器复制的 Cookie",
                    },
                ),
                "quality": (
                    ["480p", "720p", "1080p"],
                    {"default": "1080p"},
                ),
            }
        }

    def download(self, source_url, cookie, quality):
        source_url = str(source_url or "").strip()
        if not source_url:
            raise ValueError("source_url 不能为空")

        cookie = str(cookie or "").strip()
        session, aweme = fetch_aweme(
            source_url,
            cookie,
        )
        path, _selected_source = download_aweme(
            session,
            aweme,
            DEFAULT_OUTPUT_DIR,
            quality=quality,
        )
        image, audio, fps = load_media_outputs(path)
        if InputImpl is None:
            raise RuntimeError(
                "当前 ComfyUI 不支持原生 VIDEO 类型，请升级到 ComfyUI 0.31 或更高版本"
            )
        video = InputImpl.VideoFromFile(path)
        return video, image, audio, fps


NODE_CLASS_MAPPINGS = {
    "DouyinDownload1080P": DouyinDownload1080P,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "DouyinDownload1080P": "音符视频提取（480/720/1080p）",
}

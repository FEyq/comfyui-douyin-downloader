# ComfyUI Douyin Downloader

ComfyUI 自定义节点：下载抖音视频并输出原生 `VIDEO`、视频帧、音频和帧率。

## 安装

将本目录复制到：

```text
ComfyUI/custom_nodes/comfyui_douyin_downloader
```

在 ComfyUI 根目录使用实际运行的 Python 安装依赖：

```bat
python\python.exe -m pip install -r ComfyUI\custom_nodes\comfyui_douyin_downloader\requirements.txt
```

如果当前命令行已位于本节点目录：

```bat
..\..\..\python\python.exe -m pip install -r requirements.txt
```

安装后完全重启 ComfyUI。

## 节点接口

输入：

- `source_url`：抖音视频链接或短链接。
- `cookie`：可选的抖音登录 Cookie。
- `quality`：`480p`、`720p` 或 `1080p`。

输出：

- `video`：ComfyUI 原生 `VIDEO`，可直接连接 `SaveVideo`，不需要 `CreateVideo`。
- `image`：`IMAGE` 视频帧批次。
- `audio`：`AUDIO` 音频字典；无音频时为空。
- `fps`：`FLOAT` 帧率。

节点会优先使用选择的清晰度；没有对应档位时自动选择最高可用清晰度。

示例工作流：`workflows/verify_1080p.json`

## 注意

Cookie 是敏感凭据，请不要写入工作流、日志或 GitHub。ComfyUI 运行时使用的 Python 必须安装 `requests`、`gmssl` 和 `av`。

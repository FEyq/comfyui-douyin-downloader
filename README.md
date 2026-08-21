# comfyui-抖音视频提取

ComfyUI 自定义节点：下载抖音视频，并输出原生 `VIDEO`、视频帧、音频和帧率。

## 安装

将本仓库放入：

```text
ComfyUI/custom_nodes/comfyui-douyin-downloader
```

使用 ComfyUI 实际运行的 Python 安装依赖。例如 ComfyUI Portable：

```bat
python_embeded\python.exe -m pip install -r custom_nodes\comfyui-douyin-downloader\requirements.txt
```

Aki 等版本请把上面的 Python 路径替换为对应的 `python.exe`。也可以在节点目录双击：

```text
install_comfyui_requirements.bat
```

安装完成后完全重启 ComfyUI。

## 节点接口

输入：

- `source_url`：抖音视频链接或短链接。
- `cookie`：可选的抖音登录 Cookie。
- `quality`：`480p`、`720p` 或 `1080p`。

输出：

- `video`：ComfyUI 原生 `VIDEO`，可直接连接 `SaveVideo`。
- `image`：`IMAGE` 视频帧批次。
- `audio`：`AUDIO` 音频字典；无音频时为空。
- `fps`：`FLOAT` 帧率。

节点会优先使用选择的清晰度；没有对应档位时自动选择最高可用清晰度。

示例工作流：`workflows/verify_1080p.json`

## 三步获取 Cookie

Cookie 只保存在本机，用于访问需要登录的抖音视频。获取脚本不会读取现有 Chrome/Edge 的 Cookie 数据库或密码。

1. 双击 `获取抖音Cookie.bat`。
2. 在自动打开的临时抖音页面中扫码登录。
3. 登录成功后，脚本窗口会自动显示 Cookie，并复制到剪贴板。

将复制的 Cookie 粘贴到节点的 `cookie` 输入框即可。脚本会自动检查并安装 Playwright；如果电脑没有可用的 Chrome/Edge，请执行：

```bash
python -m playwright install chromium
```

也可以使用命令行启动：

```bash
python cookie_helper.py
```

## 安全提示

Cookie 是登录凭据，请勿写入工作流、日志或 GitHub。脚本中的“保存到 config.ini”只用于本地保存，`config.ini` 已被 `.gitignore` 忽略；不要把它上传到仓库。

## 许可证

MIT License。请遵守抖音服务条款、版权和隐私相关法律法规，仅下载你有权使用的内容。

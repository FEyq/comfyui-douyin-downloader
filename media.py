"""Decode a downloaded video into ComfyUI-compatible media values."""

from __future__ import annotations

import os


def _video_fps(stream):
    """Return a stream's frame rate without failing on incomplete metadata."""
    for value in (
        getattr(stream, "average_rate", None),
        getattr(stream, "base_rate", None),
        getattr(stream, "guessed_rate", None),
        getattr(stream, "guess_rate", None),
    ):
        if value:
            try:
                return float(value)
            except (TypeError, ValueError, ZeroDivisionError):
                pass
    return 0.0


def _stream_description(stream):
    """Build safe diagnostic text; never include request headers or cookies."""
    codec_context = getattr(stream, "codec_context", None)
    codec_name = getattr(codec_context, "name", None) or "unknown"
    width = getattr(codec_context, "width", None) or getattr(stream, "width", None)
    height = getattr(codec_context, "height", None) or getattr(stream, "height", None)
    index = getattr(stream, "index", "?")
    return f"index={index}, codec={codec_name}, size={width}x{height}"


def _get_stream(container, media_type):
    streams = list(getattr(container.streams, media_type))
    if not streams:
        raise RuntimeError(
            "下载的文件没有视频轨道" if media_type == "video" else "下载的文件没有音频轨道"
        )
    return streams[0]


def _decode_stream(path, av, media_type):
    """Decode one stream without using ``stream.index``.

    Some PyAV builds resolve ``container.decode(video=<index>)`` against a
    filtered stream collection.  A real stream index can therefore be out of
    range even though the stream exists.  Passing the stream object avoids
    that ambiguity.  The demux path is retained as a compatibility fallback
    for older/newer PyAV combinations.
    """
    with av.open(path) as container:
        stream = _get_stream(container, media_type)
        description = _stream_description(stream)
        fps = _video_fps(stream) if media_type == "video" else 0.0

        try:
            frames = list(container.decode(stream))
        except Exception as direct_error:
            # Reopen the file before retrying: a failed decoder may already
            # have consumed packets from the first container.
            try:
                with av.open(path) as retry_container:
                    retry_stream = _get_stream(retry_container, media_type)
                    frames = []
                    for packet in retry_container.demux(retry_stream):
                        frames.extend(packet.decode())
                    if media_type == "video":
                        fps = _video_fps(retry_stream)
            except Exception as demux_error:
                raise RuntimeError(
                    f"{media_type} 轨道解码失败（{description}）；"
                    f"stream/demux 错误：{demux_error}"
                ) from direct_error

        return frames, fps


def _load_audio(path, av, torch):
    try:
        frames, _ = _decode_stream(path, av, "audio")
    except RuntimeError as exc:
        # A video-only file is valid.  _get_stream already distinguishes this
        # case, so only suppress the explicit "no audio track" condition.
        if "没有音频轨道" in str(exc):
            return None
        raise

    if not frames:
        return None

    chunks = []
    for frame in frames:
        # ComfyUI AUDIO convention: [batch, channels, samples].
        # PyAV 16's AudioFrame.to_ndarray() does not accept a format keyword.
        # The decoded frame already carries its sample format, so convert the
        # returned array to normalized float32 here instead.
        array = frame.to_ndarray()
        tensor = torch.from_numpy(array)
        if tensor.ndim == 1:
            tensor = tensor.unsqueeze(0)
        if not tensor.is_floating_point():
            info = torch.iinfo(tensor.dtype)
            scale = float(max(abs(info.min), info.max))
            tensor = tensor.to(dtype=torch.float32) / scale
        else:
            tensor = tensor.to(dtype=torch.float32)
        chunks.append(tensor)

    if not chunks:
        return None

    waveform = torch.cat(chunks, dim=-1).to(dtype=torch.float32).unsqueeze(0)
    sample_rate = int(getattr(frames[0], "sample_rate", None) or 44100)
    return {"waveform": waveform, "sample_rate": sample_rate}


def load_media_outputs(path):
    """Return ``(images, audio, fps)`` for a local video file.

    ``images`` is a ComfyUI IMAGE batch in ``[frames, height, width, RGB]``
    format. ``audio`` follows ComfyUI's ``AUDIO`` dictionary convention and
    is ``None`` when the source has no audio track.
    """
    if not os.path.isfile(path):
        raise RuntimeError(f"视频文件不存在：{path}")

    try:
        import av
        import numpy as np
        import torch
    except ImportError as exc:
        raise RuntimeError(
            "ComfyUI 节点缺少视频解码依赖 av，请使用 ComfyUI 实际运行的 Python "
            "重新安装节点 requirements.txt"
        ) from exc

    try:
        frames, fps = _decode_stream(path, av, "video")
        if not frames:
            raise RuntimeError("视频没有可解码的图像帧")

        image = torch.from_numpy(
            np.stack([frame.to_ndarray(format="rgb24") for frame in frames])
        ).to(dtype=torch.float32) / 255.0
        audio = _load_audio(path, av, torch)
        return image, audio, float(fps)
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(f"视频帧/音频解码失败：{exc}") from exc

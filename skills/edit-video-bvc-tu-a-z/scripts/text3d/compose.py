#!/usr/bin/env python3
"""compose — ghép 3D: [video có chữ] + [nhân vật tách từ video gốc] đè lên trên → chữ chìm sau người
  python compose.py <text_layer.mp4> <video_gốc.mp4> <mask.mp4> -o <out.mp4> [--no-mask 13.2-17.5,40-44]
--no-mask: các khoảng không có người ngồi (cảnh chèn, quay màn hình…) → tắt mask, chữ nằm TRÊN hình.
Tiếng lấy từ text_layer (đã có SFX). text_layer phải render với "punch": false (zoom làm lệch 2 lớp).
"""
import argparse
import json
import subprocess

def _mac_vt(preview, w=3840, h=2160, fps=30):
    """macOS (Apple Silicon lẫn Intel): bộ nén phần cứng VideoToolbox — nhanh ~6 lần libx264, chất lượng gần bằng.
    Trả về tham số ffmpeg ["-c:v", "h264_videotoolbox", ...] hoặc None (không phải Mac / máy không hỗ trợ /
    đặt biến môi trường HMT_CPU=1 để ép nén bằng CPU)."""
    import os as _os, subprocess as _sp, sys as _sys
    if _sys.platform != "darwin" or _os.environ.get("HMT_CPU"):
        return None

    def ok(*o):
        return _sp.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=black:s=256x256:d=0.1",
                        "-c:v", "h264_videotoolbox", *o, "-f", "null", "-"], capture_output=True).returncode == 0
    base = ["-c:v", "h264_videotoolbox", "-profile:v", "high"]
    if ok("-q:v", "60"):            # chip Apple (M1/M2/M3/M4…): chất lượng cố định (đo 4K: q75 ≈ SSIM 0.992)
        return base + ["-q:v", "55" if preview else "75"]
    if ok("-b:v", "5M"):            # Mac Intel: VideoToolbox chỉ nén theo bitrate → tính theo độ phân giải
        mbps = max(4, round(w * h * fps * (0.04 if preview else 0.11) / 1e6))
        return base + ["-b:v", f"{mbps}M", "-maxrate", f"{int(mbps * 1.5)}M", "-bufsize", f"{mbps * 2}M"]
    return None

ap = argparse.ArgumentParser()
ap.add_argument("text")
ap.add_argument("orig")
ap.add_argument("mask")
ap.add_argument("-o", "--out", required=True)
ap.add_argument("--no-mask", default="")
a = ap.parse_args()
st = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                "stream=width,height", "-of", "json", a.text], capture_output=True,
                               text=True).stdout)["streams"][0]
w, h = st["width"], st["height"]
off = ""
for r in filter(None, a.no_mask.split(",")):
    s, e = r.split("-")
    off += f",drawbox=x=0:y=0:w=iw:h=ih:color=black:t=fill:enable='between(t,{s},{e})'"
fc = (f"[2:v]scale={w}:{h},format=gray{off}[m];[1:v]scale={w}:{h},format=rgba[o];[o][m]alphamerge[p];"
      f"[0:v][p]overlay=format=auto,format=yuv420p[v]")
enc = ["-preset", "veryfast", "-crf", "20"] if w * h < 2_500_000 else ["-preset", "slow", "-crf", "17"]
subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", a.text, "-i", a.orig, "-i", a.mask,
                "-filter_complex", fc, "-map", "[v]", "-map", "0:a", *(_mac_vt(False, w, h) or ["-c:v", "libx264", *enc]), "-c:a", "copy",
                "-movflags", "+faststart", a.out], check=True)
print("Xong →", a.out)

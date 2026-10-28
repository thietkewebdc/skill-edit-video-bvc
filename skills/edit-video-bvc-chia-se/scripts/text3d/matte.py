#!/usr/bin/env python3
"""matte — tách NHÂN VẬT khỏi nền bằng Robust Video Matting (ONNX, CPU) → mask xám (trắng = người)
  python matte.py <video> -o <work>/mask.mp4
Cần file mô hình rvm_mobilenetv3_fp32.onnx (~14 MB) nằm cạnh script này.
Nguồn chính thức: https://github.com/PeterL1n/RobustVideoMatting/releases/download/v1.0.0/rvm_mobilenetv3_fp32.onnx
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
MODEL = HERE / "rvm_mobilenetv3_fp32.onnx"

ap = argparse.ArgumentParser()
ap.add_argument("video")
ap.add_argument("-o", "--out", required=True)
a = ap.parse_args()
if not MODEL.exists():
    sys.exit(f"THIẾU mô hình {MODEL.name} — xin phép người dùng rồi tải (~14 MB) từ trang phát hành chính thức\n"
             "https://github.com/PeterL1n/RobustVideoMatting/releases/download/v1.0.0/rvm_mobilenetv3_fp32.onnx\n"
             f"và đặt vào {HERE}")
import onnxruntime as ort  # noqa: E402

st = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                "stream=width,height,r_frame_rate", "-of", "json", a.video],
                               capture_output=True, text=True).stdout)["streams"][0]
sw, sh = st["width"], st["height"]
n, d = st["r_frame_rate"].split("/")
fps = float(n) / float(d)
k = 1920 / max(sw, sh)                                   # xử lý ở cạnh dài 1920 (đủ nét, nhanh)
Wd, Hd = int(sw * k) // 2 * 2, int(sh * k) // 2 * 2
sess = ort.InferenceSession(str(MODEL), providers=["CPUExecutionProvider"])
dec = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-i", a.video, "-vf", f"scale={Wd}:{Hd}",
                        "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{Wd}x{Hd}",
                        "-r", f"{fps:.3f}", "-i", "-", "-c:v", "libx264", "-crf", "8", "-pix_fmt", "yuv420p", a.out],
                       stdin=subprocess.PIPE)
rec = [np.zeros([1, 1, 1, 1], np.float32)] * 4
ds = np.array([0.25], np.float32)
cnt = 0
while True:
    buf = dec.stdout.read(Wd * Hd * 3)
    if len(buf) < Wd * Hd * 3:
        break
    x = (np.frombuffer(buf, np.uint8).reshape(Hd, Wd, 3).astype(np.float32) / 255).transpose(2, 0, 1)[None]
    _, pha, *rec = sess.run(None, {"src": x, "r1i": rec[0], "r2i": rec[1], "r3i": rec[2], "r4i": rec[3],
                                   "downsample_ratio": ds})
    enc.stdin.write((pha[0, 0] * 255).clip(0, 255).astype(np.uint8).tobytes())
    cnt += 1
enc.stdin.close()
enc.wait()
print(f"{cnt} khung → {a.out}")

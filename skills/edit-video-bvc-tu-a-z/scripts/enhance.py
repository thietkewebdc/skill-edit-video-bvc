#!/usr/bin/env python3
"""enhance — đưa âm lượng giọng nói về chuẩn cho video ĐÃ CẮT (chạy trước bước phủ chữ).
Hình giữ nguyên (copy, không encode lại). KHÔNG làm đẹp hình (chủ kênh chốt).
Khử ồn là TÙY CHỌN (--denoise): bật khi nền ồn (quán cà phê, quạt, xe…), xem `denoise.py --check`.

  python enhance.py <cut.mp4> -o <cut_enh.mp4> [--lufs -14] [--denoise [0.85]]

• loudnorm về --lufs (mặc định -14 LUFS: chuẩn TikTok / YouTube / Facebook), LRA 7 (đoạn nhỏ nâng lên,
  đoạn to hạ xuống → không quá to, không quá nhỏ), đỉnh tối đa -1.5 dBTP (không rè).
• Chạy 2 lượt (đo rồi chuẩn): loudnorm 1 lượt thường hụt ~2 LUFS.
"""
import argparse
import json
import re
import subprocess
import sys


def measure(video, lufs):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", video, "-map", "0:a", "-af",
                        f"loudnorm=I={lufs}:LRA=7:TP=-1.5:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True)
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", r.stderr, re.S)
    return json.loads(m.group(0)) if m else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video"); ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--lufs", type=float, default=-14, help="độ lớn chuẩn (LUFS)")
    ap.add_argument("--denoise", nargs="?", const=0.85, type=float, default=None, metavar="MIX",
                    help="khử ồn RNNoise trước khi chuẩn âm; MIX = tỉ lệ tiếng đã khử (mặc định 0.85)")
    a = ap.parse_args()
    if a.denoise is not None:
        import os, tempfile
        tmp = os.path.join(tempfile.mkdtemp(), "dn.mp4")
        subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "denoise.py"), a.video, "-o", tmp, "--mix", str(a.denoise)], check=True)
        a.video = tmp
    f = f"loudnorm=I={a.lufs}:LRA=7:TP=-1.5"
    m = measure(a.video, a.lufs)
    if m:
        f += (f":measured_I={m['input_i']}:measured_LRA={m['input_lra']}:measured_TP={m['input_tp']}"
              f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", a.video, "-map", "0:v", "-map", "0:a", "-c:v", "copy",
                    "-af", f"{f},aresample=48000,aformat=channel_layouts=stereo",
                    "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", a.out], check=True)
    print(f"Xong → {a.out}  (âm lượng chuẩn {a.lufs} LUFS)")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()

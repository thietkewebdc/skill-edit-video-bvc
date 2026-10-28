#!/usr/bin/env python3
"""add_music — thêm nhạc nền vào video đã hoàn thiện (bước cuối, tùy chọn).

  python add_music.py <video> <nhạc.mp3> -o <out.mp4> [--rel -17] [--fade 4] [--xfade 3]

• San đều âm lượng các đoạn trong bài nhạc (loudnorm, LRA thấp) rồi đặt cả bài thấp hơn giọng nói
  `--rel` dB (mặc định -17 dB: riu riu, không lấn tiếng). Giọng đo bằng EBU R128 trên chính video.
• Nhạc ngắn hơn video → tự lặp lại, nối mượt bằng crossfade `--xfade` giây.
• Mở nhẹ 1.5s đầu, nhỏ dần `--fade` giây cuối video. Hình giữ nguyên (copy, không encode lại).
"""
import argparse
import math
import re
import subprocess
import sys


def dur(path):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                                capture_output=True, text=True, check=True).stdout.strip())


def loudness(path):
    err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-vn", "-af", "ebur128", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    vals = re.findall(r"^\s+I:\s+(-?[\d.]+) LUFS", err, re.M)
    return float(vals[-1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video"); ap.add_argument("music"); ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--rel", type=float, default=-17.0, help="nhạc thấp hơn giọng bao nhiêu dB")
    ap.add_argument("--fade", type=float, default=4.0)
    ap.add_argument("--fade-in", type=float, default=1.5)
    ap.add_argument("--xfade", type=float, default=3.0)
    a = ap.parse_args()

    D, L = dur(a.video), dur(a.music)
    voice = loudness(a.video)
    target = voice + a.rel
    n = max(1, math.ceil((D - a.xfade) / (L - a.xfade)))
    inputs = ["-i", a.video]
    for _ in range(n):
        inputs += ["-i", a.music]
    norm = f"loudnorm=I={target:.1f}:LRA=3:TP=-6,aresample=48000,aformat=channel_layouts=stereo"
    parts = [f"[{k + 1}:a]{norm}[m{k}]" for k in range(n)]
    last = "m0"
    for k in range(1, n):
        parts.append(f"[{last}][m{k}]acrossfade=d={a.xfade}:c1=tri:c2=tri[x{k}]")
        last = f"x{k}"
    parts.append(f"[{last}]atrim=0:{D:.3f},asetpts=PTS-STARTPTS,afade=t=in:d={a.fade_in},"
                 f"afade=t=out:st={max(0, D - a.fade):.3f}:d={a.fade}[bg]")
    parts.append("[0:a]aresample=48000[v];[v][bg]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[a]")
    fc = ";".join(parts)
    subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", fc, "-map", "0:v", "-map", "[a]",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", a.out], check=True)
    print(f"Giọng {voice:.1f} LUFS → nhạc {target:.1f} LUFS ({a.rel:+.0f} dB), lặp {n} lần, fade cuối {a.fade}s → {a.out}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()

#!/usr/bin/env python3
"""Giai đoạn C — ẢNH BÌA / THUMBNAIL (phát triển bởi Bùi Viết Cường).
  python3 thumb.py frames  <video> <thư_mục_ra> [--n 12]          # trích ~12 khung có mặt rõ, chọn khung đẹp nhất
  python3 thumb.py make --photo <ảnh|video> [--at 12.5] --hook "LƯƠNG 120 TRIỆU|VẪN VỠ NỢ|VÌ 600 TRIỆU?" \
        --out <tiền_tố> [--sizes 9x16,16x9,1x1] [--variants A,B] [--tag "#Bùi Viết Cường"] [--avatar <png>] [--icon auto|dollar|clock|chart|none]
Ra <tiền_tố>_<kiểu>_<khung>.jpg + <tiền_tố>_check.jpg (thu nhỏ 160px + vùng an toàn TikTok)."""
import argparse, os, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image, ImageDraw
from cover_v2 import compose_thumbnail, black

AV = os.path.expanduser("~/.claude/skills/edit-kieu-toan-khung-chuyen-nghiep/assets/avatar-giang-vien.png")
SIZES = {"9x16": (1080, 1920), "16x9": (1280, 720), "1x1": (1080, 1080)}

def grab(path, at):
    if path.lower().endswith((".png", ".jpg", ".jpeg", ".webp")): return Image.open(path)
    t = os.path.join(tempfile.mkdtemp(), "f.png"); subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(at or 0), "-i", path, "-frames:v", "1", t], check=True); return Image.open(t)

def cmd_frames(a):
    import cv2, numpy as np
    os.makedirs(a.outdir, exist_ok=True); dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", a.video]))
    casc = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml"); eyes = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_eye.xml"); rows = []
    for i in range(a.n * 3):
        t = dur * (i + 0.5) / (a.n * 3); f = os.path.join(a.outdir, f"_t{t:07.2f}.png")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(t), "-i", a.video, "-frames:v", "1", "-vf", "scale=-2:960", f], check=True)
        g = cv2.cvtColor(cv2.imread(f), cv2.COLOR_BGR2GRAY); fs = casc.detectMultiScale(g, 1.1, 5, minSize=(60, 60))
        if not len(fs): os.remove(f); continue
        x, y, w, h = max(fs, key=lambda q: q[2] * q[3]); sharp = cv2.Laplacian(g[y:y + h, x:x + w], cv2.CV_64F).var(); ne = len(eyes.detectMultiScale(g[y:y + h // 2, x:x + w], 1.1, 4))
        rows.append((sharp * (1.0 + 0.4 * min(ne, 2)) * (0.6 + w / g.shape[1]), t, f))
    rows.sort(reverse=True)
    for k, (s, t, f) in enumerate(rows[:a.n], 1): os.rename(f, os.path.join(a.outdir, f"khung{k:02d}_{t:.1f}s.png"))
    for _, _, f in rows[a.n:]: os.remove(f)
    print(f"Đã lưu {min(a.n, len(rows))} khung vào {a.outdir} (xếp theo độ nét + mắt mở + mặt to). Chọn 1 khung rồi chạy: thumb.py make --photo <khung> ...")

def safe_sheet(res, path, name):
    W, H = res.size; s = res.resize((W * 270 // H if H > W else 270, 270 if H > W else H * 270 // W)); sm = res.resize((max(80, W * 160 // max(W, H)), max(80, H * 160 // max(W, H))))
    ov = res.copy().convert("RGBA"); d = ImageDraw.Draw(ov, "RGBA")
    if H > W:  # vùng cần tránh của TikTok
        d.rectangle([0, 0, W, int(H * 0.10)], fill=(255, 0, 0, 70)); d.rectangle([int(W * 0.84), int(H * 0.50), W, int(H * 0.80)], fill=(255, 0, 0, 70)); d.rectangle([0, int(H * 0.80), W, H], fill=(255, 0, 0, 55))
    return sm, ov.convert("RGB").resize(s.size)

def cmd_make(a):
    photo = grab(a.photo, a.at); hook = a.hook.split("|"); outs = []; sheet = []
    for v in a.variants.split(","):
        for sz in a.sizes.split(","):
            o = f"{a.out}_{v}_{sz}.jpg"; res, found = compose_thumbnail(photo, hook, o, SIZES[sz], a.tag, os.path.expanduser(a.avatar), v, a.icon); outs.append(o)
            if not found: print(f"! {o}: không dò thấy mặt, dùng khung mặc định, kiểm tra lại")
            if sz == "9x16": sheet.append(safe_sheet(res, o, v))
            print("ok", o)
    if sheet:
        Wd = sum(s[0].width + s[1].width + 30 for s in sheet); Hd = max(s[1].height for s in sheet) + 20; cv = Image.new("RGB", (Wd, Hd), (30, 30, 36)); x = 10
        for sm, ov in sheet: cv.paste(sm, (x, 10)); x += sm.width + 10; cv.paste(ov, (x, 10)); x += ov.width + 20
        cv.save(f"{a.out}_check.jpg", quality=90); print("kiểm tra mobile + vùng an toàn:", f"{a.out}_check.jpg")

ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest="cmd", required=True)
f = sp.add_parser("frames"); f.add_argument("video"); f.add_argument("outdir"); f.add_argument("--n", type=int, default=12)
m = sp.add_parser("make"); m.add_argument("--photo", required=True); m.add_argument("--at", type=float, default=0); m.add_argument("--hook", required=True); m.add_argument("--out", required=True)
m.add_argument("--sizes", default="9x16,16x9,1x1"); m.add_argument("--variants", default="A,B"); m.add_argument("--tag", default="#Bùi Viết Cường"); m.add_argument("--avatar", default=AV); m.add_argument("--icon", default="auto")
a = ap.parse_args(); (cmd_frames if a.cmd == "frames" else cmd_make)(a)

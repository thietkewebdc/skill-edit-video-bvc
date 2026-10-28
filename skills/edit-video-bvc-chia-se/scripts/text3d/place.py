#!/usr/bin/env python3
"""place — tự đặt vị trí + độ rộng khối chữ để chữ chìm SAU người mà vẫn đọc được (luật chủ kênh):
  • mỗi CHỮ CÁI bị che TỐI ĐA 1/2, tối đa 2 chữ cái bị chạm (đo suốt thời gian chữ hiện, percentile 95)
  • các dòng rộng BẰNG NHAU (tw), chữ càng to càng tốt; có ít nhất 1 chữ cái chìm một phần (chiều sâu 3D)
  python place.py <video> <mask.mp4> <plan_3d_base.json> -o <plan_3d.json>
Mục có "auto_place": true được đặt tự động (ghi x, y, tw); mục khác giữ nguyên.
"""
import argparse
import json
import subprocess
from pathlib import Path

import numpy as np

import engine3d as R

S = R.S
MAX_OCC, MAX_TOUCH, TOUCH = 0.50, 2, 0.08

ap = argparse.ArgumentParser()
ap.add_argument("video")
ap.add_argument("mask")
ap.add_argument("plan")
ap.add_argument("-o", "--out", required=True)
a = ap.parse_args()

st = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                "stream=width,height", "-of", "json", a.video], capture_output=True,
                               text=True).stdout)["streams"][0]
S.H = round(S.W * st["height"] / st["width"])
MW, MH = S.W, S.H


def mask_frames(t0, t1):
    r = subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", f"{t0}", "-i", a.mask, "-t", f"{t1 - t0}",
                        "-vf", f"fps=15,scale={MW}:{MH}", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                       capture_output=True)
    fr = (np.frombuffer(r.stdout, np.uint8).reshape(-1, MH, MW) > 127).astype(np.float32)
    ii = np.pad(fr.cumsum(1).cumsum(2), ((0, 0), (1, 0), (1, 0)))
    return ii, np.linspace(t0, t1, len(fr), endpoint=False)


def letters(e):
    lay = R.sync_layout(e)
    at = e.get("at", [e["start"]] * len(lay))
    out = []
    for (i, w, acc, cx, cy, fs, ww), t in zip(lay, at):
        if w == "·":
            continue
        left, hh = cx - ww / 2, 0.26 * fs
        for k in range(len(w)):
            xa = left + (S.text_width(w[:k], fs) if k else 0)
            out.append((xa, cy - hh, left + S.text_width(w[:k + 1], fs), cy + hh, t))
    return out


def evaluate(ii, ts, L):
    xs = [v for b in L for v in (b[0], b[2])]
    ys = [v for b in L for v in (b[1], b[3])]
    if min(xs) < 0.03 * MW or max(xs) > 0.97 * MW or min(ys) < 0.03 * MH or max(ys) > 0.97 * MH:
        return None
    occ = []
    for xa, ya, xb, yb, t in L:
        x0, x1, y0, y1 = int(max(0, xa)), int(min(MW, xb)), int(max(0, ya)), int(min(MH, yb))
        ar = ii[:, y1, x1] - ii[:, y0, x1] - ii[:, y1, x0] + ii[:, y0, x0]
        sel = ts >= t - 0.05
        ar = (ar[sel] if sel.any() else ar) / max(1, (x1 - x0) * (y1 - y0))
        occ.append(float(np.percentile(ar, 95)))
    occ = np.array(occ)
    return occ.max(), int((occ > TOUCH).sum())


plan = json.loads(Path(a.plan).read_text(encoding="utf-8-sig"))
for e in plan.get("emphasis", []):
    if not e.get("auto_place"):
        continue
    ii, ts = mask_frames(e["start"], e["end"])
    best = None
    for tw in (0.84, 0.78, 0.72, 0.66, 0.60, 0.54, 0.48, 0.44, 0.40, 0.36, 0.33, 0.30):
        if best and best[0][0]:
            break                                   # đã có cỡ to nhất đạt luật
        # "y_min" (plan hoặc từng khối): tâm khối không cao hơn mức này — 0.12 mặc định đẩy chữ sát đỉnh khung,
        # chạm thanh "Đang theo dõi / Dành cho bạn" của TikTok (Ngày 3 short 2026-10-03 → 0.18)
        for y in np.arange(float(e.get("y_min", plan.get("y_min", 0.12))), 0.62, 0.02):
            L0 = letters(dict(e, x=0.5, y=float(y), tw=tw))
            for x in np.arange(0.10, 0.91, 0.01):
                dx = (x - 0.5) * MW
                r = evaluate(ii, ts, [(p + dx, q, u + dx, v, t) for p, q, u, v, t in L0])
                if r is None:
                    continue
                mo, nt = r
                ok = mo <= MAX_OCC and nt <= MAX_TOUCH
                score = (ok, tw, 1 if 0.2 <= mo <= MAX_OCC else 0, -abs(y - 0.26), 0 if ok else -mo)
                if best is None or score > best[0]:
                    best = (score, round(float(x), 2), round(float(y), 2), tw, mo, nt)
    _, e["x"], e["y"], e["tw"], mo, nt = best
    e.pop("fs", None)
    e.pop("auto_place")
    print(f"{e['start']:>7}s {'OK' if best[0][0] else '!! KHÔNG ĐẠT'} tw={e['tw']:.2f} x={e['x']:.2f} "
          f"y={e['y']:.2f} che nhiều nhất {mo * 100:.0f}% 1 chữ cái, {nt} chữ cái bị chạm | {e['text']}")
Path(a.out).write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
print("→", a.out)

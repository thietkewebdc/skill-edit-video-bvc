# -*- coding: utf-8 -*-
"""NGƯỜI QUE NÉT CHÌ — dựng video hoạt hình từ voice over.

  python stick.py plan   voice.mp3 -o DỰ_ÁN/        # nghe voice → words.json + scenes.json (1 câu = 1 cảnh)
  python stick.py still  DỰ_ÁN/scenes.json --scene 3 [--at 0.5] -o a.png
  python stick.py sheet  DỰ_ÁN/scenes.json -o sheet.png [--at 0.6]     # tờ duyệt: mọi cảnh trên 1 ảnh
  python stick.py render DỰ_ÁN/scenes.json -o out.mp4 [--preview] [--scenes 3-5] [--cpu]
"""
import argparse, copy, json, math, os, re, subprocess, sys, time, unicodedata

import numpy as np, skia

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stickdraw import *  # noqa

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

# ───────────────────────── tiện ích ─────────────────────────
def die(msg):
    print("LỖI:", msg, file=sys.stderr)
    sys.exit(1)


def norm_tok(s):
    s = unicodedata.normalize("NFC", s.lower())
    return re.sub(r"[^\w]", "", s)


def load_plan(path):
    with open(path, encoding="utf-8-sig") as f:
        plan = json.load(f)
    base = os.path.dirname(os.path.abspath(path))
    plan["_base"] = base
    wp = plan.get("words")
    plan["_words"] = []
    if wp:
        wp = wp if os.path.isabs(wp) else os.path.join(base, wp)
        if os.path.exists(wp):
            with open(wp, encoding="utf-8") as f:
                plan["_words"] = json.load(f)
    return plan


def resolve_t(val, scene, plan):
    """số giây (tính từ đầu cảnh) | "cụm từ" | "cụm từ+0.3" → giây tính từ đầu cảnh."""
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val)
    off = 0.0
    m = re.match(r"^(.*?)([+-]\d+(?:\.\d+)?)$", s.strip())
    if m and m.group(1).strip():
        s, off = m.group(1), float(m.group(2))
    toks = [norm_tok(x) for x in s.split() if norm_tok(x)]
    W = [w for w in plan["_words"] if scene["start"] - 0.4 <= w["s"] <= scene["end"] + 0.2]
    nw = [norm_tok(w["w"]) for w in W]
    for i in range(len(W) - len(toks) + 1):
        if nw[i:i + len(toks)] == toks:
            return W[i]["s"] - scene["start"] + off
    print(f"  ! cảnh {scene.get('i', '?')}: không tìm thấy từ '{val}' — dùng 0s", file=sys.stderr)
    return 0.0


# ───────────────────────── trạng thái phần tử theo thời gian ─────────────────────────
DEF = dict(opacity=1.0, dark=0.0, glow=0.0, crack=0.0, rot=0.0, broken=0.0, mend=0.0, grow=1.0, open=1.0, light=1.0, face=0.0,
           leaves=0.0, beat=0.0, reach_w=1.0, draw=1.0, rain=0.0, weight=1.0, h=0.55, s=0.3, x=0.5, y=0.8)


def prep_items(items, scene, plan):
    cast = plan.get("cast", {})
    out = []
    for n, it in enumerate(items):
        it = copy.deepcopy(it)
        if it.get("type", "fig") == "fig" and it.get("id") in cast:
            merged = copy.deepcopy(cast[it["id"]])
            merged.update(it)
            it = merged
        it.setdefault("type", "fig")
        it["_seed"] = abs(hash(str(it.get("id", n)))) % 9973 if it.get("id") else 101 + n * 37
        ks = []
        for k in it.get("keys", []):
            k = dict(k)
            k["_t"] = resolve_t(k.get("t", 0), scene, plan)
            ks.append(k)
        it["keys"] = sorted(ks, key=lambda k: k["_t"])
        for fld in ("appear", "vanish"):
            if fld in it:
                it["_" + fld] = resolve_t(it[fld], scene, plan)
        out.append(it)
    return out


def eval_item(it, t):
    st = {k: v for k, v in it.items() if k != "keys"}
    for k, v in DEF.items():
        st.setdefault(k, v)
    ang = pose_angles(st.get("pose", "stand")) if st["type"] in ("fig", "crowd") else None
    for k in it["keys"]:
        if t < k["_t"]:
            break
        d = k.get("d", 0.6)
        f = ease((t - k["_t"]) / d) if d > 0 else 1.0
        for key, val in k.items():
            if key in ("t", "d", "_t"):
                continue
            if key == "pose" and ang is not None:
                ang = blend_pose(ang, pose_angles(val), f)
                st["pose"] = val
            elif isinstance(val, (int, float)) and not isinstance(val, bool) and isinstance(st.get(key), (int, float)):
                st[key] = lerp(st[key], val, f)
            elif isinstance(val, list) and isinstance(st.get(key), list) and len(val) == len(st[key]) and all(
                    isinstance(v, (int, float)) for v in val):
                st[key] = [lerp(a, b, f) for a, b in zip(st[key], val)]
            else:
                st[key] = val
    if "_appear" in st:
        st["opacity"] *= ease((t - st["_appear"]) / 0.35)
    if "_vanish" in st:
        st["opacity"] *= 1 - ease((t - st["_vanish"]) / 0.35)
    st["_ang"] = ang
    return st


def apply_do(st, t, it):
    do = st.get("do") or []
    if isinstance(do, str):
        do = [do]
    ang = {k: (list(v) if isinstance(v, tuple) else v) for k, v in (st["_ang"] or {}).items()}
    ph0 = (st["_seed"] % 100) / 100.0
    bob, dx = 0.0, 0.0
    st["_talk"] = False
    for m in do:
        if m == "walk":
            x1 = eval_item(it, t - 0.05)["x"]
            x2 = eval_item(it, t + 0.05)["x"]
            moving = abs(x2 - x1) > 1e-4
            if moving and "face" not in it and not any("face" in k for k in it["keys"]):
                st["face"] = 1.0 if x2 > x1 else -1.0
            if moving or st.get("walk_in_place"):
                cad = st.get("cadence", 1.7)
                sw = math.sin((t + ph0) * 2 * math.pi * cad)
                ang["l1"] = [24 * sw, -8 - 34 * max(0, -sw)]
                ang["l2"] = [-24 * sw, -8 - 34 * max(0, sw)]
                if not st.get("ik2") and st.get("pose", "walk") in ("walk", "stand", "relaxed"):
                    ang["a1"] = [20 * sw, 16]
                    ang["a2"] = [-20 * sw, 16]
                bob += abs(math.cos((t + ph0) * 2 * math.pi * cad)) * 0.012
        elif m == "talk":
            st["_talk"] = math.sin((t + ph0) * 2 * math.pi * 4.5) > 0.1
        elif m == "breathe":
            bob += (math.sin((t + ph0) * 2 * math.pi * 0.35) + 1) * 0.003
        elif m == "shake":
            dx += math.sin(t * 2 * math.pi * 11 + ph0 * 9) * 0.006
        elif m == "bounce":
            bob += abs(math.sin((t + ph0) * math.pi * 2.2)) * 0.05
        elif m == "sob":
            ang["tilt"] = ang.get("tilt", 0) + math.sin(t * 2 * math.pi * 3) * 2.5
            bob += abs(math.sin(t * 2 * math.pi * 3)) * 0.006
        elif m == "wave":
            a2 = ang["a2"]
            ang["a2"] = [a2[0], a2[1] + math.sin(t * 2 * math.pi * 2) * 30]
        elif m == "nod":
            ang["tilt"] = ang.get("tilt", 0) + (math.sin(t * 2 * math.pi * 1.3) + 0.5) * 7
        elif m == "headshake":
            st["face"] = st.get("face", 0) + math.sin(t * 2 * math.pi * 2.4) * 0.45
        elif m == "sway":
            ang["lean"] = ang.get("lean", 0) + math.sin((t + ph0) * 2 * math.pi * 0.5) * 5
        elif m == "cheer":
            k = math.sin((t + ph0) * 2 * math.pi * 1.8) * 18
            ang["a1"] = [-150 - k, -10]
            ang["a2"] = [150 + k, 10]
            bob += abs(math.sin((t + ph0) * 2 * math.pi * 1.8)) * 0.02
        elif m == "jab":
            a2 = ang["a2"]
            ang["a2"] = [a2[0] + math.sin(t * 2 * math.pi * 3) * 7, a2[1]]
            dx += math.sin(t * 2 * math.pi * 3) * 0.004
        elif m == "tremble":
            dx += math.sin(t * 2 * math.pi * 17 + ph0) * 0.0025
    st["_ang"] = {k: (tuple(v) if isinstance(v, list) else v) for k, v in ang.items()}
    st["_bobf"], st["_dxf"] = bob, dx


# ───────────────────────── đám đông ─────────────────────────
def crowd_members(cr, t):
    rnd = random.Random(cr.get("seed", 7))
    n = int(cr.get("n", 16))
    lay = cr.get("layout", "circle")
    kinds = cr.get("kinds", ["man", "woman", "boy", "girl", "man", "woman"])
    exprs = cr.get("exprs", [cr.get("expr", "happy")])
    mem = []
    for i in range(n):
        if lay == "circle":
            a = math.pi / 2 + 2 * math.pi * i / n
            x = cr.get("cx", 0.5) + cr.get("rx", 0.42) * math.cos(a)
            y = cr.get("cy", 0.7) + cr.get("ry", 0.1) * math.sin(a)
            depth = (math.sin(a) + 1) / 2
        elif lay == "rows":
            rows = int(cr.get("rows", 3))
            per = math.ceil(n / rows)
            r_, c_ = divmod(i, per)
            depth = 1 - r_ / max(1, rows - 1) if rows > 1 else 1
            y = cr.get("y", 0.85) - (1 - depth) * cr.get("depth_y", 0.12)
            span = cr.get("w", 0.9) * (0.7 + 0.3 * depth)
            x = cr.get("cx", 0.5) - span / 2 + span * (c_ + 0.5 + (0.5 if r_ % 2 else 0) * 0.5) / per
        else:  # line
            depth = 1
            x = cr.get("cx", 0.5) - cr.get("w", 0.9) / 2 + cr.get("w", 0.9) * (i + 0.5) / n
            y = cr.get("y", 0.8)
        kind = kinds[rnd.randrange(len(kinds))]
        h = cr.get("h", 0.2) * (0.62 + 0.38 * depth) * (0.72 if kind in ("boy", "girl") else 1.0) * rnd.uniform(0.94, 1.06)
        mem.append(dict(type="fig", kind=kind, x=x, y=y, h=h, face=0, pose=cr.get("pose", "stand"), expr=exprs[rnd.randrange(len(exprs))],
                        do=cr.get("do", ["breathe"]), dark=cr.get("dark", 0), glow=cr.get("glow", 0), _seed=1000 + i * 17 + cr.get("seed", 7),
                        keys=[], _depth=depth, _i=i, opacity=cr.get("opacity", 1.0), weight=cr.get("weight", 1.0)))
    return mem


# ───────────────────────── nền ─────────────────────────
def draw_bg(pen, bg, ox, oy, pw, ph, U, t):
    if isinstance(bg, str):
        bg = {"type": bg}
    typ = bg.get("type", "paper")
    col = pen.ink
    k = U / 1080
    hz = oy + ph * bg.get("horizon", 0.64)
    rnd = random.Random(bg.get("seed", 3))
    L, R, B = ox, ox + pw, oy + ph

    def floor_lines(alpha=0.35, n=16):
        vp = (ox + pw * bg.get("vx", 0.5), hz - ph * 0.45)
        p = skia.Path()
        for i in range(n + 1):
            bx = L - pw * 0.6 + pw * 2.2 * i / n
            f = (hz - vp[1]) / (B - vp[1])
            p.moveTo(vp[0] + (bx - vp[0]) * f, hz)
            p.lineTo(bx, B)
        for i in range(1, 5):
            yy = hz + (B - hz) * (i / 5) ** 1.6
            p.moveTo(L, yy)
            p.lineTo(R, yy)
        pen.stroke(p, 1.6 * k, alpha, col, sketch=1, dev=1.2)
        pen.stroke(path_poly([(L, hz), (R, hz)]), 3 * k, 0.7, col)
        sh = path_rect(L, hz, pw, (B - hz) * 0.25)
        pen.hatch(sh, 6, 12, 1, 0.12, col)

    if typ in ("floor", "room"):
        floor_lines()
        if typ == "room":
            pen.stroke(path_poly([(L, hz - 12 * k), (R, hz - 12 * k)]), 2 * k, 0.5, col)
            if bg.get("window", True):
                wx, wy, ww, wh = ox + pw * bg.get("wx", 0.14), oy + ph * 0.16, pw * 0.26, ph * 0.26
                win = path_rect(wx, wy, ww, wh)
                pen.fill(win, LIGHT, 0.9)
                pen.glow(wx + ww / 2, wy + wh / 2, ww * 1.2, (255, 248, 225), 0.5)
                pen.stroke(win, 4 * k, 0.9, col)
                pen.stroke(path_poly([(wx + ww / 2, wy), (wx + ww / 2, wy + wh)]), 3 * k, 0.8, col)
                pen.stroke(path_poly([(wx, wy + wh / 2), (wx + ww, wy + wh / 2)]), 3 * k, 0.8, col)
                beam = path_poly([(wx, wy + wh), (wx + ww, wy + wh), (wx + ww * 2.4, B), (wx + ww * 0.6, B)], True)
                pen.fill(beam, (255, 246, 222), 0.25, skia.BlendMode.kScreen)
    elif typ == "hall":
        vp = (ox + pw * 0.5, hz - ph * 0.35)
        rows, cols = 7, 12
        ys = [hz + (B - hz) * (i / rows) ** 1.7 for i in range(rows + 1)]
        def xat(bx, y):
            f = (y - vp[1]) / (B - vp[1])
            return vp[0] + (bx - vp[0]) * f
        for r_ in range(rows):
            for c_ in range(cols):
                if (r_ + c_) % 2:
                    continue
                b0 = L - pw * 0.8 + pw * 2.6 * c_ / cols
                b1 = L - pw * 0.8 + pw * 2.6 * (c_ + 1) / cols
                y0, y1 = ys[r_], ys[r_ + 1]
                tile = path_poly([(xat(b0, y0), y0), (xat(b1, y0), y0), (xat(b1, y1), y1), (xat(b0, y1), y1)], True)
                pen.fill(tile, (40, 40, 44), 0.55)
        pen.stroke(path_poly([(L, hz), (R, hz)]), 3 * k, 0.7, col)
        for wx in (0.12, 0.62):
            x0, y0, ww, wh = ox + pw * wx, oy + ph * 0.12, pw * 0.26, hz - (oy + ph * 0.12) - ph * 0.02
            win = path_rect(x0, y0, ww, wh)
            pen.fill(win, (240, 242, 244), 0.95)
            pen.stroke(win, 3 * k, 0.9, col)
            for j in range(1, 4):
                pen.stroke(path_poly([(x0, y0 + wh * j / 4), (x0 + ww, y0 + wh * j / 4)]), 2 * k, 0.6, col, sketch=1)
            pen.stroke(path_poly([(x0 + ww / 2, y0), (x0 + ww / 2, y0 + wh)]), 2 * k, 0.6, col, sketch=1)
            for s in (-1, 1):
                cur = path_poly([(x0 + (ww if s > 0 else 0), y0 - ph * 0.02), (x0 + (ww if s > 0 else 0) + s * pw * 0.07, y0 - ph * 0.02),
                                 (x0 + (ww if s > 0 else 0) + s * pw * 0.05, hz), (x0 + (ww if s > 0 else 0) - s * pw * 0.01, hz)], True)
                pen.fill(cur, (50, 50, 55), 0.75)
            beam = path_poly([(x0, y0 + wh), (x0 + ww, y0 + wh), (x0 + ww * 1.3, B), (x0 - ww * 0.1, B)], True)
            pen.fill(beam, (255, 255, 255), 0.2, skia.BlendMode.kScreen)
        cx_ = ox + pw * 0.5
        pen.stroke(path_poly([(cx_, oy), (cx_, oy + ph * 0.07)]), 2 * k, 0.8, col)
        for j in range(5):
            a = -60 + 30 * j
            pen.stroke(path_quad((cx_, oy + ph * 0.07), mv((cx_, oy + ph * 0.07), a * 1.6, pw * 0.05), mv((cx_, oy + ph * 0.1), a * 1.5, pw * 0.07)),
                       2.4 * k, 0.8, col, sketch=1)
    elif typ in ("outdoor", "path", "field"):
        pts = [(L + pw * i / 8, hz - ph * 0.03 * (0.5 + 0.5 * math.sin(i * 1.7 + rnd.random()))) for i in range(9)]
        if typ == "field":
            pts = [(L, hz), (R, hz)]
        hp_ = path_smooth(pts)
        pen.stroke(hp_, 2.5 * k, 0.55, col)
        fill = skia.Path(hp_)
        fill.lineTo(R, B)
        fill.lineTo(L, B)
        fill.close()
        pen.hatch(fill, 9, 8, 1, 0.1, col)
        for i in range(int(bg.get("trees", 3))):
            tx = L + pw * rnd.uniform(0.05, 0.95)
            ty = hz - ph * 0.01
            ts = pw * rnd.uniform(0.03, 0.05)
            pen.stroke(path_poly([(tx, ty), (tx, ty - ts * 1.1)]), 2 * k, 0.5, col, sketch=1)
            pen.stroke(path_circle(tx, ty - ts * 1.5, ts * 0.6), 1.6 * k, 0.45, col, sketch=1, dev=2.5)
        gp = skia.Path()
        for i in range(int(40 * pw / 1080 * 1080 / U)):
            gx, gy = L + pw * rnd.random(), hz + (B - hz) * rnd.uniform(0.15, 1.0)
            gs = (6 + 16 * (gy - hz) / (B - hz)) * k
            for j in (-1, 0, 1):
                gp.moveTo(gx + j * gs * 0.3, gy)
                gp.lineTo(gx + j * gs * 0.6 + rnd.uniform(-2, 2) * k, gy - gs)
        pen.stroke(gp, 1.5 * k, 0.45, col, sketch=1)
        if typ == "path" or bg.get("road"):
            bx = ox + pw * bg.get("road_x", 0.5)
            lft, rgt = [], []
            for i in range(13):
                f = i / 12
                y = lerp(B + ph * 0.02, hz, f ** 0.8)
                wv = math.sin(f * 5 + 1) * pw * 0.12 * (1 - f)
                half = pw * lerp(0.3, 0.012, f ** 0.7)
                c_ = lerp(bx, ox + pw * bg.get("road_end", 0.55), f) + wv
                lft.append((c_ - half, y))
                rgt.append((c_ + half, y))
            road = path_smooth(lft + rgt[::-1], True)
            pen.fill(road, (246, 236, 214), 0.85)
            pen.stroke(path_smooth(lft), 2.4 * k, 0.6, col)
            pen.stroke(path_smooth(rgt), 2.4 * k, 0.6, col)
    elif typ == "river":
        # bờ xa (đồi + cây) ở đường chân trời, mặt sông kẻ ngang dày dần về gần; sóng động thì thêm prop "waves"
        hills = [(L + pw * i / 10, hz - ph * (0.035 + 0.03 * math.sin(i * 1.3 + rnd.random() * 2))) for i in range(11)]
        hp_ = path_smooth(hills)
        land = skia.Path(hp_)
        land.lineTo(R, hz)
        land.lineTo(L, hz)
        land.close()
        pen.fill(land, (214, 200, 172), 0.55)
        pen.hatch(land, 8, 60, 1, 0.18, col)
        pen.stroke(hp_, 2.2 * k, 0.5, col, sketch=1)
        for i in range(int(bg.get("trees", 6))):
            tx = L + pw * rnd.uniform(0.03, 0.97)
            ts = pw * rnd.uniform(0.018, 0.03)
            pen.stroke(path_poly([(tx, hz - ph * 0.02), (tx, hz - ph * 0.02 - ts * 1.1)]), 1.8 * k, 0.45, col, sketch=1)
            pen.stroke(path_circle(tx, hz - ph * 0.02 - ts * 1.5, ts * 0.6), 1.5 * k, 0.4, col, sketch=1, dev=2.5)
        pen.stroke(path_poly([(L, hz), (R, hz)]), 2.6 * k, 0.6, col)
        water = path_rect(L, hz, pw, B - hz)
        pen.fill(water, (226, 222, 208), 0.45)
        wp = skia.Path()
        for i in range(int(bg.get("lines", 26))):
            f = (i + rnd.random() * 0.6) / bg.get("lines", 26)
            yy = hz + (B - hz) * f ** 1.5
            x0 = L + pw * rnd.uniform(-0.1, 0.7)
            wp.moveTo(x0, yy)
            wp.lineTo(x0 + pw * rnd.uniform(0.08, 0.3) * (0.4 + f), yy)
        pen.stroke(wp, 1.6 * k, 0.4, col, sketch=1)
        if bg.get("bank"):                                           # bờ gần (đất) ở 1 bên: "left" | "right"
            sd = -1 if bg["bank"] == "left" else 1
            bx = ox + pw * (0.5 + sd * 0.5)
            bank = path_smooth([(bx, hz + (B - hz) * 0.25), (bx - sd * pw * 0.18, hz + (B - hz) * 0.45),
                                (bx - sd * pw * 0.32, B), (bx, B)], True)
            pen.fill(bank, (222, 206, 176), 1)
            pen.hatch(bank, 7, 30, 1, 0.3, col)
            pen.stroke(bank, 2.6 * k, 0.8, col)
    elif typ == "hut":
        roofL = [(L - pw * 0.05, oy + ph * 0.32), (ox + pw * 0.5, oy - ph * 0.02)]
        roofR = [(R + pw * 0.05, oy + ph * 0.32), (ox + pw * 0.5, oy - ph * 0.02)]
        for rl in (roofL, roofR):
            reg = path_poly([rl[0], rl[1], (rl[1][0], oy - ph), (rl[0][0], oy - ph)], True)
            pen.fill(reg, (190, 160, 115), 0.6)
            p = skia.Path()
            for i in range(90):
                f = rnd.random()
                a0 = (lerp(rl[0][0], rl[1][0], f), lerp(rl[0][1], rl[1][1], f))
                p.moveTo(*a0)
                p.lineTo(a0[0] + rnd.uniform(-20, 20) * k, a0[1] - rnd.uniform(40, 130) * k)
            pen.stroke(p, 1.6 * k, 0.55, col, sketch=1)
            pen.stroke(path_poly(rl), 5 * k, 0.8, col)
        for px_ in (0.06, 0.94):
            post = path_rect(ox + pw * px_ - 12 * k, oy + ph * 0.28, 24 * k, hz - oy - ph * 0.28)
            pen.fill(post, (170, 140, 100), 0.8)
            pen.hatch(post, 4, 90, 1, 0.4, col)
            pen.stroke(post, 2.4 * k, 0.8, col)
        floor_lines(0.2, 10)
        mat = path_poly([(ox + pw * 0.15, hz + (B - hz) * 0.35), (ox + pw * 0.85, hz + (B - hz) * 0.35), (ox + pw * 0.98, B - (B - hz) * 0.1),
                         (ox + pw * 0.02, B - (B - hz) * 0.1)], True)
        pen.hatch(mat, 7, 0, 1, 0.25, col, cross=True)
        pen.stroke(mat, 2 * k, 0.5, col)
        pen.glow(ox + pw * 0.5, oy + ph * 0.55, pw * 0.8, GLOW, 0.35)
    elif typ == "doorway":
        whole = path_rect(L, oy, pw, ph)
        dx_, dw, dh = ox + pw * bg.get("door_x", 0.5), pw * bg.get("door_w", 0.42), ph * bg.get("door_h", 0.5)
        hole = path_rect(dx_ - dw / 2, hz - dh, dw, dh)
        pen.c.save()
        pen.c.clipPath(hole, skia.ClipOp.kDifference, True)
        pen.fill(whole, (60, 50, 40), 0.35)
        pen.hatch(whole, 5, 70, 1.2, 0.35, col, cross=True)
        pen.c.restore()
        pen.fill(hole, LIGHT, 1)
        pen.glow(dx_, hz - dh / 2, dh * 0.9, (255, 250, 238), 0.6)
        pen.stroke(hole, 5 * k, 0.9, col)
        spill = path_poly([(dx_ - dw / 2, hz), (dx_ + dw / 2, hz), (dx_ + dw * 1.1, B), (dx_ - dw * 1.1, B)], True)
        pen.fill(spill, (255, 248, 232), 0.55, skia.BlendMode.kScreen)
    elif typ == "studio":
        # sàn mờ + góc trái-trên tối gạch chì + vệt sáng xiên + mép phải tối
        sh = path_poly([(L, oy), (ox + pw * bg.get("dark_w", 0.42), oy), (L, oy + ph * bg.get("dark_h", 0.75))], True)
        pnt = skia.Paint(AntiAlias=True)
        pnt.setShader(skia.GradientShader.MakeLinear([skia.Point(L, oy), skia.Point(ox + pw * 0.22, oy + ph * 0.38)],
                                                     [argb((60, 42, 25), 0.55), argb((60, 42, 25), 0.0)]))
        pen.c.drawPath(sh, pnt)
        pen.hatch(sh, 4, 25, 1.4, 0.35, col)
        pen.hatch(path_poly([(L, oy), (ox + pw * 0.25, oy), (L, oy + ph * 0.45)], True), 3.5, 115, 1.2, 0.3, col)
        rp = path_rect(ox + pw * 0.93, oy, pw * 0.07, ph)
        pr_ = skia.Paint(AntiAlias=True)
        pr_.setShader(skia.GradientShader.MakeLinear([skia.Point(ox + pw * 0.93, 0), skia.Point(R, 0)],
                                                     [argb((60, 42, 25), 0), argb((60, 42, 25), 0.45)]))
        pen.c.drawPath(rp, pr_)
        beam = path_poly([(ox + pw * 0.42, oy), (ox + pw * 0.95, oy), (ox + pw * 1.0, B), (ox + pw * 0.15, B)], True)
        pen.fill(beam, (255, 244, 220), 0.22, skia.BlendMode.kScreen)
        fl = path_rect(L, hz, pw, B - hz)
        pf = skia.Paint(AntiAlias=True)
        pf.setShader(skia.GradientShader.MakeLinear([skia.Point(0, hz), skia.Point(0, B)],
                                                    [argb((90, 65, 40), 0.0), argb((90, 65, 40), 0.3)]))
        pen.c.drawPath(fl, pf)
        pen.stroke(path_smooth([(L, hz + ph * 0.01), (ox + pw * 0.5, hz - ph * 0.005), (R, hz + ph * 0.012)]), 2.2 * k, 0.35, col, sketch=1)
        pen.hatch(path_rect(L, hz, pw, (B - hz) * 0.12), 5, 3, 1, 0.12, col)
    elif typ == "night":
        for i in range(40):
            sx, sy = L + pw * rnd.random(), oy + ph * rnd.uniform(0, 0.55)
            pen.fill(path_circle(sx, sy, rnd.uniform(1.5, 3.5) * k), (250, 245, 225), 0.8 * (0.6 + 0.4 * math.sin(t * 3 + i)))
        mx_, my_ = ox + pw * 0.78, oy + ph * 0.14
        moon = skia.Op(path_circle(mx_, my_, 60 * k), path_circle(mx_ + 28 * k, my_ - 16 * k, 55 * k), skia.PathOp.kDifference_PathOp)
        if moon:
            pen.glow(mx_, my_, 180 * k, (255, 245, 210), 0.35)
            pen.fill(moon, (250, 242, 215), 0.95)
        pen.stroke(path_poly([(L, hz), (R, hz)]), 2.5 * k, 0.5, col)
    if bg.get("sun"):
        sx, sy, ss = bg["sun"]
        PROPS["sun"](pen, ox + pw * sx, oy + ph * sy, U * ss, {}, t)
    if bg.get("ground"):
        pen.stroke(path_poly([(L, hz), (R, hz)]), 2.5 * k, 0.5, col)


# ───────────────────────── fx ─────────────────────────
def draw_fx(pen, fx, ox, oy, pw, ph, U, t, scene, plan):
    name = fx.get("name")
    a = fx.get("a", 0.6)
    if "_appear" in fx:
        a *= ease((t - fx["_appear"]) / fx.get("fade", 0.6))
    if "_vanish" in fx:
        a *= 1 - ease((t - fx["_vanish"]) / fx.get("fade", 0.6))
    if a <= 0:
        return
    x, y = ox + pw * fx.get("x", 0.5), oy + ph * fx.get("y", 0.5)
    col = tuple(fx.get("color", GLOW))
    if name == "glow":
        pul = 1 + fx.get("pulse", 0) * 0.12 * math.sin(t * 2 * math.pi * 0.6)
        pen.glow(x, y, U * fx.get("r", 0.5) * pul, col, a)
    elif name == "rays":
        n = int(fx.get("n", 12))
        L_ = U * fx.get("len", 1.2)
        spin = t * fx.get("spin", 2)
        for i in range(n):
            ang = spin + i * 360 / n
            wd = fx.get("width", 6)
            p = path_poly([(x, y), mv((x, y), ang - wd / 2, L_), mv((x, y), ang + wd / 2, L_)], True)
            pnt = skia.Paint(AntiAlias=True)
            pnt.setShader(skia.GradientShader.MakeRadial(skia.Point(x, y), L_, [argb(col, a * 0.5), argb(col, 0)]))
            pnt.setBlendMode(skia.BlendMode.kScreen)
            pen.c.drawPath(p, pnt)
    elif name == "rings":
        for i in range(int(fx.get("n", 3))):
            ph_ = (t * fx.get("speed", 0.35) + i / fx.get("n", 3)) % 1.0
            r = U * fx.get("r", 0.5) * (0.35 + ph_)
            pnt = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=U * 0.012, Color=argb(col, a * (1 - ph_)))
            pnt.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, U * 0.008))
            pnt.setBlendMode(skia.BlendMode.kScreen)
            pen.c.drawOval(skia.Rect.MakeLTRB(x - r, y - r * fx.get("squash", 0.9), x + r, y + r * fx.get("squash", 0.9)), pnt)
    elif name == "dust":
        rnd = random.Random(5)
        for i in range(int(fx.get("n", 30))):
            px_ = ox + pw * ((rnd.random() + t * 0.01 * rnd.uniform(-1, 1)) % 1)
            py_ = oy + ph * ((rnd.random() - t * 0.02 * rnd.uniform(0.3, 1)) % 1)
            pen.fill(path_circle(px_, py_, U * rnd.uniform(0.002, 0.005)), (255, 245, 215), a * 0.8)
    elif name == "rain":
        rnd = random.Random(8)
        p = skia.Path()
        for i in range(int(fx.get("n", 80))):
            rx = ox + pw * rnd.random()
            ry = oy + ph * ((rnd.random() + t * rnd.uniform(0.8, 1.2)) % 1)
            p.moveTo(rx, ry)
            p.lineTo(rx - U * 0.01, ry + U * 0.04)
        pen.stroke(p, U * 0.002, a, pen.ink, sketch=1)
    elif name == "darken":
        pen.fill(path_rect(ox, oy, pw, ph), (15, 12, 10), a)
    elif name == "vignette":
        pnt = skia.Paint(AntiAlias=True)
        pnt.setShader(skia.GradientShader.MakeRadial(skia.Point(ox + pw / 2, oy + ph / 2), math.hypot(pw, ph) / 2,
                                                     [argb((0, 0, 0), 0), argb((0, 0, 0), 0), argb((20, 12, 5), a)], [0, 0.55, 1]))
        pen.c.drawRect(skia.Rect.MakeXYWH(ox, oy, pw, ph), pnt)
    elif name == "flash":
        at = resolve_t(fx.get("at", 0), scene, plan)
        f = t - at
        if 0 <= f < 0.5:
            pen.fill(path_rect(ox, oy, pw, ph), (255, 252, 240), a * (1 - f / 0.5))
    elif name == "warm":
        pen.fill(path_rect(ox, oy, pw, ph), (255, 200, 120), a * 0.3, skia.BlendMode.kSoftLight)


# ───────────────────────── vẽ 1 panel ─────────────────────────
def draw_panel(c, panel, scene, plan, t, tq, seed_boil, W, H):
    rx, ry, rw, rh = panel.get("rect", [0, 0, 1, 1])
    ox, oy, pw, ph = rx * W, ry * H, rw * W, rh * H
    U = min(pw, ph)
    tone = panel.get("tone", scene.get("tone", "warm"))
    T = TONES.get(tone, TONES["warm"])
    c.save()
    c.clipRect(skia.Rect.MakeXYWH(ox, oy, pw, ph))
    en = panel.get("enter")
    if en:
        f = ease((t - resolve_t(panel.get("enter_t", 0), scene, plan)) / panel.get("enter_d", 0.6))
        if en == "slide_left":
            c.translate((1 - f) * -pw, 0)
        elif en == "slide_right":
            c.translate((1 - f) * pw, 0)
        elif en == "slide_up":
            c.translate(0, (1 - f) * ph)
    k = U / 1080
    # nền (giấy + bối cảnh) tĩnh → vẽ 1 lần, dùng lại cho mọi khung
    key = (id(panel), int(pw), int(ph))
    bgimg = _BG_CACHE.get(key)
    if bgimg is None:
        bs = make_surface(int(pw), int(ph))
        bc = bs.getCanvas()
        bc.drawImage(paper_image(int(pw), int(ph), tone, plan.get("seed", 1)), 0, 0)
        bgpen = Pen(bc, k, plan.get("seed", 1) * 7 + scene.get("i", 0), T["ink"], rough=1.0)
        draw_bg(bgpen, panel.get("bg", scene.get("bg", "paper")), 0, 0, pw, ph, U, 0.0)
        bgimg = bs.makeImageSnapshot()
        if len(_BG_CACHE) > 12:
            _BG_CACHE.clear()
        _BG_CACHE[key] = bgimg
    c.drawImage(bgimg, ox, oy, skia.SamplingOptions(skia.FilterMode.kLinear))
    pen = Pen(c, k, seed_boil, T["ink"], rough=plan.get("rough", 1.0))
    items = panel["_items"]
    fxs = panel.get("_fx", [])
    for fx in fxs:
        if not fx.get("front"):
            draw_fx(pen, fx, ox, oy, pw, ph, U, t, scene, plan)

    # 1) trạng thái
    states, figs = [], {}
    for it in items:
        if it["type"] == "crowd":
            cst = eval_item(it, tq)
            mem = crowd_members(cst, tq)
            ms = []
            for m in mem:
                mst = eval_item(m, tq)
                apply_do(mst, tq, m)
                mst["h"] = m["h"]
                mst["opacity"] = cst["opacity"]
                ms.append(mst)
            states.append(("crowd", cst, ms))
            continue
        st = eval_item(it, tq)
        if it["type"] == "fig":
            apply_do(st, tq, it)
        states.append((it["type"], st, None))
    # 2) khung xương
    for typ, st, ms in states:
        group = ms if typ == "crowd" else ([st] if typ == "fig" else [])
        for s_ in group:
            Hpx = s_["h"] * U
            s_["_bob"] = s_["_bobf"] * Hpx
            s_["_dx"] = s_["_dxf"] * U
            s_["_sk"] = skeleton(s_, U, ox, oy, pw, ph)
            s_["_sk"]["_dx"] = s_["_dx"]
            if s_.get("id"):
                figs[s_["id"]] = s_["_sk"]
    # 3) IK: tự thân → nắm tay → với tới
    def target_of(spec, sk):
        if isinstance(spec, list):
            return (ox + pw * spec[0], oy + ph * spec[1])
        sid, _, part = str(spec).partition(".")
        src = sk if sid == "self" else figs.get(sid)
        if src is None:
            return None
        return anchors(src).get(part or "shoulder")
    for typ, st, ms in states:
        group = ms if typ == "crowd" else ([st] if typ == "fig" else [])
        for s_ in group:
            sk = s_["_sk"]
            an = anchors(sk)
            for w_ in ("1", "2"):
                tag = s_["_ang"].get("ik" + w_)
                if tag and tag in an:
                    apply_ik(sk, w_, an[tag])
    for typ, st, ms in states:
        if typ == "crowd" and st.get("hold"):
            ordered = sorted(ms, key=lambda m: m["x"]) if st.get("layout") != "circle" else ms
            n = len(ordered)
            for i, m in enumerate(ordered):
                for j in ((i - 1), (i + 1)):
                    if st.get("layout") != "circle" and not (0 <= j < n):
                        continue
                    o = ordered[j % n]
                    a, b = m["_sk"], o["_sk"]
                    if abs(a["sh"][0] - b["sh"][0]) > (a["H"] + b["H"]) * 0.75:
                        continue
                    side = "L" if b["sh"][0] < a["sh"][0] else "R"
                    tgt = ((a["sh"][0] + b["sh"][0]) / 2, (a["hip"][1] + b["hip"][1]) / 2 - 0.02 * a["H"])
                    if st.get("pose") == "cheer" or "cheer" in (st.get("do") or []):
                        tgt = ((a["sh"][0] + b["sh"][0]) / 2, min(a["head"][1], b["head"][1]) - 0.2 * a["H"])
                    apply_ik(a, screen_arm(a, side), tgt)
    for typ, st, ms in states:
        if typ != "fig":
            continue
        sk = st["_sk"]
        holds = st.get("hold") or []
        if isinstance(holds, str):
            holds = [holds]
        for pid in holds:
            o = figs.get(pid)
            if not o:
                continue
            side = "L" if o["sh"][0] < sk["sh"][0] else "R"
            lowh = max(sk["hip"][1], o["hip"][1]) - 0.03 * max(sk["H"], o["H"])
            tgt = ((sk["sh"][0] + o["sh"][0]) / 2, lowh)
            apply_ik(sk, screen_arm(sk, side), tgt)
        reach = st.get("reach")
        if reach:
            for rs in (reach if isinstance(reach, list) and reach and isinstance(reach[0], dict) else [reach]):
                tgt = target_of(rs.get("to"), sk)
                if tgt:
                    off = rs.get("off", [0, 0])
                    tgt = (tgt[0] + off[0] * U, tgt[1] + off[1] * U)
                    arm = rs.get("arm", "R")
                    wi = screen_arm(sk, arm) if arm in ("L", "R") else arm
                    rw = max(0.0, min(1.0, st.get("reach_w", 1.0)))
                    if rw <= 0:
                        continue
                    e0, h0 = sk["e" + wi], sk["h" + wi]
                    apply_ik(sk, wi, tgt)
                    if rw < 1:   # chuyển dần từ tư thế gốc sang với tới
                        f = ease(rw)
                        sk["e" + wi] = (lerp(e0[0], sk["e" + wi][0], f), lerp(e0[1], sk["e" + wi][1], f))
                        sk["h" + wi] = (lerp(h0[0], sk["h" + wi][0], f), lerp(h0[1], sk["h" + wi][1], f))
    # 4) vẽ
    for typ, st, ms in states:
        if typ == "crowd":
            for m in sorted(ms, key=lambda m: m["y"]):
                _draw_fig(pen, m, tq, tone)
            continue
        if st["opacity"] <= 0.01:
            continue
        if typ == "fig":
            _draw_fig(pen, st, tq, tone)
            hp_ = st.get("hold_prop")
            if hp_:
                sk = st["_sk"]
                hand = sk["h" + screen_arm(sk, hp_.get("arm", "R"))] if hp_.get("arm") in ("L", "R") else sk["h2"]
                P = dict(hp_)
                P["_ground"] = sk["ground"][1]
                sz = U * hp_.get("s", 0.12)
                off = hp_.get("off", [0, 0])
                _layer(pen.c, st["opacity"], lambda: PROPS[hp_["name"]](pen, hand[0] + off[0] * U, hand[1] + off[1] * U, sz, P, tq))
        elif typ == "prop":
            fn = PROPS.get(st.get("name"))
            if not fn:
                print(f"  ! không có đạo cụ '{st.get('name')}'", file=sys.stderr)
                continue
            if st.get("at"):
                pos = target_of(st["at"], None)
                if pos is None:
                    continue
                off = st.get("off", [0, 0])
                px_, py_ = pos[0] + off[0] * U, pos[1] + off[1] * U
            else:
                px_, py_ = ox + pw * st["x"], oy + ph * st["y"]
            if st.get("to"):
                st["_to"] = (ox + pw * st["to"][0], oy + ph * st["to"][1])
            def dp(st=st, fn=fn, px_=px_, py_=py_):
                if st.get("rot") and st.get("name") not in ("knife", "frame"):
                    pen.c.save()
                    pen.c.rotate(st["rot"], px_, py_)
                    fn(pen, px_, py_, st["s"] * U, st, tq)
                    pen.c.restore()
                else:
                    fn(pen, px_, py_, st["s"] * U, st, tq)
            _layer(pen.c, st["opacity"], dp)
        elif typ == "text":
            _layer(pen.c, st["opacity"], lambda st=st: draw_text(pen.c, st.get("text", ""), ox + pw * st["x"], oy + ph * st["y"],
                                                                  U * st.get("size", 0.06), tuple(st.get("color", T["ink"])), 1.0,
                                                                  st.get("font", "Montserrat-Black.ttf")))
    for fx in fxs:
        if fx.get("front"):
            draw_fx(pen, fx, ox, oy, pw, ph, U, t, scene, plan)
    c.restore()
    if panel.get("border"):
        pen.stroke(path_rect(ox, oy, pw, ph), 4 * k, 0.8, T["ink"], sketch=2)


_BG_CACHE = {}


def _layer(c, opacity, fn):
    if opacity < 0.995:
        c.saveLayerAlpha(None, int(255 * max(0, opacity)))
        fn()
        c.restore()
    else:
        fn()


def _draw_fig(pen, st, tq, tone):
    sk = st["_sk"]
    def go():
        if st.get("rot"):
            pen.c.save()
            pen.c.rotate(st["rot"], *sk["ground"])
            draw_figure(pen, sk, st, tq, tone)
            pen.c.restore()
        else:
            draw_figure(pen, sk, st, tq, tone)
    _layer(pen.c, st["opacity"], go)


# ───────────────────────── cảnh / khung hình ─────────────────────────
def prepare(plan):
    for i, sc in enumerate(plan["scenes"]):
        sc.setdefault("i", i + 1)
        panels = sc.get("panels") or [{"rect": [0, 0, 1, 1], "items": sc.get("items", []), "fx": sc.get("fx", [])}]
        for p in panels:
            p["_items"] = prep_items(p.get("items", []), sc, plan)
            fx = []
            for f in p.get("fx", []):
                f = dict(f)
                for fld in ("appear", "vanish"):
                    if fld in f:
                        f["_" + fld] = resolve_t(f[fld], sc, plan)
                fx.append(f)
            p["_fx"] = fx
        sc["_panels"] = panels


def draw_scene(c, sc, plan, t, W, H):
    afps = plan.get("anim_fps", 15)
    bfps = plan.get("boil_fps", 6)
    tq = math.floor(t * afps) / afps
    seed_boil = int(math.floor(t * bfps)) if bfps else 0
    dur = sc["end"] - sc["start"]
    cam = sc.get("cam", {})
    c.save()
    if cam != "none":
        z0, x0, y0 = cam.get("from", [1.0, 0.5, 0.5])
        z1, x1, y1 = cam.get("to", [cam.get("zoom", [1.0, 1.06])[1] if "zoom" in cam else 1.06, x0, y0])
        if "zoom" in cam:
            z0 = cam["zoom"][0]
        f = ease(t / max(0.1, dur)) if cam.get("ease", True) else max(0, min(1, t / max(0.1, dur)))
        z = max(1.0, lerp(z0, z1, f))
        cx_, cy_ = lerp(x0, x1, f), lerp(y0, y1, f)
        cx_ = min(max(cx_, 0.5 / z), 1 - 0.5 / z)
        cy_ = min(max(cy_, 0.5 / z), 1 - 0.5 / z)
        c.translate(W / 2, H / 2)
        c.scale(z, z)
        c.translate(-cx_ * W, -cy_ * H)
    for p in sc["_panels"]:
        draw_panel(c, p, sc, plan, t, tq, seed_boil + sc["i"] * 1000, W, H)
    c.restore()


def _line_box(text, size, font="Montserrat-Black.ttf", tracking=0.0):
    """bề ngang + đỉnh/đáy THẬT của dòng (fTop/fBottom gồm cả dấu tiếng Việt chồng: Ề, Ổ, Ữ)"""
    f = skia.Font(typeface(font), size)
    m = f.getMetrics()
    t = nfc(str(text))
    w = f.measureText(t) + tracking * size * max(0, len(t) - 1)
    return w, -m.fTop, m.fBottom


def _draw_tracked(c, text, cx, y, size, color, a, font="Montserrat-Black.ttf", tracking=0.0, shadow=0.0):
    """chữ giãn cách đều (tracking theo em), canh giữa ở cx, đường chân chữ y"""
    t = nfc(str(text))
    f = skia.Font(typeface(font), size)
    f.setEdging(skia.Font.Edging.kAntiAlias)
    ws = [f.measureText(ch) for ch in t]
    tot = sum(ws) + tracking * size * max(0, len(t) - 1)
    x = cx - tot / 2
    for ch, w in zip(t, ws):
        if shadow:
            p = skia.Paint(AntiAlias=True, Color=argb((10, 8, 6), a * shadow))
            p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, size * 0.06))
            c.drawString(ch, x + size * 0.02, y + size * 0.04, f, p)
        c.drawString(ch, x, y, f, skia.Paint(AntiAlias=True, Color=argb(color, a)))
        x += w + tracking * size


def draw_title_pro(c, ti, f, dur, W, H):
    """Tiêu đề kiểu biên tập: dải nâu trong mờ mép nhòe · dòng 1 kem to · vạch mảnh + hình thoi · dòng 2 vàng ấm giãn chữ.
    Khoảng dòng đo bằng đỉnh/đáy thật của chữ → dấu không bao giờ chạm dòng trên."""
    lines = ti["lines"]
    U = min(W, H)
    cx, cy = W * ti.get("x", 0.5), H * ti.get("y", 0.3)
    width = W * ti.get("width", 0.8)
    f1, f2 = ti.get("font", "Montserrat-Black.ttf"), ti.get("font2", "Montserrat-Bold.ttf")
    trk2 = ti.get("tracking2", 0.16)
    s1 = min(width / max(1, _line_box(lines[0], 100, f1)[0]) * 100, U * ti.get("max_size", 0.15))
    w1, a1, d1 = _line_box(lines[0], s1, f1)
    s2 = s2w = 0
    if len(lines) > 1:
        s2 = min(w1 * 0.94 / max(1, _line_box(lines[1], 100, f2, trk2)[0]) * 100, s1 * 0.5)
        s2w, a2, d2 = _line_box(lines[1], s2, f2, trk2)
    gap = s1 * 0.16                                    # khoảng thở quanh vạch giữa
    h = a1 + d1 + (gap * 2 + s1 * 0.04 + a2 + d2 if s2 else 0)
    top = cy - h / 2
    # nhịp: dải nền → dòng 1 trồi lên → vạch kéo ra → dòng 2; ra: mờ chung 0.4s
    out = 1 - ease((f - dur + 0.4) / 0.4)
    def ph(t0, d=0.45):
        return ease((f - t0) / d)
    a_bg, a_l1, a_ln, a_l2 = ph(0, 0.35) * out, ph(0.1) * out, ph(0.35, 0.5) * out, ph(0.55) * out
    if a_bg <= 0:
        return
    padx, pady = U * 0.07, s1 * 0.32
    band = skia.Rect.MakeXYWH(cx - max(w1, s2w) / 2 - padx, top - pady, max(w1, s2w) + padx * 2, h + pady * 2)
    p = skia.Paint(AntiAlias=True, Color=argb(tuple(ti.get("band", (46, 34, 22))), ti.get("band_a", 0.62) * a_bg))
    p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, U * 0.035))
    c.drawRoundRect(band, U * 0.03, U * 0.03, p)
    col1 = tuple(ti.get("color", (250, 242, 222)))
    col2 = tuple(ti.get("color2", (242, 196, 104)))
    rise = (1 - a_l1 / max(out, 1e-3)) * s1 * 0.18 if out > 0 else 0
    y1 = top + a1 + rise
    draw_text(c, lines[0], cx, y1, s1, col1, a_l1, font=f1, shadow=0.55)
    if s2:
        ly = top + a1 + d1 + gap
        half = w1 * 0.5 * a_ln / max(out, 1e-3) if out > 0 else 0
        if half > 1:
            lp = skia.Paint(AntiAlias=True, Color=argb(col2, 0.9 * a_ln), StrokeWidth=max(2.0, s1 * 0.028),
                            Style=skia.Paint.kStroke_Style, StrokeCap=skia.Paint.kRound_Cap)
            dg = s1 * 0.09
            c.drawLine(cx - half, ly, cx - dg * 1.8, ly, lp)
            c.drawLine(cx + dg * 1.8, ly, cx + half, ly, lp)
            dia = skia.Path()
            dia.moveTo(cx, ly - dg); dia.lineTo(cx + dg, ly); dia.lineTo(cx, ly + dg); dia.lineTo(cx - dg, ly); dia.close()
            c.drawPath(dia, skia.Paint(AntiAlias=True, Color=argb(col2, a_ln)))
        y2 = ly + s1 * 0.04 + gap + a2
        _draw_tracked(c, lines[1], cx, y2, s2, col2, a_l2, font=f2, tracking=trk2, shadow=0.5)


def draw_title(c, plan, T, W, H):
    ti = plan.get("title")
    if not ti or not ti.get("lines"):
        return
    st = ti.get("start", 0.0)
    dur = ti.get("dur", 5.0)
    f = T - st
    if f < 0 or f > dur:
        return
    if ti.get("style", "pro") == "pro":
        draw_title_pro(c, ti, f, dur, W, H)
        return
    a = ease(f / 0.25) * (1 - ease((f - dur + 0.35) / 0.35))
    pop = 1 + 0.08 * (1 - ease(f / 0.3))
    lines = ti["lines"]
    width = W * ti.get("width", 0.72)
    U = min(W, H)
    sizes = [width / max(1, text_width(l, 100)) * 100 for l in lines]
    sizes = [min(s_, U * ti.get("max_size", 0.2)) for s_ in sizes]
    tot = sum(s_ * 0.95 for s_ in sizes)
    x = W * ti.get("x", 0.5)
    y = H * ti.get("y", 0.42) - tot / 2
    col = tuple(ti.get("color", (255, 255, 255)))
    oc = tuple(ti.get("outline", (38, 28, 18)))
    c.save()
    c.translate(x, H * ti.get("y", 0.42))
    c.scale(pop, pop)
    c.translate(-x, -H * ti.get("y", 0.42))
    for l, s_ in zip(lines, sizes):
        y += s_ * 0.86
        draw_text(c, l, x, y, s_, col, a, outline=oc, ow=0.14, shadow=0.6)
        y += s_ * 0.09
    c.restore()


def frame_at(c, plan, T, W, H):
    scenes = plan["scenes"]
    cur = None
    for sc in scenes:
        if sc["start"] <= T < sc["end"]:
            cur = sc
            break
    if cur is None:
        cur = scenes[-1] if T >= scenes[-1]["start"] else scenes[0]
    idx = scenes.index(cur)
    draw_scene(c, cur, plan, T - cur["start"], W, H)
    # chuyển cảnh: cảnh sau hiện dần trong td giây cuối cảnh hiện tại
    if idx + 1 < len(scenes):
        nx = scenes[idx + 1]
        tr = nx.get("trans", plan.get("trans", "fade"))
        td = nx.get("trans_d", 0.45 if tr == "fade" else 0.35)
        left = cur["end"] - T
        if tr != "cut" and left < td:
            f = ease(1 - left / td)
            if tr == "dip":
                c.drawColor(argb(TONES["warm"]["light"], f))
            elif tr == "wipe":
                c.save()
                c.clipRect(skia.Rect.MakeXYWH(0, 0, W * f, H))
                draw_scene(c, nx, plan, T - nx["start"], W, H)
                c.restore()
            else:
                c.saveLayerAlpha(None, int(255 * f))
                draw_scene(c, nx, plan, max(0.0, T - nx["start"]), W, H)
                c.restore()
    draw_title(c, plan, T, W, H)


def make_surface(W, H):
    return skia.Surface.MakeRaster(skia.ImageInfo.Make(W, H, skia.kRGBA_8888_ColorType, skia.kPremul_AlphaType))


def render_image(plan, T, W, H):
    surf = make_surface(W, H)
    c = surf.getCanvas()
    c.clear(skia.ColorWHITE)
    frame_at(c, plan, T, W, H)
    return surf.makeImageSnapshot()


# ───────────────────────── lệnh ─────────────────────────
def _cuda_dlls():
    import importlib
    for mod in ("nvidia.cublas", "nvidia.cudnn"):
        try:
            d = os.path.join(importlib.import_module(mod).__path__[0], "bin")
            os.add_dll_directory(d)
            os.environ["PATH"] = d + os.pathsep + os.environ.get("PATH", "")
        except (ImportError, OSError, AttributeError):
            pass


def transcribe(path, model="large-v3", lang="vi", cpu=False):
    _cuda_dlls()
    from faster_whisper import WhisperModel

    def run(device, ctype):
        m = WhisperModel(model, device=device, compute_type=ctype)
        segs, _ = m.transcribe(str(path), language=lang, word_timestamps=True, vad_filter=True)
        return [{"w": w.word.strip(), "s": round(w.start, 3), "e": round(w.end, 3)} for s in segs for w in (s.words or []) if w.word.strip()]
    if not cpu:
        try:
            return run("cuda", "float16")
        except Exception as e:  # noqa
            print("  (GPU lỗi, chuyển CPU):", str(e)[:120], file=sys.stderr)
    return run("cpu", "int8")


def split_sentences(words, max_len=10.0, min_len=2.8):
    sents, cur = [], []
    for i, w in enumerate(words):
        cur.append(w)
        dur = cur[-1]["e"] - cur[0]["s"]
        gap = (words[i + 1]["s"] - w["e"]) if i + 1 < len(words) else 9
        end = w["w"][-1:] in ".?!…"
        soft = w["w"][-1:] in ",;:"
        if end or (soft and dur >= 6.5) or (gap >= 0.8 and dur >= 2.5) or dur >= max_len:
            sents.append(cur)
            cur = []
    if cur:
        sents.append(cur)
    out = []
    for s in sents:
        if out and (s[-1]["e"] - s[0]["s"] < min_len) and (out[-1][-1]["e"] - out[-1][0]["s"] < max_len):
            out[-1] = out[-1] + s
        else:
            out.append(s)
    if len(out) > 1 and out[0][-1]["e"] - out[0][0]["s"] < min_len:
        out[1] = out[0] + out[1]
        out.pop(0)
    return out


def cmd_plan(a):
    os.makedirs(a.out, exist_ok=True)
    wj = os.path.join(a.out, "words.json")
    if os.path.exists(wj) and not a.force:
        words = json.load(open(wj, encoding="utf-8"))
        print("dùng lại", wj)
    else:
        print("đang nghe voice…")
        words = transcribe(a.voice, a.model, a.lang, a.cpu)
        json.dump(words, open(wj, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    sents = split_sentences(words, a.max, a.min)
    scenes = []
    for i, s in enumerate(sents):
        st = 0.0 if i == 0 else round(max(sents[i - 1][-1]["e"], s[0]["s"] - 0.15), 3)
        scenes.append({"i": i + 1, "start": st, "end": None, "text": " ".join(w["w"] for w in s), "bg": "paper", "tone": "warm",
                       "cam": {"zoom": [1.0, 1.06]}, "items": []})
    for i in range(len(scenes) - 1):
        scenes[i]["end"] = scenes[i + 1]["start"]
    scenes[-1]["end"] = round(words[-1]["e"] + 0.5, 3)
    size = [1080, 1920] if not a.horizontal else [1920, 1080]
    plan = {"voice": os.path.abspath(a.voice), "words": "words.json", "size": size, "fps": 30, "anim_fps": 15, "boil_fps": 6, "seed": 1,
            "title": {"lines": [], "dur": 5.0, "y": 0.24, "style": "pro"}, "cast": {}, "scenes": scenes}
    sj = os.path.join(a.out, "scenes.json")
    if os.path.exists(sj) and not a.force:
        sj = os.path.join(a.out, "scenes.template.json")
    json.dump(plan, open(sj, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"→ {sj}  ({len(scenes)} cảnh, {scenes[-1]['end']:.1f}s)")
    for sc in scenes:
        print(f"  {sc['i']:>2}  {sc['start']:6.2f}–{sc['end']:6.2f} ({sc['end'] - sc['start']:4.1f}s)  {sc['text']}")


def _size(plan, preview):
    W, H = plan.get("size", [1080, 1920])
    if preview:
        W, H = W // 2, H // 2
    return W, H


def _save_png(img, path):
    img.save(path, skia.kPNG)


def cmd_still(a):
    plan = load_plan(a.plan)
    prepare(plan)
    sc = plan["scenes"][a.scene - 1]
    W, H = _size(plan, a.half)
    T = sc["start"] + (sc["end"] - sc["start"]) * a.at if a.at <= 1 else sc["start"] + a.at
    T = min(T, sc["end"] - 0.5)
    _save_png(render_image(plan, T, W, H), a.out)
    print("→", a.out)


def cmd_sheet(a):
    plan = load_plan(a.plan)
    prepare(plan)
    W, H = plan.get("size", [1080, 1920])
    sc_ = a.scale
    w, h = int(W * sc_), int(H * sc_)
    sel = plan["scenes"]
    if a.scenes:
        lo, _, hi = a.scenes.partition("-")
        sel = [s for s in sel if int(lo) <= s["i"] <= int(hi or lo)]
    cols = a.cols
    rows = math.ceil(len(sel) / cols)
    surf = make_surface(cols * w, rows * (h + 34))
    c = surf.getCanvas()
    c.clear(argb((30, 30, 30)))
    for n, sc in enumerate(sel):
        T = sc["start"] + (sc["end"] - sc["start"]) * a.at
        T = min(T, sc["end"] - 0.5)
        img = render_image(plan, T, W, H)
        r_, c_ = divmod(n, cols)
        c.drawImageRect(img, skia.Rect.MakeXYWH(c_ * w, r_ * (h + 34) + 34, w, h), skia.SamplingOptions(skia.FilterMode.kLinear))
        draw_text(c, f"{sc['i']}  {sc['start']:.1f}s", c_ * w + 8, r_ * (h + 34) + 26, 22, (255, 230, 150), 1, "Montserrat-Bold.ttf", "left")
    surf.makeImageSnapshot().save(a.out, skia.kPNG)
    print("→", a.out)


def _video_encoder(preview, cpu=False):
    test = None if cpu else subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=black:s=256x256:d=0.1", "-c:v", "h264_nvenc",
                                            "-f", "null", "-"], capture_output=True)
    if test and test.returncode == 0:
        return "h264_nvenc", ["-preset", "p4" if preview else "p6", "-rc", "vbr", "-cq", "24" if preview else "18", "-b:v", "0"]
    vt = None if cpu else _mac_vt(preview)          # Mac → VideoToolbox
    if vt:
        return vt[1], vt[2:]
    return "libx264", (["-preset", "veryfast", "-crf", "24"] if preview else ["-preset", "medium", "-crf", "17"])


def _loudnorm(voice, I=-14.0, TP=-1.5, LRA=11):
    """Chuẩn âm 2 lượt (đo trước → áp tuyến tính) để ra đúng −14 LUFS."""
    base = f"loudnorm=I={I}:TP={TP}:LRA={LRA}"
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", voice, "-af", base + ":print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="ignore")
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", r.stderr)
    if not m:
        return base
    j = json.loads(m.group(0))
    # tăng gain + limiter chặn đỉnh (loudnorm linear bỏ cuộc khi voice đã chạm 0 dB); limiter làm hụt → đo lại và bù
    gain = I - float(j["input_i"])
    # limiter chạy ở 192 kHz để bắt cả đỉnh liên mẫu (true peak); chừa 1 dB cho AAC — trước đây ra +0.5 dBTP (con thuyền trống)
    chain = lambda g: (f"volume={g:.2f}dB,aresample=192000,alimiter=limit={10 ** ((TP - 1.0) / 20):.3f}:level=false:attack=3:release=60,"
                       f"aresample=48000")
    for _ in range(3):
        r = subprocess.run(["ffmpeg", "-hide_banner", "-i", voice, "-af", chain(gain) + ",ebur128", "-f", "null", "-"],
                           capture_output=True, text=True, encoding="utf-8", errors="ignore")
        mi = re.findall(r"^\s+I:\s+(-?[\d.]+) LUFS", r.stderr, re.M)
        if not mi or abs(float(mi[-1]) - I) < 0.3:
            break
        gain += I - float(mi[-1])
    return chain(gain)


_W = {}


def _winit(plan_path, W, H):
    p = load_plan(plan_path)
    prepare(p)
    _W.update(plan=p, W=W, H=H, surf=make_surface(W, H))


def _wframe(T):
    s = _W["surf"]
    c = s.getCanvas()
    c.clear(skia.ColorWHITE)
    frame_at(c, _W["plan"], T, _W["W"], _W["H"])
    return np.ascontiguousarray(s.toarray()[:, :, :3]).tobytes()


def cmd_render(a):
    plan = load_plan(a.plan)
    prepare(plan)
    W, H = _size(plan, a.preview)
    fps = plan.get("fps", 30)
    t0, t1 = 0.0, plan["scenes"][-1]["end"]
    if a.scenes:
        lo, _, hi = a.scenes.partition("-")
        t0 = plan["scenes"][int(lo) - 1]["start"]
        t1 = plan["scenes"][int(hi or lo) - 1]["end"]
    n = int(round((t1 - t0) * fps))
    enc, eargs = _video_encoder(a.preview, a.cpu)
    voice = plan.get("voice")
    if voice and not os.path.isabs(voice):
        voice = os.path.join(plan["_base"], voice)
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", str(fps), "-i", "-"]
    if voice and os.path.exists(voice):
        cmd += ["-ss", f"{t0:.3f}", "-i", voice, "-map", "0:v", "-map", "1:a",
                "-af", _loudnorm(voice) + ",apad", "-c:a", "aac", "-b:a", "192k", "-ar", "48000"]
    cmd += ["-c:v", enc] + eargs + ["-pix_fmt", "yuv420p", "-t", f"{n / fps:.3f}", "-movflags", "+faststart", a.out]
    jobs = a.jobs or max(1, min(16, (os.cpu_count() or 4) - 4))
    print(f"render {W}x{H} {n} khung ({n / fps:.1f}s) · {enc} · {jobs} luồng vẽ")
    cmd[cmd.index("rgba")] = "rgb24"
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    tic = time.time()
    times = [t0 + i / fps for i in range(n)]
    import multiprocessing as mp
    with mp.Pool(jobs, initializer=_winit, initargs=(os.path.abspath(a.plan), W, H)) as pool:
        for i, buf in enumerate(pool.imap(_wframe, times, chunksize=2)):
            pr.stdin.write(buf)
            if i % (fps * 10) == 0:
                el = time.time() - tic
                print(f"  {times[i]:6.1f}s  ({i}/{n})  {i / max(el, 1e-3):.1f} fps", flush=True)
    pr.stdin.close()
    pr.wait()
    if pr.returncode:
        die("ffmpeg lỗi")
    print(f"→ {a.out}  ({time.time() - tic:.0f}s)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("plan")
    p.add_argument("voice")
    p.add_argument("-o", "--out", required=True)
    p.add_argument("--model", default="large-v3")
    p.add_argument("--lang", default="vi")
    p.add_argument("--max", type=float, default=10.0, help="cảnh dài tối đa (s)")
    p.add_argument("--min", type=float, default=2.8, help="câu ngắn hơn thì gộp")
    p.add_argument("--horizontal", action="store_true", help="khung ngang 1920x1080")
    p.add_argument("--force", action="store_true")
    p.add_argument("--cpu", action="store_true")
    p.set_defaults(f=cmd_plan)
    p = sp.add_parser("still")
    p.add_argument("plan")
    p.add_argument("--scene", type=int, required=True)
    p.add_argument("--at", type=float, default=0.55, help="≤1: tỉ lệ thời lượng cảnh; >1: giây")
    p.add_argument("--half", action="store_true")
    p.add_argument("-o", "--out", required=True)
    p.set_defaults(f=cmd_still)
    p = sp.add_parser("sheet")
    p.add_argument("plan")
    p.add_argument("-o", "--out", required=True)
    p.add_argument("--at", type=float, default=0.6)
    p.add_argument("--cols", type=int, default=6)
    p.add_argument("--scale", type=float, default=0.25)
    p.add_argument("--scenes")
    p.set_defaults(f=cmd_sheet)
    p = sp.add_parser("render")
    p.add_argument("plan")
    p.add_argument("-o", "--out", required=True)
    p.add_argument("--preview", action="store_true")
    p.add_argument("--scenes", help="vd 3-5")
    p.add_argument("--cpu", action="store_true")
    p.add_argument("--jobs", type=int, default=0, help="số tiến trình vẽ song song (mặc định: số nhân − 4, tối đa 16)")
    p.set_defaults(f=cmd_render)
    a = ap.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()

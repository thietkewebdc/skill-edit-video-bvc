# -*- coding: utf-8 -*-
"""Thư viện vẽ NGƯỜI QUE NÉT CHÌ trên giấy sepia (skia).

Mọi toạ độ trong cảnh là tỉ lệ 0..1 của khung (hoặc khung con/panel);
kích thước (h của người, s của đạo cụ) là tỉ lệ của U = cạnh ngắn của panel.
"""
import math, os, random, unicodedata
from functools import lru_cache

import numpy as np, cv2, skia

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(os.path.dirname(HERE), "fonts")

# ───────────────────────── màu / tông ─────────────────────────
TONES = {
    "warm":    dict(paper=(236, 222, 194), edge=(146, 104, 58), light=(255, 243, 212), ink=(46, 36, 26), vig=0.55, grain=9),
    "golden":  dict(paper=(240, 219, 176), edge=(166, 108, 42), light=(255, 240, 196), ink=(50, 38, 24), vig=0.5, grain=9),
    "neutral": dict(paper=(236, 229, 213), edge=(160, 140, 110), light=(249, 245, 235), ink=(42, 38, 34), vig=0.42, grain=8),
    "cold":    dict(paper=(212, 212, 208), edge=(96, 96, 100), light=(238, 238, 236), ink=(28, 28, 30), vig=0.55, grain=8),
    "dark":    dict(paper=(150, 134, 110), edge=(48, 38, 28), light=(206, 190, 162), ink=(22, 18, 14), vig=0.78, grain=10),
}
GLOW = (255, 206, 120)
LIGHT = (255, 248, 228)


def argb(c, a=1.0):
    return skia.ColorSetARGB(int(max(0, min(1, a)) * 255), int(c[0]), int(c[1]), int(c[2]))


def lerp(a, b, f):
    return a + (b - a) * f


def lerpc(c1, c2, f):
    return tuple(lerp(x, y, f) for x, y in zip(c1, c2))


def ease(f):
    f = max(0.0, min(1.0, f))
    return f * f * (3 - 2 * f)


def dirv(a):
    r = math.radians(a)
    return (math.sin(r), math.cos(r))          # 0° = xuống, 90° = phải, 180° = lên


def mv(p, a, l):
    d = dirv(a)
    return (p[0] + d[0] * l, p[1] + d[1] * l)


def ang_of(p, q):
    return math.degrees(math.atan2(q[0] - p[0], q[1] - p[1]))


# ───────────────────────── giấy ─────────────────────────
@lru_cache(maxsize=16)
def paper_image(w, h, tone, seed=0):
    T = TONES.get(tone, TONES["warm"])
    rng = np.random.default_rng(seed + 17)
    lum = cv2.resize(rng.normal(0, 1, (7, 5)).astype(np.float32), (w, h), interpolation=cv2.INTER_CUBIC) * 5
    lum += cv2.resize(rng.normal(0, 1, (max(2, h // 28), max(2, w // 28))).astype(np.float32), (w, h),
                      interpolation=cv2.INTER_CUBIC) * 3
    g = rng.normal(0, 1, (h, w)).astype(np.float32) * T["grain"] * 0.45
    lum += cv2.GaussianBlur(g, (0, 0), 0.7)
    fib = np.zeros((h, w), np.float32)
    for _ in range(int(w * h / 5000)):
        x, y = int(rng.uniform(0, w)), int(rng.uniform(0, h))
        a = rng.uniform(0, math.pi)
        L = rng.uniform(6, 26) * w / 1080
        cv2.line(fib, (x, y), (int(x + math.cos(a) * L), int(y + math.sin(a) * L)), float(rng.choice([-1, 1]) * rng.uniform(4, 9)), 1)
    lum += cv2.GaussianBlur(fib, (0, 0), 0.8)
    img = np.array(T["paper"], np.float32)[None, None, :] + lum[..., None]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt(((xx - w * 0.5) / (w * 0.62)) ** 2 + ((yy - h * 0.46) / (h * 0.62)) ** 2)
    v = (np.clip(d - 0.35, 0, 1.3) ** 1.6 * T["vig"])[..., None]
    img = img * (1 - v) + np.array(T["edge"], np.float32) * v
    c = (np.clip(1 - d, 0, 1) ** 2 * 0.35)[..., None]
    img = img * (1 - c) + np.array(T["light"], np.float32) * c
    rgba = np.dstack([np.clip(img, 0, 255).astype(np.uint8), np.full((h, w), 255, np.uint8)])
    return skia.Image.fromarray(np.ascontiguousarray(rgba), colorType=skia.kRGBA_8888_ColorType)


# ───────────────────────── bút chì ─────────────────────────
ROUND = skia.Paint.kRound_Cap


class Pen:
    """Nét chì run tay: mỗi nét vẽ 2–3 lượt lệch nhẹ; seed đổi theo thời gian → hiệu ứng 'boil'."""

    def __init__(self, canvas, k, seed, ink, rough=1.0):
        self.c, self.k, self.seed, self.ink, self.rough = canvas, k, seed, ink, rough
        self.n = 0

    def _pe(self, seg, dev):
        self.n += 1
        return skia.DiscretePathEffect.Make(max(2.5, seg * self.k), dev * self.k * self.rough, (self.seed * 131 + self.n * 7) & 0xFFFF)

    def stroke(self, path, w=4.0, a=1.0, color=None, sketch=2, dev=1.0):
        color = color or self.ink
        b = path.computeTightBounds()
        sz = max(b.width(), b.height())
        lim = 70 * self.k
        if sz < lim:            # hình nhỏ: giảm run để không méo thành đa giác
            dev *= (sz / lim) ** 1.5
        p = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeCap=ROUND,
                       StrokeJoin=skia.Paint.kRound_Join)
        passes = [(1.0, 1.0, 0.8 * dev, 16)]
        if sketch >= 2:
            passes.append((0.42, 0.45, 2.0 * dev, 24))
        if sketch >= 3:
            passes.append((0.3, 0.3, 3.2 * dev, 34))
        for wm, am, d, seg in passes:
            p.setStrokeWidth(max(0.7, w * wm))
            p.setColor(argb(color, a * am))
            seg = min(seg * self.k, sz / 14) / self.k      # đoạn ngắn theo cỡ hình → nét cong không gãy cạnh
            if d * self.k * self.rough > 0.15 and seg * self.k >= 2.5:
                p.setPathEffect(self._pe(seg, d))
                self.c.drawPath(path, p)
            else:                                         # skia-python không nhận None → vẽ bằng paint không hiệu ứng
                q = skia.Paint(p)
                q.setPathEffect(skia.CornerPathEffect.Make(0.01))
                self.c.drawPath(path, q)

    def fill(self, path, color, a=1.0, blend=None):
        p = skia.Paint(AntiAlias=True, Color=argb(color, a))
        if blend:
            p.setBlendMode(blend)
        self.c.drawPath(path, p)

    def hatch(self, path, spacing=7.0, angle=45, w=1.2, a=0.35, color=None, cross=False):
        b = path.computeTightBounds()
        cx, cy = b.centerX(), b.centerY()
        R = math.hypot(b.width(), b.height()) / 2 + 2
        sp = max(2.0, spacing * self.k)
        hp = skia.Path()
        for ang in ([angle, angle + 90] if cross else [angle]):
            d = (math.cos(math.radians(ang)), math.sin(math.radians(ang)))
            n = (-d[1], d[0])
            o = -R
            while o <= R:
                hp.moveTo(cx + n[0] * o - d[0] * R, cy + n[1] * o - d[1] * R)
                hp.lineTo(cx + n[0] * o + d[0] * R, cy + n[1] * o + d[1] * R)
                o += sp
        self.c.save()
        self.c.clipPath(path, doAntiAlias=True)
        self.stroke(hp, w * self.k, a, color, sketch=1, dev=1.4)
        self.c.restore()

    def glow(self, x, y, r, color=GLOW, a=0.6, blend=skia.BlendMode.kScreen):
        if r <= 1 or a <= 0:
            return
        p = skia.Paint(AntiAlias=True)
        p.setShader(skia.GradientShader.MakeRadial(skia.Point(x, y), r, [argb(color, a), argb(color, a * 0.35), argb(color, 0)],
                                                   [0.0, 0.45, 1.0]))
        p.setBlendMode(blend)
        self.c.drawCircle(x, y, r, p)


def path_poly(pts, close=False):
    p = skia.Path()
    p.moveTo(*pts[0])
    for q in pts[1:]:
        p.lineTo(*q)
    if close:
        p.close()
    return p


def path_smooth(pts, close=False):
    """Catmull-Rom → cubic."""
    p = skia.Path()
    n = len(pts)
    if n < 3:
        return path_poly(pts, close)
    P = list(pts) + ([pts[0], pts[1], pts[2]] if close else [])
    p.moveTo(*P[0])
    m = n if close else n - 1
    for i in range(m):
        p0 = P[i - 1] if (i > 0 or close) else P[0]
        p1, p2 = P[i], P[i + 1]
        p3 = P[i + 2] if i + 2 < len(P) else P[-1]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        p.cubicTo(*c1, *c2, *p2)
    if close:
        p.close()
    return p


def path_circle(x, y, r):
    p = skia.Path()
    p.addCircle(x, y, r)
    return p


def path_oval(cx, cy, rx, ry, rot=0):
    p = skia.Path()
    p.addOval(skia.Rect.MakeLTRB(cx - rx, cy - ry, cx + rx, cy + ry))
    if rot:
        p.transform(skia.Matrix.RotateDeg(rot, skia.Point(cx, cy)))
    return p


def path_rect(x, y, w, h, r=0):
    p = skia.Path()
    if r:
        p.addRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, w, h), r, r))
    else:
        p.addRect(skia.Rect.MakeXYWH(x, y, w, h))
    return p


def path_quad(a, c, b):
    p = skia.Path()
    p.moveTo(*a)
    p.quadTo(*c, *b)
    return p


@lru_cache(maxsize=8)
def typeface(name="Montserrat-Black.ttf"):
    return skia.Typeface.MakeFromFile(os.path.join(FONT_DIR, name))


def nfc(s):
    return unicodedata.normalize("NFC", s)


# ───────────────────────── người que ─────────────────────────
ADULT = dict(torso=0.30, ua=0.165, fa=0.15, th=0.205, sh=0.20, head=0.135, neck=0.018)
CHILD = dict(torso=0.25, ua=0.14, fa=0.13, th=0.17, sh=0.16, head=0.19, neck=0.012)
# kiểu "soft": thân áo dài có khối, đầu to, chân ngắn (mẫu hoạt hình chì mượt)
SOFT = dict(torso=0.34, ua=0.16, fa=0.15, th=0.17, sh=0.17, head=0.135, neck=0.0, shw=0.07)
SOFT_CHILD = dict(torso=0.3, ua=0.14, fa=0.13, th=0.15, sh=0.15, head=0.16, neck=0.0, shw=0.065)

KINDS = {
    "man":      dict(hair="spiky"),
    "woman":    dict(hair="long"),
    "boy":      dict(hair="spiky", child=True),
    "girl":     dict(hair="pigtails", child=True, dress=True),
    "old":      dict(hair="wisps"),
    "oldwoman": dict(hair="bun"),
    "plain":    dict(hair=None),
    "baby":     dict(hair="tuft", child=True),
}

# (góc cánh tay trên, độ gập khuỷu) — quy ước nhân vật NHÌN SANG PHẢI; a1 = tay sau/trái, a2 = tay trước/phải.
POSES = {
    "stand":     dict(a1=(-14, 6), a2=(14, -6), l1=(-7, 0), l2=(7, 0)),
    "relaxed":   dict(a1=(-8, 4), a2=(8, -4), l1=(-5, 0), l2=(5, 0)),
    "arms_open": dict(a1=(-62, -12), a2=(62, 12), l1=(-9, 0), l2=(9, 0)),
    "cheer":     dict(a1=(-155, -8), a2=(155, 8), l1=(-10, 0), l2=(10, 0)),
    "point":     dict(a1=(-14, 8), a2=(96, 0), l1=(-8, 0), l2=(10, 0), lean=4),
    "angry_point": dict(a1=(-38, 70), a2=(98, -4), l1=(-14, 0), l2=(16, 0), lean=9),
    "wave":      dict(a1=(-14, 6), a2=(140, 35), l1=(-7, 0), l2=(7, 0)),
    "think":     dict(a1=(-14, 6), a2=(18, -150), l1=(-7, 0), l2=(7, 0), ik2="chin"),
    "hand_chest": dict(a1=(-10, 5), a2=(25, -150), l1=(-6, 0), l2=(6, 0), ik2="chest"),
    "hands_chest": dict(a1=(-25, 150), a2=(25, -150), l1=(-6, 0), l2=(6, 0), ik1="chest", ik2="chest"),
    "cover_face": dict(a1=(-25, 150), a2=(25, -150), l1=(-6, 0), l2=(6, 0), tilt=12, lean=6, ik1="eyeL", ik2="eyeR"),
    "hands_head": dict(a1=(-150, 110), a2=(150, -110), l1=(-8, 0), l2=(8, 0), ik1="headL", ik2="headR"),
    "shrug":     dict(a1=(-48, -85), a2=(48, 85), l1=(-7, 0), l2=(7, 0)),
    "hips":      dict(a1=(-48, 58), a2=(48, -58), l1=(-12, 0), l2=(12, 0)),
    "hug":       dict(a1=(55, 40), a2=(78, 30), l1=(-6, 0), l2=(8, 0), lean=6),
    "reach":     dict(a1=(55, 5), a2=(82, 0), l1=(-8, 0), l2=(12, 0), lean=8),
    "push":      dict(a1=(82, -8), a2=(94, -8), l1=(-20, 0), l2=(18, 0), lean=14),
    "defend":    dict(a1=(35, -118), a2=(55, -120), l1=(-16, 0), l2=(8, 0), lean=-12, tilt=-6),
    "carry":     dict(a1=(28, -70), a2=(38, -68), l1=(-7, 0), l2=(7, 0)),
    "slump":     dict(a1=(-4, 2), a2=(4, -2), l1=(-5, 0), l2=(5, 0), lean=8, tilt=18),
    "bow":       dict(a1=(-2, 0), a2=(4, 0), l1=(-4, 0), l2=(4, 0), lean=38, tilt=10),
    "lean_back": dict(a1=(-40, -30), a2=(30, 40), l1=(-18, 0), l2=(12, 0), lean=-14, tilt=-8),
    "cane":      dict(a1=(-10, 5), a2=(22, -18), l1=(-6, 0), l2=(8, 0), lean=7, tilt=4),
    "sit":       dict(a1=(25, 0), a2=(40, 0), l1=(86, 0), l2=(96, 0), lean=-4),
    "sit_knees": dict(a1=(62, 40), a2=(72, 30), l1=(128, -118), l2=(138, -124), lean=6, tilt=8),
    "sit_cross": dict(a1=(-28, 50), a2=(28, -50), l1=(-98, 145), l2=(98, -145), tilt=6),
    "sit_chair": dict(a1=(20, -40), a2=(30, -40), l1=(90, -90), l2=(96, -92)),
    "kneel":     dict(a1=(40, 20), a2=(62, 10), l1=(0, -90), l2=(82, -82), lean=4),
    "kneel2":    dict(a1=(10, 10), a2=(20, 10), l1=(2, -92), l2=(6, -94), lean=6, tilt=10),
    "crouch":    dict(a1=(45, 10), a2=(62, 0), l1=(58, -112), l2=(72, -122), lean=22),
    "run":       dict(a1=(-50, 80), a2=(60, 80), l1=(-40, -60), l2=(45, -10), lean=14),
    "jump":      dict(a1=(-150, 0), a2=(150, 0), l1=(-25, -40), l2=(25, 40)),
    "walk":      dict(a1=(-14, 10), a2=(14, 10), l1=(-8, -4), l2=(8, -4)),
    "clasp":     dict(a1=(-10, 60), a2=(10, -60), l1=(-6, 0), l2=(6, 0), ik1="belly", ik2="belly"),
    "bend":      dict(a1=(25, 10), a2=(45, 0), l1=(-14, 10), l2=(20, -30), lean=34, tilt=16),
    "peek":      dict(a1=(-8, 50), a2=(8, -50), l1=(-6, 0), l2=(8, 0), lean=14, tilt=14, ik1="belly", ik2="belly"),
    "fall":      dict(a1=(-120, 20), a2=(130, -20), l1=(-30, -30), l2=(40, 20), lean=-20),
}
ANG_KEYS = ("a1", "a2", "l1", "l2")


def pose_angles(name):
    base = dict(POSES["stand"])
    base.update(dict(lean=0, tilt=0))
    if isinstance(name, dict):
        src = dict(POSES.get(name.get("base", "stand"), {}))
        src.update({k: v for k, v in name.items() if k != "base"})
    else:
        src = POSES.get(name, POSES["stand"])
    base.update(src)
    return base


def blend_pose(A, B, f):
    out = dict(B if f >= 0.5 else A)
    for k in ANG_KEYS:
        out[k] = (lerp(A[k][0], B[k][0], f), lerp(A[k][1], B[k][1], f))
    for k in ("lean", "tilt"):
        out[k] = lerp(A.get(k, 0), B.get(k, 0), f)
    # ik chỉ giữ khi cả hai đầu đều có (tránh giật); lúc chuyển thì theo tư thế đích
    for k in ("ik1", "ik2"):
        out[k] = B.get(k) if f >= 0.85 else (A.get(k) if f < 0.15 and A.get(k) == B.get(k) else None)
    return out


def solve_ik(sh, target, l1, l2, prefer_out=0):
    d = math.hypot(target[0] - sh[0], target[1] - sh[1])
    d = max(1e-3, min(d, (l1 + l2) * 0.999))
    th = ang_of(sh, target)
    c = (l1 * l1 + d * d - l2 * l2) / (2 * l1 * d)
    al = math.degrees(math.acos(max(-1, min(1, c))))
    best = None
    for sg in (1, -1):
        up = th + sg * al
        el = mv(sh, up, l1)
        score = el[1] + prefer_out * (el[0] - sh[0])
        if best is None or score > best[0]:
            best = (score, up, el)
    _, up, el = best
    return el, mv(el, ang_of(el, target), l2)


def skeleton(st, U, ox=0.0, oy=0.0, pw=1.0, ph=1.0):
    """st: trạng thái người que đã tính theo thời gian. Trả về dict các khớp (px)."""
    kind = KINDS.get(st.get("kind", "man"), KINDS["man"])
    soft = st.get("style") == "soft"
    pr = (SOFT_CHILD if kind.get("child") else SOFT) if soft else (CHILD if kind.get("child") else ADULT)
    H = st["h"] * U
    ang = st["_ang"]
    face = st.get("face", 0)
    flip = st.get("flip", face < 0)
    m = -1 if flip else 1

    def limb(base, a, L1, L2):
        up, bend = a[0] * m, a[1] * m
        j = mv(base, up, L1)
        return j, mv(j, up + bend, L2)

    k1, f1 = limb((0, 0), ang["l1"], pr["th"] * H, pr["sh"] * H)
    k2, f2 = limb((0, 0), ang["l2"], pr["th"] * H, pr["sh"] * H)
    low = max(k1[1], f1[1], k2[1], f2[1], 0.0)
    gx, gy = ox + st["x"] * pw, oy + st["y"] * ph
    hip = (gx + st.get("_dx", 0), gy - low - st.get("_bob", 0))
    sh_ = lambda p: (p[0] + hip[0], p[1] + hip[1])
    k1, f1, k2, f2 = map(sh_, (k1, f1, k2, f2))
    lean = ang.get("lean", 0) * m
    neck = mv(hip, 180 - lean, pr["torso"] * H)
    shoulder = mv(neck, -lean, pr["torso"] * H * 0.1)
    r = pr["head"] * H
    head = mv(neck, 180 - lean * 0.7, r + pr["neck"] * H)
    off = pr.get("shw", 0) * H * (1 - 0.65 * min(1.0, abs(face)))
    perp = dirv(90 - lean)
    sh1 = (shoulder[0] - m * off * perp[0], shoulder[1] - m * off * perp[1])
    sh2 = (shoulder[0] + m * off * perp[0], shoulder[1] + m * off * perp[1])
    e1, h1 = limb(sh1, ang["a1"], pr["ua"] * H, pr["fa"] * H)
    e2, h2 = limb(sh2, ang["a2"], pr["ua"] * H, pr["fa"] * H)
    return dict(H=H, r=r, m=m, hip=hip, neck=neck, sh=shoulder, sh1=sh1, sh2=sh2, head=head, e1=e1, h1=h1, e2=e2, h2=h2,
                soft=soft,
                k1=k1, f1=f1, k2=k2, f2=f2, ground=(gx, gy), pr=pr, kind=kind, lean=lean,
                tilt=ang.get("tilt", 0), face=face)


def anchors(sk):
    hx, hy = sk["head"]
    r, fo = sk["r"], sk["face"] * 0.3 * sk["r"]
    tv = sk["tilt"] / 30.0 * 0.25 * r
    return {
        "chin": (hx + fo * 0.8, hy + 0.9 * r),
        "mouth": (hx + fo, hy + 0.45 * r + tv),
        "eyeL": (hx + fo - 0.32 * r, hy + tv + 0.15 * r), "eyeR": (hx + fo + 0.32 * r, hy + tv + 0.15 * r),
        "headL": (hx - 0.95 * r, hy - 0.25 * r), "headR": (hx + 0.95 * r, hy - 0.25 * r),
        "head": (hx, hy), "top": (hx, hy - r),
        "chest": mv(sk["sh"], ang_of(sk["sh"], sk["hip"]), sk["pr"]["torso"] * sk["H"] * 0.28),
        "belly": mv(sk["sh"], ang_of(sk["sh"], sk["hip"]), sk["pr"]["torso"] * sk["H"] * 0.6),
        "hipL": (sk["hip"][0] - 0.05 * sk["H"], sk["hip"][1]), "hipR": (sk["hip"][0] + 0.05 * sk["H"], sk["hip"][1]),
        "shoulder": sk["sh"], "hand": sk["h2"], "hand1": sk["h1"], "hand2": sk["h2"],
        "knee": sk["k2"], "hip": sk["hip"],
    }


def apply_ik(sk, which, target):
    pr, H = sk["pr"], sk["H"]
    e, h = solve_ik(sk.get("sh" + which, sk["sh"]), target, pr["ua"] * H, pr["fa"] * H)
    sk["e" + which], sk["h" + which] = e, h


def screen_arm(sk, side):
    """side 'L'/'R' → '1'/'2' tùy nhân vật có lật hay không."""
    left = "1" if sk["m"] > 0 else "2"
    return left if side == "L" else ("2" if left == "1" else "1")


# ─── mặt ───
def draw_face(pen, sk, st, t, col, w):
    hx, hy = sk["head"]
    r = sk["r"]
    face = sk["face"]
    fo = face * 0.3 * r
    tv = sk["tilt"] / 30.0 * 0.25 * r
    spread = 0.3 * r * (1 - 0.3 * abs(face))
    ex = (hx + fo - spread, hx + fo + spread)
    ey = hy - 0.02 * r + tv
    my = hy + 0.42 * r + tv
    mx = hx + fo
    ex_ = st.get("expr", "happy")
    talk = st.get("_talk", False)
    c = pen.c

    def dot(x, y, rx, ry):
        pen.fill(path_oval(x, y, rx, ry), col, 0.95)

    def arc(a, ctl, b, ww=None, alpha=0.95):
        pen.stroke(path_quad(a, ctl, b), ww or w, alpha, col, sketch=1, dev=0.5)

    # mắt
    if ex_ in ("joy", "calm", "cry_hard"):
        for x in ex:
            if ex_ == "joy":
                arc((x - 0.1 * r, ey + 0.04 * r), (x, ey - 0.12 * r), (x + 0.1 * r, ey + 0.04 * r))
            else:
                arc((x - 0.1 * r, ey), (x, ey + 0.1 * r), (x + 0.1 * r, ey))
    elif ex_ == "hurt":
        for i, x in enumerate(ex):
            s = -1 if i == 0 else 1
            pen.stroke(path_poly([(x - 0.1 * r * s, ey - 0.07 * r), (x + 0.08 * r * s, ey), (x - 0.1 * r * s, ey + 0.07 * r)]),
                       w, 0.95, col, sketch=1, dev=0.4)
    else:
        big = 1.35 if ex_ in ("surprised", "scared") else 1.0
        for x in ex:
            dot(x, ey, 0.065 * r * big, 0.09 * r * big)

    # lông mày
    by = ey - 0.26 * r
    if ex_ in ("angry", "shout"):
        for i, x in enumerate(ex):
            s = 1 if i == 0 else -1
            pen.stroke(path_poly([(x - 0.15 * r * s, by - 0.07 * r), (x + 0.1 * r * s, by + 0.06 * r)]), w * 1.25, 1, col, sketch=1)
    elif ex_ in ("sad", "worried", "cry", "hurt", "scared", "cry_hard"):
        for i, x in enumerate(ex):
            s = 1 if i == 0 else -1
            pen.stroke(path_quad((x - 0.14 * r * s, by + 0.04 * r), (x - 0.02 * r * s, by + 0.02 * r),
                                 (x + 0.1 * r * s, by - 0.07 * r)), w * 0.9, 0.9, col, sketch=1)
    elif ex_ in ("surprised",):
        for x in ex:
            arc((x - 0.1 * r, by - 0.02 * r), (x, by - 0.1 * r), (x + 0.1 * r, by - 0.02 * r), w * 0.8)

    # miệng
    mw = 0.22 * r
    if talk and ex_ not in ("shout", "surprised", "joy"):
        pen.fill(path_oval(mx, my, 0.09 * r, 0.075 * r), col, 0.9)
    elif ex_ in ("happy", "smile", "calm", "proud"):
        k = 0.16 if ex_ == "happy" else 0.1
        arc((mx - mw, my - 0.02 * r), (mx, my + k * 2 * r), (mx + mw, my - 0.02 * r))
    elif ex_ == "joy":
        p = skia.Path()
        p.moveTo(mx - mw * 1.1, my - 0.04 * r)
        p.quadTo(mx, my + 0.42 * r, mx + mw * 1.1, my - 0.04 * r)
        p.close()
        pen.fill(p, col, 0.9)
    elif ex_ in ("sad", "cry", "cry_hard"):
        arc((mx - mw * 0.85, my + 0.08 * r), (mx, my - 0.12 * r), (mx + mw * 0.85, my + 0.08 * r))
    elif ex_ == "worried":
        pen.stroke(path_smooth([(mx - mw * 0.8, my + 0.04 * r), (mx - mw * 0.3, my - 0.03 * r), (mx + mw * 0.2, my + 0.03 * r),
                                (mx + mw * 0.8, my - 0.02 * r)]), w, 0.95, col, sketch=1, dev=0.4)
    elif ex_ == "angry":
        arc((mx - mw * 0.8, my + 0.07 * r), (mx, my - 0.07 * r), (mx + mw * 0.8, my + 0.07 * r), w * 1.1)
    elif ex_ == "shout":
        p = path_oval(mx, my + 0.02 * r, 0.24 * r, 0.17 * r)
        pen.fill(p, col, 0.92)
        pen.stroke(path_poly([(mx - 0.18 * r, my - 0.06 * r), (mx + 0.18 * r, my - 0.06 * r)]), w * 0.7, 0.9, (240, 232, 215), sketch=1)
    elif ex_ in ("surprised", "scared"):
        pen.stroke(path_oval(mx, my + 0.03 * r, 0.08 * r, 0.11 * r), w, 0.95, col, sketch=1, dev=0.4)
    elif ex_ == "hurt":
        pen.stroke(path_poly([(mx - mw, my), (mx - mw * 0.5, my - 0.06 * r), (mx, my + 0.02 * r), (mx + mw * 0.5, my - 0.06 * r),
                              (mx + mw, my)]), w, 0.95, col, sketch=1, dev=0.4)
    else:  # neutral
        pen.stroke(path_poly([(mx - mw * 0.7, my), (mx + mw * 0.7, my)]), w, 0.95, col, sketch=1, dev=0.4)

    # nước mắt
    if ex_ in ("cry", "cry_hard") or st.get("tears"):
        for i, x in enumerate(ex):
            for j in range(2):
                ph = ((t * 0.9 + j * 0.5 + i * 0.27) % 1.0)
                yy = ey + 0.12 * r + ph * 0.6 * r
                p = skia.Path()
                s = 0.05 * r
                p.moveTo(x, yy - s * 1.6)
                p.quadTo(x + s * 1.1, yy + s * 0.2, x, yy + s)
                p.quadTo(x - s * 1.1, yy + s * 0.2, x, yy - s * 1.6)
                pen.fill(p, (235, 240, 245), 0.9 * (1 - ph))
                pen.stroke(p, w * 0.5, 0.7 * (1 - ph), col, sketch=1, dev=0.2)


def draw_hair(pen, sk, st, col, w, seed):
    hair = st.get("hair", sk["kind"].get("hair"))
    if not hair:
        return
    hx, hy = sk["head"]
    r = sk["r"]
    rnd = random.Random(seed)
    if hair in ("spiky", "tuft"):
        n = 3 if hair == "tuft" else rnd.randint(7, 10)
        for i in range(n):
            a = -48 + 96 * (i + rnd.uniform(-0.3, 0.3)) / max(1, n - 1)
            if hair == "tuft":
                a = -15 + 15 * i
            base = (hx + math.sin(math.radians(a)) * r * 0.97, hy - math.cos(math.radians(a)) * r * 0.97)
            out = a + rnd.uniform(-22, 22)
            L = r * rnd.uniform(0.2, 0.42)
            tip = (base[0] + math.sin(math.radians(out)) * L, base[1] - math.cos(math.radians(out)) * L)
            ctl = ((base[0] + tip[0]) / 2 + rnd.uniform(-0.08, 0.08) * r, (base[1] + tip[1]) / 2)
            pen.stroke(path_quad((base[0], base[1] + 0.05 * r), ctl, tip), w * rnd.uniform(0.55, 0.9), 0.9, col, sketch=1, dev=0.5)
    elif hair == "long":
        for s in (-1, 1):
            pts = [(hx + s * 0.15 * r, hy - 1.08 * r), (hx + s * 0.8 * r, hy - 0.85 * r), (hx + s * 1.12 * r, hy - 0.1 * r),
                   (hx + s * 1.1 * r, hy + 0.75 * r), (hx + s * 0.82 * r, hy + 1.18 * r)]
            pen.stroke(path_smooth(pts), w * 0.9, 0.9, col, sketch=2, dev=0.6)
            for j in range(3):
                q = [(hx + s * (0.3 + 0.18 * j) * r, hy - (0.95 - 0.1 * j) * r), (hx + s * (0.95 - 0.05 * j) * r, hy - 0.1 * r),
                     (hx + s * (0.95 - 0.06 * j) * r, hy + (0.6 + 0.12 * j) * r)]
                pen.stroke(path_smooth(q), w * 0.4, 0.55, col, sketch=1, dev=0.8)
        pen.stroke(path_quad((hx - 0.75 * r, hy - 0.62 * r), (hx - 0.2 * r, hy - 0.2 * r), (hx + 0.35 * r, hy - 0.72 * r)),
                   w * 0.7, 0.8, col, sketch=1)
    elif hair == "pigtails":
        for s in (-1, 1):
            pen.stroke(path_oval(hx + s * 1.12 * r, hy - 0.05 * r, 0.2 * r, 0.34 * r, rot=s * -25), w * 0.8, 0.9, col, sketch=2)
            pen.stroke(path_poly([(hx + s * 0.9 * r, hy - 0.3 * r), (hx + s * 0.98 * r, hy - 0.18 * r)]), w * 1.2, 1, col, sketch=1)
        pen.stroke(path_quad((hx - 0.7 * r, hy - 0.7 * r), (hx, hy - 0.35 * r), (hx + 0.7 * r, hy - 0.7 * r)), w * 0.6, 0.8, col, sketch=1)
    elif hair == "wisps":
        for i in range(4):
            a = -30 + 20 * i
            b = (hx + math.sin(math.radians(a)) * r, hy - math.cos(math.radians(a)) * r)
            pen.stroke(path_smooth([b, (b[0] + 0.08 * r, b[1] - 0.14 * r), (b[0] - 0.05 * r, b[1] - 0.24 * r)]), w * 0.5, 0.8, col,
                       sketch=1)
        for s in (-1, 1):
            for j in range(3):
                b = (hx + s * 0.97 * r, hy - 0.1 * r + j * 0.12 * r)
                pen.stroke(path_poly([b, (b[0] + s * 0.12 * r, b[1] + 0.03 * r)]), w * 0.5, 0.8, col, sketch=1)
    elif hair == "bun":
        pen.fill(path_circle(hx, hy - 1.12 * r, 0.3 * r), (225, 215, 195), 1)
        pen.stroke(path_circle(hx, hy - 1.12 * r, 0.3 * r), w * 0.8, 0.9, col, sketch=2)
        pen.stroke(path_quad((hx - 0.95 * r, hy - 0.2 * r), (hx - 0.4 * r, hy - 1.15 * r), (hx + 0.95 * r, hy - 0.25 * r)),
                   w * 0.6, 0.8, col, sketch=1)


def _soft_paint_fill(pen, path, c0, c1, p0, p1, a=1.0):
    p = skia.Paint(AntiAlias=True)
    p.setShader(skia.GradientShader.MakeLinear([skia.Point(*p0), skia.Point(*p1)], [argb(c0, a), argb(c1, a)]))
    pen.c.drawPath(path, p)


def draw_figure_soft(pen, sk, st, t, tone):
    """Người que có khối: thân áo dài tô chì, đầu tròn có tai/mũi, tóc chùm; ánh sáng từ trên-trái."""
    col = pen.ink
    H, r = sk["H"], sk["r"]
    dark = st.get("dark", 0.0)
    face = sk["face"]
    m = sk["m"]
    w = max(1.4, 0.0085 * H) * st.get("weight", 1.0)
    light = lerpc((246, 236, 214), (40, 34, 28), dark)
    shade = lerpc((196, 178, 148), (24, 20, 16), dark)
    seed = st.get("_seed", 1)
    if st.get("glow", 0) > 0:
        pen.glow(sk["head"][0], (sk["head"][1] + sk["hip"][1]) / 2, H * 0.62, GLOW, 0.55 * st["glow"])
    # bóng đổ mềm
    gx, gy = sk["ground"][0] + sk.get("_dx", 0), sk["ground"][1]
    sp = skia.Paint(AntiAlias=True, Color=argb((40, 28, 16), 0.28))
    sp.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 0.025 * H))
    pen.c.drawOval(skia.Rect.MakeLTRB(gx - 0.2 * H + 0.06 * H, gy - 0.025 * H, gx + 0.22 * H + 0.06 * H, gy + 0.03 * H), sp)

    d = dirv(ang_of(sk["neck"], sk["hip"]))          # dọc thân
    pp = (-d[1], d[0])                                 # ngang thân
    hip, neck = sk["hip"], sk["neck"]
    hw = 0.13 * H
    hem = (hip[0] + d[0] * 0.035 * H, hip[1] + d[1] * 0.035 * H)
    # chân (từ trong áo)
    for i, s in (("1", -1), ("2", 1)):
        root = (hip[0] + pp[0] * s * 0.045 * H * m, hip[1] + pp[1] * s * 0.045 * H * m)
        pen.stroke(path_smooth([root, sk["k" + i], sk["f" + i]]), w * 1.05, 1, col, sketch=2, dev=0.6)
    for i, s in (("1", -1), ("2", 1)):
        f = sk["f" + i]
        fx = m * 0.035 * H if abs(face) > 0.3 else s * 0.03 * H
        p = path_oval(f[0] + fx, f[1] - 0.008 * H, 0.05 * H, 0.024 * H)
        _soft_paint_fill(pen, p, light, shade, (f[0], f[1] - 0.03 * H), (f[0], f[1] + 0.01 * H))
        pen.stroke(p, w * 0.8, 1, col, sketch=2, dev=0.5)

    def arm(i):
        rt, e, h = sk["sh" + i], sk["e" + i], sk["h" + i]
        pen.stroke(path_smooth([rt, e, h]), w * 0.95, 1, col, sketch=2, dev=0.6)
        a = ang_of(e, h)
        c = mv(h, a, 0.018 * H)
        p = path_oval(c[0], c[1], 0.03 * H, 0.038 * H, rot=-a)
        _soft_paint_fill(pen, p, light, shade, (c[0] - 0.03 * H, c[1] - 0.03 * H), (c[0] + 0.03 * H, c[1] + 0.03 * H))
        pen.stroke(p, w * 0.75, 1, col, sketch=2, dev=0.5)
        th = mv(c, a - 70 * m, 0.03 * H)
        pen.stroke(path_quad(c, mv(c, a - 40 * m, 0.03 * H), th), w * 0.5, 0.8, col, sketch=1, dev=0.3)

    back = "1" if m > 0 else "2"
    if abs(face) > 0.35:
        arm(back)
    # áo dài
    sw = 0.075 * H * (1 - 0.35 * min(1, abs(face)))
    hw2 = hw * (1 - 0.25 * min(1, abs(face)))
    P = lambda base, a, b: (base[0] + pp[0] * a + d[0] * b, base[1] + pp[1] * a + d[1] * b)
    body = path_smooth([P(neck, -0.03 * H, -0.01 * H), P(neck, -sw, 0.03 * H), P(neck, -sw * 1.25, 0.12 * H),
                        P(hem, -hw2, 0), P(hem, -hw2 * 0.4, 0.012 * H), P(hem, hw2 * 0.4, 0.012 * H), P(hem, hw2, 0),
                        P(neck, sw * 1.25, 0.12 * H), P(neck, sw, 0.03 * H), P(neck, 0.03 * H, -0.01 * H)], close=True)
    b = body.computeTightBounds()
    _soft_paint_fill(pen, body, light, shade, (b.left(), b.top()), (b.right(), b.bottom()))
    pen.c.save()
    pen.c.clipPath(body, doAntiAlias=True)
    pen.hatch(body, 3.2, 62, 1.0, 0.32, col)
    sh_side = path_rect(b.centerX() + b.width() * 0.12, b.top() - 5, b.width(), b.height() + 10)
    pen.hatch(sh_side, 2.6, 120, 1.0, 0.35, col)
    pen.c.restore()
    pen.stroke(body, w * 0.95, 1, col, sketch=3, dev=0.7)
    if st.get("crack", 0) > 0:
        a_ = anchors(sk)
        c0, c1 = a_["chest"], a_["belly"]
        pts = [(lerp(c0[0], c1[0], i / 6 * st["crack"]) + (0.02 if i % 2 else -0.02) * H, lerp(c0[1], c1[1], i / 6 * st["crack"]))
               for i in range(7)]
        pen.stroke(path_poly(pts), w * 0.8, 1, col, sketch=2, dev=0.3)

    # đầu
    hx, hy = sk["head"]
    hp = path_circle(hx, hy, r)
    ex = (1 - 0.55 * min(1, abs(face)))
    for s in (-1, 1):
        if abs(face) > 0.4 and s == (1 if face > 0 else -1):
            continue
        ecx = hx + s * r * 1.06 * ex - face * 0.15 * r
        ep = path_oval(ecx, hy + 0.08 * r, 0.16 * r, 0.21 * r)
        _soft_paint_fill(pen, ep, light, shade, (ecx, hy - 0.1 * r), (ecx, hy + 0.3 * r))
        pen.stroke(ep, w * 0.75, 1, col, sketch=2, dev=0.4)
    pg = skia.Paint(AntiAlias=True)
    pg.setShader(skia.GradientShader.MakeRadial(skia.Point(hx - 0.35 * r, hy - 0.4 * r), r * 1.7, [argb(light), argb(shade)]))
    pen.c.drawPath(hp, pg)
    pen.c.save()
    pen.c.clipPath(hp, doAntiAlias=True)
    pen.c.clipPath(path_circle(hx - 0.32 * r, hy - 0.3 * r, r * 1.0), skia.ClipOp.kDifference, True)
    pen.hatch(hp, 2.8, 60, 1.0, 0.38, col)
    pen.c.restore()
    pen.stroke(hp, w * 0.95, 1, col, sketch=3, dev=0.7)
    # tóc chùm
    rnd = random.Random(seed)
    cx_ = hx - face * 0.15 * r
    hair = st.get("hair", sk["kind"].get("hair"))
    if hair:
        n = 16 if hair in ("spiky", "long", "tuft") else 8
        for i in range(n):
            a0 = rnd.uniform(-38, 38) - face * 12
            base = (cx_ + math.sin(math.radians(a0)) * r * 0.92, hy - math.cos(math.radians(a0)) * r * 0.92)
            ang = a0 * 1.3 + rnd.uniform(-18, 18)
            L = r * rnd.uniform(0.22, 0.5)
            tip = (base[0] + math.sin(math.radians(ang)) * L, base[1] - math.cos(math.radians(ang)) * L)
            ctl = ((base[0] + tip[0]) / 2 + rnd.uniform(-0.06, 0.06) * r, (base[1] + tip[1]) / 2)
            pen.stroke(path_quad(base, ctl, tip), w * rnd.uniform(0.35, 0.7), 0.9, col, sketch=1, dev=0.3)
        if hair == "long":
            for s in (-1, 1):
                pen.stroke(path_smooth([(hx + s * 0.4 * r, hy - 0.95 * r), (hx + s * 1.05 * r, hy - 0.2 * r), (hx + s * 0.95 * r, hy + 0.9 * r)]),
                           w * 0.7, 0.85, col, sketch=2, dev=0.5)
    # mặt: mắt, mũi tròn, miệng
    fcol = lerpc(col, (235, 225, 205), 1.0 if dark > 0.55 else 0.0)
    fo = face * 0.32 * r
    tv = sk["tilt"] / 30.0 * 0.25 * r
    nx_, ny_ = hx + fo * 1.25, hy + 0.12 * r + tv
    draw_face(pen, sk, dict(st, expr=st.get("expr", "smile")), t, fcol, max(1.2, 0.011 * H))
    np_ = path_oval(nx_, ny_, 0.11 * r, 0.09 * r)
    _soft_paint_fill(pen, np_, light, shade, (nx_, ny_ - 0.08 * r), (nx_, ny_ + 0.08 * r))
    pen.stroke(np_, w * 0.6, 1, fcol, sketch=1, dev=0.3)
    # tay trước
    arm("2" if back == "1" else "1")
    if abs(face) <= 0.35:
        arm(back)


def draw_figure(pen, sk, st, t, tone):
    if sk.get("soft"):
        return draw_figure_soft(pen, sk, st, t, tone)
    col = pen.ink
    H, r = sk["H"], sk["r"]
    dark = st.get("dark", 0.0)
    w = max(1.6, 0.0115 * H * (1 + dark * 1.4)) * st.get("weight", 1.0)
    light = lerpc((250, 244, 230), (30, 26, 22), dark)
    seed = st.get("_seed", 1)

    if st.get("glow", 0) > 0:
        pen.glow(sk["head"][0], (sk["head"][1] + sk["hip"][1]) / 2, H * 0.62, GLOW, 0.55 * st["glow"])
        pen.glow(sk["head"][0], sk["head"][1], r * 2.2, (255, 236, 190), 0.6 * st["glow"])
    if st.get("shadow", True):
        gx, gy = sk["ground"][0] + sk.get("_dx", 0), sk["ground"][1]
        ovl = path_oval(gx + 0.05 * H, gy + 0.008 * H, 0.2 * H, 0.03 * H)
        pen.fill(ovl, col, 0.12)
        pen.hatch(ovl, 5, 20, 1.0, 0.18, col)

    # thân + chân
    pen.stroke(path_poly([sk["hip"], sk["k1"], sk["f1"]]), w, 1, col)
    pen.stroke(path_poly([sk["hip"], sk["k2"], sk["f2"]]), w, 1, col)
    if st.get("dress", sk["kind"].get("dress")):
        a = anchors(sk)["chest"]
        hp = sk["hip"]
        dw = 0.13 * H
        p = path_poly([(a[0] - 0.035 * H, a[1]), (a[0] + 0.035 * H, a[1]), (hp[0] + dw, hp[1] + 0.06 * H),
                       (hp[0] - dw, hp[1] + 0.06 * H)], close=True)
        pen.fill(p, light, 1)
        pen.hatch(p, 9, -35, 1, 0.18, col)
        pen.stroke(p, w * 0.8, 1, col)
    else:
        pen.stroke(path_poly([sk["neck"], sk["hip"]]), w, 1, col)
    if st.get("shirt") or st.get("sweater"):
        a = anchors(sk)
        c1, hp = sk["neck"], sk["hip"]
        sw = 0.07 * H
        p = path_poly([(c1[0] - sw * 0.7, c1[1]), (c1[0] + sw * 0.7, c1[1]), (hp[0] + sw, hp[1]), (hp[0] - sw, hp[1])], close=True)
        pen.fill(p, light, 1)
        if st.get("sweater"):
            for j in range(1, 5):
                y = lerp(c1[1], hp[1], j / 5)
                pen.stroke(path_poly([(lerp(c1[0], hp[0], j / 5) - sw * 0.9, y), (lerp(c1[0], hp[0], j / 5) + sw * 0.9, y)]),
                           w * 0.5, 0.7, col, sketch=1)
        pen.stroke(p, w * 0.8, 1, col)
    if st.get("crack", 0) > 0:
        a = anchors(sk)
        c0, c1 = a["chest"], a["belly"]
        n = 6
        pts = []
        for i in range(n + 1):
            f = i / n * st["crack"]
            x = lerp(c0[0], c1[0], f) + (0.025 * H if i % 2 else -0.02 * H) + 0.03 * H * sk["m"]
            pts.append((x, lerp(c0[1], c1[1], f)))
        pen.stroke(path_poly(pts), w * 0.7, 1, col, sketch=2, dev=0.3)

    # đầu
    hx, hy = sk["head"]
    hp = path_circle(hx, hy, r)
    if st.get("hair", sk["kind"].get("hair")) == "long":
        back = path_smooth([(hx - 0.9 * r, hy - 0.8 * r), (hx - 1.12 * r, hy + 0.2 * r), (hx - 0.82 * r, hy + 1.18 * r),
                            (hx + 0.82 * r, hy + 1.18 * r), (hx + 1.12 * r, hy + 0.2 * r), (hx + 0.9 * r, hy - 0.8 * r)], close=True)
        pen.fill(back, lerpc((200, 182, 150), (20, 16, 12), dark), 0.55)
    pen.fill(hp, light, 1)
    if dark < 0.5:
        pen.c.save()
        pen.c.clipPath(hp, doAntiAlias=True)
        pen.c.clipPath(path_circle(hx - 0.28 * r, hy - 0.25 * r, r * 1.02), skia.ClipOp.kDifference, True)
        pen.hatch(hp, 4.5, 60, 1.0, 0.3, col)
        pen.c.restore()
    pen.stroke(hp, w * 0.95, 1, col, sketch=2, dev=0.9)
    draw_hair(pen, sk, st, col, w, seed)
    fcol = lerpc(col, (235, 225, 205), 1.0 if dark > 0.55 else 0.0)
    draw_face(pen, sk, st, t, fcol, max(1.2, 0.012 * H))

    # tay (vẽ sau đầu để che mặt được)
    for i in ("1", "2"):
        pen.stroke(path_poly([sk["sh"], sk["e" + i], sk["h" + i]]), w, 1, col)
    # bàn tay, bàn chân
    for i in ("1", "2"):
        e, h = sk["e" + i], sk["h" + i]
        a = ang_of(e, h)
        c = mv(h, a, 0.012 * H)
        p = path_oval(c[0], c[1], 0.022 * H, 0.03 * H, rot=-a)
        pen.fill(p, light, 1)
        pen.stroke(p, w * 0.7, 1, col, sketch=1, dev=0.5)
    for i, s in (("1", -1), ("2", 1)):
        k, f = sk["k" + i], sk["f" + i]
        fx = sk["m"] * 0.03 * H if abs(sk["face"]) > 0.3 else s * 0.028 * H
        p = path_oval(f[0] + fx, f[1] - 0.004 * H, 0.046 * H, 0.02 * H, rot=0)
        pen.fill(p, light, 1)
        pen.stroke(p, w * 0.7, 1, col, sketch=1, dev=0.5)


# ───────────────────────── đạo cụ ─────────────────────────
PROPS = {}


def prop(name):
    def deco(fn):
        PROPS[name] = fn
        return fn
    return deco


def heart_pts(cx, cy, s, n=72):
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        x = 16 * math.sin(a) ** 3
        y = 13 * math.cos(a) - 5 * math.cos(2 * a) - 2 * math.cos(3 * a) - math.cos(4 * a)
        pts.append((cx + x / 34 * s, cy - (y + 2) / 34 * s))
    return pts


@prop("heart")
def _heart(pen, x, y, s, P, t):
    """broken 0..1 (khe nứt tách ra), mend 0..1 (băng dán), beat (nhịp đập), glow, dark 0..1"""
    s *= 1 + P.get("beat", 0) * 0.05 * max(0, math.sin(t * 2 * math.pi * 1.2)) ** 6
    pts = heart_pts(x, y, s)
    hp = path_poly(pts, True)
    col = pen.ink
    fillc = lerpc((236, 226, 206), (40, 34, 28), P.get("dark", 0))
    if P.get("glow"):
        pen.glow(x, y, s * 1.1, GLOW, 0.6 * P["glow"])
    br = P.get("broken", 0)
    if br <= 0 and not P.get("crack"):
        pen.fill(hp, fillc, 1)
        pen.hatch(hp, 6, 50, 1.2, 0.3, col)
        pen.stroke(hp, s * 0.022, 1, col, sketch=3)
        return
    zig = [(x + (0.035 if i % 2 else -0.035) * s * (1 if i not in (0, 7) else 0), y - 0.36 * s + i * 0.12 * s) for i in range(8)]
    for side in (-1, 1):
        clip = path_poly(zig + ([(x + side * s, y + 0.6 * s), (x + side * s, y - 0.6 * s)]), True)
        pen.c.save()
        pen.c.translate(side * br * 0.12 * s, 0)
        pen.c.rotate(side * br * 8, x, y + 0.5 * s)
        pen.c.clipPath(clip, doAntiAlias=True)
        pen.fill(hp, fillc, 1)
        pen.hatch(hp, 6, 50 if side < 0 else 130, 1.2, 0.3, col)
        pen.stroke(hp, s * 0.022, 1, col, sketch=3)
        pen.stroke(path_poly(zig), s * 0.016, 1, col, sketch=2)
        pen.c.restore()
    md = P.get("mend", 0)
    if md > 0:
        n = 4
        for i in range(n):
            f = max(0, min(1, md * n - i))
            if f <= 0:
                break
            yy = y - 0.28 * s + i * 0.19 * s
            p = path_rect(x - 0.13 * s * f, yy - 0.035 * s, 0.26 * s * f, 0.07 * s, 0.01 * s)
            p.transform(skia.Matrix.RotateDeg(-12 + 8 * i, skia.Point(x, yy)))
            pen.fill(p, (245, 238, 220), 0.95)
            pen.stroke(p, s * 0.008, 0.9, col, sketch=1)


@prop("house")
def _house(pen, x, y, s, P, t):
    """Nhà tranh ấm: light 0..1 (cửa sổ sáng)."""
    col = pen.ink
    w, h = s, s * 0.62
    L, B = x - w / 2, y
    light = P.get("light", 1)
    if light:
        pen.glow(x, B - h * 0.5, s * 0.95, GLOW, 0.45 * light)
    body = path_rect(L + w * 0.08, B - h * 0.62, w * 0.84, h * 0.62)
    pen.fill(body, (234, 220, 192), 1)
    pen.hatch(body, 10, 0, 1, 0.25, col)
    roof = path_poly([(L - w * 0.03, B - h * 0.6), (x, B - h * 1.15), (L + w * 1.03, B - h * 0.6)], True)
    pen.fill(roof, (220, 200, 165), 1)
    pen.hatch(roof, 5, 70, 1, 0.45, col)
    pen.stroke(roof, s * 0.012, 1, col)
    pen.stroke(body, s * 0.011, 1, col)
    pen.stroke(path_rect(L + w * 0.7, B - h * 1.08, w * 0.08, h * 0.25), s * 0.009, 1, col)
    for wx in (0.2, 0.54):
        win = path_rect(L + w * wx, B - h * 0.45, w * 0.18, h * 0.22)
        if light:
            pen.fill(win, (255, 214, 130), 0.85 * light)
            pen.glow(L + w * (wx + 0.09), B - h * 0.34, w * 0.18, GLOW, 0.5 * light)
        pen.stroke(win, s * 0.008, 1, col)
        pen.stroke(path_poly([(L + w * (wx + 0.09), B - h * 0.45), (L + w * (wx + 0.09), B - h * 0.23)]), s * 0.005, 1, col, sketch=1)
    door = path_rect(L + w * 0.42, B - h * 0.3, w * 0.1, h * 0.3)
    pen.stroke(door, s * 0.008, 1, col)


@prop("mansion")
def _mansion(pen, x, y, s, P, t):
    col = pen.ink
    w, h = s, s * 0.7
    L, B = x - w / 2, y
    body = path_rect(L, B - h * 0.7, w, h * 0.7)
    pen.fill(body, (215, 212, 205), 1)
    pen.stroke(body, s * 0.01, 1, col)
    ped = path_poly([(L + w * 0.3, B - h * 0.7), (x, B - h * 0.95), (L + w * 0.7, B - h * 0.7)], True)
    pen.fill(ped, (215, 212, 205), 1)
    pen.stroke(ped, s * 0.009, 1, col)
    pen.stroke(path_rect(L - w * 0.02, B - h * 0.74, w * 1.04, h * 0.04), s * 0.008, 1, col)
    for i in range(6):
        cx_ = L + w * (0.34 + i * 0.064)
        pen.stroke(path_poly([(cx_, B - h * 0.68), (cx_, B - h * 0.08)]), s * 0.012, 1, col, sketch=1)
    for row in range(2):
        for i in range(8):
            if 1 < i < 6 and row == 1:
                continue
            wx = L + w * (0.04 + i * 0.12)
            if 0.28 < (wx - L) / w < 0.7:
                continue
            win = path_rect(wx, B - h * (0.6 - row * 0.28), w * 0.06, h * 0.16)
            pen.fill(win, (60, 62, 68), 0.75)
            pen.stroke(win, s * 0.006, 1, col, sketch=1)
    for i in range(3):
        pen.stroke(path_poly([(L + w * (0.28 - i * 0.02), B - h * 0.08 + i * h * 0.03), (L + w * (0.72 + i * 0.02), B - h * 0.08 + i * h * 0.03)]),
                   s * 0.006, 1, col, sketch=1)


@prop("tree")
def _tree(pen, x, y, s, P, t):
    """Cây lớn: leaves 0..1, grow 0..1, glow."""
    col = pen.ink
    rnd = random.Random(P.get("seed", 5))
    grow = P.get("grow", 1.0)
    depth = P.get("depth", 7)
    leaves = P.get("leaves", 0.0)
    tips = []
    if P.get("glow"):
        pen.glow(x, y - s * 0.6, s * 0.9, GLOW, 0.55 * P["glow"])

    def br(p, a, L, d):
        g = max(0.0, min(1.0, grow * (depth + 1) - (depth - d)))
        if g <= 0:
            return
        e = mv(p, a + rnd.uniform(-4, 4), L * g)
        mid = mv(p, a + rnd.uniform(-8, 8), L * g * 0.5)
        pen.stroke(path_smooth([p, mid, e]), max(1.0, s * 0.0018 * (d + 1) ** 1.45), 1, col, sketch=2 if d > 2 else 1)
        if d == 0:
            tips.append(e)
            return
        k = 3 if d > depth - 2 else 2
        for i in range(k):
            sp = (i - (k - 1) / 2) * rnd.uniform(24, 38)
            br(e, a + sp + rnd.uniform(-8, 8), L * rnd.uniform(0.66, 0.8), d - 1)

    trunk_h = s * 0.42
    base = (x, y)
    top = (x, y - trunk_h * grow)
    tw = s * 0.055
    tr = path_smooth([(x - tw * 1.9, y), (x - tw * 0.9, y - trunk_h * 0.3 * grow), (x - tw * 0.7, top[1] + trunk_h * 0.15), (x - tw * 0.5, top[1]),
                      (x + tw * 0.5, top[1]), (x + tw * 0.7, top[1] + trunk_h * 0.15), (x + tw * 0.9, y - trunk_h * 0.3 * grow),
                      (x + tw * 1.9, y)], True)
    pen.fill(tr, (205, 185, 150), 1)
    pen.hatch(tr, 5, 90, 1, 0.45, col)
    pen.stroke(tr, s * 0.012, 1, col)
    for sd, L_ in ((-1, 0.16), (-1, 0.09), (1, 0.14), (1, 0.08)):
        st_ = (x + sd * tw * 1.2, y - s * 0.01)
        en_ = (x + sd * (tw * 1.4 + s * L_), y + s * 0.025 * (0.6 if L_ > 0.1 else 1.2))
        pen.stroke(path_quad(st_, (lerp(st_[0], en_[0], 0.5), y + s * 0.002), en_), s * 0.009, 0.85, col, sketch=1)
    for i in range(3):
        br(top, 180 + (i - 1) * 32, s * 0.2, depth - 1)
    if leaves > 0:
        for p in tips:
            if rnd.random() > leaves:
                continue
            cl = path_circle(p[0], p[1], s * rnd.uniform(0.02, 0.04))
            pen.fill(cl, (205, 195, 150), 0.35)
            pen.stroke(cl, s * 0.0025, 0.55, col, sketch=1, dev=1.5)


@prop("sapling")
def _sapling(pen, x, y, s, P, t):
    col = pen.ink
    g = P.get("grow", 1.0)
    top = (x, y - s * g)
    pen.stroke(path_smooth([(x, y), (x + s * 0.03, y - s * 0.5 * g), top]), s * 0.035, 1, col)
    for i in range(int(3 + 5 * g)):
        f = 0.3 + i * 0.1
        if f > g:
            break
        p0 = (x + s * 0.02, y - s * f)
        sd = 1 if i % 2 else -1
        tip = (p0[0] + sd * s * 0.22, p0[1] - s * 0.1)
        lp = skia.Path()
        lp.moveTo(*p0)
        lp.quadTo(p0[0] + sd * s * 0.1, p0[1] - s * 0.14, *tip)
        lp.quadTo(p0[0] + sd * s * 0.14, p0[1] + s * 0.02, *p0)
        pen.fill(lp, (225, 215, 180), 1)
        pen.stroke(lp, s * 0.012, 1, col, sketch=1)
    for i in range(5):
        pen.stroke(path_quad((x, y), (x + (i - 2) * s * 0.06, y + s * 0.06), (x + (i - 2) * s * 0.12, y + s * 0.1)), s * 0.012, 0.8, col,
                   sketch=1)


@prop("sun")
def _sun(pen, x, y, s, P, t):
    col = pen.ink
    r = s / 2
    pen.glow(x, y, s * 2.2, GLOW, 0.65)
    pen.glow(x, y, s * 0.9, (255, 245, 215), 0.8)
    pen.fill(path_circle(x, y, r), (255, 238, 190), 0.9)
    pen.stroke(path_circle(x, y, r), s * 0.02, 0.8, col)
    rot = t * 6
    for i in range(16):
        a = rot + i * 22.5
        l1, l2 = r * 1.25, r * (1.65 if i % 2 else 1.95)
        pen.stroke(path_poly([mv((x, y), a, l1), mv((x, y), a, l2)]), s * 0.018, 0.75, col, sketch=1)


@prop("cloud")
def _cloud(pen, x, y, s, P, t):
    col = pen.ink
    pts = []
    for i in range(9):
        a = math.pi * 2 * i / 9
        rr = s * (0.28 if i % 2 else 0.36)
        pts.append((x + math.cos(a) * s * 0.5 + math.cos(a) * rr * 0.4, y + math.sin(a) * s * 0.22 + math.sin(a) * rr * 0.25))
    p = path_smooth(pts, True)
    pen.fill(p, lerpc((245, 240, 230), (120, 118, 118), P.get("dark", 0)), 0.95)
    pen.stroke(p, s * 0.018, 1, col)
    rain = P.get("rain", 0)
    if rain:
        rnd = random.Random(3)
        rp = skia.Path()
        for i in range(int(18 * rain)):
            rx = x + rnd.uniform(-0.45, 0.45) * s
            ry = y + s * 0.25 + ((rnd.random() + t * 1.4) % 1.0) * s * 1.1
            rp.moveTo(rx, ry)
            rp.lineTo(rx - s * 0.03, ry + s * 0.1)
        pen.stroke(rp, s * 0.01, 0.7, col, sketch=1)


@prop("door")
def _door(pen, x, y, s, P, t):
    """s = chiều cao cửa; open 0..1; light 0..1 (ánh sáng tràn ra)."""
    col = pen.ink
    h, w = s, s * 0.48
    L, T = x - w / 2, y - h
    op = P.get("open", 1.0)
    li = P.get("light", 1.0)
    hole = path_rect(L, T, w, h)
    pen.fill(hole, LIGHT, 1)
    if li:
        pen.glow(x, y - h * 0.5, h * 0.9, (255, 250, 235), 0.7 * li)
        spill = path_poly([(L, y), (L + w, y), (x + w * 1.4, y + h * 0.35), (x - w * 1.4, y + h * 0.35)], True)
        pen.fill(spill, (255, 250, 238), 0.45 * li, skia.BlendMode.kScreen)
    fr = path_rect(L - w * 0.06, T - w * 0.06, w * 1.12, h + w * 0.06)
    pen.stroke(fr, s * 0.012, 1, col)
    pen.stroke(hole, s * 0.008, 1, col)
    dw = w * (1 - op * 0.75)
    panel = path_poly([(L, T), (L - dw * 0.35 * op + dw * (1 - op), T - h * 0.03 * op), (L - dw * 0.35 * op + dw * (1 - op), y + h * 0.03 * op),
                       (L, y)], True)
    if op < 0.02:
        panel = path_rect(L, T, w, h)
    pen.fill(panel, (205, 185, 150), 1)
    pen.hatch(panel, 6, 88, 1, 0.45, col)
    pen.stroke(panel, s * 0.01, 1, col)


@prop("vase")
def _vase(pen, x, y, s, P, t):
    col = pen.ink
    broken = P.get("broken", 0)
    pts = [(-0.12, 0), (-0.28, -0.12), (-0.3, -0.42), (-0.14, -0.66), (-0.1, -0.8), (-0.16, -0.9),
           (0.16, -0.9), (0.1, -0.8), (0.14, -0.66), (0.3, -0.42), (0.28, -0.12), (0.12, 0)]
    pen.c.save()
    if broken:
        pen.c.rotate(-100, x, y)
    p = path_smooth([(x + a * s, y + b * s) for a, b in pts], True)
    pen.fill(p, (200, 180, 150), 1)
    pen.hatch(p, 5, 60, 1, 0.4, col)
    pen.stroke(p, s * 0.02, 1, col)
    pen.c.restore()
    if broken:
        rnd = random.Random(9)
        for i in range(7):
            cx_, cy_ = x + rnd.uniform(-1.1, 1.3) * s, y + rnd.uniform(-0.05, 0.25) * s
            sh = path_poly([(cx_ + rnd.uniform(-0.1, 0.1) * s, cy_ + rnd.uniform(-0.06, 0.06) * s) for _ in range(4)], True)
            pen.fill(sh, (200, 180, 150), 1)
            pen.stroke(sh, s * 0.012, 1, col, sketch=1)


@prop("shards")
def _shards(pen, x, y, s, P, t):
    """Mảnh gốm vỡ rải trên sàn: n, spread (tỉ lệ s). Mảnh có độ dày + vân trang trí."""
    col = pen.ink
    rnd = random.Random(P.get("seed", 11))
    n = int(P.get("n", 12))
    pieces = []
    for i in range(n):
        cx_ = x + rnd.uniform(-1, 1) * s * P.get("spread", 1.0)
        cy_ = y + rnd.uniform(-0.12, 0.18) * s
        sz = s * rnd.uniform(0.08, 0.2) * (0.6 + 0.4 * (cy_ - y + 0.12 * s) / (0.3 * s))
        pieces.append((cy_, cx_, sz, rnd.uniform(0, 360), rnd.random()))
    for cy_, cx_, sz, rot, k in sorted(pieces):
        pts = []
        for j in range(5):
            a = math.radians(rot + j * 72 + rnd.uniform(-20, 20))
            pts.append((cx_ + math.cos(a) * sz * rnd.uniform(0.6, 1.0), cy_ + math.sin(a) * sz * 0.4 * rnd.uniform(0.6, 1.0)))
        top = path_poly(pts, True)
        side = path_poly([(px_, py_ + sz * 0.12) for px_, py_ in pts], True)
        sp = skia.Paint(AntiAlias=True, Color=argb((40, 28, 16), 0.25))
        sp.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, sz * 0.15))
        pen.c.drawPath(side, sp)
        pen.fill(side, (150, 120, 90), 1)
        pen.fill(top, (225, 205, 175) if k > 0.4 else (205, 180, 145), 1)
        pen.hatch(top, 3, 40 + k * 60, 1, 0.3, col)
        pen.stroke(top, s * 0.008, 1, col, sketch=2, dev=0.5)
    for i in range(int(n * 2.5)):
        px_, py_ = x + rnd.uniform(-1.2, 1.2) * s, y + rnd.uniform(-0.05, 0.25) * s
        pen.fill(path_circle(px_, py_, s * rnd.uniform(0.005, 0.012)), col, 0.6)


@prop("pot")
def _pot(pen, x, y, s, P, t):
    """Bình gốm có hoa văn; broken 0..1 = nửa trên vỡ mất (miệng răng cưa); rot."""
    col = pen.ink
    br = P.get("broken", 0)
    pts = [(-0.18, 0), (-0.36, -0.16), (-0.4, -0.45), (-0.25, -0.72), (-0.15, -0.85), (-0.2, -0.95),
           (0.2, -0.95), (0.15, -0.85), (0.25, -0.72), (0.4, -0.45), (0.36, -0.16), (0.18, 0)]
    body = path_smooth([(x + a * s, y + b * s) for a, b in pts], True)
    pen.c.save()
    if br:
        cut = [(x - 0.5 * s, y + 0.05 * s), (x + 0.5 * s, y + 0.05 * s)]
        for i in range(9):
            f = 1 - i / 8
            cut.append((x + (f - 0.5) * s, y - s * (0.55 + 0.35 * (1 - br)) + (0.08 * s if i % 2 else -0.04 * s)))
        pen.c.clipPath(path_poly(cut, True), doAntiAlias=True)
    _soft_paint_fill(pen, body, (232, 214, 184), (150, 118, 82), (x - 0.4 * s, y - s), (x + 0.4 * s, y))
    pen.hatch(body, 3, 70, 1, 0.3, col)
    for k in range(3):
        yy = y - s * (0.3 + 0.18 * k)
        pen.stroke(path_smooth([(x - 0.36 * s, yy), (x - 0.12 * s, yy + 0.05 * s), (x + 0.12 * s, yy - 0.04 * s), (x + 0.36 * s, yy)]),
                   s * 0.01, 0.75, col, sketch=1)
        for j in range(5):
            cx_ = x + (-0.24 + j * 0.12) * s
            pen.stroke(path_circle(cx_, yy - 0.07 * s, 0.025 * s), s * 0.006, 0.6, col, sketch=1)
    pen.stroke(body, s * 0.016, 1, col, sketch=2)
    pen.c.restore()


@prop("knife")
def _knife(pen, x, y, s, P, t):
    col = pen.ink
    pen.c.save()
    pen.c.rotate(P.get("rot", -35), x, y)
    blade = path_poly([(x, y - s * 0.05), (x + s * 0.65, y - s * 0.02), (x + s * 0.8, y + s * 0.04), (x, y + s * 0.05)], True)
    pen.fill(blade, (235, 235, 232), 1)
    pen.hatch(blade, 4, 20, 1, 0.3, col)
    pen.stroke(blade, s * 0.02, 1, col)
    hd = path_rect(x - s * 0.3, y - s * 0.045, s * 0.3, s * 0.09, s * 0.03)
    pen.fill(hd, (90, 70, 50), 1)
    pen.stroke(hd, s * 0.02, 1, col)
    pen.stroke(path_poly([(x, y - s * 0.1), (x, y + s * 0.1)]), s * 0.035, 1, col)
    pen.c.restore()


@prop("bubble")
def _bubble(pen, x, y, s, P, t):
    """Bóng thoại: content = scribble | angry | heart | ! | ? | ... | text:<chữ>; tail=[dx,dy] (tỉ lệ s); spiky=true."""
    col = pen.ink
    w, h = s, s * 0.62
    tdx, tdy = P.get("tail", [-0.35, 0.6])
    if P.get("spiky"):
        pts = []
        for i in range(22):
            a = 2 * math.pi * i / 22
            k = 1.0 if i % 2 else 0.78
            pts.append((x + math.cos(a) * w * 0.55 * k, y + math.sin(a) * h * 0.55 * k))
        p = path_poly(pts, True)
    else:
        p = path_oval(x, y, w * 0.5, h * 0.5)
    tail = path_poly([(x + tdx * s * 0.35 - s * 0.06, y + h * 0.3), (x + tdx * s, y + tdy * s), (x + tdx * s * 0.35 + s * 0.08, y + h * 0.3)],
                     True)
    both = skia.Op(p, tail, skia.PathOp.kUnion_PathOp) or p
    pen.fill(both, (250, 246, 236), 0.96)
    pen.stroke(both, s * 0.02, 1, col)
    c = str(P.get("content", "scribble"))
    if c in ("scribble", "angry"):
        rnd = random.Random(int(t * 6) if c == "angry" else 4)
        pts = [(x + rnd.uniform(-0.3, 0.3) * w, y + rnd.uniform(-0.18, 0.18) * h * 1.3) for _ in range(12)]
        pen.stroke(path_poly(pts) if c == "angry" else path_smooth(pts), s * 0.02, 0.9, col, sketch=2, dev=2)
    elif c == "heart":
        _heart(pen, x, y + s * 0.03, s * 0.42, {}, t)
    elif c in ("!", "?", "...", "!!", "?!"):
        draw_text(pen.c, c, x, y + s * 0.1, s * 0.34, pen.ink, 1.0)
    elif c.startswith("text:"):
        txt = c[5:]
        size = s * 0.2
        f = skia.Font(typeface("Montserrat-Bold.ttf"), size)
        while f.measureText(nfc(txt)) > w * 0.8 and size > 6:
            size *= 0.92
            f = skia.Font(typeface("Montserrat-Bold.ttf"), size)
        draw_text(pen.c, txt, x, y + size * 0.35, size, pen.ink, 1.0, "Montserrat-Bold.ttf")


@prop("lamp")
def _lamp(pen, x, y, s, P, t):
    col = pen.ink
    fl = 1 + 0.08 * math.sin(t * 13) + 0.05 * math.sin(t * 7.3)
    pen.glow(x, y - s * 0.55, s * 1.6 * fl, GLOW, 0.7)
    base = path_oval(x, y - s * 0.12, s * 0.28, s * 0.12)
    pen.fill(base, (190, 170, 130), 1)
    pen.stroke(base, s * 0.03, 1, col)
    glass = path_smooth([(x - s * 0.1, y - s * 0.2), (x - s * 0.2, y - s * 0.45), (x - s * 0.1, y - s * 0.8), (x + s * 0.1, y - s * 0.8),
                         (x + s * 0.2, y - s * 0.45), (x + s * 0.1, y - s * 0.2)], True)
    pen.fill(glass, (255, 240, 200), 0.6)
    pen.stroke(glass, s * 0.02, 0.8, col)
    fp = path_smooth([(x, y - s * (0.62 + 0.04 * fl)), (x + s * 0.06, y - s * 0.42), (x, y - s * 0.34), (x - s * 0.06, y - s * 0.42)], True)
    pen.fill(fp, (255, 190, 80), 1)
    pen.glow(x, y - s * 0.45, s * 0.35, (255, 220, 140), 0.9)


@prop("candle")
def _candle(pen, x, y, s, P, t):
    col = pen.ink
    fl = 1 + 0.1 * math.sin(t * 11)
    pen.glow(x, y - s * 1.05, s * 1.3 * fl, GLOW, 0.65)
    body = path_rect(x - s * 0.12, y - s * 0.9, s * 0.24, s * 0.9)
    pen.fill(body, (245, 238, 220), 1)
    pen.stroke(body, s * 0.03, 1, col)
    fp = path_smooth([(x, y - s * (1.25 + 0.05 * fl)), (x + s * 0.07, y - s * 1.02), (x, y - s * 0.94), (x - s * 0.07, y - s * 1.02)], True)
    pen.fill(fp, (255, 190, 80), 1)


@prop("frame")
def _frame(pen, x, y, s, P, t):
    """Khung ảnh kỷ niệm; oval=true cho khung bầu dục."""
    col = pen.ink
    pen.c.save()
    pen.c.rotate(P.get("rot", 0), x, y)
    w, h = s, s * 0.8
    if P.get("oval"):
        o, i = path_oval(x, y, w * 0.45, h * 0.55), path_oval(x, y, w * 0.34, h * 0.43)
    else:
        o, i = path_rect(x - w / 2, y - h / 2, w, h), path_rect(x - w * 0.37, y - h * 0.35, w * 0.74, h * 0.7)
    pen.fill(o, (205, 185, 150), 1)
    pen.hatch(o, 4, 45, 1, 0.35, col)
    pen.fill(i, (240, 232, 214), 1)
    pen.hatch(i, 7, -30, 1, 0.15, col)
    pen.stroke(o, s * 0.03, 1, col)
    pen.stroke(i, s * 0.02, 1, col)
    pen.c.restore()


@prop("coins")
def _coins(pen, x, y, s, P, t):
    col = pen.ink
    n = int(P.get("n", 5))
    for j in range(n):
        c = path_oval(x, y - j * s * 0.1, s * 0.4, s * 0.12)
        pen.fill(c, (225, 200, 140), 1)
        pen.stroke(c, s * 0.03, 1, col)


@prop("moneybag")
def _moneybag(pen, x, y, s, P, t):
    col = pen.ink
    p = path_smooth([(x - s * 0.15, y - s * 0.72), (x - s * 0.42, y - s * 0.35), (x - s * 0.38, y), (x + s * 0.38, y),
                     (x + s * 0.42, y - s * 0.35), (x + s * 0.15, y - s * 0.72)], True)
    pen.fill(p, (215, 195, 150), 1)
    pen.hatch(p, 6, 60, 1, 0.3, col)
    pen.stroke(p, s * 0.03, 1, col)
    pen.stroke(path_poly([(x - s * 0.16, y - s * 0.74), (x + s * 0.16, y - s * 0.74)]), s * 0.04, 1, col)
    draw_text(pen.c, "đ", x, y - s * 0.15, s * 0.42, col, 0.9)


@prop("wall")
def _wall(pen, x, y, s, P, t):
    """Bức tường gạch (ngăn cách). s = chiều cao; width = tỉ lệ s."""
    col = pen.ink
    h, w = s, s * P.get("width", 0.35)
    L, T = x - w / 2, y - h
    rc = path_rect(L, T, w, h)
    pen.fill(rc, (205, 190, 165), 1)
    bp = skia.Path()
    rows = 9
    for r_ in range(rows + 1):
        yy = T + h * r_ / rows
        bp.moveTo(L, yy)
        bp.lineTo(L + w, yy)
        if r_ < rows:
            off = 0.5 if r_ % 2 else 0
            for c_ in range(3):
                xx = L + w * ((c_ + off) / 2.5)
                if L < xx < L + w:
                    bp.moveTo(xx, yy)
                    bp.lineTo(xx, yy + h / rows)
    pen.stroke(bp, s * 0.006, 0.8, col, sketch=1)
    pen.stroke(rc, s * 0.01, 1, col)


@prop("clock")
def _clock(pen, x, y, s, P, t):
    col = pen.ink
    r = s / 2
    c = path_circle(x, y, r)
    pen.fill(c, (245, 238, 222), 1)
    pen.stroke(c, s * 0.035, 1, col)
    for i in range(12):
        pen.stroke(path_poly([mv((x, y), i * 30, r * 0.8), mv((x, y), i * 30, r * 0.92)]), s * 0.02, 1, col, sketch=1)
    sp = P.get("speed", 1.0)
    pen.stroke(path_poly([(x, y), mv((x, y), 180 - t * 60 * sp, r * 0.75)]), s * 0.025, 1, col, sketch=1)
    pen.stroke(path_poly([(x, y), mv((x, y), 180 - t * 5 * sp - 90, r * 0.5)]), s * 0.04, 1, col, sketch=1)


@prop("phone")
def _phone(pen, x, y, s, P, t):
    col = pen.ink
    body = path_rect(x - s * 0.25, y - s * 0.5, s * 0.5, s, s * 0.07)
    pen.fill(body, (60, 58, 56), 1)
    scr = path_rect(x - s * 0.21, y - s * 0.42, s * 0.42, s * 0.8, s * 0.03)
    pen.fill(scr, (230, 235, 240), 1)
    if P.get("glow"):
        pen.glow(x, y, s * 0.8, (220, 235, 255), 0.5 * P["glow"])
    pen.stroke(body, s * 0.03, 1, col)


@prop("playbtn")
def _playbtn(pen, x, y, s, P, t):
    """Kỷ niệm chương nút Play (tâm x,y; s = bề ngang). gold=true → nút vàng; glow, rot."""
    col = pen.ink
    pen.c.save()
    pen.c.rotate(P.get("rot", 0), x, y)
    w, h = s, s * 1.2
    if P.get("glow"):
        pen.glow(x, y, s * 1.1, GLOW, 0.55 * P["glow"])
    frame = path_rect(x - w / 2, y - h / 2, w, h, s * 0.04)
    pen.fill(frame, (120, 92, 62), 1)
    pen.hatch(frame, 4, 45, 1, 0.35, col)
    plate = path_rect(x - w * 0.42, y - h * 0.42, w * 0.84, h * 0.84, s * 0.02)
    metal = (236, 200, 110) if P.get("gold") else (214, 216, 220)
    pen.fill(plate, metal, 1)
    pen.hatch(plate, 9, -35, 1, 0.12, col)
    by = y - h * 0.08
    btn = path_rect(x - w * 0.27, by - w * 0.19, w * 0.54, w * 0.38, w * 0.1)
    pen.fill(btn, (250, 250, 248), 1)
    pen.stroke(btn, s * 0.025, 1, col)
    tri = path_poly([(x - w * 0.07, by - w * 0.1), (x + w * 0.11, by), (x - w * 0.07, by + w * 0.1)], True)
    pen.fill(tri, (150, 150, 155) if not P.get("gold") else (190, 140, 50), 1)
    pen.stroke(tri, s * 0.015, 1, col)
    for k in range(3):
        ly = y + h * (0.2 + k * 0.06)
        pen.stroke(path_poly([(x - w * (0.22 - k * 0.04), ly), (x + w * (0.22 - k * 0.04), ly)]), s * 0.012, 0.6, col)
    pen.stroke(plate, s * 0.015, 1, col)
    pen.stroke(frame, s * 0.03, 1, col)
    pen.c.restore()


@prop("screen")
def _screen(pen, x, y, s, P, t):
    """Khung video (tâm x,y; s = cạnh dài). vertical=true → dọc 9:16; play=true → nút ▶; dim 0..1 làm tối; glow."""
    col = pen.ink
    v = P.get("vertical")
    w, h = (s * 0.5625, s) if v else (s, s * 0.5625)
    if P.get("glow"):
        pen.glow(x, y, s * 0.8, GLOW, 0.5 * P["glow"])
    body = path_rect(x - w / 2, y - h / 2, w, h, s * 0.03)
    pen.fill(body, (70, 64, 58), 1)
    scr = path_rect(x - w / 2 + s * 0.03, y - h / 2 + s * 0.03, w - s * 0.06, h - s * 0.06, s * 0.015)
    d = P.get("dim", 0)
    base = (236, 226, 204)
    pen.fill(scr, tuple(int(c * (1 - 0.55 * d)) for c in base), 1)
    pen.hatch(scr, 8, -30, 1, 0.12 + 0.3 * d, col)
    if P.get("play", True):
        r = min(w, h) * 0.16
        pen.fill(path_circle(x, y, r), (200, 70, 55), 0.95)
        tri = path_poly([(x - r * 0.35, y - r * 0.5), (x + r * 0.55, y), (x - r * 0.35, y + r * 0.5)], True)
        pen.fill(tri, (250, 245, 235), 1)
        pen.stroke(path_circle(x, y, r), s * 0.012, 1, col)
    pen.stroke(body, s * 0.025, 1, col)


@prop("table")
def _table(pen, x, y, s, P, t):
    col = pen.ink
    top = path_rect(x - s / 2, y - s * 0.42, s, s * 0.05)
    pen.fill(top, (200, 175, 135), 1)
    pen.hatch(top, 4, 5, 1, 0.4, col)
    pen.stroke(top, s * 0.012, 1, col)
    for lx in (-0.44, 0.4):
        pen.stroke(path_poly([(x + s * lx, y - s * 0.37), (x + s * lx, y)]), s * 0.018, 1, col)


@prop("chair")
def _chair(pen, x, y, s, P, t):
    col = pen.ink
    pen.stroke(path_poly([(x - s * 0.2, y), (x - s * 0.2, y - s * 0.45), (x + s * 0.2, y - s * 0.45), (x + s * 0.2, y)]), s * 0.03, 1, col)
    pen.stroke(path_poly([(x - s * 0.2, y - s * 0.45), (x - s * 0.22, y - s)]), s * 0.03, 1, col)


@prop("arrow")
def _arrow(pen, x, y, s, P, t):
    """Mũi tên cong từ (x,y) tới to=[x2,y2] (toạ độ panel 0..1 → được đổi sẵn thành px trong P['_to'])."""
    col = pen.ink
    x2, y2 = P["_to"]
    mx, my = (x + x2) / 2, (y + y2) / 2 - P.get("bend", 0.2) * math.hypot(x2 - x, y2 - y)
    prog = P.get("draw", 1.0)
    pts = []
    for i in range(int(24 * prog) + 1):
        f = i / 24
        pts.append(((1 - f) ** 2 * x + 2 * (1 - f) * f * mx + f * f * x2, (1 - f) ** 2 * y + 2 * (1 - f) * f * my + f * f * y2))
    if len(pts) < 2:
        return
    pen.stroke(path_poly(pts), s * 0.03, 1, col)
    if prog >= 0.98:
        a = ang_of(pts[-3], pts[-1])
        pen.stroke(path_poly([mv(pts[-1], a + 150, s * 0.18), pts[-1], mv(pts[-1], a - 150, s * 0.18)]), s * 0.03, 1, col)


@prop("lightning")
def _lightning(pen, x, y, s, P, t):
    col = pen.ink
    p = path_poly([(x, y - s * 0.5), (x + s * 0.18, y - s * 0.5), (x + s * 0.05, y - s * 0.08), (x + s * 0.2, y - s * 0.08),
                   (x - s * 0.1, y + s * 0.5), (x - s * 0.01, y + s * 0.02), (x - s * 0.15, y + s * 0.02)], True)
    pen.fill(p, (60, 50, 40), 0.9)
    pen.stroke(p, s * 0.02, 1, col, sketch=2)


@prop("sparkle")
def _sparkle(pen, x, y, s, P, t):
    rnd = random.Random(P.get("seed", 2))
    for i in range(int(P.get("n", 6))):
        cx_, cy_ = x + rnd.uniform(-0.5, 0.5) * s, y + rnd.uniform(-0.5, 0.5) * s
        ph = (t * 1.3 + rnd.random()) % 1
        k = math.sin(ph * math.pi)
        r = s * 0.06 * k
        if r < 0.5:
            continue
        p = path_poly([(cx_, cy_ - r), (cx_ + r * 0.25, cy_ - r * 0.25), (cx_ + r, cy_), (cx_ + r * 0.25, cy_ + r * 0.25), (cx_, cy_ + r),
                       (cx_ - r * 0.25, cy_ + r * 0.25), (cx_ - r, cy_), (cx_ - r * 0.25, cy_ - r * 0.25)], True)
        pen.glow(cx_, cy_, r * 3, GLOW, 0.6 * k)
        pen.fill(p, (255, 245, 210), 0.95)


@prop("mark")
def _mark(pen, x, y, s, P, t):
    draw_text(pen.c, P.get("text", "?"), x, y + s * 0.35, s, pen.ink, 0.95)


@prop("bridge")
def _bridge(pen, x, y, s, P, t):
    col = pen.ink
    w = s
    pts = [(x - w / 2 + w * i / 20, y - math.sin(math.pi * i / 20) * s * 0.22) for i in range(21)]
    pen.stroke(path_poly(pts), s * 0.02, 1, col)
    pen.stroke(path_poly([(a, b + s * 0.05) for a, b in pts]), s * 0.02, 1, col)
    for i in range(0, 21, 2):
        a, b = pts[i]
        pen.stroke(path_poly([(a, b), (a, b - s * 0.1)]), s * 0.012, 1, col, sketch=1)
    pen.stroke(path_poly([(a, b - s * 0.1) for a, b in pts]), s * 0.012, 1, col, sketch=1)


@prop("stairs")
def _stairs(pen, x, y, s, P, t):
    col = pen.ink
    n = int(P.get("n", 5))
    sw, sh = s / n, s * 0.8 / n
    pts = [(x - s / 2, y)]
    for i in range(n):
        pts += [(x - s / 2 + i * sw, y - (i + 1) * sh), (x - s / 2 + (i + 1) * sw, y - (i + 1) * sh)]
    pts += [(x + s / 2, y)]
    p = path_poly(pts, True)
    pen.fill(p, (225, 212, 188), 1)
    pen.hatch(p, 8, 45, 1, 0.25, col)
    pen.stroke(p, s * 0.012, 1, col)


@prop("gift")
def _gift(pen, x, y, s, P, t):
    col = pen.ink
    b = path_rect(x - s * 0.4, y - s * 0.6, s * 0.8, s * 0.6)
    pen.fill(b, (235, 222, 196), 1)
    pen.stroke(b, s * 0.03, 1, col)
    pen.stroke(path_rect(x - s * 0.45, y - s * 0.75, s * 0.9, s * 0.16), s * 0.03, 1, col)
    pen.stroke(path_poly([(x, y), (x, y - s * 0.75)]), s * 0.05, 1, col)
    for sd in (-1, 1):
        pen.stroke(path_oval(x + sd * s * 0.14, y - s * 0.85, s * 0.14, s * 0.08, rot=sd * 20), s * 0.03, 1, col)


@prop("book")
def _book(pen, x, y, s, P, t):
    col = pen.ink
    for sd in (-1, 1):
        p = path_poly([(x, y), (x + sd * s * 0.5, y - s * 0.06), (x + sd * s * 0.5, y - s * 0.46), (x, y - s * 0.4)], True)
        pen.fill(p, (245, 238, 220), 1)
        pen.stroke(p, s * 0.025, 1, col)
        for j in range(4):
            yy = y - s * (0.32 - j * 0.07)
            pen.stroke(path_poly([(x + sd * s * 0.08, yy), (x + sd * s * 0.42, yy - s * 0.03)]), s * 0.01, 0.6, col, sketch=1)


@prop("briefcase")
def _briefcase(pen, x, y, s, P, t):
    col = pen.ink
    b = path_rect(x - s * 0.5, y, s, s * 0.7, s * 0.06)
    pen.fill(b, (190, 165, 125), 1)
    pen.hatch(b, 6, 60, 1, 0.35, col)
    pen.stroke(b, s * 0.04, 1, col)
    pen.stroke(path_rect(x - s * 0.18, y - s * 0.16, s * 0.36, s * 0.18, s * 0.05), s * 0.04, 1, col)


@prop("cane")
def _cane(pen, x, y, s, P, t):
    col = pen.ink
    g = P.get("_ground", y + s)
    pen.stroke(path_poly([(x, y), (x + s * 0.02, g)]), s * 0.05, 1, col)
    pen.stroke(path_quad((x, y), (x - s * 0.02, y - s * 0.12), (x - s * 0.12, y - s * 0.06)), s * 0.05, 1, col)


@prop("flower")
def _flower(pen, x, y, s, P, t):
    col = pen.ink
    top = (x, y - s)
    pen.stroke(path_quad((x, y), (x + s * 0.1, y - s * 0.5), top), s * 0.04, 1, col)
    for i in range(6):
        c = mv(top, i * 60, s * 0.14)
        p = path_oval(c[0], c[1], s * 0.1, s * 0.16, rot=-i * 60)
        pen.fill(p, (245, 235, 215), 1)
        pen.stroke(p, s * 0.025, 1, col, sketch=1)
    pen.fill(path_circle(*top, s * 0.07), (200, 170, 110), 1)


@prop("tape")
def _tape(pen, x, y, s, P, t):
    col = pen.ink
    o, i = path_circle(x, y, s * 0.5), path_circle(x, y, s * 0.25)
    pen.fill(o, (230, 225, 210), 1)
    pen.hatch(o, 4, 30, 1, 0.3, col)
    pen.fill(i, (245, 240, 228), 1)
    pen.stroke(o, s * 0.04, 1, col)
    pen.stroke(i, s * 0.04, 1, col)


@prop("chain")
def _chain(pen, x, y, s, P, t):
    col = pen.ink
    n = int(P.get("n", 6))
    for i in range(n):
        cx_ = x - s / 2 + s * (i + 0.5) / n
        pen.stroke(path_oval(cx_, y, s / n * 0.6, s / n * 0.32 if i % 2 else s / n * 0.12), s * 0.02, 1, col)


@prop("mountain")
def _mountain(pen, x, y, s, P, t):
    col = pen.ink
    p = path_poly([(x - s * 0.6, y), (x - s * 0.15, y - s * 0.7), (x, y - s * 0.55), (x + s * 0.2, y - s * 0.85), (x + s * 0.65, y)], True)
    pen.fill(p, (215, 200, 175), 1)
    pen.hatch(p, 7, 60, 1, 0.3, col)
    pen.stroke(p, s * 0.012, 1, col)


@prop("rock")
def _rock(pen, x, y, s, P, t):
    col = pen.ink
    p = path_smooth([(x - s * 0.5, y), (x - s * 0.4, y - s * 0.35), (x, y - s * 0.5), (x + s * 0.42, y - s * 0.3), (x + s * 0.5, y)], True)
    pen.fill(p, (190, 178, 160), 1)
    pen.hatch(p, 5, 45, 1, 0.4, col)
    pen.stroke(p, s * 0.025, 1, col)


@prop("boat")
def _boat(pen, x, y, s, P, t):
    """Thuyền gỗ nhìn ngang. (x,y) = tâm mép nước, s = chiều dài. bob 0..1 (nhấp nhô), flip (mũi sang trái),
    oar 0..1 (mái chèo), ripple 0..1 (gợn nước quanh thân), dark 0..1. Người ngồi trong thuyền: đặt fig TRƯỚC thuyền
    trong items, chân ở y − 0.06·s, thân thuyền che chân."""
    col = pen.ink
    bob = P.get("bob", 0.6)
    ph = P.get("phase", 0.0)
    dy = math.sin(t * 1.7 + ph) * s * 0.012 * bob
    rot = math.sin(t * 1.3 + ph + 0.8) * 2.2 * bob
    sd = 1
    pen.c.save()
    pen.c.rotate(rot, x, y)
    pen.c.translate(0, dy)
    if P.get("flip"):                                              # mũi sang trái = lật gương quanh tâm thuyền
        pen.c.translate(x, 0)
        pen.c.scale(-1, 1)
        pen.c.translate(-x, 0)
    L, R = x - s / 2, x + s / 2
    rim = [(L + s * 0.02, y - s * 0.17), (x - s * 0.25, y - s * 0.12), (x + s * 0.2, y - s * 0.12), (R + s * 0.05, y - s * 0.21)]
    keel = [(x + s * 0.36, y + s * 0.03), (x, y + s * 0.06), (x - s * 0.38, y + s * 0.02)]
    hull = path_smooth(rim + keel, True)
    wood = lerpc((196, 160, 112), (40, 34, 28), P.get("dark", 0))
    pen.fill(hull, wood, 1)
    pen.hatch(hull, 7, 15, 1, 0.35, col)
    for j in (0.35, 0.65):                                         # ván thuyền
        pl = [(lerp(a[0], b[0], j), lerp(a[1], b[1], j)) for a, b in zip(rim[1:3], keel[::-1][1:3])]
        pen.stroke(path_smooth([rim[0]] + pl + [rim[3]]), s * 0.006, 0.6, col, sketch=1)
    inner = path_smooth([rim[0], (x - s * 0.22, y - s * 0.155), (x + s * 0.22, y - s * 0.155), rim[3]])
    pen.stroke(inner, s * 0.008, 0.8, col, sketch=1)
    pen.stroke(hull, s * 0.012, 1, col, sketch=2)
    if P.get("oar"):
        o = P["oar"]
        a0 = (x - s * 0.05 * sd, y - s * 0.2)
        a1 = (x + s * 0.32 * sd * o, y + s * 0.12)
        pen.stroke(path_poly([a0, a1]), s * 0.012, 1, col)
        blade = path_oval(a1[0], a1[1], s * 0.05, s * 0.018, rot=35 * sd)
        pen.fill(blade, wood, 1)
        pen.stroke(blade, s * 0.008, 1, col)
    pen.c.restore()
    rp = P.get("ripple", 1)
    if rp:                                                         # gợn nước chạy ngang quanh thân
        p = skia.Path()
        for i in range(5):
            f = ((t * 0.35 + i / 5) % 1)
            w = s * (0.55 + 0.5 * f)
            yy = y + s * (0.035 + 0.05 * f)
            p.moveTo(x - w / 2, yy)
            p.quadTo(x - w / 4, yy - s * 0.012, x, yy)
            p.quadTo(x + w / 4, yy + s * 0.012, x + w / 2, yy)
            pen.stroke(p, s * 0.006, 0.55 * rp * (1 - f), col, sketch=1)
            p = skia.Path()


@prop("waves")
def _waves(pen, x, y, s, P, t):
    """Sóng gợn trôi trên mặt nước: (x,y) tâm, s = bề ngang; n hàng, depth (bề dày vùng sóng theo s), speed."""
    col = pen.ink
    n = int(P.get("n", 9))
    depth = P.get("depth", 0.3)
    sp = P.get("speed", 1.0)
    rnd = random.Random(P.get("seed", 5))
    for i in range(n):
        f = i / max(1, n - 1)
        yy = y - s * depth / 2 + s * depth * f
        w = s * (0.06 + 0.1 * f)
        for j in range(3 + i // 3):
            cx_ = x - s / 2 + ((rnd.random() + t * 0.03 * sp * (0.5 + f)) % 1) * s
            p = path_quad((cx_ - w / 2, yy), (cx_, yy - w * 0.12), (cx_ + w / 2, yy))
            pen.stroke(p, s * (0.0018 + 0.0025 * f), 0.35 + 0.3 * f, col, sketch=1)


# ───────────────────────── chữ ─────────────────────────
def draw_text(c, text, x, y, size, color, a=1.0, font="Montserrat-Black.ttf", align="center", outline=None, ow=0.0,
              shadow=0.0):
    text = nfc(str(text))
    f = skia.Font(typeface(font), size)
    f.setEdging(skia.Font.Edging.kAntiAlias)
    w = f.measureText(text)
    x0 = x - w / 2 if align == "center" else (x - w if align == "right" else x)
    if shadow:
        p = skia.Paint(AntiAlias=True, Color=argb((10, 8, 6), a * shadow))
        p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, size * 0.08))
        c.drawString(text, x0 + size * 0.03, y + size * 0.05, f, p)
    if outline:
        p = skia.Paint(AntiAlias=True, Color=argb(outline, a), Style=skia.Paint.kStroke_Style, StrokeWidth=size * ow,
                       StrokeJoin=skia.Paint.kRound_Join)
        c.drawString(text, x0, y, f, p)
    c.drawString(text, x0, y, f, skia.Paint(AntiAlias=True, Color=argb(color, a)))
    return w


def text_width(text, size, font="Montserrat-Black.ttf"):
    return skia.Font(typeface(font), size).measureText(nfc(str(text)))

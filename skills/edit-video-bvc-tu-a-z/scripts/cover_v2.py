"""Ảnh bìa / thumbnail v2 — phong cách TikTok chuẩn (theo ảnh mẫu của anh Cường, 26/10/2026).
Phát triển bởi Bùi Viết Cường.

Bố cục 9:16 (1080×1920), tỷ lệ theo ảnh mẫu:
- 0–10% trên cùng để trống (thanh tìm kiếm TikTok), 20% dưới cùng dành cho caption/giao diện.
- Logo tròn góc trên trái (tâm ≈ 17% × 16.5%).
- Người nói: mặt ở ≈ 27% chiều cao, thấy vai.
- Thẻ tên dạng tab gắn góc trên trái ô tiêu đề; ô tiêu đề navy bo góc ≈ 55–74% chiều cao, viền vàng phát sáng ở cạnh dưới + cạnh phải.
- Hook 3 dòng: dòng trắng + dòng trắng + dòng VÀNG to hơn (hoặc kiểu B: chữ số vàng).
- Hoa văn mờ theo chủ đề ($, đồng hồ, biểu đồ) sau chữ. Dải navy đậm dần từ 70% xuống đáy.

Dùng: from cover_v2 import cover_overlay_v2, compose_thumbnail
"""
import os, re, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

GOLD = (244, 200, 15)        # #F4C80F — vàng nhận diện kênh
GOLD_L = (255, 222, 90)
NAVY = (10, 31, 90)          # thân ô tiêu đề
NAVY_D = (6, 14, 42)         # dải tối đáy khung
EDGE = (60, 110, 230)

_FONT_DIRS = [os.path.expanduser(p) for p in (
    "~/.claude/skills/edit-video-bvc-tu-a-z/fonts", "~/.claude/skills/edit-video-bvc-chia-se/fonts",
    "~/.claude/skills/chuyen-gia-edit-HMT-tu-a-z/fonts")]

def _font(name, size):
    for d in _FONT_DIRS:
        p = os.path.join(d, name)
        if os.path.exists(p): return ImageFont.truetype(p, int(size))
    return ImageFont.load_default()

def black(s): return _font("Montserrat-Black.ttf", s)
def bold(s): return _font("Montserrat-Bold.ttf", s)

# ---------------- hoa văn chủ đề ----------------
def detect_icon(hook_lines):
    t = " ".join(hook_lines).upper()
    if re.search(r"TRIỆU|TỶ|TIỀN|LƯƠNG|DOANH THU|LỜI|LỖ|NỢ|GIÁ|PHÍ|\$|K\b", t): return "dollar"
    if re.search(r"PHÚT|GIỜ|TIẾNG|NGÀY|THÁNG|NĂM|NHANH|THỜI GIAN", t): return "clock"
    if re.search(r"TĂNG|GIẢM|%|DOANH SỐ|KHÁCH|TOP|VIEW", t): return "chart"
    return "none"

def draw_icon(layer, kind, box, alpha=46):
    x0, y0, x1, y1 = box; cx, cy = x1 - (x1 - x0) * 0.20, (y0 + y1) / 2; r = (y1 - y0) * 0.46
    d = ImageDraw.Draw(layer); c = (255, 255, 255, alpha)
    if kind == "dollar":
        f = black(int(r * 2.1)); d.text((cx, cy), "$", font=f, fill=c, anchor="mm")
    elif kind == "clock":
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=c, width=int(r * 0.12))
        d.line([cx, cy, cx, cy - r * 0.62], fill=c, width=int(r * 0.1)); d.line([cx, cy, cx + r * 0.45, cy + r * 0.2], fill=c, width=int(r * 0.1))
    elif kind == "chart":
        w = r * 0.36
        for i, h in enumerate((0.45, 0.7, 1.0)):
            bx = cx - r * 0.9 + i * (w + r * 0.16); d.rounded_rectangle([bx, cy + r - 2 * r * h, bx + w, cy + r], 6, fill=c)
        d.line([cx - r * 0.9, cy + r * 0.2, cx + r * 0.2, cy - r * 0.55], fill=c, width=int(r * 0.09))

# ---------------- avatar tròn ----------------
def avatar_circle(path, d):
    im = Image.open(path).convert("RGBA"); s = min(im.size); im = im.crop(((im.width - s) // 2, 0, (im.width - s) // 2 + s, s)).resize((d, d), Image.LANCZOS)
    m = Image.new("L", (d, d), 0); ImageDraw.Draw(m).ellipse([0, 0, d - 1, d - 1], fill=255); im.putalpha(m)
    pad = 24; out = Image.new("RGBA", (d + 2 * pad, d + 2 * pad), (0, 0, 0, 0)); o = ImageDraw.Draw(out)
    glow = Image.new("RGBA", out.size, (0, 0, 0, 0)); ImageDraw.Draw(glow).ellipse([2, 2, d + 2 * pad - 3, d + 2 * pad - 3], fill=GOLD + (200,))
    out.alpha_composite(glow.filter(ImageFilter.GaussianBlur(7)))
    o.ellipse([pad - 6, pad - 6, pad + d + 5, pad + d + 5], fill=NAVY_D + (255,)); o.ellipse([pad - 4, pad - 4, pad + d + 3, pad + d + 3], outline=GOLD + (255,), width=4)
    out.alpha_composite(im, (pad, pad)); return out

# ---------------- lớp phủ chính ----------------
def _runs(line, mode, is_last):
    """Tách dòng thành các đoạn (text, màu): kiểu A = dòng cuối vàng; kiểu B = token có chữ số màu vàng."""
    if mode == "A": return [(line, GOLD if is_last else (255, 255, 255))]
    toks = line.split(" "); runs = []
    for t in toks:
        col = GOLD if re.search(r"\d", t) or t.endswith("?") and is_last else (255, 255, 255)
        runs.append((t, col))
    return runs

def cover_overlay_v2(hook_lines, tag="#Bùi Viết Cường", avatar_path=None, size=(1080, 1920), mode="A", icon="auto", box_top=0.558):
    W, H = size; k = W / 1080.0
    hook_lines = [str(x).strip().upper() for x in hook_lines if str(x).strip()][:4] or ["HOOK"]
    n = len(hook_lines)
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    # dải navy đậm dần từ 66% → đáy
    yy = np.linspace(0, 1, H, dtype=np.float32)[:, None]
    a = np.clip((yy - 0.62) / 0.28, 0, 1) ** 1.15
    g = np.zeros((H, W, 4), np.uint8); g[..., 0], g[..., 1], g[..., 2] = NAVY_D
    g[..., 3] = np.repeat((a * 246).astype(np.uint8), W, axis=1)
    img.alpha_composite(Image.fromarray(g, "RGBA"))
    # vignette nhẹ phía trên để avatar nổi
    top = np.zeros((H, W, 4), np.uint8); top[..., :3] = 0
    top[..., 3] = np.repeat((np.clip(1 - yy / 0.22, 0, 1) ** 2 * 70).astype(np.uint8), W, axis=1); img.alpha_composite(Image.fromarray(top, "RGBA"))
    # logo tròn
    if avatar_path and os.path.exists(os.path.expanduser(avatar_path)):
        av = avatar_circle(os.path.expanduser(avatar_path), int(172 * k)); img.alpha_composite(av, (int(W * 0.172 - av.width / 2), int(H * 0.165 - av.height / 2)))
    # kích thước ô tiêu đề
    cw = int(W * 0.77); cx0 = (W - cw) // 2; cy0 = int(H * box_top)
    sz = int(76 * k); dd = ImageDraw.Draw(img)
    def width_of(line, f): return dd.textlength(line, font=f)
    while sz > 36 * k and max(width_of(l, black(sz * (1.1 if (mode == "A" and i == n - 1 and n > 1) else 1))) for i, l in enumerate(hook_lines)) > cw - 90 * k: sz -= 2
    lh = [int(sz * (1.38 if (mode == "A" and i == n - 1 and n > 1) else 1.24) * (1.1 if (mode == "A" and i == n - 1 and n > 1) else 1)) for i in range(n)]
    ch = int(60 * k + sum(lh) + 22 * k); max_h = H * 0.742 - cy0
    if ch > max_h: ch = int(max_h)
    # thẻ tên (tab)
    ft = bold(int(34 * k)); tw = int(dd.textlength(tag, font=ft)) + int(56 * k); th = int(54 * k)
    tab = Image.new("RGBA", (W, H), (0, 0, 0, 0)); td = ImageDraw.Draw(tab)
    td.rounded_rectangle([cx0, cy0 - th, cx0 + tw, cy0 + 20], int(14 * k), fill=(8, 22, 70, 255))
    td.text((cx0 + int(28 * k), cy0 - th // 2 + 2), tag, font=ft, fill=(240, 244, 255, 255), anchor="lm")
    # bóng + thân ô (hơi trong suốt để thấy hoa văn nền)
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(sh).rounded_rectangle([cx0 + 6, cy0 + 12, cx0 + cw + 6, cy0 + ch + 12], int(28 * k), fill=(0, 0, 0, 170))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(12 * k)))
    body = Image.new("RGBA", (cw, ch), (0, 0, 0, 0)); bd = ImageDraw.Draw(body)
    grad = np.zeros((ch, cw, 4), np.uint8); t = np.linspace(0, 1, ch)[:, None]
    for c, (a0, b0) in enumerate(zip((16, 38, 112), (8, 22, 70))): grad[..., c] = np.repeat((a0 + (b0 - a0) * t).astype(np.uint8), cw, axis=1)
    grad[..., 3] = 238; gi = Image.fromarray(grad, "RGBA"); mk = Image.new("L", (cw, ch), 0); ImageDraw.Draw(mk).rounded_rectangle([0, 0, cw - 1, ch - 1], int(28 * k), fill=255)
    body = Image.composite(gi, body, mk); img.alpha_composite(body, (cx0, cy0))
    ic = detect_icon(hook_lines) if icon == "auto" else icon
    if ic != "none":
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); draw_icon(lay, ic, (cx0, cy0, cx0 + cw, cy0 + ch)); lay.putalpha(Image.eval(lay.split()[3], lambda v: v))
        clip = Image.new("L", (W, H), 0); ImageDraw.Draw(clip).rounded_rectangle([cx0, cy0, cx0 + cw, cy0 + ch], int(28 * k), fill=255)
        la = lay.split()[3]; la = Image.fromarray((np.asarray(la, np.float32) * np.asarray(clip, np.float32) / 255).astype(np.uint8)); lay.putalpha(la); img.alpha_composite(lay)
    img.alpha_composite(tab)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([cx0, cy0, cx0 + cw, cy0 + ch], int(28 * k), outline=EDGE + (255,), width=max(2, int(3 * k)))
    # viền vàng phát sáng: cạnh dưới + cạnh phải
    R = int(28 * k); gl = Image.new("RGBA", (W, H), (0, 0, 0, 0)); gd = ImageDraw.Draw(gl); lw = int(7 * k)
    gd.line([cx0 + R, cy0 + ch, cx0 + cw - R, cy0 + ch], fill=GOLD + (255,), width=lw)
    gd.line([cx0 + cw, cy0 + R + int(ch * 0.12), cx0 + cw, cy0 + ch - R], fill=GOLD + (255,), width=lw)
    gd.arc([cx0 + cw - 2 * R, cy0 + ch - 2 * R, cx0 + cw, cy0 + ch], 0, 90, fill=GOLD + (255,), width=lw)
    img.alpha_composite(gl.filter(ImageFilter.GaussianBlur(11 * k))); img.alpha_composite(gl)
    # chữ
    y = cy0 + int(34 * k)
    for i, ln in enumerate(hook_lines):
        big = (mode == "A" and i == n - 1 and n > 1); f = black(sz * (1.1 if big else 1.0))
        runs = _runs(ln, mode, i == n - 1)
        if mode == "A": tot = dd.textlength(ln, font=f); x = cx0 + (cw - tot) / 2
        else: tot = dd.textlength(ln, font=f); x = cx0 + (cw - tot) / 2
        cyl = y + lh[i] / 2
        for j, (txt, col) in enumerate(runs):
            seg = txt + (" " if (mode == "B" and j < len(runs) - 1) else "")
            d.text((x + 3 * k, cyl + 4 * k), seg, font=f, fill=(0, 0, 0, 200), anchor="lm"); d.text((x, cyl), seg, font=f, fill=col + (255,), anchor="lm")
            x += d.textlength(seg, font=f)
        y += lh[i]
    return np.asarray(img)

# ---------------- ảnh nền theo khuôn mặt ----------------
def fit_photo(photo, size, face_y=0.27, face_h=0.17, warm=True):
    """Phóng + cắt để mặt nằm ở face_y (tỷ lệ chiều cao), cao ≈ face_h chiều cao khung."""
    import cv2
    W, H = size; im = photo.convert("RGB"); a = np.asarray(im)[:, :, ::-1]
    gray = cv2.cvtColor(a, cv2.COLOR_BGR2GRAY)
    casc = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    faces = casc.detectMultiScale(gray, 1.1, 5, minSize=(int(im.height * 0.06),) * 2)
    if len(faces):
        x, y, w, h = max(faces, key=lambda f: f[2] * f[3]); fcx, fcy, fh = x + w / 2, y + h / 2, h * 1.25
    else:
        fcx, fcy, fh = im.width / 2, im.height * 0.38, im.height * 0.2
    s = max(W / im.width, H / im.height, face_h * H / fh)           # tỷ lệ phóng
    sw, sh = int(im.width * s), int(im.height * s); big = im.resize((sw, sh), Image.LANCZOS)
    left = int(min(max(fcx * s - W / 2, 0), sw - W)); top = int(min(max(fcy * s - face_y * H, 0), sh - H))
    out = big.crop((left, top, left + W, top + H))
    if warm: out = ImageEnhance.Contrast(ImageEnhance.Color(out).enhance(1.12)).enhance(1.06)
    return out, bool(len(faces))

def compose_thumbnail(photo, hook_lines, out, size=(1080, 1920), tag="#Bùi Viết Cường", avatar=None, mode="A", icon="auto"):
    W, H = size
    face_h, face_y, box_top = (0.17, 0.27, 0.558) if H > W else ((0.30, 0.40, 0.60) if W == H else (0.27, 0.42, 0.60))
    if mode == "B": face_h *= (1.18 if H > W else 1.08)
    base, found = fit_photo(photo, size, face_y=face_y, face_h=face_h)
    if W > H: return _landscape(base, hook_lines, out, size, tag, avatar, mode, icon), found
    ov = cover_overlay_v2(hook_lines, tag=tag, avatar_path=avatar, size=size, mode=mode, icon=icon, box_top=box_top)
    res = Image.alpha_composite(base.convert("RGBA"), Image.fromarray(ov, "RGBA")).convert("RGB"); res.save(out, quality=95); return res, found

def _landscape(base, hook_lines, out, size, tag, avatar, mode, icon):
    """16:9: người bên phải, hook 3 dòng bên trái trên nền navy; dòng cuối vàng."""
    W, H = size; img = base.convert("RGBA")
    # đưa người sang phải: dịch ảnh nền
    shifted = Image.new("RGBA", (W, H), NAVY_D + (255,)); shifted.alpha_composite(img.crop((int(W * 0.12), 0, W, H)), (int(W * 0.34), 0)); img = shifted
    g = np.zeros((H, W, 4), np.uint8); g[..., 0], g[..., 1], g[..., 2] = NAVY_D; xx = np.linspace(0, 1, W)[None, :]
    g[..., 3] = np.repeat((np.clip(1 - (xx - 0.30) / 0.30, 0, 1) ** 1.1 * 252).astype(np.uint8), H, axis=0); img.alpha_composite(Image.fromarray(g, "RGBA"))
    d = ImageDraw.Draw(img); lines = [str(x).upper() for x in hook_lines if str(x).strip()][:4]; n = len(lines); sz = int(H * 0.15)
    while sz > 30 and max(d.textlength(l, font=black(sz)) for l in lines) > W * 0.60: sz -= 2
    y = int(H * 0.30)
    ft = bold(int(H * 0.04)); tw = int(d.textlength(tag, font=ft)) + 40; d.rounded_rectangle([int(W * 0.05), int(H * 0.15), int(W * 0.05) + tw, int(H * 0.15) + int(H * 0.075)], 10, fill=(8, 22, 70, 255), outline=GOLD + (255,), width=2)
    d.text((int(W * 0.05) + 20, int(H * 0.15) + int(H * 0.0375)), tag, font=ft, fill=(255, 255, 255, 255), anchor="lm")
    for i, l in enumerate(lines):
        big = (mode == "A" and i == n - 1 and n > 1); f = black(sz * (1.08 if big else 1)); x = int(W * 0.05)
        runs = _runs(l, mode, i == n - 1)
        for j, (txt, col) in enumerate(runs):
            seg = txt + (" " if (mode == "B" and j < len(runs) - 1) else "")
            d.text((x + 4, y + 5), seg, font=f, fill=(0, 0, 0, 210), anchor="lm"); d.text((x, y), seg, font=f, fill=col + (255,), anchor="lm"); x += d.textlength(seg, font=f)
        y += int(sz * 1.2)
    if avatar and os.path.exists(os.path.expanduser(avatar)): av = avatar_circle(os.path.expanduser(avatar), int(H * 0.2)); img.alpha_composite(av, (W - av.width - 24, 20))
    res = img.convert("RGB"); res.save(out, quality=95); return res

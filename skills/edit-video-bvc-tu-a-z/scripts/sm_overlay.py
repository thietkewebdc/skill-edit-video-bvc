#!/usr/bin/env python3
"""sm_overlay v2 — engine phủ chữ / minh họa / hiệu ứng / SFX lên video dọc. KHÔNG cắt ghép video.

Lệnh:
  transcribe <video> -o words.json [--model small]      STT từng từ (faster-whisper)
  check      <video> <plan.json>                        kiểm tra nhịp, vị trí, chồng lấn
  snap       <video> <plan.json> --at 1,8.5 -o dir      ảnh PNG có overlay để QA
  render     <video> <plan.json> -o out.mp4 [--preview] render bản cuối

Thông số thiết kế nằm ở phần CONFIG. SFX riêng: thả file WAV vào thư mục sfx/ của skill
(tên file = tên SFX, VD sfx/whoosh.wav, sfx/impact.wav) — engine tự dùng thay âm tạo bằng code.
"""
import argparse
import json
import math
import random
import shutil
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

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

SKILL_DIR = Path(__file__).resolve().parent.parent
FONTS_DIR = SKILL_DIR / "fonts"
SFX_DIR = SKILL_DIR / "sfx"

# ───────────────────────── CONFIG ─────────────────────────
W = 1080                       # hệ tọa độ ASS (tự scale theo độ phân giải video)
H = 1920                       # tính lại theo tỉ lệ video
ACCENTS = {"yellow": "F4C80F", "cyan": "00FFFF"}   # cặp màu tiêu đề/chữ nhấn (đo từ mẫu)
WHITE = "FFFFFF"
ACC = ACCENTS["yellow"]        # đặt theo plan["accent"]

# Sub (KHÔNG dùng mẫu tiêu đề): trắng ngà + từ đang nói vàng #F4C80F, 1 lớp bóng đặc đổ chéo
SUB_BASE = "F5EFE3"
SUB_HI = "F4C80F"
# cỡ sub (đơn vị canvas, tự nhân theo độ phân giải): dọc 60 → 60 px Full HD / 120 px 4K (~3.1% chiều cao)
SUB = dict(fs=60, y=0.66, max_words=3, max_chars=18, gap_break=0.35, fsp=0.5, lowercase=True)

FONT = {"bold": r"\fnMontserrat\b1", "black": r"\fnMontserrat Black\b0"}

# Khối chữ tiêu đề / chữ nhấn
BLOCK_MAX_W = 0.84             # dòng rộng tối đa (tỉ lệ khung)
SMALL_RATIO = 0.85             # dòng trắng không bao giờ to quá 85% dòng màu (giữ thứ bậc)
BALANCE_MIN_W = 0.50           # dòng trắng rộng tối thiểu 50% khung khi dòng màu cực ngắn
LINE_GAP = 0.40                # hệ số khoảng dòng → 2 dòng sát nhau (chủ kênh chốt, sát hơn mẫu gốc)
MARK_GAP = 0.12                # cộng thêm khi dòng dưới có dấu tiếng Việt phía trên chữ hoa (Ổ, Ấ, Ờ...)
DOT_GAP = 0.16                 # cộng thêm khi dòng trên có dấu nặng dưới chân chữ (Ỵ, Ạ, Ệ...)
BLOCK_Y = 0.585                # tâm khối chữ
FS_SCALE = 1.0                 # hệ số cỡ chữ khối (khung ngang tự đặt)
DY = 0.0                       # dời minh họa xuống (khung ngang tự đặt)
# Khung NGANG 16:9: canvas 1920x1080, chữ khối nhỏ theo chiều cao, khối chữ + minh họa thấp hơn để không đè cằm
LANDSCAPE = dict(W=1920, FS_SCALE=0.56, BLOCK_MAX_W=0.62, BLOCK_Y=0.68, DY=0.12, SUB_Y=0.87, SUB_FS=50)   # ngang: 50 px Full HD / 100 px 4K

STROKE = 0.009                 # viền đen = 0.9% cỡ chữ (tiêu đề ~2.5px, sub 1px)
SHADOW_OFF = 0.022             # bóng lệch chéo 2.2% cỡ chữ (khép sát chữ)
SHADOW_OPACITY = 0.75          # bóng đen 75% (nhẹ hơn đen đặc)
BLOCK_SHADOW_OFF = 0.016       # chữ khối: bóng lệch 1.6% cỡ chữ (sát chữ), không viền
BLOCK_SHADOW_OPACITY = 0.85

# tên riêng luôn viết hoa chữ cái đầu trong sub (bổ sung theo từng video bằng plan["proper_nouns"])
PROPER_DEFAULT = [
    "Facebook", "YouTube", "TikTok", "Zalo", "Google", "Instagram", "Messenger", "Shopee", "Lazada",
    "Tiki", "Canva", "ChatGPT", "Claude", "Apple", "iPhone", "Samsung", "Grab", "Netflix", "Amazon",
    "Việt Nam", "Hà Nội", "Sài Gòn", "TP.HCM", "Hồ Chí Minh", "Đà Nẵng", "Hải Phòng", "Cần Thơ", "Đà Lạt",
    "Nha Trang", "Phú Quốc", "Singapore", "Thái Lan", "Nhật Bản", "Hàn Quốc", "Trung Quốc",
    "Cyprus", "Dubai", "Châu Âu", "Suối Mơ",
]

# gradient trên màu chính (sáng → màu chính → đậm), từ trên xuống
GRADIENTS = {
    "F4C80F": ["FFF3C4", "F4C80F", "B07A08"],   # vàng champagne → vàng → vàng đồng
    "00FFFF": ["E6FFFF", "00FFFF", "0079A8"],   # xanh nhạt → cyan → xanh biển sâu
}


def grad_color(stops, t):
    t = max(0.0, min(1.0, t)) * (len(stops) - 1)
    i = min(int(t), len(stops) - 2)
    f = t - i
    a, b = stops[i], stops[i + 1]
    ch = [round(int(a[j:j + 2], 16) * (1 - f) + int(b[j:j + 2], 16) * f) for j in (0, 2, 4)]
    return "".join(f"{v:02X}" for v in ch)


BAND = (0.44, 0.72)
SR = 48000
SFX_MASTER_DB = -7.0           # âm lượng tổng hiệu ứng (dB) — chủ kênh chốt -7 dB
SFX_GAIN = dict(whoosh=0.26, whoosh_soft=0.14, swish=0.16, impact=0.42, impact_soft=0.24,
                riser=0.16, sparkle=0.10, pop=0.16, tick=0.12, chime=0.11, shimmer=0.09)
# ──────────────────────────────────────────────────────────


def die(msg):
    print(f"LỖI: {msg}", file=sys.stderr)
    sys.exit(1)


def probe(video):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                          "format=duration:stream=codec_type,width,height,r_frame_rate", "-of", "json", str(video)],
                         capture_output=True, text=True, encoding="utf-8")
    if out.returncode != 0:
        die(f"không đọc được video: {video}")
    d = json.loads(out.stdout)
    v = next(s for s in d["streams"] if s["codec_type"] == "video")
    has_audio = any(s["codec_type"] == "audio" for s in d["streams"])
    n, _, m = v.get("r_frame_rate", "30/1").partition("/")
    fps = float(n) / float(m or 1)
    return float(d["format"]["duration"]), v["width"], v["height"], has_audio, fps


# ───────────────────────── ASS helpers ─────────────────────────
def col(hexrgb):
    return f"&H{hexrgb[4:6]}{hexrgb[2:4]}{hexrgb[0:2]}&"


def alpha(opacity):
    return f"&H{int(round((1 - opacity) * 255)):02X}&"


def ts(t):
    cs = int(round(max(0.0, t) * 100))
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def clean(s):
    return s.replace("\\", "").replace("{", "").replace("}", "")


def parse_markup(s, upper_all=False):
    """'giữa {GIA ĐÌNH}' -> [(text, is_accent)]; '|' = xuống dòng. {..} luôn IN HOA."""
    segs, buf, acc = [], "", False
    for ch in s:
        if ch in "{}":
            if buf:
                segs.append((buf, acc))
            buf, acc = "", ch == "{"
        else:
            buf += ch
    if buf:
        segs.append((buf, acc))
    return [(clean(t).upper() if (upper_all or a) else clean(t), a) for t, a in segs]


def seg_lines(segs):
    lines, cur = [], []
    for txt, a in segs:
        for i, p in enumerate(txt.split("|")):
            if i > 0:
                lines.append(cur)
                cur = []
            if p:
                cur.append((p, a))
    lines.append(cur)
    out = []
    for ln in lines:
        ln = [(t, a) for t, a in ln]
        if "".join(t for t, _ in ln).strip():
            ln[0] = (ln[0][0].lstrip(), ln[0][1])
            ln[-1] = (ln[-1][0].rstrip(), ln[-1][1])
            out.append(ln)
    return out


def split_accent_lines(markup):
    """Không có '|': tách theo ranh giới màu → 'CÓ MẶT {THỰC SỰ}' = 2 dòng."""
    if "|" in markup:
        return seg_lines(parse_markup(markup, upper_all=True))
    segs = [(t, a) for t, a in parse_markup(markup, upper_all=True) if t.strip()]
    return [[(t.strip(), a)] for t, a in segs]


ASS_EM = 1.562  # libass: \fs = (usWinAscent+usWinDescent)/upem = 1.562 em với Montserrat (đo từ font)
WIN_ASC = 0.710  # baseline nằm ở 71% chiều cao hộp dòng (winAscent / tổng)
CAP = 0.448      # chiều cao chữ hoa = 0.70 em = 0.448 \fs
EST_EM = 1.22    # hệ số của hàm ước lượng dự phòng (đã hiệu chỉnh bằng render)


def est_units(text, black=True):
    u = 0.0
    for ch in text:
        if ch == " ":
            u += 0.26
        elif ch in "MWÔỐỒỔỖỘ@%":
            u += 0.78 if black else 0.74
        elif ch in "I1!|.,:;'":
            u += 0.30
        elif ch.isupper() or ch.isdigit():
            u += 0.59 if black else 0.56
        else:
            u += 0.50 if black else 0.46
    return u / EST_EM


def fit_fs(lines_text, max_w, fs_max, fs_min=30, fsp=0, black=True):
    fs = fs_max
    while fs > fs_min:
        if max(text_width(t, fs, "black" if black else "bold", fsp) for t in lines_text) <= max_w:
            break
        fs -= 1
    return fs


# ───────────────────────── đo bề rộng chữ bằng chính file font ─────────────────────────
import struct
import unicodedata

_FM = {}


def _font_metrics(name):
    """đọc cmap + hmtx của TTF → (upem, {codepoint: advance}). Không cần thư viện ngoài."""
    if name in _FM:
        return _FM[name]
    f = FONTS_DIR / {"black": "Montserrat-Black.ttf", "bold": "Montserrat-Bold.ttf"}[name]
    try:
        d = f.read_bytes()
        n = struct.unpack(">H", d[4:6])[0]
        tab = {d[12 + 16 * i:16 + 16 * i].decode("latin1"): struct.unpack(">II", d[20 + 16 * i:28 + 16 * i])
               for i in range(n)}
        head = tab["head"][0]
        upem = struct.unpack(">H", d[head + 18:head + 20])[0]
        hhea = tab["hhea"][0]
        nhm = struct.unpack(">H", d[hhea + 34:hhea + 36])[0]
        hmtx = tab["hmtx"][0]
        adv = [struct.unpack(">H", d[hmtx + 4 * i:hmtx + 4 * i + 2])[0] for i in range(nhm)]
        cm = tab["cmap"][0]
        nsub = struct.unpack(">H", d[cm + 2:cm + 4])[0]
        cmap = {}
        for i in range(nsub):
            pid, eid, off = struct.unpack(">HHI", d[cm + 4 + 8 * i:cm + 12 + 8 * i])
            o = cm + off
            fmt = struct.unpack(">H", d[o:o + 2])[0]
            if fmt == 4 and not cmap:
                seg = struct.unpack(">H", d[o + 6:o + 8])[0] // 2
                ends = struct.unpack(f">{seg}H", d[o + 14:o + 14 + 2 * seg])
                sts = struct.unpack(f">{seg}H", d[o + 16 + 2 * seg:o + 16 + 4 * seg])
                dl = struct.unpack(f">{seg}h", d[o + 16 + 4 * seg:o + 16 + 6 * seg])
                ro_off = o + 16 + 6 * seg
                ro = struct.unpack(f">{seg}H", d[ro_off:ro_off + 2 * seg])
                for s in range(seg):
                    for ch in range(sts[s], ends[s] + 1):
                        if ch == 0xFFFF:
                            continue
                        if ro[s] == 0:
                            g = (ch + dl[s]) & 0xFFFF
                        else:
                            a = ro_off + 2 * s + ro[s] + 2 * (ch - sts[s])
                            g = struct.unpack(">H", d[a:a + 2])[0]
                            g = (g + dl[s]) & 0xFFFF if g else 0
                        cmap[ch] = g
        res = (upem, {ch: adv[min(g, nhm - 1)] for ch, g in cmap.items()})
    except Exception:
        res = None
    _FM[name] = res
    return res


def text_width(text, fs, font="black", fsp=0.0):
    """bề rộng (px hệ ASS) của text ở cỡ \\fs — đo từ font thật, fallback ước lượng."""
    m = _font_metrics(font)
    if not m:
        return est_units(text, font == "black") * fs + len(text) * fsp
    upem, adv = m
    em = fs / ASS_EM
    w = 0
    for ch in text:
        a = adv.get(ord(ch))
        if a is None:
            base = unicodedata.normalize("NFD", ch)[0]
            a = adv.get(ord(base), upem * 0.6)
        w += a
    return w / upem * em + len(text) * fsp


class Ass:
    def __init__(self):
        self.ev = []

    def add(self, layer, t0, t1, text):
        if t1 - t0 > 0.005:
            self.ev.append((layer, t0, t1, text))

    def dump(self, path):
        head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Base,Montserrat,48,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,0,0,5,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        rows = [f"Dialogue: {l},{ts(a)},{ts(b)},Base,,0,0,0,,{t}"
                for l, a, b, t in sorted(self.ev, key=lambda e: (e[1], e[0]))]
        Path(path).write_text(head + "\n".join(rows) + "\n", encoding="utf-8-sig")


def rect(A, layer, t0, t1, color, op, tags=""):
    A.add(layer, t0, t1, rf"{{\an7\pos(0,0)\bord0\shad0\1c{col(color)}\1a{alpha(op)}{tags}\p1}}m 0 0 l {W} 0 {W} {H} 0 {H}{{\p0}}")


# ───────────────────────── vector drawing ─────────────────────────
def area(pts):
    return sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1]
               for i in range(len(pts))) / 2


def path(polys):
    out = []
    for pts, hole in polys:
        p = pts if (area(pts) > 0) == (not hole) else pts[::-1]
        out.append("m " + " ".join(f"{round(x * 4)} {round(y * 4)}" + (" l" if i == 0 else "")
                                   for i, (x, y) in enumerate(p)))
    return " ".join(out)


def seg(a, b, w):
    (x1, y1), (x2, y2) = a, b
    L = math.hypot(x2 - x1, y2 - y1) or 1
    dx, dy = (x2 - x1) / L, (y2 - y1) / L
    e = w / 2
    x1, y1, x2, y2 = x1 - dx * e, y1 - dy * e, x2 + dx * e, y2 + dy * e
    nx, ny = -dy * w / 2, dx * w / 2
    return ([(x1 + nx, y1 + ny), (x2 + nx, y2 + ny), (x2 - nx, y2 - ny), (x1 - nx, y1 - ny)], False)


def circle(cx, cy, r, n=48):
    return [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


def ring(cx, cy, r, w):
    return [(circle(cx, cy, r + w / 2), False), (circle(cx, cy, r - w / 2), True)]


def dot(cx, cy, r):
    return [(circle(cx, cy, r, 24), False)]


def polyline(pts, w, closed=False):
    n = len(pts) if closed else len(pts) - 1
    out = [seg(pts[i], pts[(i + 1) % len(pts)], w) for i in range(n)]
    if len(pts) <= 12:                     # khớp bo tròn cho nét sang (bỏ qua đường cong nhiều điểm)
        for q in pts:
            out += dot(q[0], q[1], w * 0.5)
    return out


def bbox(polys):
    xs = [x for p, _ in polys for x, _ in p]
    ys = [y for p, _ in polys for _, y in p]
    return min(xs), min(ys), max(xs), max(ys)


def emit_drawing(A, layer, t0, t1, polys, *, color=None, op=1.0, glow=True, draw_ms=650,
                 fade=(120, 250), extra="", wipe=True, bb=None, gradient=True):
    if not polys:
        return
    color = color or ACC
    p = path(polys)
    x0, y0, x1, y1 = bb or bbox(polys)
    clip = ""
    if wipe:
        clip = rf"\clip({x0 - 12:.0f},{y0 - 12:.0f},{x0 - 12:.0f},{y1 + 12:.0f})\t(0,{draw_ms},0.6,\clip({x0 - 12:.0f},{y0 - 12:.0f},{x1 + 12:.0f},{y1 + 12:.0f}))"
    base = rf"\an7\pos(0,0)\bord0\shad0\1c{col(color)}\fad({fade[0]},{fade[1]}){clip}{extra}"
    A.add(layer, t0, t1, rf"{{{base}\1c&H000000&\1a{alpha(0.5 * op)}\blur6}}{{\p3}}{p}{{\p0}}")
    if glow:
        A.add(layer + 1, t0, t1, rf"{{{base}\1a{alpha(0.35 * op)}\blur8}}{{\p3}}{p}{{\p0}}")
    if not gradient or color != ACC:
        A.add(layer + 2, t0, t1, rf"{{{base}\1a{alpha(op)}}}{{\p3}}{p}{{\p0}}")
        return
    # gradient dọc: chia thành các dải clip không chồng nhau (vẫn 1 lớp nét)
    stops = GRADIENTS.get(ACC, [ACC, ACC, ACC])
    top, bot = y0 - 14, y1 + 14
    n = 12
    for k in range(n):
        by0 = top + (bot - top) * k / n
        by1 = top + (bot - top) * (k + 1) / n + 1
        cband = grad_color(stops, (k + 0.5) / n)
        if wipe:
            clip = rf"\clip({x0 - 12:.0f},{by0:.0f},{x0 - 12:.0f},{by1:.0f})\t(0,{draw_ms},0.6,\clip({x0 - 12:.0f},{by0:.0f},{x1 + 12:.0f},{by1:.0f}))"
        else:
            clip = rf"\clip({x0 - 400:.0f},{by0:.0f},{x1 + 400:.0f},{by1:.0f})"
        bb_ = rf"\an7\pos(0,0)\bord0\shad0\1c{col(cband)}\fad({fade[0]},{fade[1]}){clip}{extra}"
        A.add(layer + 2, t0, t1, rf"{{{bb_}\1a{alpha(op)}}}{{\p3}}{p}{{\p0}}")


def U(cx, cy, S):
    return lambda u, v: (cx + (u - 50) * S / 100, cy + (v - 50) * S / 100)


def local_ring(r, w):
    """ring vẽ trong hệ tọa độ cục bộ (0..2r) để dùng với \\an5 + scale quanh tâm."""
    return path(ring(r, r, r, w))


# ───────────────────────── FX phụ trợ ─────────────────────────
def fx_particles(A, t, cx, cy, spread_x, n=16, color=None, seed=0, layer=70):
    rnd = random.Random(seed)
    color = color or ACC
    for _ in range(n):
        a = rnd.uniform(0, 2 * math.pi)
        dist = rnd.uniform(90, 260)
        sx = cx + rnd.uniform(-spread_x, spread_x)
        sy = cy + rnd.uniform(-20, 20)
        ex, ey = sx + math.cos(a) * dist, sy + math.sin(a) * dist * 0.7 - 40
        r = rnd.uniform(3, 7.5)
        c = color if rnd.random() < 0.65 else WHITE
        life = rnd.uniform(0.55, 0.95)
        A.add(layer, t, t + life,
              rf"{{\an5\move({sx:.0f},{sy:.0f},{ex:.0f},{ey:.0f},0,{int(life * 1000)})\bord0\shad0\1c{col(c)}\blur1.2\fad(0,{int(life * 600)})\t(0,{int(life * 1000)},\fscx30\fscy30)\p3}}"
              + path(dot(r, r, r)) + r"{\p0}")


def fx_shockwave(A, t, cx, cy, layer=69, color=None):
    color = color or ACC
    A.add(layer, t, t + 0.55, rf"{{\an5\pos({cx:.0f},{cy:.0f})\bord0\shad0\1c{col(color)}\blur2\fscx25\fscy25\1a&H40&\t(0,550,0.5,\fscx260\fscy200\1a&HFF&)\p3}}"
          + local_ring(120, 6) + r"{\p0}")


def fx_flash(A, t, op=0.14, layer=68):
    rect(A, layer, t, t + 0.26, WHITE, op, r"\fad(0,230)")


def fx_leak(A, t, dur=1.4, layer=67, seed=0):
    """vệt sáng ấm quét chéo (light leak)."""
    rnd = random.Random(seed)
    r = 380
    y0 = H * rnd.uniform(0.25, 0.45)
    shape = path([(circle(r, r, r, 40), False)])
    A.add(layer, t, t + dur, rf"{{\an5\move({-r:.0f},{y0:.0f},{W + r:.0f},{y0 + 380:.0f})\bord0\shad0\1c{col('FFB35C')}\1a&HA0&\blur60\fscy55\frz-25\fad(250,400)\p3}}{shape}{{\p0}}")
    A.add(layer, t + 0.1, t + dur, rf"{{\an5\move({-r * 0.6:.0f},{y0 + 80:.0f},{W + r:.0f},{y0 + 520:.0f})\bord0\shad0\1c{col('FFF1D0')}\1a&HC0&\blur45\fscx50\fscy30\frz-25\fad(250,400)\p3}}{shape}{{\p0}}")


# ───────────────────────── Khối chữ (tiêu đề + chữ nhấn) ─────────────────────────
def layout_block(lines, big_max, cy, max_w=None):
    big_max = big_max * FS_SCALE
    max_w = max_w or W * BLOCK_MAX_W
    texts = ["".join(t for t, _ in ln) for ln in lines]
    big = [any(a for _, a in ln) for ln in lines]
    if not any(big):
        big = [True] * len(lines)
    fs_big = min(fit_fs([texts[i]], max_w, big_max) for i in range(len(lines)) if big[i])
    # CÂN BẰNG: dòng trắng tự co giãn để rộng bằng dòng màu (khối chữ vuông như mẫu);
    # dòng màu quá ngắn thì dòng trắng rộng tối thiểu BALANCE_MIN_W, và luôn nhỏ hơn dòng màu
    w_big = max(text_width(texts[i], fs_big) for i in range(len(lines)) if big[i])
    target = min(max_w, max(w_big, W * BALANCE_MIN_W))
    fss = [fs_big if big[i] else min(fit_fs([texts[i]], target, big_max), round(fs_big * SMALL_RATIO))
           for i in range(len(lines))]
    cap = [CAP * f for f in fss]            # chiều cao chữ hoa
    tops, cap_top = [], 0.0
    for i, f in enumerate(fss):
        if i > 0:
            marks = any(m in unicodedata.normalize("NFD", texts[i]) for m in "\u0300\u0301\u0303\u0309\u0302\u0306")
            cap_top = base + (LINE_GAP + (MARK_GAP if marks else 0)) * cap[i]
            if "̣" in unicodedata.normalize("NFD", texts[i - 1]):   # dấu nặng dòng trên (Ỵ, Ạ, Ệ...)
                cap_top += DOT_GAP * cap[i - 1]
        top = cap_top - (WIN_ASC - CAP) * f
        base = top + WIN_ASC * f
        tops.append(top)
    total = base - (tops[0] + (WIN_ASC - CAP) * fss[0])
    shift = cy - total / 2 - (tops[0] + (WIN_ASC - CAP) * fss[0])
    centers = [tp + shift + f / 2 for tp, f in zip(tops, fss)]
    return fss, centers, big, (cy - total / 2, cy + total / 2)


def text_style(fs):
    """1 lớp chữ: viền đen thật mỏng + bóng đen nhẹ, khép sát, đổ chéo phải-dưới."""
    b = max(1.0, round(fs * STROKE, 1))          # viền mỏng
    d = max(1.5, round(fs * SHADOW_OFF, 1))      # bóng khép sát
    return (rf"\bord{b}\3c&H000000&\3a&H00&\shad0\xshad{d}\yshad{d}"
            rf"\4c&H000000&\4a{alpha(SHADOW_OPACITY)}"), d


def shadow_tags(fs):
    return text_style(fs)


def block_style(fs):
    """chữ khối (tiêu đề, chữ nhấn, số đếm): không viền, bóng đen đổ SÁT chữ."""
    d = max(1.5, round(fs * BLOCK_SHADOW_OFF, 1))
    return (rf"\bord0\shad0\xshad{d}\yshad{d}\4c&H000000&\4a{alpha(BLOCK_SHADOW_OPACITY)}"), d


def emit_line(A, layer, t0, t1, x, y, fs, segs, *, pre=None, anim=None, exit_ms=0, move=None, per_char=None):
    """1 lớp chữ duy nhất (chữ + bóng cùng 1 event). Không fade alpha → không lộ bóng chồng chữ.
    pre/anim: callable(_)->str chỉ dùng scale/blur/clip/move; ra = cắt gọn."""
    pre = pre or (lambda a: "")
    anim = anim or (lambda a: "")
    sh, d = block_style(fs)
    if per_char:
        out, k = [], 0
        for t, a in segs:
            for ch in t:
                st = per_char(k)
                out.append(rf"{{\1c{col(ACC if a else WHITE)}\alpha&HFF&\t({st},{st + 1},\alpha&H00&)}}{ch}")
                k += 1
        body = "".join(out)
    else:
        body = "".join(rf"{{\1c{col(ACC if a else WHITE)}}}{t}" for t, a in segs)
    pos = rf"\move({move[0]:.0f},{move[1]:.0f},{x:.0f},{y:.0f},0,{move[2]})" if move else rf"\pos({x:.0f},{y:.0f})"
    A.add(layer, t0, t1, rf"{{\an5{pos}{FONT['black']}\fs{fs}{sh}{pre('')}{anim('')}}}" + body)
    return d


def emit_glint(A, layer, t, x, y, fs, segs, times=(0,)):
    """tia sáng quét ngang qua dòng chữ màu."""
    text = "".join(t_ for t_, _ in segs)
    wdt = est_units(text) * fs
    x0, x1 = x - wdt / 2 - 80, x + wdt / 2 + 20
    top, bot = y - fs * 0.6, y + fs * 0.6
    for k, dt in enumerate(times):
        tt = t + dt
        A.add(layer, tt, tt + 0.6, rf"{{\an5\pos({x:.0f},{y:.0f}){FONT['black']}\fs{fs}\bord0\shad0\1c&HFFFFFF&\1a&H40&\blur3\clip({x0:.0f},{top:.0f},{x0 + 60:.0f},{bot:.0f})\t(0,550,0.7,\clip({x1:.0f},{top:.0f},{x1 + 60:.0f},{bot:.0f}))}}{text}")


def fx_alpha(kind):
    """trả (pre, anim) — chỉ scale/blur, không đụng alpha (tránh lộ bóng qua chữ)."""
    if kind == "slam":
        return (lambda a: r"\fscx165\fscy165\blur10",
                lambda a: r"\t(0,200,0.6,\fscx96\fscy96\blur0)\t(200,320,\fscx100\fscy100)")
    if kind == "zoom":
        return (lambda a: r"\fscx25\fscy25",
                lambda a: r"\t(0,300,0.55,\fscx108\fscy108)\t(300,450,\fscx100\fscy100)")
    if kind == "flip3d":      # lật thẻ quanh trục ngang
        return (lambda a: r"\frx-80\fscx90\fscy90",
                lambda a: r"\t(0,380,0.5,\frx12\fscx100\fscy100)\t(380,540,\frx0)")
    if kind == "swing3d":     # xoay vào như cánh cửa quanh trục dọc
        return (lambda a: r"\fry-72\fscx88\fscy88",
                lambda a: r"\t(0,420,0.5,\fry12\fscx100\fscy100)\t(420,580,\fry0)")
    if kind == "tilt3d":      # nghiêng sâu 3D rồi dựng lại, giữ chút chiều sâu
        return (lambda a: r"\frx34\fry-22\fscx72\fscy72",
                lambda a: r"\t(0,460,0.5,\frx6\fry-8\fscx100\fscy100)\t(460,2600,\frx0\fry4)")
    if kind in ("rise", "drop"):
        return (lambda a: r"\fscx88\fscy88",
                lambda a: r"\t(0,260,0.5,\fscx100\fscy100)")
    return (lambda a: "", lambda a: "")


def render_block(A, t0, t1, lines, *, fx="slam", big_max=250, cy=None, layer=21, hold_frame0=False,
                 glint=False, particles=True, seed=0):
    cy = H * (cy or BLOCK_Y)
    fss, ys, big, (btop, bbot) = layout_block(lines, big_max, cy)
    x = W / 2
    order = list(range(len(lines)))
    land = t0
    for i in order:
        segs, fs, y = lines[i], fss[i], ys[i]
        L = layer + i * 4
        if hold_frame0:
            dur = int((t1 - t0) * 1000)
            emit_line(A, L, t0, t1, x, y, fs, segs)   # tiêu đề đứng yên, sắc nét, 1 lớp
            continue
        if fx == "slam":
            d0 = 0.0 if big[i] else -0.05
            ti = t0 + (0.12 if big[i] else 0) + d0
            if big[i]:
                pre, anim = fx_alpha("slam")
                emit_line(A, L, ti, t1, x, y, fs, segs, pre=pre, anim=anim)
                land = ti + 0.2
            else:
                pre, anim = fx_alpha("drop")
                emit_line(A, L, max(t0, ti), t1, x, y, fs, segs, pre=pre, anim=anim, move=(x, y - 45, 260))
        elif fx == "zoom":
            ti = t0 + (0.18 if big[i] else 0.0)
            pre, anim = fx_alpha("zoom" if big[i] else "rise")
            emit_line(A, L, ti, t1, x, y, fs, segs, pre=pre, anim=anim)
            if big[i]:
                land = ti + 0.3
        elif fx == "stagger":
            n_words = sum(len(t.split()) for t, _ in segs)
            ti = t0 + i * 0.28
            words = [(w, a) for t, a in segs for w in t.split()]
            # từng từ trượt lên theo nhịp 110ms
            wx = x - text_width(" ".join(w for w, _ in words), fs) / 2
            for k, (w, a) in enumerate(words):
                ww = text_width(w, fs)
                cxw = wx + ww / 2
                pre, anim = fx_alpha("rise")
                emit_line(A, L + k, ti + k * 0.11, t1, cxw, y, fs, [(w, a)], pre=pre, anim=anim,
                          move=(cxw, y + 30, 300))
                wx += ww + text_width(" ", fs)
            if big[i]:
                land = ti + 0.11 * n_words
        elif fx == "wipe":
            ti = t0 + i * 0.16
            wdt = text_width("".join(t for t, _ in segs), fs)
            clip0 = rf"\clip({x - wdt / 2 - 30:.0f},0,{x - wdt / 2 - 30:.0f},{H})"
            clip1 = rf"\t(0,380,0.6,\clip({x - wdt / 2 - 30:.0f},0,{x + wdt / 2 + 40:.0f},{H}))"
            emit_line(A, L, ti, t1, x, y, fs, segs, pre=lambda a: clip0, anim=lambda a: clip1)
            if big[i]:
                land = ti + 0.3
        elif fx == "type":
            n_prev = sum(len("".join(t for t, _ in lines[j])) for j in range(i))
            emit_line(A, L, t0, t1, x, y, fs, segs, per_char=lambda k, n0=n_prev: (n0 + k) * 45)
            if big[i]:
                land = t0 + 0.045 * sum(len("".join(t for t, _ in ln)) for ln in lines)
        elif fx in ("flip3d", "swing3d", "tilt3d"):
            ti = t0 + i * 0.09
            pre, anim = fx_alpha(fx)
            emit_line(A, L, ti, t1, x, y, fs, segs, pre=pre, anim=anim)
            if big[i]:
                land = ti + 0.42
        else:  # rise
            ti = t0 + i * 0.12
            pre, anim = fx_alpha("rise")
            emit_line(A, L, ti, t1, x, y, fs, segs, pre=pre, anim=anim, move=(x, y + 26, 380))
            if big[i]:
                land = ti + 0.3
    bi = next(i for i in range(len(lines)) if big[i])
    if glint:
        gt = (0.6, 3.2) if hold_frame0 else (land - t0 + 0.12,)
        emit_glint(A, layer + 30, t0, x, ys[bi], fss[bi], lines[bi], [g for g in gt if t0 + g + 0.6 < t1])
    if particles and not hold_frame0 and fx in ("slam", "zoom", "flip3d", "swing3d", "tilt3d"):
        fx_particles(A, land, x, ys[bi], est_units("".join(t for t, _ in lines[bi])) * fss[bi] / 2, seed=seed)
    return land, (btop, bbot), ys[bi]


# ───────────────────────── Tiêu đề ─────────────────────────
def render_title(A, t, events):
    t0, t1 = float(t.get("start", 0)), float(t["end"])
    lines = split_accent_lines("|".join(t["lines"]) if isinstance(t["lines"], list) else t["lines"])
    if t.get("letterbox"):
        render_letterbox(A, {"start": t0, "end": t1 + 0.3}, instant=True)
    if t.get("dim", 0):
        rect(A, 10, t0, t1, "000000", t["dim"], r"\fad(0,350)")
    render_block(A, t0, t1, lines, big_max=t.get("fs", 350), cy=t.get("y"), layer=11, hold_frame0=True,
                 glint=False, particles=False, seed=1)   # không hiệu ứng ánh sáng đầu video
    events += [(t0 + 0.02, "impact_soft"), (t1 - 0.3, "whoosh")]
    return (t0, t1)


# ───────────────────────── Chữ nhấn ─────────────────────────
EMPH_VARIANTS = {
    "impact": dict(dim=0.22, fs=330, fx="slam", punch=1.07),
    "chapter": dict(dim=0.45, fs=250, fx="wipe", punch=1.05),
    "whisper": dict(dim=0.0, fs=190, fx="rise", punch=0),
}
FX_SFX = {
    "slam": [(-0.2, "whoosh"), (0.12, "impact")],
    "zoom": [(-0.7, "riser"), (0.18, "impact")],
    "stagger": [(-0.15, "swish"), ("words", "pop")],
    "wipe": [(-0.15, "whoosh"), (0.3, "sparkle")],
    "type": [("chars", "tick")],
    "rise": [(-0.15, "whoosh_soft")],
    "flip3d": [(-0.2, "swish"), (0.3, "impact_soft")],
    "swing3d": [(-0.2, "whoosh"), (0.4, "pop")],
    "tilt3d": [(-0.2, "whoosh"), (0.35, "impact_soft")],
}


def render_emphasis(A, e, events, punches, idx):
    t0, t1 = float(e["start"]), float(e["end"])
    v = EMPH_VARIANTS[e.get("variant", "impact")]
    fx = e.get("fx", v["fx"])
    markup = e["text"]
    if e.get("kicker"):
        markup = e["kicker"].upper().replace("{", "").replace("}", "") + "|" + markup
    lines = split_accent_lines(markup)
    if v["dim"]:
        rect(A, 20, t0, t1, "000000", v["dim"], r"\fad(160,200)")
    land, (btop, bbot), ybig = render_block(A, t0, t1, lines, fx=fx, big_max=e.get("fs", v["fs"]),
                                             cy=e.get("y"), layer=21, seed=idx + 11,
                                             particles=e.get("particles", True))
    if fx in ("slam", "zoom", "flip3d", "tilt3d") and e.get("variant", "impact") != "whisper":
        fx_shockwave(A, land, W / 2, ybig)
        if e.get("flash", fx == "slam"):
            fx_flash(A, land - 0.02)
    if e.get("leak"):
        fx_leak(A, t0, 1.4, seed=idx)
    p = e.get("punch", v["punch"] if fx in ("slam", "zoom", "wipe", "flip3d", "tilt3d") else 0)
    if p is True:
        p = 1.07
    if p:
        punches.append((land - 0.1, t1, float(p)))
    if e.get("sfx") != "none":
        n_chars = sum(len("".join(t for t, _ in ln)) for ln in lines)
        n_words = sum(len(t.split()) for ln in lines for t, _ in ln)
        for when, kind in (FX_SFX.get(fx, []) if not e.get("sfx") else [(-0.15, e["sfx"])]):
            if e.get("variant") == "whisper" and kind == "whoosh":
                kind = "whoosh_soft"
            if e.get("variant") == "chapter" and kind == "impact":
                kind = "impact_soft"
            if when == "words":
                events += [(t0 + k * 0.11, kind) for k in range(n_words)]
            elif when == "chars":
                events += [(t0 + k * 0.045, kind) for k in range(0, n_chars, 2)]
            else:
                events.append((t0 + when, kind))
    return (t0, t1)


# ───────────────────────── Minh họa ─────────────────────────
LABEL_SCALE = 1.0          # plan "label_scale": nhãn minh họa to hơn (bản dọc selfie cận: 1.6 — nhãn 40 quá nhỏ trên điện thoại)


def lbl(A, layer, t0, t1, x, y, text, fs=40, color=WHITE, fsp=4):
    fs = fs * LABEL_SCALE
    sh, d = shadow_tags(fs)
    A.add(layer, t0, t1, rf"{{\an5\move({x:.0f},{y + 20:.0f},{x:.0f},{y:.0f},0,300){FONT['black']}\fs{fs}\fsp{fsp}{sh}\1c{col(color)}}}{clean(text).upper()}")


def render_letterbox(A, e, instant=False):
    t0, t1 = float(e["start"]), float(e["end"])
    bar = H * e.get("size", 0.085)
    top = r"\pos(0,0)" if instant else rf"\move(0,{-bar:.0f},0,0,0,500)"
    bot = rf"\pos(0,{H - bar:.0f})" if instant else rf"\move(0,{H:.0f},0,{H - bar:.0f},0,500)"
    for p in (top, bot):
        A.add(40, t0, t1, rf"{{\an7{p}\bord0\shad0\1c&H000000&\fad(0,300)\p1}}m 0 0 l {W} 0 {W} {bar:.0f} 0 {bar:.0f}{{\p0}}")


def render_illustration(A, e, events, idx):
    t0, t1 = float(e["start"]), float(e["end"])
    kind = e["type"]
    cx, cy = W * e.get("x", 0.5), H * (e.get("y", 0.535) + DY)
    L = 50
    w = 5
    ms = int((t1 - t0) * 1000)
    label = e.get("label")
    sfx = e.get("sfx")

    def add_sfx(default):
        k = sfx or default
        if k and k != "none":
            events.append((t0, k))

    if kind == "clock":
        S = e.get("size", 210); u = U(cx, cy, S)
        polys = ring(cx, cy, S * 0.46, w)
        for k in range(12):
            a = 2 * math.pi * k / 12
            r1 = 0.36 if k % 3 == 0 else 0.40
            polys.append(seg((cx + S * r1 * math.cos(a), cy + S * r1 * math.sin(a)),
                             (cx + S * 0.43 * math.cos(a), cy + S * 0.43 * math.sin(a)), w * (1.1 if k % 3 == 0 else 0.7)))
        polys.append(seg(u(50, 50), u(36, 40), w * 1.2))
        polys += dot(cx, cy, 6)
        bb = bbox(polys)
        emit_drawing(A, L, t0, t1, polys, bb=bb)
        emit_drawing(A, L + 3, t0, t1, [seg(u(50, 50), u(50, 15), w)], bb=bb, glow=False,
                     extra=rf"\org({cx:.0f},{cy:.0f})\t(0,{ms},\frz-360)")
        if label:
            lbl(A, L + 6, t0 + 0.3, t1, cx, cy + S * 0.66, label)
        if not sfx:
            events.extend((t0 + 0.5 * i, "tick") for i in range(5))
        else:
            add_sfx(None)

    elif kind == "scale":
        S = e.get("size", 260); u = U(cx, cy, S)
        base = [seg(u(50, 22), u(50, 90), w), seg(u(34, 90), u(66, 90), w)] + dot(*u(50, 18), 6)
        bb = (cx - S * 0.55, cy - S * 0.4, cx + S * 0.55, cy + S * 0.45)
        emit_drawing(A, L, t0, t1, base, bb=bb)
        beam = [seg(u(8, 24), u(92, 24), w)]
        for px in (8, 92):
            beam += [seg(u(px, 24), u(px - 9, 54), w * 0.7), seg(u(px, 24), u(px + 9, 54), w * 0.7)]
            arc = [u(px - 11 + 22 * i / 16, 54 + 9 * math.sin(math.pi * i / 16)) for i in range(17)]
            beam += polyline(arc, w) + [seg(u(px - 11, 54), u(px + 11, 54), w * 0.7)]
        ox, oy = u(50, 24)
        emit_drawing(A, L + 3, t0, t1, beam, bb=bb,
                     extra=rf"\org({ox:.0f},{oy:.0f})\frz9\t(0,700,0.6,\frz-8)\t(700,1250,\frz4)\t(1250,1700,\frz0)")
        if e.get("left_label"):
            lbl(A, L + 6, t0 + 0.6, t1, *u(8, 78), e["left_label"], fs=34)
        if e.get("right_label"):
            lbl(A, L + 6, t0 + 0.6, t1, *u(92, 78), e["right_label"], fs=34, color=ACC)
        add_sfx("chime")

    elif kind == "split":
        ya, yb = H * (0.47 + DY), H * (0.61 + DY)
        A.add(L, t0, t1, rf"{{\an7\pos({W / 2 - 2:.0f},{ya:.0f})\bord0\shad0\1c{col(ACC)}\clip(0,{(ya + yb) / 2:.0f},{W},{(ya + yb) / 2:.0f})\t(0,450,0.5,\clip(0,{ya - 5:.0f},{W},{yb + 5:.0f}))\fad(0,250)\p1}}m 0 0 l 4 0 4 {yb - ya:.0f} 0 {yb - ya:.0f}{{\p0}}")
        ym = H * (0.54 + DY)
        for side, key, acc in ((-1, "left_label", False), (1, "right_label", True)):
            if e.get(key):
                segs = [(clean(e[key]).upper(), acc)]
                fs = fit_fs([segs[0][0]], 420, 96)
                x = W / 2 + side * 250
                pre, anim = fx_alpha("rise")
                emit_line(A, L + 2 + (side > 0) * 3, t0 + 0.2 + (side > 0) * 0.15, t1, x, ym, fs, segs,
                          pre=pre, anim=anim, move=(W / 2 + side * 140, ym, 380))
        add_sfx("swish")

    elif kind == "quote":
        gy = H * (e.get("y", 0.49) + DY)
        if label:
            segs = seg_lines(parse_markup(label))
            fs = fit_fs(["".join(x for x, _ in ln) for ln in segs], 820, 50, black=False)
            for k, ln in enumerate(segs):
                y = gy + H * 0.065 + k * fs * 0.95
                sh, _ = shadow_tags(fs)
                A.add(L + 3, t0 + 0.25 + k * 0.15, t1, rf"{{\an5\move({W / 2:.0f},{y + 18:.0f},{W / 2:.0f},{y:.0f},0,450){FONT['bold']}\fs{fs}{sh}}}"
                      + "".join(rf"{{\1c{col(ACC if a else WHITE)}}}{t}" for t, a in ln))
        pre, anim = fx_alpha("zoom")
        emit_line(A, L, t0, t1, W / 2, gy, 260, [("“", True)], pre=pre, anim=anim)
        add_sfx("shimmer")

    elif kind == "frame":
        ix, top, bot, ln = 64, H * 0.14, H * 0.86, 80
        for (x, y), sx, sy in (((ix, top), 1, 1), ((W - ix, top), -1, 1), ((ix, bot), 1, -1), ((W - ix, bot), -1, -1)):
            polys = [seg((x, y), (x + sx * ln, y), 4), seg((x, y), (x, y + sy * ln), 4)]
            emit_drawing(A, L, t0, t1, polys, wipe=False, fade=(250, 300),
                         extra=rf"\move({-sx * 50},{-sy * 50},0,0,0,500)")
        add_sfx("shimmer")

    elif kind == "checklist":
        items = e.get("items", [])
        y0 = H * (e.get("y", 0.50) + DY)   # checklist nhận "y" (mặc định 0.50 như cũ)
        for i, it in enumerate(items):
            ti = t0 + i * 0.5
            y = y0 + i * 76
            tx = W * e.get("x", 0.25)
            chk = polyline([(tx - 46, y), (tx - 33, y + 14), (tx - 6, y - 18)], 6)
            emit_drawing(A, L, ti, t1, chk, draw_ms=280)
            sh, _ = shadow_tags(42)
            A.add(L + 4, ti + 0.1, t1, rf"{{\an4\move({tx + 40:.0f},{y:.0f},{tx + 10:.0f},{y:.0f},0,300){FONT['bold']}\fs42{sh}\1c&HFFFFFF&}}{clean(it)}")
            if not sfx:
                events.append((ti + 0.05, "pop"))
        if sfx:
            add_sfx(None)

    elif kind == "growth":
        S = e.get("size", 240); u = U(cx, cy, S)
        axes = polyline([u(6, 6), u(6, 92), u(96, 92)], w * 0.7)
        pts = [u(10, 82), u(28, 68), u(44, 72), u(60, 48), u(76, 40), u(92, 12)]
        line = polyline(pts, w * 1.2) + [seg(u(92, 12), u(80, 13), w * 1.2), seg(u(92, 12), u(91, 25), w * 1.2)]
        emit_drawing(A, L, t0, t1, axes, draw_ms=400, glow=False, op=0.8, color=WHITE)
        emit_drawing(A, L + 3, t0 + 0.2, t1, line, draw_ms=900)
        if label:
            pre, anim = fx_alpha("zoom")
            emit_line(A, L + 6, t0 + 0.9, t1, *u(62, -24), 90, [(clean(label).upper(), True)], pre=pre, anim=anim)
            fx_particles(A, t0 + 1.2, *u(62, -24), 80, n=10, seed=idx)
        add_sfx("riser")

    elif kind == "counter":
        # số đếm nhảy từ 0 → value
        val = float(e.get("value", 100))
        suffix, prefix = e.get("suffix", ""), e.get("prefix", "")
        dec = int(e.get("decimals", 0))
        steps, run = 22, 0.9
        fs = e.get("fs", 230)
        y = H * (e.get("y", 0.54) + DY)
        for k in range(steps + 1):
            a = t0 + run * k / steps
            b = t0 + run * (k + 1) / steps if k < steps else t1
            p = 1 - (1 - k / steps) ** 3
            txt = f"{prefix}{val * p:,.{dec}f}{suffix}".replace(",", ".")
            sh, _ = block_style(fs)
            A.add(L + 2, a, b, rf"{{\an5\pos({W / 2:.0f},{y:.0f}){FONT['black']}\fs{fs}{sh}\1c{col(ACC)}}}{txt}")
        if label:
            lbl(A, L + 6, t0 + 0.2, t1, W / 2, y + fs * 0.55, label, fs=40)
        fx_particles(A, t0 + run, W / 2, y, 200, n=14, seed=idx)
        if not sfx:
            events.extend([(t0 + run * k / 10, "tick") for k in range(10)] + [(t0 + run, "impact_soft")])
        else:
            add_sfx(None)

    elif kind.startswith("icon:"):
        name = kind.split(":", 1)[1]
        S = e.get("size", 150)
        cy = H * (e.get("y", 0.51) + DY)                 # huy hiệu nằm cao hơn một chút để nhãn không chạm sub
        u = U(cx, cy, S)
        w = 3.4                                   # nét mảnh, thanh lịch
        if name == "home":
            polys = polyline([u(8, 48), u(50, 10), u(92, 48)], w) + polyline([u(20, 38), u(20, 90), u(80, 90), u(80, 38)], w) \
                + polyline([u(42, 90), u(42, 64), u(58, 64), u(58, 90)], w)
        elif name == "heart":
            hp = []
            for i in range(48):
                tt = 2 * math.pi * i / 48
                hx = 16 * math.sin(tt) ** 3
                hy = 13 * math.cos(tt) - 5 * math.cos(2 * tt) - 2 * math.cos(3 * tt) - math.cos(4 * tt)
                hp.append(u(50 + hx * 2.7, 46 - hy * 2.7))
            polys = polyline(hp, w, closed=True)
        elif name == "star":
            sp = [u(50 + (46 if i % 2 == 0 else 19) * math.cos(-math.pi / 2 + math.pi * i / 5),
                    52 + (46 if i % 2 == 0 else 19) * math.sin(-math.pi / 2 + math.pi * i / 5)) for i in range(10)]
            polys = polyline(sp, w, closed=True)
        elif name == "briefcase":
            polys = polyline([u(8, 32), u(92, 32), u(92, 86), u(8, 86)], w, closed=True) \
                + polyline([u(36, 32), u(36, 18), u(64, 18), u(64, 32)], w) + [seg(u(8, 54), u(92, 54), w * 0.7)]
        elif name == "target":
            polys = ring(cx, cy, S * 0.46, w) + ring(cx, cy, S * 0.30, w) + ring(cx, cy, S * 0.14, w) + dot(cx, cy, 6)
        elif name == "bulb":
            bp = [u(50 + 30 * math.cos(a), 40 + 30 * math.sin(a))
                  for a in [math.pi * (0.75 + 1.5 * i / 30) for i in range(31)]]
            polys = polyline(bp, w) + polyline([bp[0], u(38, 74), u(62, 74), bp[-1]], w) \
                + [seg(u(40, 84), u(60, 84), w), seg(u(44, 93), u(56, 93), w)]
        else:
            die(f"icon không hỗ trợ: {name} (home, heart, star, briefcase, target, bulb)")
        if e.get("emblem", True):                # huy hiệu: vòng đôi + 4 điểm kim cương
            R1, R2 = S * 0.78, S * 0.86
            polys += ring(cx, cy, R1, 1.8) + ring(cx, cy, R2, 1.1)
            for ang in (0, 90, 180, 270):
                a_ = math.radians(ang)
                px, py = cx + R2 * math.cos(a_), cy + R2 * math.sin(a_)
                dm = 7
                polys.append(([(px, py - dm), (px + dm * 0.7, py), (px, py + dm), (px - dm * 0.7, py)], False))
        if e.get("spin3d", True):
            emit_drawing(A, L, t0, t1, polys, wipe=False,
                         extra=rf"\org({cx:.0f},{cy:.0f})\fry-270\t(0,900,0.45,\fry0)")
        else:
            emit_drawing(A, L, t0, t1, polys)
        fx_particles(A, t0 + 0.55, cx, cy, S * 0.4, n=10, seed=idx + 5)
        if label:
            lbl(A, L + 6, t0 + 0.35, t1, cx, cy + S * 1.06, label)
        add_sfx("chime")
        events.append((t0 + 0.5, "sparkle"))

    elif kind == "cube":
        # khối lập phương nét, xoay 3D thật (chiếu phối cảnh, cập nhật 20 lần/giây)
        S = e.get("size", 90)
        cy = H * (e.get("y", 0.50) + DY)
        verts = [(x_, y_, z_) for x_ in (-1, 1) for y_ in (-1, 1) for z_ in (-1, 1)]
        edges = [(a_, b_) for a_ in range(8) for b_ in range(a_ + 1, 8)
                 if sum(verts[a_][k] != verts[b_][k] for k in range(3)) == 1]
        step = 0.05
        n = max(1, int((t1 - t0) / step))
        for k in range(n):
            tt = k * step
            grow = min(1.0, tt / 0.45)
            grow = 1 - (1 - grow) ** 3
            ay, ax = 0.6 + tt * 1.4, 0.45 + 0.15 * math.sin(tt * 1.2)
            pts = []
            for x_, y_, z_ in verts:
                x1_ = x_ * math.cos(ay) + z_ * math.sin(ay)
                z1_ = -x_ * math.sin(ay) + z_ * math.cos(ay)
                y1_ = y_ * math.cos(ax) - z1_ * math.sin(ax)
                z2_ = y_ * math.sin(ax) + z1_ * math.cos(ax)
                f = 4.2 / (4.2 + z2_)
                pts.append((cx + x1_ * S * f * grow, cy + y1_ * S * f * grow))
            polys = [seg(pts[a_], pts[b_], w) for a_, b_ in edges] + [x for q in pts for x in dot(*q, 5)]
            last = k == n - 1
            emit_drawing(A, L, t0 + tt, t1 if last else t0 + tt + step + 0.01, polys, wipe=False,
                         fade=(0, 0), glow=True)
        if label:
            lbl(A, L + 6, t0 + 0.35, t1, cx, cy - S * 1.5, label)
        add_sfx("shimmer")

    elif kind == "stamp":
        text = clean(e.get("label", "")).upper()
        y = H * (e.get("y", 0.505) + DY)
        per = 40
        sh, _ = shadow_tags(40)
        A.add(L + 1, t0, t1, rf"{{\an5\pos({W / 2:.0f},{y:.0f}){FONT['black']}\fs40\fsp10{sh}\1c{col(ACC)}}}"
              + "".join(rf"{{\alpha&HFF&\t({k * per},{k * per + 1},\alpha&H00&)}}{ch}" for k, ch in enumerate(text)))
        tw = text_width(text, 40, fsp=10) * 1.04
        for side in (-1, 1):
            x_in = W / 2 + side * (tw / 2 + 24)
            emit_drawing(A, L + 3, t0 + 0.15, t1, [seg((x_in, y), (x_in + side * 70, y), 3)], draw_ms=400, glow=False)
        if not sfx:
            events.extend((t0 + k * per / 1000, "tick") for k in range(0, len(text), 2))

    elif kind == "letterbox":
        render_letterbox(A, e)
    else:
        die(f"loại minh họa không hỗ trợ: {kind}")
    return (t0, t1)


# ───────────────────────── Sub ─────────────────────────
PUNCT = ".,!?…;:"


def build_chunks(words):
    chunks, cur = [], []
    for i, w in enumerate(words):
        cur.append(w)
        nxt = words[i + 1] if i + 1 < len(words) else None
        txt = " ".join(x["w"] for x in cur)
        if (nxt is None or len(cur) >= SUB["max_words"] or w["w"][-1] in PUNCT
                or nxt["s"] - w["e"] > SUB["gap_break"]
                or len(txt) + 1 + len(nxt["w"]) > SUB["max_chars"]):
            chunks.append(cur)
            cur = []
    return chunks


def subtract(a, b, blocks):
    out = [(a, b)]
    for x, y in blocks:
        nxt = []
        for p, q in out:
            if y <= p or x >= q:
                nxt.append((p, q))
                continue
            if x > p:
                nxt.append((p, x))
            if y < q:
                nxt.append((y, q))
        out = nxt
    return [(p, q) for p, q in out if q - p > 0.04]


def fmt_word(w):
    t = clean(w).strip(PUNCT + "\"'“”")
    keep = (len(t) > 1 and t.isupper()) or any(ch.isupper() for ch in t[1:])   # AI, CEO, YouTube, TikTok
    if SUB["lowercase"] and not keep:
        t = t.lower()
    return t


def display_words(words, proper):
    """chữ hiển thị cho từng từ: viết thường + khôi phục tên riêng (người, địa danh, thương hiệu)."""
    disp = [fmt_word(w["w"]) for w in words]
    low = [d.lower() for d in disp]
    phrases = sorted({p.strip() for p in proper if p.strip()}, key=lambda s: -len(s.split()))
    for ph in phrases:
        toks = ph.split()
        lt = [t.lower() for t in toks]
        n = len(toks)
        for i in range(len(disp) - n + 1):
            if low[i:i + n] == lt:
                for k in range(n):
                    disp[i + k] = toks[k]
    return disp


def render_subs(A, words, blocks, dur, proper=(), zones=()):
    """zones: [{"start", "end", "y"}] — dời sub sang độ cao khác trong khoảng đó (VD đoạn quay màn hình có sub sẵn)."""
    disp = display_words(words, list(PROPER_DEFAULT) + list(proper))
    for i, w in enumerate(words):
        w["_i"] = i
    chunks = build_chunks(words)
    for ci, ch in enumerate(chunks):
        c0 = ch[0]["s"]
        nstart = chunks[ci + 1][0]["s"] if ci + 1 < len(chunks) else dur
        c1 = min(ch[-1]["e"] + 0.25, nstart)
        # cụm sub CHỒNG LÊN vùng (không chỉ bắt đầu trong vùng) → dời; trước đây cụm vào sớm 0.3s vẫn đè nhãn minh họa
        y = H * next((z["y"] for z in zones if c0 < z["end"] and c1 > z["start"]), SUB["y"])
        toks = [disp[w["_i"]] for w in ch]
        plain = " ".join(toks)
        for wi, w in enumerate(ch):
            s = c0 if wi == 0 else w["s"]
            e = ch[wi + 1]["s"] if wi + 1 < len(ch) else c1
            rich = " ".join(rf"{{\1c{col(ACC if k == wi else SUB_BASE)}}}{t}" for k, t in enumerate(toks))
            for p, q in subtract(s, e, blocks):
                A.add(2, p, q, rf"{{\an5\pos({W / 2:.0f},{y:.0f}){FONT['bold']}\fs{SUB['fs']}\fsp{SUB['fsp']}{text_style(SUB['fs'])[0]}}}{rich}")


# ───────────────────────── SFX ─────────────────────────
def _np():
    try:
        import numpy as np
        return np
    except ImportError:
        die("thiếu numpy: pip install numpy")


def _lp(np, x, fc):
    """low-pass 1 cực, fc có thể là mảng."""
    a = 1 - np.exp(-2 * np.pi * np.broadcast_to(fc, x.shape) / SR)
    y = np.empty_like(x); s = 0.0
    for i in range(len(x)):
        s += a[i] * (x[i] - s)
        y[i] = s
    return y


def _reverb(np, st, rng, decay=1.2, wet=0.28):
    n = int(decay * SR)
    t = np.arange(n) / SR
    out = []
    for ch in range(2):
        ir = rng.standard_normal(n) * np.exp(-t * 6.9 / decay)
        ir = _lp(np, ir, 5000.0)
        ir /= np.sqrt((ir ** 2).sum()) + 1e-9
        m = len(st) + n - 1
        N = 1 << (m - 1).bit_length()
        y = np.fft.irfft(np.fft.rfft(st[:, ch], N) * np.fft.rfft(ir, N), N)[:m]
        out.append(y)
    wetsig = np.stack(out, 1)
    dry = np.vstack([st, np.zeros((n - 1, 2))])
    return dry * (1 - wet) + wetsig * wet * 2.2


def synth(kind, np, rng):
    t_ = lambda d: np.arange(int(d * SR)) / SR
    if kind in ("whoosh", "whoosh_soft", "swish"):
        d = 0.42 if kind == "swish" else 0.8
        t = t_(d); n = len(t)
        pk = 0.55 * d
        fc = np.where(t < pk, 250 + 5200 * (t / pk) ** 1.6, 5450 - 4700 * np.clip((t - pk) / (d - pk), 0, 1) ** 0.7)
        if kind == "swish":
            fc = fc * 1.5
        body = _lp(np, rng.standard_normal(n), fc)
        body -= _lp(np, body, 180.0)
        air = _lp(np, rng.standard_normal(n), fc * 2.2) * 0.35
        f = 90 + 260 * np.sin(np.pi * np.clip(t / d, 0, 1))
        tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.25
        env = np.where(t < pk, np.sin(0.5 * np.pi * np.clip(t / pk, 0, 1)) ** 2, np.cos(0.5 * np.pi * np.clip((t - pk) / (d - pk), 0, 1)) ** 2)
        mono = (body + air + tone) * env
        pan = t / d
        st = np.stack([mono * (1 - 0.45 * pan), mono * (0.55 + 0.45 * pan)], 1)
        st = _reverb(np, st, rng, 0.9, 0.22)
    elif kind in ("impact", "impact_soft"):
        d = 1.4
        t = t_(d)
        f = 38 + 30 * np.exp(-t / 0.08)
        boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.45)
        thump = np.sin(2 * np.pi * 110 * t) * np.exp(-t / 0.07) * 0.6
        crack = _lp(np, rng.standard_normal(len(t)), 3500.0) * np.exp(-t / 0.012) * 1.4
        mono = np.tanh((boom + thump + crack) * 1.6)
        mono *= np.minimum(1, t / 0.002)
        st = np.stack([mono, mono], 1)
        st = _reverb(np, st, rng, 1.6, 0.3 if kind == "impact" else 0.38)
    elif kind == "riser":
        d = 0.8; t = t_(d)
        f = 160 * (6 ** (t / d))
        ton = np.sin(2 * np.pi * np.cumsum(f) / SR) + 0.5 * np.sin(2 * np.pi * np.cumsum(f * 1.5) / SR)
        noi = _lp(np, rng.standard_normal(len(t)), 300 + 6000 * (t / d) ** 2) * 1.2
        mono = (ton * 0.5 + noi) * (t / d) ** 2.2 * np.minimum(1, (d - t) / 0.03)
        st = _reverb(np, np.stack([mono, mono], 1), rng, 0.8, 0.25)
    elif kind == "sparkle":
        d = 0.9; n = int(d * SR); mono = np.zeros(n)
        for _ in range(14):
            s = int(rng.uniform(0, 0.45) * SR)
            f = rng.uniform(3000, 7500)
            tt = np.arange(n - s) / SR
            mono[s:] += np.sin(2 * np.pi * f * tt) * np.exp(-tt / rng.uniform(0.05, 0.14)) * rng.uniform(0.3, 1)
        st = _reverb(np, np.stack([mono, np.roll(mono, 240)], 1), rng, 1.0, 0.35)
    elif kind == "pop":
        t = t_(0.09)
        f = 900 * np.exp(-t / 0.03) + 380
        mono = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.03) * np.minimum(1, t / 0.001)
        st = _reverb(np, np.stack([mono, mono], 1), rng, 0.4, 0.15)
    elif kind == "tick":
        t = t_(0.05)
        mono = np.sin(2 * np.pi * 2400 * t) * np.exp(-t / 0.006) + 0.3 * rng.standard_normal(len(t)) * np.exp(-t / 0.002)
        st = np.stack([mono, mono], 1)
    elif kind == "chime":
        t = t_(1.6)
        mono = sum(am * np.sin(2 * np.pi * f * t) for f, am in ((1318.5, 1), (1975.5, .5), (2637, .25), (3951, .12)))
        mono *= np.exp(-t / 0.5) * np.minimum(1, t / 0.004)
        st = _reverb(np, np.stack([mono, mono * 0.9], 1), rng, 1.4, 0.3)
    elif kind == "shimmer":
        t = t_(1.9); n = len(t); mono = np.zeros(n)
        for k, f in enumerate((2093, 2349, 2637, 3136, 3520, 4186)):
            off = int(k * 0.035 * SR)
            tt = t[: n - off]
            mono[off:] += np.sin(2 * np.pi * f * tt) * np.exp(-tt / 0.6) * np.minimum(1, tt / 0.01)
        st = _reverb(np, np.stack([mono, np.roll(mono, 300)], 1), rng, 1.6, 0.35)
    else:
        return None
    return st / (np.abs(st).max() + 1e-9)


def load_custom(np, kind):
    f = SFX_DIR / f"{kind}.wav"
    if not f.exists():
        return None
    with wave.open(str(f)) as w:
        ch, sw, sr, n = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
        raw = w.readframes(n)
    if sw != 2:
        print(f"  (bỏ qua {f.name}: chỉ hỗ trợ WAV 16-bit)")
        return None
    x = np.frombuffer(raw, "<i2").astype(float).reshape(-1, ch) / 32768
    if ch == 1:
        x = np.repeat(x, 2, 1)
    x = x[:, :2]
    if sr != SR:
        idx = np.arange(0, len(x), sr / SR)
        x = np.stack([np.interp(idx, np.arange(len(x)), x[:, c]) for c in range(2)], 1)
    return x / (np.abs(x).max() + 1e-9)


def build_sfx(events, dur, out_wav, volume=1.0):
    np = _np()
    rng = np.random.default_rng(7)
    buf = np.zeros((int((dur + 3) * SR), 2))
    cache = {}
    for t, kind in events:
        if kind not in cache:
            cache[kind] = load_custom(np, kind)
            if cache[kind] is None:
                cache[kind] = synth(kind, np, rng)
        s = cache[kind]
        if s is None:
            continue
        i = max(0, int(t * SR))
        j = min(len(buf), i + len(s))
        buf[i:j] += s[: j - i] * SFX_GAIN.get(kind, 0.12) * volume * (10 ** (SFX_MASTER_DB / 20))
    buf = np.tanh(buf[: int(dur * SR) + 1] * 1.1) / 1.1
    with wave.open(str(out_wav), "wb") as f:
        f.setnchannels(2); f.setsampwidth(2); f.setframerate(SR)
        f.writeframes((np.clip(buf, -1, 1) * 32767).astype("<i2").tobytes())


# ───────────────────────── plan -> ass ─────────────────────────
def load_plan(plan_path):
    p = Path(plan_path)
    plan = json.loads(p.read_text(encoding="utf-8-sig"))
    plan["_dir"] = p.parent
    return plan


def load_words(plan):
    wf = plan.get("words_file")
    if not wf:
        return []
    wp = Path(wf)
    if not wp.is_absolute():
        wp = plan["_dir"] / wp
    d = json.loads(wp.read_text(encoding="utf-8-sig"))
    return d["words"] if isinstance(d, dict) else d


def build(video, plan, ass_path):
    """→ (dur, sfx_events, punches, fps, size)"""
    global W, H, ACC, FS_SCALE, BLOCK_MAX_W, BLOCK_Y, DY, LABEL_SCALE
    LABEL_SCALE = float(plan.get("label_scale", 1.0))
    dur, vw, vh, _, fps = probe(video)
    if vw > vh:       # khung ngang
        L = LANDSCAPE
        W, FS_SCALE, BLOCK_MAX_W, BLOCK_Y, DY = L["W"], L["FS_SCALE"], L["BLOCK_MAX_W"], L["BLOCK_Y"], L["DY"]
        SUB["y"], SUB["fs"] = L["SUB_Y"], L["SUB_FS"]
    H = round(W * vh / vw)
    ACC = ACCENTS.get(plan.get("accent", "yellow"), plan.get("accent", ACCENTS["yellow"]).lstrip("#"))
    A = Ass()
    blocks, events, punches = [], [], []
    if plan.get("title"):
        a, b = render_title(A, plan["title"], events)
        blocks.append((a, b + 0.05))
    for k, e in enumerate(plan.get("emphasis", [])):
        a, b = render_emphasis(A, e, events, punches, k)
        if e.get("hide_subs", True):
            blocks.append((a - 0.05, b + 0.05))
    for k, e in enumerate(plan.get("illustrations", [])):
        a, b = render_illustration(A, e, events, k)
        if e.get("hide_subs"):
            blocks.append((a, b))
    words = load_words(plan)
    if words:
        render_subs(A, words, blocks, dur, plan.get("proper_nouns", []), plan.get("sub_zones", []))
    A.dump(ass_path)
    if plan.get("punch", True) is False:
        punches = []
    return dur, events, punches, fps, (vw, vh)


def punch_filter(punches, fps, size, t_offset=0.0):
    if not punches:
        return ""
    terms = []
    for a, b, z in punches:
        up = f"clip((it-{a:.3f})/0.22,0,1)"
        dn = f"clip(({b:.3f}-it)/0.35,0,1)"
        terms.append(f"{z - 1:.3f}*({up}*{up}*(3-2*{up}))*({dn}*{dn}*(3-2*{dn}))")
    z = "1+" + "+".join(terms)
    return (f"zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:"
            f"s={size[0]}x{size[1]}:fps={fps:.3f},")


def _stage(tmp):
    shutil.copytree(FONTS_DIR, Path(tmp) / "fonts")


def run_ff(args, cwd):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"] + args, cwd=cwd)
    if r.returncode != 0:
        die("ffmpeg thất bại (xem thông báo phía trên)")


# ───────────────────────── check ─────────────────────────
def check(video, plan):
    dur = probe(video)[0]
    warn = []
    t = plan.get("title")
    title_end = 0.0
    if not t:
        warn.append("Chưa có tiêu đề.")
    else:
        title_end = float(t["end"])
        if float(t.get("start", 0)) != 0:
            warn.append("Tiêu đề phải bắt đầu ở 0s (frame đầu tiên).")
        d = title_end - float(t.get("start", 0))
        if not 5 <= d <= 10:
            warn.append(f"Tiêu đề dài {d:.1f}s — yêu cầu 5–10s.")
        lines = split_accent_lines("|".join(t["lines"]) if isinstance(t["lines"], list) else t["lines"])
        if len(lines) > 3:
            warn.append("Tiêu đề quá 3 dòng — rút gọn thành hook 2–6 từ.")
        kinds = [("mix" if len({a for _, a in ln}) > 1 else ("màu" if ln[0][1] else "trắng")) for ln in lines if ln]
        if sorted(kinds) != ["màu", "trắng"]:
            warn.append("Tiêu đề phải đúng 2 dòng: 1 dòng trắng + 1 dòng màu (trắng trên–màu dưới "
                        "hoặc màu trên–trắng dưới), mỗi dòng 1 màu.")
        if t.get("base"):
            warn.append("'base' đã bỏ — dòng không màu luôn trắng; muốn đảo thì đặt {..} ở dòng trên.")
        nw = sum(len(x.split()) for ln in lines for x, _ in ln)
        if nw > 8:
            warn.append(f"Tiêu đề {nw} từ — mẫu nên 2–6 từ (hook rút gọn).")
    if plan.get("accent", "yellow") not in ACCENTS:
        warn.append("accent nên là 'yellow' hoặc 'cyan'.")

    effects = [("chữ nhấn", float(e["start"]), float(e["end"])) for e in plan.get("emphasis", [])]
    effects += [(f"minh họa {i['type']}", float(i["start"]), float(i["end"]))
                for i in plan.get("illustrations", []) if i["type"] != "letterbox"]
    effects.sort(key=lambda x: x[1])
    prev = title_end
    for k, (name, a, b) in enumerate(effects):
        g = a - prev
        if g > 10.5:
            warn.append(f"Khoảng trống {g:.1f}s không có hiệu ứng trước {name} @ {a:.1f}s (tối đa ~10s).")
        if k > 0 and g < 5.5 and name != "minh họa stamp" and effects[k - 1][0] != "minh họa stamp":
            warn.append(f"{name} @ {a:.1f}s sát hiệu ứng trước ({g:.1f}s) — nhịp mục tiêu 8–10s.")
        if k > 0 and a < effects[k - 1][2] and "stamp" not in name + effects[k - 1][0]:
            warn.append(f"{name} @ {a:.1f}s chồng lên {effects[k - 1][0]} @ {effects[k - 1][1]:.1f}s.")
        if a < title_end:
            warn.append(f"{name} @ {a:.1f}s chồng lên tiêu đề.")
        if b > dur + 0.01:
            warn.append(f"{name} kết thúc sau khi video hết.")
        prev = a
    if effects and dur - effects[-1][1] > 10.5:
        warn.append(f"Cuối video trống {dur - effects[-1][1]:.1f}s không có hiệu ứng.")
    for e in plan.get("emphasis", []):
        d = float(e["end"]) - float(e["start"])
        if not 1.2 <= d <= 3.0:
            warn.append(f"Chữ nhấn @ {float(e['start']):.1f}s dài {d:.1f}s (nên 1.4–2.6s).")
        if len(split_accent_lines(e["text"])) > 3:
            warn.append(f"Chữ nhấn @ {float(e['start']):.1f}s quá 3 dòng.")
    for i in plan.get("illustrations", []):
        if "y" in i and not (BAND[0] <= i["y"] <= BAND[1]):
            warn.append(f"Minh họa {i['type']} y={i['y']} ngoài vùng an toàn ({BAND[0]}–{BAND[1]}).")
    if not load_words(plan):
        warn.append("Chưa có words_file → video sẽ không có sub.")
    n_e = len(plan.get("emphasis", []))
    n_i = len([i for i in plan.get("illustrations", []) if i["type"] != "letterbox"])
    print(f"Video {dur:.1f}s · {n_e} chữ nhấn · {n_i} minh họa · "
          f"nhịp TB {((dur - title_end) / max(1, len(effects))):.1f}s/hiệu ứng")
    if warn:
        print("CẢNH BÁO:")
        for w in warn:
            print("  - " + w)
    else:
        print("OK — không có cảnh báo.")


# ───────────────────────── commands ─────────────────────────
def _cuda_dlls():
    """Windows: chỉ cho ctranslate2 chỗ cuBLAS/cuDNN cài bằng pip (nvidia-cublas-cu12, nvidia-cudnn-cu12) → whisper chạy GPU."""
    import importlib, os
    for mod in ("nvidia.cublas", "nvidia.cudnn"):
        try:
            d = os.path.join(importlib.import_module(mod).__path__[0], "bin")
            os.add_dll_directory(d)
            os.environ["PATH"] = d + os.pathsep + os.environ.get("PATH", "")
        except (ImportError, OSError, AttributeError):
            pass


def prev_scale(size):
    return "scale=1920:-2" if size[0] > size[1] else "scale=1080:-2"


def _video_encoder(preview, cpu=False):
    """GPU NVIDIA → NVENC (nhanh gấp nhiều lần); thử mã hóa 1 khung thật, lỗi (hoặc --cpu) thì dùng libx264."""
    test = None if cpu else subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=black:s=256x256:d=0.1",
                                            "-c:v", "h264_nvenc", "-f", "null", "-"], capture_output=True)
    if test and test.returncode == 0:
        return "h264_nvenc", ["-preset", "p4" if preview else "p6", "-rc", "vbr",
                              "-cq", "23" if preview else "18", "-b:v", "0"]
    vt = None if cpu else _mac_vt(preview)          # Mac → VideoToolbox
    if vt:
        return vt[1], vt[2:]
    return "libx264", (["-preset", "veryfast", "-crf", "23"] if preview else ["-preset", "slow", "-crf", "17"])


def cmd_transcribe(a):
    _cuda_dlls()
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        die("thiếu faster-whisper: pip install faster-whisper")

    def run(device, ctype):
        m = WhisperModel(a.model, device=device, compute_type=ctype)
        segs, _ = m.transcribe(str(a.video), language=a.lang, word_timestamps=True, vad_filter=True)
        return [{"w": w.word.strip(), "s": round(w.start, 3), "e": round(w.end, 3)}
                for s in segs for w in (s.words or []) if w.word.strip()]
    try:
        words = run("cuda", "float16")
    except Exception:
        words = run("cpu", "int8")
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps({"words": words}, ensure_ascii=False, indent=0), encoding="utf-8")
    lines, cur, t0 = [], [], 0
    for w in words:
        if not cur:
            t0 = w["s"]
        cur.append(w["w"])
        if w["w"][-1] in ".?!" or len(cur) >= 14:
            lines.append(f"[{t0:6.2f}] " + " ".join(cur)); cur = []
    if cur:
        lines.append(f"[{t0:6.2f}] " + " ".join(cur))
    Path(a.out).with_suffix(".txt").write_text("\n".join(lines), encoding="utf-8")
    print(f"{len(words)} từ → {a.out}\nBản đọc có mốc thời gian → {Path(a.out).with_suffix('.txt')}")


def cmd_check(a):
    check(a.video, load_plan(a.plan))


def cmd_snap(a):
    plan = load_plan(a.plan)
    out = Path(a.out).resolve(); out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        _stage(tmp)
        dur, _, punches, fps, size = build(a.video, plan, Path(tmp) / "o.ass")
        for t in [float(x) for x in a.at.split(",")]:
            pf = punch_filter(punches, fps, size)
            if pf:
                pf += f"setpts=PTS+{t}/TB,"
            run_ff(["-ss", f"{t}", "-i", str(Path(a.video).resolve()), "-frames:v", "1",
                    "-vf", f"setpts=PTS+{t}/TB,{pf}{prev_scale(size)},ass=o.ass:fontsdir=fonts",
                    str(out / f"snap_{t:07.2f}.png")], tmp)
    print(f"Ảnh QA → {out}")


def cmd_render(a):
    plan = load_plan(a.plan)
    video = Path(a.video).resolve()
    out = Path(a.out).resolve(); out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        _stage(tmp)
        dur, events, punches, fps, size = build(video, plan, Path(tmp) / "o.ass")
        # KHÔNG lưu file .ass cạnh video: trình phát sẽ tự mở nó như phụ đề và vẽ chữ lần 2 đè lên
        has_audio = probe(video)[3]
        build_sfx(events, dur, Path(tmp) / "sfx.wav", plan.get("sfx_volume", 1.0))
        vf = punch_filter(punches, fps, size) + (prev_scale(size) + "," if a.preview else "") + "ass=o.ass:fontsdir=fonts"
        vcodec, enc = _video_encoder(a.preview, a.cpu)
        if has_audio:
            fc = f"[0:v]{vf}[v];[0:a][1:a]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.89[a]"
        else:
            fc = f"[0:v]{vf}[v];[1:a]anull[a]"
        run_ff(["-i", str(video), "-i", "sfx.wav", "-filter_complex", fc, "-map", "[v]", "-map", "[a]",
                "-c:v", vcodec, *enc, "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                "-movflags", "+faststart", "-shortest", str(out)], tmp)
    print(f"Xong → {out}  ({len(events)} SFX, {len(punches)} zoom punch, {vcodec})")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("transcribe"); p.add_argument("video"); p.add_argument("-o", "--out", required=True)
    p.add_argument("--model", default="small"); p.add_argument("--lang", default="vi"); p.set_defaults(f=cmd_transcribe)
    p = sp.add_parser("check"); p.add_argument("video"); p.add_argument("plan"); p.set_defaults(f=cmd_check)
    p = sp.add_parser("snap"); p.add_argument("video"); p.add_argument("plan")
    p.add_argument("--at", required=True); p.add_argument("-o", "--out", required=True); p.set_defaults(f=cmd_snap)
    p = sp.add_parser("render"); p.add_argument("video"); p.add_argument("plan")
    p.add_argument("-o", "--out", required=True); p.add_argument("--preview", action="store_true")
    p.add_argument("--cpu", action="store_true", help="bỏ qua NVENC, nén bằng libx264"); p.set_defaults(f=cmd_render)
    a = ap.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()

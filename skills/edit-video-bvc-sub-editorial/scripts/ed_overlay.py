#!/usr/bin/env python3
"""ed_overlay — SUB KIỂU EDITORIAL (mẫu "Your home deserves an agent…").
Serif cao gầy + sans mảnh/đậm, chữ hiện từng từ bằng blur-in theo lời nói, chữ chìm sau người,
badge viên thuốc, chữ rải quanh tay, vạch gạch đỏ, flash trắng chuyển cảnh, SFX rất nhẹ.

  python ed_overlay.py transcribe <video> -o <work>/words.json [--lang vi] [--model small]
  python ed_overlay.py check  <video> <work>/plan.json
  python ed_overlay.py snap   <video> <work>/plan.json --at 1,3.2 -o <work>/qa
  python ed_overlay.py render <video> <work>/plan.json -o <work>/out.mp4 [--preview]

Cấu trúc plan.json: references/plan-schema.md. Kiểu chữ: references/kieu-chu.md.
"""
import argparse
import json
import shutil
import struct
import subprocess
import sys
import tempfile
import unicodedata
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
SR = 48000

W, H = 1080, 1920          # hệ tọa độ ASS (H tính lại theo tỉ lệ video)
REFW = 1080                # bề ngang tham chiếu cho "w" (khung ngang vẫn đo theo 1080 để chữ không phình)

# key: (tên font trong ASS, \b, \i, file, co ngang % — Playfair rộng hơn Didone của mẫu nên ép lại)
FONTS = {
    "serif":    ("Playfair Display", 0, 0, "PlayfairDisplay-Regular.ttf", 82),
    "serif_i":  ("Playfair Display", 0, 1, "PlayfairDisplay-Italic.ttf", 86),
    "serif_mi": ("Playfair Display Medium", 0, 1, "PlayfairDisplay-MediumItalic.ttf", 86),
    "light":    ("Inter Light", 0, 0, "Inter-Light.ttf", 100),
    "semi":     ("Inter SemiBold", 0, 0, "Inter-SemiBold.ttf", 100),
    "bold":     ("Inter", 1, 0, "Inter-Bold.ttf", 100),
    "xbold":    ("Inter ExtraBold", 0, 0, "Inter-ExtraBold.ttf", 100),
    "black":    ("Inter Black", 0, 0, "Inter-Black.ttf", 100),     # chữ in hoa MẬP của mẫu (BUT, TOP 1%, INVESTMENT)
}
# "fill" của dòng: None = màu phẳng/gradient · "liquid" = vân nước/kim loại CHẢY trong chữ ·
# "invert" = ÂM BẢN của chính cảnh phía sau (nền tối → chữ sáng, nền sáng → chữ tối, chạy theo hình)

# bảng màu đo từ video mẫu (median pixel) — list = gradient ngang, dict có "dir": "v" = gradient dọc
PAL = {
    "white": "#FFFFFF",
    "ink": "#1E1A1A",                                        # chữ tối trên nền sáng (than what's)
    "plum": "#662676",                                       # YOUR PROPERTY
    "violet": ["#7B51AF", "#68297A"],                        # LET ME
    "purple_grad": ["#5A2A90", "#A57DD8"],                   # TRANSPARENCY.
    "lilac_grad": ["#8A56B6", "#C39BEB"],                    # honored / you
    "teal": "#3F93AE",
    "teal_grad": ["#2E8FB0", "#6CC3D6"],                     # investment (italic)
    "teal_deep": {"stops": ["#7CC4D2", "#0B5577"], "dir": "v"},   # AGENT. / CAN SEE.
    "sky_grad": ["#2299C4", "#6CC9EA"],                      # visible.
    "slate_grad": ["#3C4652", "#7EBAD0"],                    # something
    "silver": {"stops": ["#F6F6F6", "#8D939A"], "dir": "v"},  # INVESTMENT
    "neon_pink": ["#FF7BFF", "#C9A8FF", "#A8FEFF"],          # TOP 1% (mẫu gốc)
    # PHONG CÁCH CỐ ĐỊNH của kênh (chủ kênh chốt 2026-09-30, mẫu Short Hook Demo bản vàng): chữ khóa VÀNG SÁNG phẳng
    # + quầng tối mềm (halo "dark") + bóng gọn — đọc rõ trên trời/đồi/xe trắng lẫn áo tối
    "gold": "#FFD60A",
    "gold_grad": ["#FFE55C", "#FFC300"],
    "gold_soft": ["#FFD60A", "#FFF1A6"],
    "neon": ["#FFF36B", "#FFD60A", "#FFB800"],               # neon vàng
    "red": "#FA2000",                                        # vạch gạch
    "yellow": "#FFE82A",                                     # viền badge
    "pill_fill": "#2B2B2B",
    "glass": "#8F8984",
}

# preset: mặc định cho khoảnh khắc + từng dòng theo thứ tự
PRESETS = {
    # màu mặc định = VÀNG SÁNG + halo "dark" (phong cách cố định của kênh, xem PAL); màu mẫu gốc (violet, plum, teal…) vẫn gọi được
    "serif_hook":     dict(y=0.27, behind=True, drift=0.05, lines=[dict(font="serif", w=0.62, color="gold_grad", halo="dark", caps=True)]),
    "caps_title":     dict(y=0.22, behind=True, drift=0.05, enter="pop", lines=[dict(font="black", w=0.86, color="gold", halo="dark", caps=True)]),
    "neon":           dict(y=0.24, behind=True, drift=0.05, exit_s=0.5, lines=[dict(font="black", w=0.76, color="neon", glow=True, caps=True)]),
    "strike":         dict(y=0.30, behind=True, drift=0.03, lines=[dict(font="black", w=0.56, color="gold", halo="dark", caps=True, strike={})]),
    "caps_big":       dict(y=0.24, behind=True, drift=0.06, enter="pop", lines=[dict(font="black", w=0.60, color="gold", halo="dark", caps=True)]),
    "thin_silver":    dict(y=0.22, behind=True, drift=0.04, gap=0.14, lines=[dict(font="light", fs=90, color="white", halo="dark"),
                                                                             dict(font="black", w=0.80, color="gold", halo="dark", caps=True)]),
    "serif_top_pair": dict(y=0.29, behind=True, drift=0.03, gap=-0.04, lines=[dict(font="serif", w=0.56, color="white", halo="dark"),
                                                                             dict(font="serif_i", w=0.50, color="gold_soft", halo="dark", fill="liquid")]),
    "serif_dark":     dict(y=0.30, behind=True, drift=0.03, lines=[dict(font="serif_i", w=0.70, color="ink", shadow=False)]),
    "serif_pair":     dict(y=0.50, drift=0.03, gap=-0.04, lines=[dict(font="serif", w=0.62, color="white"),
                                                                 dict(font="serif_i", w=0.66, color="gold_grad", halo="dark", fill="liquid")]),
    "thin_caps":      dict(y=0.49, drift=0.02, gap=0.12, lines=[dict(font="light", fs=80, color="white"),
                                                                 dict(font="black", w=0.46, color="gold", halo="dark", caps=True, fill="liquid")]),
    "thin_bold":      dict(y=0.49, drift=0.0, gap=0.04, lines=[dict(font="light", fs=58, color="white"),
                                                                dict(font="bold", fs=62, color="gold", halo="dark")]),
    "gradient_serif": dict(y=0.48, drift=0.02, gap=-0.04, lines=[dict(font="serif_mi", w=0.50, color="gold_grad", halo="dark", fill="liquid"),
                                                                 dict(font="serif_i", w=0.54, color="white")]),
    "serif_italic":   dict(y=0.50, drift=0.02, lines=[dict(font="serif_i", w=0.60, color="white")]),
    "caps_italic":    dict(y=0.50, drift=0.03, lines=[dict(font="serif_i", w=0.74, color="gold_grad", halo="dark", caps=True, fill="liquid")]),
    "serif_color":    dict(y=0.52, drift=0.03, lines=[dict(font="serif_i", w=0.58, color="gold_grad", halo="dark", fill="liquid")]),
    "caps_invert":    dict(y=0.24, behind=True, drift=0.05, enter="pop", lines=[dict(font="black", w=0.80, color="white", caps=True, fill="invert")]),
}
TOP_TIER = 0.36            # y < 0.36: tầng trên (sau đầu) · 0.36–0.64: tầng giữa (ngực) — ẩn sub

# sub (chủ kênh chốt 2026-09-30): GẦN GIỮA KHUNG cho dễ nhìn, hiện thẳng không hiệu ứng; cụm giữa hiện thì sub tự ẩn
# (khuôn ②) nên không chồng; sub rơi vào mặt → tự dời xuống dưới cằm
# keep_shown=True (chủ kênh 2026-10-02): có chữ nhấn thì sub nhỏ VẪN ĐỦ CÂU — không bỏ các từ đang nhấn khỏi sub
# MẪU CHUẨN (chủ kênh 2026-10-07, theo Short Hook Demo_editorial_vang): sub nhỏ 2–4 từ, Inter Light, KHÔNG in đậm,
# cố định ở ngực (y 0.52); từ đang hiện ở chữ nhấn BỎ khỏi sub (keep_shown=False) → hết cảnh "7 THÁNG 10" + "ngày 7 tháng".
SUB = dict(y=0.52, fs=70, font="light", bold_font="light", max_words=4, min_words=2, max_chars=24, gap_break=0.3,
           keep_shown=False)
# khung NGANG 16:9 (chủ kênh 2026-10-01): sub nhỏ là 1 dòng dài 8–12 từ ở đáy khung, không phải 1–2 từ
# dòng dài nét Light chìm trên nền sáng (đường, sỏi) → SemiBold + quầng tối mềm; giữ NGUYÊN CÂU (bỏ từ đang nhấn làm câu
# khuyết: "đến bất động sản … tại đảo Síp" mất "triệu đô")
SUB_LAND = dict(y=0.86, fs=54, font="semi", max_words=12, min_words=8, max_chars=64, gap_break=0.3,
                halo=True, keep_shown=True)
SUB_ZONES = []             # plan "sub_zones": dời sub theo đoạn (đặt trong build)
SHOWN = set()              # mốc (giây, làm tròn 0.01) các từ đang hiện ở chữ nhấn → bỏ khỏi sub (không trùng chữ)
SHADOW_OFF = (0.035, 0.045)   # bóng gọn: lệch chéo phải-dưới theo em (đo từ "I take lightly.", "BUT")
SHADOW_BLUR = 0.035
SHADOW_ALPHA = "&H74&"         # ~55% đen
LIQUID = dict(freq=1.0, speed=1.0, contrast=0.9)   # vân chảy trong chữ
ENTER_S = 0.18             # blur-in
EXIT_S = 0.20              # blur-out
BLUR_IN = 14

SFX_GAIN = dict(boom=0.55, air=0.10, whoosh_soft=0.12, swipe=0.22, pop=0.20, pop_soft=0.13,
                shimmer=0.07, riser=0.16, hit=0.30, tick=0.10,
                **{f"pill{k}": 0.40 for k in range(6)})   # badge bật ra: nghe rõ (pop_soft 0.13 cũ gần như không nghe)
SFX_MASTER_DB = -9.0       # mẫu gốc: SFX rất nhỏ, giọng nói là chính, KHÔNG nhạc nền


def die(msg):
    print("LỖI:", msg, file=sys.stderr)
    sys.exit(1)


def probe(video):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type,width,height,r_frame_rate",
                        "-of", "json", str(video)], capture_output=True, text=True)
    if r.returncode:
        die(f"không đọc được video: {video}")
    d = json.loads(r.stdout)
    v = next(s for s in d["streams"] if s["codec_type"] == "video")
    n, q = v["r_frame_rate"].split("/")
    has_a = any(s["codec_type"] == "audio" for s in d["streams"])
    return float(d["format"]["duration"]), v["width"], v["height"], has_a, float(n) / float(q)


# ───────────────────────── font metrics (đọc thẳng TTF, không cần thư viện) ─────────────────────────
_FM = {}


def fm(key):
    if key in _FM:
        return _FM[key]
    f = FONTS_DIR / FONTS[key][3]
    if not f.exists():
        die(f"thiếu font {f.name} trong {FONTS_DIR} — xem fonts/README.md")
    d = f.read_bytes()
    n = struct.unpack(">H", d[4:6])[0]
    tab = {d[12 + 16 * i:16 + 16 * i].decode("latin1"): struct.unpack(">II", d[20 + 16 * i:28 + 16 * i]) for i in range(n)}
    head, hhea, hmtx, os2, cm = (tab[k][0] for k in ("head", "hhea", "hmtx", "OS/2", "cmap"))
    upem = struct.unpack(">H", d[head + 18:head + 20])[0]
    nhm = struct.unpack(">H", d[hhea + 34:hhea + 36])[0]
    adv = struct.unpack(f">{2 * nhm}H", d[hmtx:hmtx + 4 * nhm])[0::2]
    wa, wd = struct.unpack(">HH", d[os2 + 74:os2 + 78])
    xh, ch = struct.unpack(">hh", d[os2 + 86:os2 + 90])
    cmap = {}
    for i in range(struct.unpack(">H", d[cm + 2:cm + 4])[0]):
        _, _, off = struct.unpack(">HHI", d[cm + 4 + 8 * i:cm + 12 + 8 * i])
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
                for c in range(sts[s], ends[s] + 1):
                    if c == 0xFFFF:
                        continue
                    if ro[s] == 0:
                        g = (c + dl[s]) & 0xFFFF
                    else:
                        a = ro_off + 2 * s + ro[s] + 2 * (c - sts[s])
                        g = struct.unpack(">H", d[a:a + 2])[0]
                        g = (g + dl[s]) & 0xFFFF if g else 0
                    cmap[c] = g
    m = dict(upem=upem, emf=(wa + wd) / upem, asc=wa / upem, desc=wd / upem, xh=xh / upem, cap=ch / upem,
             adv={c: adv[min(g, nhm - 1)] for c, g in cmap.items()})
    _FM[key] = m
    return m


def em_px(key, fs):
    return fs / fm(key)["emf"]


def text_w(text, key, fs):
    m = fm(key)
    tot = 0
    for c in text:
        a = m["adv"].get(ord(c))
        if a is None:
            a = m["adv"].get(ord(unicodedata.normalize("NFD", c)[0]), m["upem"] * 0.55)
        tot += a
    return tot / m["upem"] * em_px(key, fs) * FONTS[key][4] / 100


def vbox(text, key, fs):
    """(trên, dưới) của phần mực so với baseline (px, trên âm)."""
    m, e = fm(key), em_px(key, fs)
    tall = any(c.isupper() or c.isdigit() or c in "bdfhklt%$&?!'" for c in text)
    top = -(m["cap"] if tall else m["xh"]) * e
    if any(unicodedata.combining(x) for c in text for x in unicodedata.normalize("NFD", c)[1:]):
        top -= 0.2 * e                                   # dấu tiếng Việt phía trên
    bot = m["desc"] * 0.75 * e if any(c in "gjpqyçQ,;" for c in text) else 0.02 * e
    return top, bot


# ───────────────────────── ASS ─────────────────────────
def col(h):
    h = h.lstrip("#")
    return f"&H{h[4:6]}{h[2:4]}{h[0:2]}&".upper()


def alp(op):
    return f"&H{255 - round(max(0, min(1, op)) * 255):02X}&"


def ts(t):
    t = max(0.0, t)
    cs = int(round(t * 100))
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def esc(s):
    return s.replace("\\", "/").replace("{", "(").replace("}", ")")


def ms(x):
    return int(round(x * 1000))


def mix(a, b, t):
    a, b = a.lstrip("#"), b.lstrip("#")
    return "#" + "".join(f"{round(int(a[i:i + 2], 16) * (1 - t) + int(b[i:i + 2], 16) * t):02X}" for i in (0, 2, 4))


def grad_at(stops, t):
    if len(stops) == 1:
        return stops[0]
    x = t * (len(stops) - 1)
    i = min(int(x), len(stops) - 2)
    return mix(stops[i], stops[i + 1], x - i)


def paint(c):
    c = PAL.get(c, c) if isinstance(c, str) else c
    if isinstance(c, str):
        return dict(stops=[c], dir="h")
    if isinstance(c, list):
        return dict(stops=[PAL.get(x, x) for x in c], dir="h")
    return dict(stops=[PAL.get(x, x) for x in c["stops"]], dir=c.get("dir", "h"))


FX_BUCKETS = ("liq_back", "inv_back", "liq_front", "inv_front")


class Ass:
    def __init__(self):
        self.ev = {k: [] for k in ("front", "back") + FX_BUCKETS}

    def add(self, layer, t0, t1, text, back=False, fx=None):
        if t1 - t0 > 0.02:
            key = (f"{fx}_" if fx else "") + ("back" if back else "front")
            self.ev[key].append((layer, t0, t1, text))

    def dump(self, path, which, white=False):
        """white=True → mọi màu thành trắng: dùng làm MẶT NẠ (độ phủ chữ) cho lớp hiệu ứng."""
        if white:
            import re
            ev = [(l, a, b, re.sub(r"\\([13])c&H[0-9A-Fa-f]{6}&", r"\\\1c&HFFFFFF&", t)) for l, a, b, t in self.ev[which]]
            self.ev = dict(self.ev, _tmp=ev)
            which = "_tmp"
        head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Base,Inter Light,48,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,5,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        rows = [f"Dialogue: {l},{ts(a)},{ts(b)},Base,,0,0,0,,{t}"
                for l, a, b, t in sorted(self.ev[which], key=lambda e: (e[1], e[0]))]
        Path(path).write_text(head + "\n".join(rows) + "\n", encoding="utf-8-sig")


def span_tags(o, vis, base_blur, enter, xa, xb, exit_blur, e_in=ENTER_S):
    """tag cho 1 cụm từ: ẩn → hiện ở o (ms) → ẩn dần xa..xb (ms)."""
    s = r"\alpha&HFF&"
    if enter == "none":
        s += rf"\blur{base_blur:g}\t({o},{o + 1},\alpha{vis})"
    else:
        s += rf"\blur{base_blur + BLUR_IN:g}\t({o},{o + ms(e_in)},\alpha{vis}\blur{base_blur:g})"
    if xb > xa:
        s += rf"\t({xa},{xb},\alpha&HFF&\blur{base_blur + exit_blur:g})"
    return s


# ───────────────────────── đồng bộ từ ─────────────────────────
def norm(s):
    s = unicodedata.normalize("NFC", s).lower()
    return "".join(c for c in s if c.isalnum())


def match_times(words, tokens, start, end, ptr0=None):
    """mốc thời gian cho từng token bằng cách dò lời nói (words.json) quanh [start, end]."""
    ptr = ptr0 if ptr0 is not None else next((i for i, w in enumerate(words) if w["s"] >= start - 0.6), len(words))
    out, prev = [], start
    for tok in tokens:
        k = norm(tok)
        hit = None
        # dò theo THỜI GIAN tới hết khoảnh khắc (chữ nhấn giữ suốt câu → từ khóa có thể nằm ở từ thứ 10+ của câu)
        for j in range(ptr, min(ptr + 60, len(words))):
            if words[j]["s"] > end + 0.4:
                break
            wn = norm(words[j]["w"])
            if k and wn and (wn == k or (len(k) >= 3 and (k in wn or wn in k))):
                hit = j
                break
        if hit is None:
            out.append(None)
        else:
            out.append(words[hit]["s"])
            prev, ptr = words[hit]["s"], hit + 1
    # lấp lỗ
    res, last = [], start
    for t in out:
        last = t if t is not None else last + 0.12
        res.append(last)
    return res, ptr


# ───────────────────────── chữ ─────────────────────────
# BỘ MÀU (plan "theme"): "vang" = mặc định của kênh (preset đã vàng + quầng tối) ·
# "tim" = bộ TÍM SÁNG (mẫu Short Hook Demo bản tím, Short Hook Demo bản tím (demo nội bộ) → preview.mp4):
# chữ in hoa plum, serif violet/purple/lilac, neon hồng, quầng TRẮNG mềm cho nổi trên trời/đồi sáng
THEMES = {
    "vang": dict(colors={}, halo=None),
    "tim": dict(colors={"gold": "plum", "gold_grad": "violet", "gold_soft": "lilac_grad", "neon": "neon_pink"}, halo=True,
                # tầng giữa (ngực, thường áo tối): tím đậm + quầng trắng bị đục → TÍM SÁNG + giữ quầng tối
                colors_mid={"gold": "violet_bright", "gold_grad": "lilac_bright", "gold_soft": "lilac_bright"}),
}
PAL["violet_bright"] = "#B98AFF"
PAL["lilac_bright"] = ["#B98AFF", "#E3CCFF"]
THEME = "vang"


def resolve_lines(m):
    pre = PRESETS.get(m.get("style", ""), {})
    raw = m.get("lines") or []
    lines = []
    for i, ln in enumerate(raw):
        base = dict(pre.get("lines", [{}])[min(i, len(pre.get("lines", [{}])) - 1)]) if pre.get("lines") else {}
        if isinstance(ln, str):
            ln = {"text": ln}
        base.update(ln)
        base.setdefault("font", "light")
        base.setdefault("color", "white")
        th = THEMES[THEME]
        mid = float(m.get("y", pre.get("y", 0.5))) >= TOP_TIER
        if mid and isinstance(base["color"], str) and base["color"] in th.get("colors_mid", {}):
            base["color"] = th["colors_mid"][base["color"]]
        elif isinstance(base["color"], str) and base["color"] in th["colors"]:
            base["color"] = th["colors"][base["color"]]
            if th["halo"] is not None and base.get("halo") == "dark":
                base["halo"] = th["halo"]
        if base.get("caps"):
            base["text"] = base["text"].upper()
            for sw in base.get("swap", []):
                sw["text"] = sw["text"].upper()
        lines.append(base)
    return lines, pre


def fit_fs(ln):
    if "fs" in ln:
        return float(ln["fs"])
    wf = float(ln.get("w", 0.5))
    return min(420.0, wf * REFW / max(1e-6, text_w(ln["text"], ln["font"], 1.0)))


def layout(m, lines, pre):
    y = float(m.get("y", pre.get("y", 0.5))) * H
    x = float(m.get("x", pre.get("x", 0.5))) * W
    gap_k = float(m.get("gap", pre.get("gap", 0.08)))
    boxes = []
    for ln in lines:
        fs = fit_fs(ln)
        ln["fs"] = fs
        t, b = vbox(ln["text"], ln["font"], fs)
        boxes.append((t, b, em_px(ln["font"], fs)))
    total = sum(b - t for t, b, _ in boxes)
    gaps = [gap_k * max(boxes[i][2], boxes[i + 1][2]) for i in range(len(boxes) - 1)]   # theo dòng TO
    cur = y - (total + sum(gaps)) / 2
    for i, (ln, (t, b, e)) in enumerate(zip(lines, boxes)):
        base = cur - t
        ln["baseline"] = base
        ln["x"] = x + float(ln.get("dx", 0)) * W
        ln["y_an2"] = base + fm(ln["font"])["desc"] * e
        ln["em"] = e
        ln["tw"] = text_w(ln["text"], ln["font"], ln["fs"])
        cur += (b - t) + (gaps[i] if i < len(gaps) else 0)


# ───────────────────────── chữ sau người: đo độ che + tự dời ─────────────────────────
class MaskReader:
    """đọc khung mask (trắng = người) ở hệ tọa độ ASS W×H."""

    def __init__(self, path):
        self.path, self.cache = str(path), {}

    def at(self, t):
        import numpy as np
        k = round(t, 2)
        if k not in self.cache:
            b = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{max(0, t):.3f}", "-i", self.path, "-frames:v", "1",
                                "-vf", f"scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True).stdout
            self.cache[k] = np.frombuffer(b, np.uint8).reshape(H, W) > 127 if len(b) == W * H else None
        return self.cache[k]


MASK = None
PLACE_LOG = []
MAX_COVER = 0.5            # luật chủ kênh: mỗi chữ cái bị che tối đa 1/2
MAX_TOUCHED = 2            # … và tối đa 2 chữ cái bị chạm


def letter_boxes(ln):
    m, e = fm(ln["font"]), ln["em"]
    k = e / m["upem"] * FONTS[ln["font"]][4] / 100
    x = ln["x"] - ln["tw"] / 2
    top, bot = ln["baseline"] - m["cap"] * e, ln["baseline"]
    out = []
    for c in ln["text"]:
        a = m["adv"].get(ord(c)) or m["adv"].get(ord(unicodedata.normalize("NFD", c)[0]), m["upem"] * 0.55)
        if not c.isspace():
            out.append((c, x + a * k * 0.08, top, x + a * k * 0.92, bot))
        x += a * k
    return out


def cover_stats(lines, frames):
    worst, touched = 0.0, 0
    for ln in lines:
        for c, x0, y0, x1, y1 in letter_boxes(ln):
            x0, x1 = max(0, int(x0)), min(W, int(x1))
            y0, y1 = max(0, int(y0)), min(H, int(y1))
            if x1 <= x0 or y1 <= y0:
                continue
            cv = max(float(f[y0:y1, x0:x1].mean()) for f in frames)
            worst = max(worst, cv)
            touched += cv > 0.08
    return worst, touched


def cover_score(lines, frames):
    """chấm chỗ "ÍT CHE NHẤT" cho cảnh cận (MẪU CHUẨN 2026-10-07): (số chữ cái bị che quá nửa, tổng độ che).
    worst thì gần như luôn 100% ở cảnh cận nên không phân biệt được chỗ tốt/xấu."""
    hidden, total = 0, 0.0
    for ln in lines:
        for c, x0, y0, x1, y1 in letter_boxes(ln):
            x0, x1 = max(0, int(x0)), min(W, int(x1))
            y0, y1 = max(0, int(y0)), min(H, int(y1))
            if x1 <= x0 or y1 <= y0:
                continue
            cv = max(float(f[y0:y1, x0:x1].mean()) for f in frames)
            hidden += cv > 0.5
            total += cv
    return hidden, round(total, 1)


FACE_CACHE = {}


def face_box(t):
    """khung MẶT (x0, y0, x1, y1, tọa độ ASS) suy từ mask người: đỉnh đầu → xuống tới chỗ bề ngang tăng vọt (vai).
    Không dùng máy dò mặt (hay trượt khi đeo kính râm). Không có người → None."""
    import numpy as np
    k = round(t, 1)
    if k in FACE_CACHE:
        return FACE_CACHE[k]
    f = MASK.at(k) if MASK is not None else None
    box = None
    if f is not None and f.any():
        rows = np.flatnonzero(f.any(1))
        top = rows[0]
        head_w, head_c, bot = 0, None, None
        for r in range(top, min(H, top + int(0.45 * H))):
            cols = np.flatnonzero(f[r])
            if len(cols) == 0:
                continue
            w = cols[-1] - cols[0]
            if r - top > 0.02 * H and head_w and w > 1.6 * head_w:
                bot = r                                   # tới vai
                break
            # chỉ đo bề ngang ĐẦU từ đỉnh tóc tới ngang tai: cảnh cận áo tối tràn mép khung thì thân rộng dần,
            # không có "bước nhảy vai" → nếu đo tiếp, khung mặt phình thành cả người (Short THỬ THÁCH 90 NGÀY)
            if w >= head_w and r - top < 0.16 * H:
                head_w, head_c = w, (cols[0] + cols[-1]) / 2
        if head_w > 0.02 * W:
            bot = bot if bot is not None else top + 1.35 * head_w
            bot = min(bot, top + 1.45 * head_w)
            box = (head_c - head_w * 0.55, top, head_c + head_w * 0.55, bot)
    FACE_CACHE[k] = box
    return box


FACES_CACHE = {}
MOMENT_BOXES = []          # (t0, t1, bbox) mọi chữ nhấn / badge / chữ rải đã đặt → sub nhỏ né (xóa đầu mỗi build)


def face_boxes(t):
    """MỌI khuôn mặt trong khung (2 người trở lên — NGAY 2: trước đây chỉ bắt đầu cao nhất, mặt người bên cạnh bị
    sub đè). Cách làm: hồ sơ "đỉnh người" theo cột (hàng đầu tiên có người ở mỗi cột) → lấy đỉnh thấp nhất làm 1 đầu,
    nở sang 2 bên tới khi đường viền tụt quá ~7% khung (hết đầu) → che cột đó đi, tìm đầu tiếp theo (tối đa 4).
    Bỏ "đầu giả" là vai/tay: rộng > 35% khung hoặc thấp hơn đầu cao nhất > 28% khung."""
    import numpy as np
    k = round(t, 1)
    if k in FACES_CACHE:
        return FACES_CACHE[k]
    f = MASK.at(k) if MASK is not None else None
    out = []
    if f is not None and f.any():
        has = f.any(0)
        top = np.where(has, f.argmax(0), H).astype(float)
        win = max(3, int(W * 0.015))
        top = np.convolve(np.pad(top, win, mode="edge"), np.ones(2 * win + 1) / (2 * win + 1), mode="same")[win:-win]
        work = top.copy()
        claimed = np.zeros(W, bool)
        first = None
        for _ in range(6):
            c = int(np.argmin(work))
            t0 = work[c]
            if t0 >= 0.9 * H or (first is not None and t0 > first + 0.2 * H):
                break
            lim = t0 + 0.07 * H
            l = c
            while l > 0 and work[l - 1] < lim:
                l -= 1
            r = c
            while r < W - 1 and work[r + 1] < lim:
                r += 1
            w = (r - l) * 1.15
            pad = int(max(w * 0.35, W * 0.02))
            # ĐẦU THẬT = đỉnh nổi lên: cả 2 bên (theo hồ sơ GỐC) phải tụt xuống ≥ 7% khung, hoặc chạm mép khung.
            # Vai / tay / cửa xe sát cạnh 1 đầu đã tìm → phía đó cao (đầu kia) → loại.
            # Người ngồi sát bên (NGAY 2): 1 bên kề đầu đã tìm → chấp nhận nếu đỉnh không thấp hơn đầu cao nhất quá 14% khung
            near = first is not None and t0 <= first + 0.14 * H
            ok_l = l == 0 or top[l - 1] >= lim or (near and claimed[max(0, l - 1)])
            ok_r = r == W - 1 or top[r + 1] >= lim or (near and claimed[min(W - 1, r + 1)])
            real = ok_l and ok_r
            work[max(0, l - pad):min(W, r + pad + 1)] = H
            claimed[max(0, l - pad):min(W, r + pad + 1)] = True
            if not real or w < 0.03 * W or w > 0.6 * W:      # selfie cận: đầu chiếm tới ~45% khung
                continue
            first = t0 if first is None else first
            cx = (l + r) / 2
            out.append((cx - w * 0.6, t0, cx + w * 0.6, t0 + 1.4 * w))
    # Bỏ "đầu giả" nhỏ là vai/tay khi người đứng xa (MẪU CHUẨN 2026-10-07: Short Hook Demo 9–10s, 32s — khung 0.07–0.13
    # rộng ở y 0.44–0.52 ngay dưới đầu thật → sub ở ngực bị đẩy xuống chân). Đầu thật của người thứ 2 thường cỡ tương đương.
    if len(out) > 1:
        main = max(out, key=lambda b: b[2] - b[0])
        mw_, mh_ = main[2] - main[0], main[3] - main[1]
        def _shoulder(b):
            gap = max(main[0] - b[2], b[0] - main[2])            # khoảng trống ngang tới đầu chính
            return b[2] - b[0] < 0.8 * mw_ and gap < 0.03 * W and b[1] > main[1] + 0.7 * mh_
        # vai/tay = hẹp hơn + SÁT cạnh đầu chính + thấp dưới đầu chính. Người thứ 2 (NGAY 2) cách ra ≥ 6% khung → giữ.
        out = [b for b in out if b is main or not _shoulder(b)]
    if not out and face_box(t):
        out = [face_box(t)]
    head_top = min((b[1] for b in out), default=None)
    # GỘP mặt dò THẬT trên khung hình (OpenCV) — mask đoán sai cằm khi cổ áo khoác rộng (Ngày 3 short 2026-10-03:
    # engine đoán cằm y 0.58, cằm thật 0.60–0.68 → 48 đoạn chữ đè cằm/miệng mà check vẫn báo OK). Kính râm làm máy
    # dò trượt → khi đó vẫn còn khung từ mask.
    for cb in cv_faces(k):
        if head_top is not None and cb[1] > head_top + 0.25 * H:
            continue                     # "mặt" thấp hơn đỉnh đầu quá 25% khung = nhận nhầm quần/áo (Short Hook Demo 10s)
        if f is not None and f.any():    # "mặt" không nằm trên người (đồi, biển hiệu phía sau — Short Hook Demo 4.5s) → bỏ
            cy_, cx_ = int(min(f.shape[0] - 1, max(0, (cb[1] + cb[3]) / 2))), int(min(f.shape[1] - 1, max(0, (cb[0] + cb[2]) / 2)))
            if not f[cy_, cx_]:
                continue
        hit = [i for i, b in enumerate(out) if overlap_frac(b, cb) > 0 or overlap_frac(cb, b) > 0]
        if hit:
            i = hit[0]
            b = out[i]
            out[i] = (min(b[0], cb[0]), min(b[1], cb[1]), max(b[2], cb[2]), max(b[3], cb[3]))
        else:
            out.append(cb)
    FACES_CACHE[k] = out
    return out


SRC_VIDEO = None
CV_CACHE = {}


def cv_faces(t):
    """mặt dò bằng OpenCV (Haar, mặt thẳng) trên khung GỐC ở giây t → [(x0,y0,x1,y1)] tọa độ ASS, nới xuống cằm + lên trán.
    Không có OpenCV / không có video → []"""
    k = round(t, 1)
    if k in CV_CACHE:
        return CV_CACHE[k]
    out = []
    try:
        import cv2
        import numpy as np
        w2, h2 = W // 2, H // 2
        b = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{max(0, k):.2f}", "-i", str(SRC_VIDEO), "-frames:v", "1",
                            "-vf", f"scale={w2}:{h2}", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                           capture_output=True).stdout if SRC_VIDEO else b""
        if len(b) == w2 * h2:
            g = cv2.equalizeHist(np.frombuffer(b, np.uint8).reshape(h2, w2))
            cas = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
            det = [tuple(2 * v for v in d) for d in cas.detectMultiScale(g, 1.1, 6, minSize=(w2 // 12, w2 // 12))]
            big = max((d[2] * d[3] for d in det), default=0)
            for x, y, w, h in det:
                if w * h < 0.4 * big:            # khung nhỏ cạnh mặt chính = nhận nhầm tay / áo (Ngày 3 short @153s)
                    continue
                # khung vuông Haar đã gần tới cằm → nới nhẹ 8% (22% cũ làm "mặt" xuống tận cổ → chữ dưới cằm bị báo nhầm)
                out.append((x - 0.04 * w, y - 0.08 * h, x + 1.04 * w, y + 1.08 * h))
    except Exception:
        out = []
    CV_CACHE[k] = out
    return out


def overlap_frac(a, b):
    """phần diện tích của khung b (mặt) bị khung a (chữ) phủ"""
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    return ix * iy / max(1, (b[2] - b[0]) * (b[3] - b[1]))


FACE_MAX = 0.03            # chữ phía TRƯỚC người gần như KHÔNG được chạm mặt (12% cũ = chữ nằm trên cằm/miệng vẫn "đạt")

# VÙNG AN TOÀN (chủ kênh chốt 2026-10-02, nới mép trên 2026-10-07 theo MẪU CHUẨN Short Hook Demo_editorial_vang):
# khung dọc 9:16 → mọi sub + chữ nhấn + badge nằm trong x 8–92%, y 15–75%. Mép trên 0.15 (không phải 0.25): chữ khóa của
# mẫu nằm NGAY TRÊN ĐẦU ở y ~0.17–0.25; ô cũ 0.25 đẩy chữ xuống đè đầu → engine thu nhỏ ×0.5 + dạt trái (rối mắt,
# Ngày 4). Dải 0–0.12 vẫn trống cho thanh "Đang theo dõi / Dành cho bạn" của TikTok. Khung ngang: tắt (None).
SAFE = dict(x0=0.08, x1=0.92, y0=0.15, y1=0.75)
SAFE_ON = True


def safe_px():
    return (SAFE["x0"] * W, SAFE["y0"] * H, SAFE["x1"] * W, SAFE["y1"] * H) if SAFE_ON else None


def shift_lines(lines, dx, dy):
    for ln in lines:
        ln["x"] += dx
        ln["baseline"] += dy
        ln["y_an2"] += dy


def clamp_safe(m, lines, pre, back=False, frames=None):
    """kéo cả khối chữ vào vùng an toàn 3:4; rộng quá thì thu cỡ. Chữ sau đầu: thu thêm nếu bị che quá luật."""
    sp = safe_px()
    bb = text_bbox(lines)
    if not sp or not bb:
        return
    x0s, y0s, x1s, y1s = sp
    label = f"{m.get('style')} @ {float(m['start']):.1f}s '{' / '.join(l['text'] for l in lines)}'"
    moved = []
    for sc_try in range(8):
        bb = text_bbox(lines)
        bw, bh = bb[2] - bb[0], bb[3] - bb[1]
        k = min(1.0, (x1s - x0s) / max(1, bw), (y1s - y0s) / max(1, bh))
        if k < 0.999:                                   # khối rộng/cao hơn vùng → thu cỡ, giữ tâm
            cx, cy = (bb[0] + bb[2]) / 2 / W, (bb[1] + bb[3]) / 2 / H
            for ln in lines:
                ln["fs"] *= k * 0.98
                ln.pop("w", None)
            layout(dict(m, x=cx, y=cy), lines, pre)
            moved.append(f"cỡ ×{k * 0.98:.2f}")
            bb = text_bbox(lines)
        dx = max(0, x0s - bb[0]) - max(0, bb[2] - x1s)
        dy = max(0, y0s - bb[1]) - max(0, bb[3] - y1s)
        if abs(dx) > 0.5 or abs(dy) > 0.5:
            shift_lines(lines, dx, dy)
            moved.append(f"dời {'xuống' if dy > 0 else 'lên'} {abs(dy) / H:.2f}" if abs(dy) > 0.5 else f"dời ngang {dx / W:+.2f}")
        break
    if back and frames:
        wv, tv = cover_stats(lines, frames)
        if wv > MAX_COVER or tv > MAX_TOUCHED:
            # bị kéo vào đầu quá luật → tìm chỗ khác TRONG vùng: dời ngang / xuống / thu nhỏ, chọn gần chỗ cũ nhất
            bb = text_bbox(lines)
            cx0, cy0 = (bb[0] + bb[2]) / 2 / W, (bb[1] + bb[3]) / 2 / H
            base = [ln["fs"] for ln in lines]
            best = alt = None
            # MẪU CHUẨN (2026-10-07): giữ giữa khung, ưu tiên dời LÊN trên đầu, không thu dưới ×0.8 (cũ: ×0.5 + dạt trái)
            for sc, dxs in ((1.0, (0,)), (0.9, (0,)), (0.8, (0,)), (1.0, (-0.12, 0.12)), (0.9, (-0.12, 0.12))):
                for dx in dxs:
                    for dy in sorted([v * 0.01 for v in range(-15, 30)], key=lambda v: (abs(v), v > 0)):
                        for ln, f0 in zip(lines, base):
                            ln["fs"] = f0 * sc
                        layout(dict(m, x=cx0 + dx, y=cy0 + dy), lines, pre)
                        if not inside_safe(lines):
                            continue
                        wv2, tv2 = cover_stats(lines, frames)
                        if dx == 0 and sc >= 0.9:
                            key_ = cover_score(lines, frames) + (cy0 + dy,)
                            if alt is None or key_ < alt[0]:
                                alt = (key_, sc, cx0, cy0 + dy, wv2, tv2)
                        if wv2 <= MAX_COVER and tv2 <= MAX_TOUCHED:
                            cost = abs(dy) * 2 + abs(dx) * 3 + (1 - sc) * 1.5 + (0 if tv2 else 0.05)
                            if best is None or cost < best[0]:
                                best = (cost, sc, cx0 + dx, cy0 + dy)
                            break
                if best:
                    break
            if best:
                _, sc, x_, y_ = best
                for ln, f0 in zip(lines, base):
                    ln["fs"] = f0 * sc
                layout(dict(m, x=x_, y=y_), lines, pre)
                moved.append(f"đầu che quá luật → dời x {x_:.2f} y {y_:.2f}, cỡ ×{sc:.1f}")
            elif alt is not None:
                _, sc, x_, y_, wv2, tv2 = alt          # cảnh cận mặt: chỗ ÍT CHE NHẤT, giữa khung (như MẪU CHUẨN)
                for ln, f0 in zip(lines, base):
                    ln["fs"] = f0 * sc
                layout(dict(m, x=x_, y=y_), lines, pre)
                moved.append(f"cảnh cận, không chỗ đúng luật → ÍT CHE NHẤT y {y_:.2f}, cỡ ×{sc:.1f} — mở ảnh snap xem còn đọc được không")
            else:
                for ln, f0 in zip(lines, base):
                    ln["fs"] = f0
                layout(dict(m, x=cx0, y=cy0), lines, pre)
                moved.append("!! KHÔNG ĐẠT: trong vùng an toàn không có chỗ sau đầu đúng luật — đặt \"behind\": false hoặc đổi khuôn")
    bb = text_bbox(lines)
    m["x"], m["y"] = (bb[0] + bb[2]) / 2 / W, (bb[1] + bb[3]) / 2 / H
    if moved:
        msg = ", ".join(dict.fromkeys(moved))
        if back and frames:
            wv, tv = cover_stats(lines, frames)
            msg += f" (che {wv:.0%}, {tv} chữ cái chạm)"
        PLACE_LOG.append(f"{label}: VÙNG 3:4 → {msg}")


def inside_safe(lines, tol=2.0, reserve=0.0):
    """khối chữ nằm trong vùng 3:4; reserve = chừa thêm dải dưới cùng (px) cho sub nhỏ chạy bên dưới"""
    sp, bb = safe_px(), text_bbox(lines)
    if not sp or not bb:
        return True
    return bb[0] >= sp[0] - tol and bb[1] >= sp[1] - tol and bb[2] <= sp[2] + tol and bb[3] <= sp[3] - reserve + tol


SOLO_STYLES = {"neon", "strike"}           # khuôn ③ dạng chữ: đứng một mình, ẩn sub (như mẫu: VIRAL, KHÔNG VIẾT)
SOLO_TYPES = {"pills", "scatter", "bubble"}  # khuôn ③ dạng đồ họa: ẩn sub


def hides_sub(m, pre=None):
    """MẪU CHUẨN (chủ kênh 2026-10-07, Short Hook Demo_editorial_vang): khoảnh khắc này có ẩn sub nhỏ không?
    ① chữ khóa tầng trên (trên/sau đầu) → sub vẫn chạy bên dưới · ② cụm giữa (ngực) → ẩn · ③ neon/vạch gạch/badge → ẩn.
    Plan ghi "hide_subs": true/false thì theo plan."""
    if m.get("hide_subs") is not None:
        return bool(m["hide_subs"])
    kind = m.get("type", "text")
    if kind != "text":
        return kind in SOLO_TYPES
    if m.get("style") in SOLO_STYLES:
        return True
    pre = pre if pre is not None else PRESETS.get(m.get("style"), {})
    y0 = m.get("_y_plan", m.get("y", pre.get("y", 0.5)))
    return float(y0) >= TOP_TIER


def sub_reserve(m):
    """chữ nhấn phía trước người mà sub vẫn chạy → chừa ~1.6 dòng sub ở mép dưới vùng (NGAY 2: cụm né mặt xuống
    đáy vùng, sub hết chỗ, đè lên nhau)"""
    return 0.0 if hides_sub(m) else float(SUB["fs"]) * 1.6


def clamp_pt(cx, cy, hw, hh):
    """giữ tâm (cx, cy) của 1 hộp nửa-rộng hw, nửa-cao hh trong vùng an toàn"""
    sp = safe_px()
    if not sp:
        return cx, cy
    x0s, y0s, x1s, y1s = sp
    cx = min(max(cx, x0s + hw), x1s - hw) if x1s - x0s > 2 * hw else (x0s + x1s) / 2
    cy = min(max(cy, y0s + hh), y1s - hh) if y1s - y0s > 2 * hh else (y0s + y1s) / 2
    return cx, cy


def text_bbox(lines):
    bs = [b for ln in lines for b in letter_boxes(ln)]
    if not bs:
        return None
    pad = 0.15 * max(ln["em"] for ln in lines)
    return (min(b[1] for b in bs) - pad, min(b[2] for b in bs) - pad, max(b[3] for b in bs) + pad, max(b[4] for b in bs) + pad)


def avoid_face(m, lines, pre, times):
    """chữ phía TRƯỚC người (không behind) đè lên mặt → dời xuống/lên gần nhất cho hết che; không được → báo."""
    faces = [b for t in times for b in face_boxes(t)]          # mọi khuôn mặt (2 người trở lên)
    if not faces:
        return
    def worst():
        bb = text_bbox(lines)
        return max(overlap_frac(bb, fb) for fb in faces) if bb else 0
    w0 = worst()
    if w0 <= FACE_MAX and (not SAFE_ON or inside_safe(lines, reserve=sub_reserve(m))):
        return
    y0 = float(m.get("y", pre.get("y", 0.5)))
    label = f"{m.get('style')} @ {float(m['start']):.1f}s '{' / '.join(l['text'] for l in lines)}'"
    for dy in sorted({round(v * 0.01, 2) for v in range(-40, 41)}, key=abs):
        y = y0 + dy
        if not 0.10 <= y <= 0.82:
            continue
        layout(dict(m, y=y), lines, pre)
        if SAFE_ON and not inside_safe(lines, reserve=sub_reserve(m)):        # chỉ chọn chỗ nằm trong vùng an toàn 3:4
            continue
        if worst() <= FACE_MAX:
            m["y"] = y
            PLACE_LOG.append(f"{label}: CHE MẶT {w0:.0%} → TỰ DỜI y {y0:.2f}→{y:.2f}")
            return
    # chỉ dời dọc không được (VD 2 mặt chiếm gần hết vùng 3:4) → thử dời ngang + thu nhỏ, chọn gần chỗ cũ nhất
    x0 = float(m.get("x", pre.get("x", 0.5)))
    base = [ln["fs"] for ln in lines]
    best = None
    for sc in (1.0, 0.85, 0.7, 0.6):
        for dx in (0, -0.14, 0.14, -0.24, 0.24):
            for dy in sorted({round(v * 0.01, 2) for v in range(-40, 41)}, key=abs):
                for ln, f0 in zip(lines, base):
                    ln["fs"] = f0 * sc
                layout(dict(m, x=x0 + dx, y=y0 + dy), lines, pre)
                if SAFE_ON and not inside_safe(lines, reserve=sub_reserve(m)):
                    continue
                if worst() <= FACE_MAX:
                    cost = abs(dy) * 1.5 + abs(dx) + (1 - sc) * 2
                    if best is None or cost < best[0]:
                        best = (cost, sc, x0 + dx, y0 + dy)
                    break
        if best and best[1] == sc:
            break
    if best:
        _, sc, x_, y_ = best
        for ln, f0 in zip(lines, base):
            ln["fs"] = f0 * sc
        layout(dict(m, x=x_, y=y_), lines, pre)
        m["x"], m["y"] = x_, y_
        PLACE_LOG.append(f"{label}: CHE MẶT {w0:.0%} → TỰ DỜI x {x0:.2f}→{x_:.2f}, y {y0:.2f}→{y_:.2f}, cỡ ×{sc:.2f}")
        return
    for ln, f0 in zip(lines, base):
        ln["fs"] = f0
    layout(dict(m, y=y0), lines, pre)
    PLACE_LOG.append(f"{label}: KHÔNG ĐẠT (che mặt {w0:.0%}) — đổi x/y/cỡ bằng tay")


def place_behind(m, lines, pre, times):
    """đúng luật che chữ; vi phạm → thử dời y / x / thu nhỏ, chọn phương án gần bản gốc nhất."""
    frames = [f for f in (MASK.at(t) for t in times) if f is not None]
    if not frames:
        return
    y0 = float(m.get("y", pre.get("y", 0.5)))
    x0 = float(m.get("x", pre.get("x", 0.5)))
    base_fs = [ln["fs"] for ln in lines]
    worst, touched = cover_stats(lines, frames)
    label = f"{m.get('style')} @ {float(m['start']):.1f}s '{' / '.join(l['text'] for l in lines)}'"
    if m.get("auto_place") is False:
        PLACE_LOG.append(f"{label}: che tối đa {worst:.0%}, {touched} chữ cái chạm — OK (auto_place tắt)")
        return
    if worst <= MAX_COVER and touched <= MAX_TOUCHED:
        if touched == 0 and m.get("sink", True):
            # CHỮ PHẢI CHÌM SAU ĐẦU (chủ kênh 2026-09-30: "chữ nhấn nào chưa ở sau đầu thì hạ xuống, tránh chữ quá cao"):
            # chữ lơ lửng trên trời → hạ dần tới khi đầu che 25–50% ở 1–2 chữ cái
            cand = None
            for k in range(1, 26):
                y = y0 + 0.01 * k
                if y > 0.45:
                    break
                layout(dict(m, y=y), lines, pre)
                wv, tv = cover_stats(lines, frames)
                if wv > MAX_COVER or tv > MAX_TOUCHED:
                    break
                if tv >= 1:
                    cand = (y, wv, tv)
                    if wv >= 0.25:
                        break
            if cand:
                layout(dict(m, y=cand[0]), lines, pre)
                m["y"] = cand[0]
                PLACE_LOG.append(f"{label}: lơ lửng (0 chữ chạm) → HẠ SAU ĐẦU y {y0:.2f}→{cand[0]:.2f} "
                                 f"(che {cand[1]:.0%}, {cand[2]} chữ cái chạm)")
                return
            layout(dict(m, y=y0), lines, pre)
        PLACE_LOG.append(f"{label}: che tối đa {worst:.0%}, {touched} chữ cái chạm — OK")
        return
    best = alt = None
    # MẪU CHUẨN (2026-10-07): chữ khóa GIỮ GIỮA KHUNG và gần đủ cỡ — ưu tiên dời LÊN trên đầu (như mẫu), không dạt
    # ngang, không thu dưới ×0.8. Chỉ khi giữa khung hết chỗ mới thử lệch ngang nhẹ.
    for sc, dxs in ((1.0, (0,)), (0.9, (0,)), (0.8, (0,)), (1.0, (-0.14, 0.14)), (0.9, (-0.14, 0.14))):
        for dx in dxs:
            for dy in sorted({round(v * 0.01, 2) for v in range(-18, 13)}, key=lambda v: (abs(v), v > 0)):
                y = y0 + dy
                if not (SAFE["y0"] if SAFE_ON else 0.14) <= y <= 0.62:   # không đẩy chữ lên quá cao (vùng an toàn 3:4)
                    continue
                for ln, f0 in zip(lines, base_fs):
                    ln["fs"] = f0 * sc
                    ln.pop("w", None)
                layout(dict(m, y=y, x=x0 + dx), lines, pre)
                if SAFE_ON and not inside_safe(lines):        # chỉ xét chỗ nằm trong vùng an toàn (khỏi bị kéo lại)
                    continue
                wv, tv = cover_stats(lines, frames)
                if dx == 0 and sc >= 0.9:                     # phương án dự phòng: giữa khung, ÍT CHE NHẤT
                    key_ = cover_score(lines, frames) + (y,)  # ít chữ cái bị che nhất → tổng che ít nhất → càng cao càng tốt
                    if alt is None or key_ < alt[0]:
                        alt = (key_, y, x0, sc, wv, tv)
                if wv <= MAX_COVER and tv <= MAX_TOUCHED:
                    cost = abs(dy) * 2 + abs(dx) * 3 + (1 - sc) * 1.5 + (0 if tv else 0.05)   # ưu tiên còn 1 chữ chìm (chiều sâu)
                    if best is None or cost < best[0]:
                        best = (cost, y, x0 + dx, sc, wv, tv)
        if best:
            break
    if best is None and alt is not None:
        # cảnh cận mặt (đầu chiếm cả phần trên khung): không chỗ nào đúng luật → như MẪU CHUẨN ("lời khuyên / tốt nhất"):
        # đặt ở chỗ ÍT CHE NHẤT, giữa khung, gần đủ cỡ — dòng trên đọc rõ, dòng dưới chìm một phần sau đầu
        _, y, x, sc, wv, tv = alt
        for ln, f0 in zip(lines, base_fs):
            ln["fs"] = f0 * sc
        layout(dict(m, y=y, x=x), lines, pre)
        m["y"] = y
        PLACE_LOG.append(f"{label}: cảnh cận, không chỗ đúng luật → ÍT CHE NHẤT y {y0:.2f}→{y:.2f}, cỡ ×{sc:.1f} "
                         f"(che {wv:.0%}, {tv} chữ cái chạm) — mở ảnh snap xem chữ còn đọc được không")
        return
    if best:
        _, y, x, sc, wv, tv = best
        for ln, f0 in zip(lines, base_fs):
            ln["fs"] = f0 * sc
        layout(dict(m, y=y, x=x), lines, pre)
        PLACE_LOG.append(f"{label}: che {worst:.0%}/{touched} chữ → TỰ DỜI y {y0:.2f}→{y:.2f}, x {x0:.2f}→{x:.2f}, "
                         f"cỡ ×{sc:.1f} (che {wv:.0%}, {tv} chữ cái chạm)")
    else:
        for ln, f0 in zip(lines, base_fs):
            ln["fs"] = f0
        layout(m, lines, pre)
        PLACE_LOG.append(f"{label}: !! KHÔNG ĐẠT (che {worst:.0%}, {touched} chữ cái) — rút chữ, tách dòng, "
                         f"hoặc đặt \"behind\": false")


def emit_text_line(A, ln, t0, t1, word_times, *, back, enter, exit_s, drift, base_layer, e_in=ENTER_S):
    """1 dòng chữ: bóng mềm + (glow) + fill (đặc hoặc gradient bằng các dải \\clip)."""
    key = ln["font"]
    name, b, i, _, cond = FONTS[key]
    fs, x, y = ln["fs"], ln["x"], ln["y_an2"]
    e = ln["em"]
    words = ln["text"].split(" ")
    if len(word_times) != len(words):
        word_times = [t0] * len(words)
    dur = t1 - t0
    xa, xb = ms(max(0, dur - exit_s)), ms(dur)
    if exit_s <= 0:
        xa = xb
    # scale: pop + drift chậm (chữ "trôi" cùng máy quay)
    s1 = 100 * (1 + drift)
    if enter == "pop":
        sc = (rf"\fscx{cond * 0.84:.1f}\fscy84\t(0,260,0.5,\fscx{cond}\fscy100)"
              rf"\t(260,{ms(dur)},\fscx{cond * s1 / 100:.1f}\fscy{s1:.1f})")
    else:
        sc = rf"\fscx{cond}\fscy100\t(0,{ms(dur)},\fscx{cond * s1 / 100:.1f}\fscy{s1:.1f})"
    pos = rf"\move({x:.0f},{y + 0.12 * e:.0f},{x:.0f},{y:.0f},0,300)" if enter == "rise" else rf"\pos({x:.0f},{y:.0f})"
    head = rf"\an2{pos}\fn{name}\b{b}\i{i}\fs{fs:.1f}{sc}"

    def body(vis, base_blur, exit_blur=10):
        out = ""
        for k, (wd, wt) in enumerate(zip(words, word_times)):
            o = ms(max(0.0, wt - t0))
            txt = esc(wd) + (" " if k < len(words) - 1 else "")
            out += "{" + span_tags(o, vis, base_blur, enter, xa, xb, exit_blur, e_in) + "}" + txt
        return out

    p = paint(ln["color"])
    stops = p["stops"]
    fx = ln.get("fill")                      # None | "liquid" | "invert"
    if fx not in (None, "liquid", "invert"):
        die(f"fill không hợp lệ: {fx}")
    if ln.get("halo"):
        # quầng mềm sau chữ (không phải viền/hộp): True = trắng (chữ TỐI trên nền rối) ·
        # "dark" = tối (chữ SÁNG nét mảnh — vàng/kem — trên trời trắng)
        hc, ha = ("&H000000&", "&HA4&") if ln["halo"] == "dark" else ("&HFFFFFF&", "&H9C&")
        A.add(base_layer, t0, t1, "{" + head + rf"\bord{0.10 * e:.1f}\shad0\1c{hc}\3c{hc}" + "}"
              + body(ha, 0.28 * e, 20), back)
    ex3 = ln.get("extrude")                  # chữ KHỐI 3D: {"depth": 0.07, "colors": ["#A86A00", "#4A2E00"]} (theo em)
    if ex3:
        ex3 = ex3 if isinstance(ex3, dict) else {}
        dep = float(ex3.get("depth", 0.07)) * e
        ec = ex3.get("colors", ["#A86A00", "#4A2E00"])
        n = max(4, int(dep / 2))
        for k in range(n, 0, -1):            # lớp sâu nhất vẽ trước, màu tối dần về phía sau
            off = dep * k / n
            hk = head.replace(rf"\pos({x:.0f},{y:.0f})", rf"\pos({x + off * 0.6:.0f},{y + off:.0f})")
            A.add(base_layer + 1, t0, t1, "{" + hk + rf"\bord0\shad0\1c{col(mix(ec[0], ec[1], k / n))}" + "}"
                  + body("&H00&", 0.6), back)
    if ln.get("shadow", True):
        # bóng GỌN của mẫu: lệch chéo phải-dưới ~4% em, nhòe rất ít, đậm ~55% — tạo khối, không lan
        dx_, dy_ = SHADOW_OFF[0] * e, SHADOW_OFF[1] * e
        if ex3:
            dx_, dy_ = dx_ + dep * 0.6, dy_ + dep
        sh_pos = rf"\pos({x + dx_:.0f},{y + dy_:.0f})"
        sh_head = (head.replace(rf"\pos({x:.0f},{y:.0f})", sh_pos) if enter != "rise" else
                   head.replace(rf"\move({x:.0f},{y + 0.12 * e:.0f},{x:.0f},{y:.0f}",
                                rf"\move({x + dx_:.0f},{y + 0.12 * e + dy_:.0f},{x + dx_:.0f},{y + dy_:.0f}"))
        A.add(base_layer, t0, t1, "{" + sh_head + r"\bord0\shad0\1c&H000000&" + "}"
              + body(SHADOW_ALPHA, SHADOW_BLUR * e, 10), back)
    if fx == "invert":
        # ÂM BẢN: chỉ cần mặt nạ hình chữ — engine đảo màu chính cảnh phía sau qua mặt nạ này
        A.add(base_layer + 2, t0, t1, "{" + head + r"\bord0\shad0\1c&HFFFFFF&" + "}" + body("&H00&", 0.6), back, fx="inv")
        return
    fxb = "liq" if fx == "liquid" else None
    if ln.get("glow"):
        n = 10
        xl = x - ln["tw"] / 2
        for s in range(n):
            a = 0 if s == 0 else xl + ln["tw"] * s / n
            bnd = W if s == n - 1 else xl + ln["tw"] * (s + 1) / n
            c = grad_at(stops, (s + 0.5) / n)
            A.add(base_layer + 1, t0, t1, "{" + head + rf"\clip({a:.0f},0,{bnd:.0f},{H})\bord{0.05 * e:.1f}\shad0"
                  rf"\1c{col(c)}\3c{col(c)}" + "}" + body("&H70&", 0.22 * e, 20), back)
    if len(stops) == 1:
        A.add(base_layer + 2, t0, t1, "{" + head + rf"\bord0\shad0\1c{col(stops[0])}" + "}" + body("&H00&", 0.6), back, fx=fxb)
    else:
        if p["dir"] == "v":
            n = 28                               # 10 dải lộ sọc khi chữ to (4K) → 28 dải mịn
            top = ln["baseline"] - fm(key)["cap"] * e
            bot = ln["baseline"]
            for s in range(n):
                a = 0 if s == 0 else top + (bot - top) * s / n
                bnd = H if s == n - 1 else top + (bot - top) * (s + 1) / n
                c = grad_at(stops, (s + 0.5) / n)
                A.add(base_layer + 2, t0, t1, "{" + head + rf"\clip(0,{a:.0f},{W},{bnd:.0f})\bord0\shad0\1c{col(c)}" + "}"
                      + body("&H00&", 0.6), back, fx=fxb)
        else:
            n = 14
            xl = x - ln["tw"] / 2
            for s in range(n):
                a = 0 if s == 0 else xl + ln["tw"] * s / n
                bnd = W if s == n - 1 else xl + ln["tw"] * (s + 1) / n
                c = grad_at(stops, (s + 0.5) / n)
                A.add(base_layer + 2, t0, t1, "{" + head + rf"\clip({a:.0f},0,{bnd:.0f},{H})\bord0\shad0\1c{col(c)}" + "}"
                      + body("&H00&", 0.6), back, fx=fxb)


def emit_strike(A, ln, t_on, t1, back, layer, color="red"):
    e = ln["em"]
    bw = ln["tw"] * 1.08 + 0.1 * e
    bh = max(6, 0.085 * e)
    x0 = ln["x"] - bw / 2
    x1 = x0 + bw
    yc = ln["baseline"] - fm(ln["font"])["cap"] * e * 0.46
    y0, y1 = yc - bh / 2, yc + bh / 2
    dur = t1 - t_on
    clip0 = rf"\clip({x0:.0f},{y0 - 3:.0f},{x0:.0f},{y1 + 3:.0f})"
    tag = (rf"\an7\pos({x0:.0f},{y0:.0f})\bord0\shad0\1c{col(PAL.get(color, color))}{clip0}"
           rf"\t(0,340,0.6,\clip({x0:.0f},{y0 - 3:.0f},{x1:.0f},{y1 + 3:.0f}))"
           rf"\t({ms(max(0.35, dur - 0.32))},{ms(dur)},\clip({x1:.0f},{y0 - 3:.0f},{x1:.0f},{y1 + 3:.0f}))\p1")
    A.add(layer, t_on, t1, "{" + tag + "}" + f"m 0 0 l {bw:.0f} 0 {bw:.0f} {bh:.0f} 0 {bh:.0f}" + "{\\p0}", back)


def stadium(w, h):
    w, h = round(w), round(h)
    r = h / 2
    k = 0.5523 * r
    f = lambda v: f"{v:.0f}"
    return (f"m {f(r)} 0 l {f(w - r)} 0 b {f(w - r + k)} 0 {f(w)} {f(r - k)} {f(w)} {f(r)} "
            f"b {f(w)} {f(r + k)} {f(w - r + k)} {f(h)} {f(w - r)} {f(h)} l {f(r)} {f(h)} "
            f"b {f(r - k)} {f(h)} 0 {f(r + k)} 0 {f(r)} b 0 {f(r - k)} {f(r - k)} 0 {f(r)} 0")


# ───────────────────────── từng loại khoảnh khắc ─────────────────────────
def do_text(A, m, words, sfx, first):
    lines, pre = resolve_lines(m)
    if not lines:
        return None
    m.setdefault("_y_plan", m.get("y", pre.get("y", 0.5)))   # tầng theo plan (trước khi engine tự dời) → quyết định ẩn sub
    layout(m, lines, pre)
    back = bool(m.get("behind", pre.get("behind", False)))
    enter = m.get("enter", pre.get("enter", "blur"))
    exit_s = float(m.get("exit_s", pre.get("exit_s", EXIT_S)))
    drift = float(m.get("drift", pre.get("drift", 0.03)))
    start = float(m["start"])
    end = float(m["end"])
    ptr = None
    times_all, word_last, seqs = [], [], []
    for ln in lines:
        # thứ tự dòng = thứ tự nói; mỗi dòng có thể có "swap" (từ cuối đổi dần: because|far more → goes → into)
        seq = [dict(text=ln["text"], t=ln.get("t"), at=ln.get("at"))] + [dict(s) for s in ln.get("swap", [])]
        seqs.append(seq)
        for si, sg in enumerate(seq):
            toks = sg["text"].split(" ")
            if sg.get("at"):
                tt = [float(v) for v in sg["at"]]
            elif sg.get("t") is not None and not m.get("sync", True):
                tt = [float(sg["t"])] * len(toks)
            elif words and m.get("sync", True):
                # dò sớm 0.35s: mốc nhận giọng hay lệch vài trăm ms → từ nói ngay trước "start" vẫn khớp (không rơi sang sub)
                t_from = float(sg["t"]) if sg.get("t") is not None else start - 0.35
                tt, ptr = match_times(words, toks, t_from, end, ptr if sg.get("t") is None else None)
                if sg.get("t") is not None:
                    tt = [max(v, float(sg["t"])) for v in tt]
            else:
                tt = [float(sg["t"]) if sg.get("t") is not None else start] * len(toks)
            sg["times"] = tt
            if m.get("dedupe_sub", True):
                SHOWN.update(round(v, 2) for v in tt)
            word_last.append(tt[-1])
    if MASK is not None:
        ts_ = sorted({max(start, s["times"][-1]) + 0.1 for q in seqs for s in q} | {(start + end) / 2, end - 0.25})
        if back:
            place_behind(m, lines, pre, ts_)
            frames_ = [f for f in (MASK.at(t) for t in ts_) if f is not None]
            clamp_safe(m, lines, pre, back, frames_)
        else:
            clamp_safe(m, lines, pre)           # vào vùng 3:4 trước (thu cỡ nếu cần) …
            avoid_face(m, lines, pre, ts_)      # … rồi né mặt, chỉ trong vùng
    else:
        clamp_safe(m, lines, pre)
    bb_ = text_bbox(lines)
    if bb_:
        MOMENT_BOXES.append((start - 0.05, end + 0.05, bb_))     # để sub né
    for ln, seq in zip(lines, seqs):
        for si, sg in enumerate(seq):
            a = max(start, sg["times"][0])
            b = seq[si + 1]["times"][0] if si + 1 < len(seq) else float(ln.get("end", end))
            lnx = dict(ln, text=sg["text"])
            if si:
                lnx["tw"] = text_w(sg["text"], ln["font"], ln["fs"])
            last = si + 1 == len(seq)
            emit_text_line(A, lnx, a, b, [max(a, v) for v in sg["times"]], back=back, enter=enter,
                           exit_s=exit_s if last else 0.10, drift=drift, base_layer=20 if back else 40)
            times_all.append(a)
            if ln.get("strike") is not None and last:
                st = ln["strike"] if isinstance(ln["strike"], dict) else {}
                t_on = float(st.get("t", sg["times"][-1] + 0.15))
                emit_strike(A, lnx, t_on, b, back, (20 if back else 40) + 5, st.get("color", "red"))
                sfx.append((t_on, "swipe"))
    # SFX mặc định: tầng trên = whoosh nhẹ; hook đầu video = boom trầm; neon = shimmer
    kinds = m.get("sfx")
    t_first = min(times_all) if times_all else start
    if kinds is None:
        top = float(m.get("y", pre.get("y", 0.5))) < TOP_TIER
        kinds = (["whoosh_soft"] if top else []) + (["boom"] if first else []) + \
                (["shimmer"] if m.get("style") == "neon" else [])
        if not top and len(lines) > 1 and m.get("style") in ("serif_pair", "thin_caps", "gradient_serif"):
            sfx.append((min(max(times_all), end - 0.2), "air"))
    for k in kinds or []:
        sfx.append((t_first - (0.12 if k in ("whoosh_soft", "air") else 0), k))
    # BỐ CỤC 3 KHUÔN (chủ kênh chốt 2026-09-30) — tối đa 2 lớp chữ cùng lúc:
    #  ① chữ sau đầu (tầng trên) + sub nhỏ chạy bên dưới (bỏ từ trùng — SHOWN)
    #  ② cụm giữa (ngực) THAY sub → ẩn sub   ③ điểm đặc biệt (neon, vạch gạch) đứng một mình → ẩn sub
    # chủ kênh 2026-09-30: "đã nhấn chữ thì không cần sub nhỏ" → MỌI khoảnh khắc chữ nhấn đều ẩn sub
    # (kể cả chữ sau đầu); muốn giữ sub song song thì ghi "hide_subs": false
    hide = hides_sub(m, pre)             # MẪU CHUẨN 2026-10-07: ① chữ khóa trên đầu → sub vẫn chạy; ②③ → ẩn sub
    t_lo = min([start] + [v for q in seqs for s in q for v in s["times"]])
    return (t_lo - 0.02, end + 0.02) if hide else None


def do_pills(A, m, sfx):
    fs = float(m.get("fs", 48))
    ph = fs * 1.95
    border = max(3, fs * 0.11)
    end = float(m["end"])
    for i, it in enumerate(m["items"]):
        t = float(it["t"])
        cx, cy = float(it["x"]) * W, float(it["y"]) * H
        tw = text_w(it["text"], "bold", fs)
        pw = max(ph, tw + ph * 0.9)
        cx, cy = clamp_pt(cx, cy, pw / 2 + border, ph / 2 + border)   # vùng an toàn 3:4
        MOMENT_BOXES.append((t, end, (cx - pw / 2 - border, cy - ph / 2 - border, cx + pw / 2 + border, cy + ph / 2 + border)))
        fill = rf"\1c{col(PAL['pill_fill'])}\1a&H38&\3c{col(PAL['yellow'])}\bord{border:.1f}\shad0"
        # 1) chấm tròn bật ra → 2) kéo dài thành viên thuốc
        A.add(60, t, t + 0.34, "{" + rf"\an5\pos({cx:.0f},{cy:.0f}){fill}\fscx0\fscy0"
              rf"\t(0,150,0.6,\fscx100\fscy100)\t(180,340,0.7,\fscx{100 * pw / ph:.0f})\p1" + "}" + stadium(ph, ph) + "{\\p0}")
        dur = end - (t + 0.32)
        ex = rf"\t({ms(max(0, dur - EXIT_S))},{ms(dur)},\alpha&HFF&\blur8)"
        A.add(60, t + 0.32, end, "{" + rf"\an5\pos({cx:.0f},{cy:.0f}){fill}\blur0.6{ex}\p1" + "}" + stadium(pw, ph) + "{\\p0}")
        A.add(61, t + 0.30, end, "{" + rf"\an5\pos({cx:.0f},{cy + fs * 0.04:.0f})\fnInter\b1\fs{fs:.0f}\bord0\shad0"
              rf"\1c&HFFFFFF&" + span_tags(0, "&H00&", 0.5, "blur", ms(max(0, dur - EXIT_S)), ms(dur + 0.02), 8, 0.14)
              + "}" + esc(it["text"]))
        sfx.append((t, f"pill{min(i, 5)}"))      # "bloop" nghe rõ, viên sau cao hơn viên trước
    return (float(m["start"]), end) if hides_sub(m) else None   # khuôn ③: badge đứng một mình, ẩn sub


def do_scatter(A, m, sfx):
    items = m["items"]
    key = m.get("font", "serif_i")
    name, b, i, _, cond = FONTS[key]
    fs = float(m.get("fs", 64))
    for k, it in enumerate(items):
        t = float(it["t"])
        end = float(it.get("end", items[k + 1]["t"] if k + 1 < len(items) and m.get("chain", True) else m["end"]))
        cx, cy = float(it["x"]) * W, float(it["y"]) * H
        dur = end - t
        xa, xb = ms(max(0, dur - 0.14)), ms(dur)
        e = em_px(key, fs)
        cx, cy = clamp_pt(cx, cy, text_w(it["text"], key, fs) / 2, e * 0.7)   # vùng an toàn 3:4
        tw_ = text_w(it["text"], key, fs) / 2
        MOMENT_BOXES.append((t, end, (cx - tw_, cy - e * 0.7, cx + tw_, cy + e * 0.7)))
        head = rf"\an5\move({cx:.0f},{cy + 0.15 * e:.0f},{cx:.0f},{cy:.0f},0,260)\fn{name}\b{b}\i{i}\fs{fs:.0f}\fscx{cond}\bord0\shad0"
        sx, sy = SHADOW_OFF[0] * e, SHADOW_OFF[1] * e
        sh_head = (rf"\an5\move({cx + sx:.0f},{cy + 0.15 * e + sy:.0f},{cx + sx:.0f},{cy + sy:.0f},0,260)"
                   rf"\fn{name}\b{b}\i{i}\fs{fs:.0f}\fscx{cond}\bord0\shad0")
        A.add(44, t, end, "{" + sh_head + r"\1c&H000000&"
              + span_tags(0, SHADOW_ALPHA, SHADOW_BLUR * e, "blur", xa, xb, 12) + "}" + esc(it["text"]))
        A.add(45, t, end, "{" + head + rf"\1c{col(PAL.get(it.get('color', 'white'), it.get('color', '#FFFFFF')))}"
              + span_tags(0, "&H00&", 0.6, "blur", xa, xb, 10) + "}" + esc(it["text"]))
        sfx.append((t, "pop_soft"))
    return (float(m["start"]), float(m["end"])) if hides_sub(m) else None


def do_bubble(A, m, sfx):
    t, end = float(m["start"]), float(m["end"])
    fs = float(m.get("fs", 40))
    bh = fs * 1.9
    tw = text_w(m["text"], "light", fs)
    bw = tw + bh * 1.1
    cx, cy = float(m.get("x", 0.56)) * W, float(m.get("y", 0.50)) * H
    cx, cy = clamp_pt(cx, cy, bw / 2 + bh * 0.6, bh / 2)          # vùng an toàn 3:4 (chừa chỗ avatar bên trái)
    dur = end - t
    ex = rf"\t({ms(max(0, dur - EXIT_S))},{ms(dur)},\alpha&HFF&\blur8)"
    pop = r"\fscx70\fscy70\t(0,220,0.5,\fscx100\fscy100)"
    A.add(62, t, end, "{" + rf"\an5\pos({cx:.0f},{cy:.0f})\1c{col(PAL['glass'])}\1a&H60&\bord0\shad0\blur1{pop}{ex}\p1" + "}"
          + stadium(bw, bh) + "{\\p0}")
    # đuôi bong bóng (dưới trái)
    tx, ty = cx - bw / 2 + bh * 0.35, cy + bh / 2 - 4
    A.add(62, t, end, "{" + rf"\an7\pos({tx:.0f},{ty:.0f})\1c{col(PAL['glass'])}\1a&H60&\bord0\shad0\blur1{ex}\p1" + "}"
          + f"m 0 0 l {bh * 0.34:.0f} 0 l {-bh * 0.10:.0f} {bh * 0.32:.0f}" + "{\\p0}")
    A.add(63, t, end, "{" + rf"\an5\pos({cx:.0f},{cy + fs * 0.03:.0f})\fnInter Light\fs{fs:.0f}\bord0\shad0\1c&HFFFFFF&{pop}"
          + span_tags(60, "&H00&", 0.5, "blur", ms(max(0, dur - EXIT_S)), ms(dur), 8, 0.14) + "}" + esc(m["text"]))
    if not m.get("avatar"):
        r = bh * 0.52
        ax = cx - bw / 2 - r - bh * 0.25
        A.add(62, t, end, "{" + rf"\an5\pos({ax:.0f},{cy:.0f})\1c&H202020&\3c&HFFFFFF&\3a&H80&\bord2\shad0{pop}{ex}\p1" + "}"
              + stadium(2 * r, 2 * r) + "{\\p0}")
        if m.get("avatar_text"):
            A.add(63, t, end, "{" + rf"\an5\pos({ax:.0f},{cy:.0f})\fnInter\b1\fs{fs:.0f}\bord0\shad0\1c&HFFFFFF&{pop}{ex}" + "}"
                  + esc(m["avatar_text"]))
    sfx += [(t, "pop"), (t, "boom_soft")]
    return (t - 0.02, end) if hides_sub(m) else None


def do_flash(A, m, sfx):
    t = float(m["t"])
    A.add(90, t - 0.12, t + 0.36, "{" + rf"\an7\pos(0,0)\bord0\shad0\1c&HFFFFFF&\alpha&HFF&"
          rf"\t(0,120,\alpha&H00&)\t(150,480,0.7,\alpha&HFF&)\p1" + "}" + f"m 0 0 l {W} 0 {W} {H} 0 {H}" + "{\\p0}")
    if m.get("riser", True):
        sfx.append((t - 0.8, "riser"))
    sfx.append((t, "hit"))


# ───────────────────────── sub từng cụm ─────────────────────────
PUNCT = ".,!?…;:"


# ngắt dòng theo TỪ GHÉP (chủ kênh 2026-10-01: "cắt theo từ ghép chuẩn" — không còn "xây thương / hiệu", "bất / động sản")
_TU_GHEP = None
LINE_START_OK = {"mà", "nhưng", "và", "để", "khi", "thì", "nếu", "vì", "nên", "rằng", "hay", "hoặc", "còn", "cùng",
                 "từ", "đến", "tại", "về", "với", "cho", "của", "trong", "là"}          # mở đầu cụm ý mới
DANGLING = {"của", "cho", "với", "tại", "về", "từ", "các", "những", "một", "là", "rất", "cũng", "đã", "đang", "sẽ",
            "không", "và", "mà", "khi", "thì", "để", "mọi", "mỗi", "vài", "hai", "ba", "đến", "tới", "trong", "ngoài",
            "trên", "dưới", "như", "bị", "được", "cái", "con", "người", "sự", "việc", "cuộc", "nhà", "quá", "hơi", "khá"}
TAIL_WORDS = {"ra", "vào", "lên", "xuống", "được", "thôi", "nhé", "nha", "nữa", "rồi", "đi", "ạ", "à", "luôn", "đó",
              "này", "kia", "ấy", "nhau", "hết", "xong", "lắm", "quá"}                  # bám vào từ đứng trước


UNITS = {"tỷ", "triệu", "nghìn", "ngàn", "trăm", "đồng", "đô", "usd", "k", "%", "ngày", "tháng", "năm", "tuần", "giờ",
         "phút", "giây", "lần", "người", "video", "sub", "tập", "kg", "km", "m", "cm"}   # đơn vị bám vào số đứng trước


def _clean(w):
    return w.strip(".,!?…;:\"'()“”‘’*").lower()


def tu_ghep():
    global _TU_GHEP
    if _TU_GHEP is None:
        _TU_GHEP = set()
        f = Path(__file__).with_name("vi_tu_ghep.txt")
        lines = f.read_text(encoding="utf-8").splitlines() if f.exists() else []
        for ln in lines + list(SUB.get("join", [])):
            ln = ln.strip()
            if ln and not ln.startswith("#"):
                _TU_GHEP.add(tuple(_clean(x) for x in ln.split()))
    return _TU_GHEP


def break_cost(s, b):
    """điểm phạt khi ngắt dòng TRƯỚC từ s[b] (âm = chỗ ngắt đẹp)."""
    lex, c = tu_ghep(), 0.0
    cw = [_clean(w["w"]) for w in s]
    for i in range(max(0, b - 3), b):                                   # có từ ghép nào vắt qua chỗ ngắt?
        for j in range(b + 1, min(len(s), i + 4) + 1):
            if tuple(cw[i:j]) in lex:
                c += 30
    prev, cur = s[b - 1]["w"], s[b]["w"]
    if prev[:1].isupper() and cur[:1].isupper() and b - 1 > 0:          # tên riêng 2 chữ hoa liền: High Ticket
        c += 8
    if cur[:1].isdigit() or cw[b - 1] in ("số", "top", "tắc"):          # "con số | 0", "quy tắc | 90/10"
        c += 15
    if prev[:1].isdigit() and cw[b] in UNITS:                           # "1 | tỷ", "90 | ngày", "3 | tháng"
        c += 20
    if prev[-1:] in ",;:":
        c -= 6
    if s[b]["s"] - s[b - 1]["e"] > SUB["gap_break"]:                    # chỗ ngừng nói
        c -= 3
    if cw[b - 1] in DANGLING:
        c += 4
    if cw[b] in TAIL_WORDS:
        c += 5
    if cw[b] in LINE_START_OK:
        c -= 2
    return c


def split_sentence(s):
    """chia 1 câu thành dòng bằng quy hoạch động: điểm ngắt (từ ghép, giới từ treo…) + độ dài dòng cân nhau."""
    n, mw, mn = len(s), SUB["max_words"], SUB.get("min_words", 1)
    extra = 1 if mw <= 3 else 0                     # sub dọc 1–2 từ: cho phép 3 từ để giữ trọn "bất động sản"
    if n <= mw:
        return [s]
    bc = [0.0] + [break_cost(s, b) for b in range(1, n)]
    k0 = -(-n // mw)
    best = None
    for k in range(max(1, -(-n // (mw + extra))), k0 + 2):
        T = n / k
        INF = float("inf")
        f = [[INF] * (k + 1) for _ in range(n + 1)]
        g = [[0] * (k + 1) for _ in range(n + 1)]
        f[0][0] = 0.0
        for j in range(1, n + 1):
            for m in range(1, k + 1):
                for i in range(max(0, j - mw - extra), j):
                    if f[i][m - 1] == INF:
                        continue
                    L = j - i
                    if L > 1 and len(" ".join(w["w"] for w in s[i:j])) > SUB["max_chars"] + 4 * extra:
                        continue
                    lc = 0.6 * (L - T) ** 2 + (4 if L > mw else 0) + (2 * (mn - L) if L < mn else 0)
                    if L == 1 and extra:                # sub dọc: 1 từ đứng trơ ("một", "những", "về") khó hiểu
                        cw1 = _clean(s[i]["w"])
                        lc += 4 + (5 if cw1 in DANGLING or cw1 in LINE_START_OK else 0)
                    v = f[i][m - 1] + lc + (bc[i] if i else 0)
                    if v < f[j][m]:
                        f[j][m], g[j][m] = v, i
        if f[n][k] == INF:
            continue
        tot = f[n][k] + 1.5 * max(0, k - k0)
        if best is None or tot < best[0]:
            parts, j = [], n
            for m in range(k, 0, -1):
                i = g[j][m]
                parts.append(s[i:j])
                j = i
            best = (tot, parts[::-1])
    return best[1] if best else [s[i:i + mw] for i in range(0, n, mw)]


# ───── viết hoa trong sub nhỏ (chủ kênh 2026-10-02): CHỈ tên riêng / thương hiệu viết hoa, còn lại viết thường.
# Whisper tự viết hoa chữ đầu câu nó đoán ("ha Thì các bạn") → hạ thường; chữ hoa đó dùng làm mốc NGẮT CÂU.
PROPER_DEFAULT = [
    "Facebook", "YouTube", "TikTok", "Zalo", "Google", "Instagram", "Messenger", "Shopee", "Lazada", "Tiki", "Canva",
    "ChatGPT", "Claude", "Gemini", "Anthropic", "OpenAI", "Apple", "iPhone", "Samsung", "Grab", "Netflix", "Amazon",
    "Việt Nam", "Hà Nội", "Sài Gòn", "TP.HCM", "Hồ Chí Minh", "Đà Nẵng", "Hải Phòng", "Cần Thơ", "Đà Lạt", "Nha Trang",
    "Phú Quốc", "Singapore", "Thái Lan", "Nhật Bản", "Hàn Quốc", "Trung Quốc", "Châu Âu", "Châu Á", "Cyprus", "Síp",
    "Dubai", "Suối Mơ", "Hồ Mạnh Thắng", "High Ticket",
]
PROPER = []                # + plan "proper_nouns" (đặt trong build)
CASE_LOG = {}


def _pkey(s):
    return s.strip(".,!?…;:\"'()“”").lower()


def sub_case(words):
    """bản sao words: chữ hoa thừa → thường (giữ tên riêng + chữ có hoa giữa/chữ số: AI, ChatGPT, TikTok, 4K);
    gắn "_ss" cho từ whisper viết hoa đầu câu (dùng làm mốc ngắt câu)."""
    lst = PROPER_DEFAULT + PROPER
    canon = {tuple(_pkey(x) for x in n.split()): n.split() for n in lst}
    names = sorted(canon, key=len, reverse=True)
    out = [dict(w) for w in words]
    keys = [_pkey(w["w"]) for w in out]
    keep = [None] * len(out)
    for i in range(len(out)):
        if keep[i]:
            continue
        for nm in names:
            if tuple(keys[i:i + len(nm)]) == nm:
                for k, tok in enumerate(canon[nm]):
                    keep[i + k] = tok
                break
    for i, w in enumerate(out):
        raw = w["w"]
        core = raw.strip(".,!?…;:\"'()“”")
        if not core:
            continue
        if keep[i]:                                               # tên riêng → đúng cách viết chuẩn
            w["w"] = raw.replace(core, keep[i])
            continue
        if core[0].isupper():
            if any(c.isupper() for c in core[1:]) or any(c.isdigit() for c in core):
                continue                                          # AI, TikTok, 4K… giữ nguyên
            low = core[0].lower() + core[1:]
            w["w"] = raw.replace(core, low)
            if i > 0:
                w["_ss"] = True
            CASE_LOG[core] = low
    return out


def build_chunks(words):
    """tách theo câu (dấu .?!… / ngừng > 1.2s / whisper viết hoa đầu câu) rồi chia dòng theo từ ghép. Dọc: 1–2 từ. Ngang: 8–12 từ."""
    sents, cur = [], []
    for k, w in enumerate(words):
        cur.append(w)
        nxt = words[k + 1] if k + 1 < len(words) else None
        if nxt is None or w["w"][-1:] in ".?!…" or nxt["s"] - w["e"] > 1.2 or nxt.get("_ss"):
            sents.append(cur)
            cur = []
    return [p for s in sents for p in split_sentence(s) if p]


def subtract(a, b, blocks):
    segs = [(a, b)]
    for x, y in blocks:
        nxt = []
        for s, e in segs:
            if y <= s or x >= e:
                nxt.append((s, e))
                continue
            if x > s:
                nxt.append((s, x))
            if y < e:
                nxt.append((y, e))
        segs = nxt
    return [(s, e) for s, e in segs if e - s >= 0.12]


def render_subs(A, words, blocks, dur):
    if not words:
        return
    words = sub_case(words)                 # chỉ tên riêng viết hoa; chữ hoa đầu câu của whisper → mốc ngắt câu
    if not SUB.get("keep_shown"):
        words = [w for w in words if round(w["s"], 2) not in SHOWN]     # từ đã hiện ở chữ nhấn → không sub lại
    # từ được NÓI trong lúc chữ nhấn đang hiện → bỏ hẳn trước khi ghép cụm; nếu để lại, cụm sub bị cắt ở mép khoảnh khắc
    # và phần đuôi hiện SAU khi giọng đã nói xong ("2026 và" hiện muộn 1.4s — Short THỬ THÁCH 90 NGÀY) → lệch tiếng
    # sub_zones có "hide": true → không sub cả đoạn (VD footage quay màn hình đã đầy chữ — chủ kênh 2026-10-02)
    blocks = list(blocks) + [(float(z["start"]), float(z["end"])) for z in SUB_ZONES if z.get("hide")]
    words = [w for w in words if not any(x <= w["s"] < y for x, y in blocks)]
    if not words:
        return
    chunks = build_chunks(words)
    fs = float(SUB["fs"])
    y = float(SUB["y"]) * H
    for k, ch in enumerate(chunks):
        a = ch[0]["s"] - 0.03
        nxt = chunks[k + 1][0]["s"] - 0.03 if k + 1 < len(chunks) else dur
        b = nxt if nxt - ch[-1]["e"] < 0.7 else ch[-1]["e"] + 0.3
        bold = any(w.get("b") for w in ch)
        key = SUB["bold_font"] if bold else SUB["font"]
        name, fb, fi, _, _ = FONTS[key]
        txt = esc(" ".join(w["w"].strip("*") for w in ch))
        fs = float(SUB["fs"])
        tw0 = text_w(" ".join(w["w"] for w in ch), key, fs)
        if tw0 > 0.92 * W:                        # dòng sub dài (bản ngang 8–12 từ) → thu cỡ cho vừa, chừa 4% mỗi bên
            fs *= 0.92 * W / tw0
        e = em_px(key, fs)
        y = float(SUB["y"]) * H
        # "sub_zones" [{start, end, y, halo}]: dời sub trong đoạn đó (VD đoạn quay màn hình đã có chữ/sub cháy sẵn ở giữa khung)
        zone = next((z for z in SUB_ZONES if "y" in z and a < z["end"] and b > z["start"]), None)
        halo = SUB.get("halo") or (zone or {}).get("halo")
        if zone:
            y = float(zone["y"]) * H
        elif MASK is not None:
            # sub rơi vào MẶT → dời xuống dưới cằm (chủ kênh: chữ không che mặt)
            tw = text_w(" ".join(w["w"] for w in ch), key, fs)
            sb = (W / 2 - tw / 2, y - fs * 0.7, W / 2 + tw / 2, y + fs * 0.5)
            faces = face_boxes(ch[0]["s"] + 0.05) + face_boxes((a + b) / 2)   # mọi khuôn mặt
            # sub nhỏ chỉ phủ vài % khung mặt nhưng vẫn đè mũi/miệng → chạm mặt là dời (không dùng ngưỡng FACE_MAX)
            hitf = [f for f in faces if overlap_frac(sb, f) > 0.005]
            if hitf:
                below = max(f[3] for f in hitf) + fs * 1.0     # dưới cằm của MẶT BỊ CHẠM (không phải mặt thấp nhất khung)
                # dưới cằm vượt vùng 3:4 → nằm ở mép dưới vùng (KHÔNG đưa lên trên đầu: chồng chữ nhấn tầng trên — NGAY 2)
                y = min(0.82 * H, below)
        sp = safe_px()
        if sp:                                    # sub nhỏ luôn trong vùng an toàn 3:4 (kể cả sub_zones)
            y = min(max(y, sp[1] + fs * 0.7), sp[3] - fs * 0.5)
        # SUB NÉ CHỮ NHẤN đang hiện (sub giờ luôn chạy — NGAY 2: cụm "chạy rất là / mượt" né mặt xuống ngực, đè sub)
        busy = [bx for s0, e0, bx in MOMENT_BOXES if s0 < b and e0 > a]
        if busy and not zone:
            tw = text_w(" ".join(w["w"] for w in ch), key, fs)
            faces_ = (face_boxes(ch[0]["s"] + 0.05) + face_boxes((a + b) / 2)) if MASK is not None else []
            def bad(yy):
                sb_ = (W / 2 - tw / 2, yy - fs * 0.75, W / 2 + tw / 2, yy + fs * 0.55)
                if sp and (sb_[1] < sp[1] - 1 or yy > sp[3]):      # tâm dòng sub không quá mép dưới vùng 3:4
                    return True
                hit = any(min(sb_[2], q[2]) > max(sb_[0], q[0]) and min(sb_[3], q[3]) > max(sb_[1], q[1]) for q in busy)
                return hit or any(overlap_frac(sb_, f) > 0.005 for f in faces_)
            if bad(y):
                cands = sorted({q[3] + fs * 0.85 for q in busy} | {q[1] - fs * 0.65 for q in busy} |
                               {y + d * fs for d in range(-12, 13)}, key=lambda v: abs(v - y))
                y = next((v for v in cands if not bad(v)), y)
        for pi, (s, t) in enumerate(subtract(a, b, blocks)):
            d = t - s
            enter, xa, xb = "none", ms(d), ms(d)      # sub nhỏ hiện thẳng, không blur vào/ra (chủ kênh chốt 2026-09-30)
            head = rf"\an5\fn{name}\b{fb}\i{fi}\fs{fs:.0f}\bord0\shad0"
            if halo:                              # quầng tối mềm (không phải viền cứng) cho dòng sub dài bản ngang
                A.add(29, s, t, "{" + rf"\an5\fn{name}\b{fb}\i{fi}\fs{fs:.0f}\bord{fs * 0.22:.1f}\shad0"
                      rf"\pos({W / 2:.0f},{y:.0f})\1c&H000000&\3c&H000000&\1a&H60&\3a&H90&\blur{fs * 0.3:.1f}" + "}" + txt)
            A.add(30, s, t, "{" + head + rf"\pos({W / 2 + SHADOW_OFF[0] * e:.0f},{y + SHADOW_OFF[1] * e:.0f})\1c&H000000&"
                  + span_tags(0, SHADOW_ALPHA, SHADOW_BLUR * 1.5 * e, enter, xa, xb, 6, 0.10) + "}" + txt)
            A.add(31, s, t, "{" + head + rf"\pos({W / 2:.0f},{y:.0f})\1c&HFFFFFF&"
                  + span_tags(0, "&H00&", 0.5, enter, xa, xb, 6, 0.10) + "}" + txt)


# ───────────────────────── SFX (tự tạo bằng numpy; thả WAV cùng tên vào sfx/ để thay) ─────────────────────────
def _lp(np, x, fc):
    a = 1 - np.exp(-2 * np.pi * np.broadcast_to(fc, x.shape) / SR)
    y = np.empty_like(x)
    s = 0.0
    for i in range(len(x)):
        s += a[i] * (x[i] - s)
        y[i] = s
    return y


def _reverb(np, st, rng, decay=1.0, wet=0.25):
    n = int(decay * SR)
    t = np.arange(n) / SR
    out = []
    for ch in range(2):
        ir = _lp(np, rng.standard_normal(n) * np.exp(-t * 6.9 / decay), 5000.0)
        ir /= np.sqrt((ir ** 2).sum()) + 1e-9
        m = len(st) + n - 1
        N = 1 << (m - 1).bit_length()
        out.append(np.fft.irfft(np.fft.rfft(st[:, ch], N) * np.fft.rfft(ir, N), N)[:m])
    return np.vstack([st, np.zeros((n - 1, 2))]) * (1 - wet) + np.stack(out, 1) * wet * 2.2


def synth(kind, np, rng):
    T = lambda d: np.arange(int(d * SR)) / SR
    if kind in ("whoosh_soft", "air"):
        d = 0.55 if kind == "whoosh_soft" else 0.38
        t = T(d)
        pk = 0.6 * d
        fc = np.where(t < pk, 600 + 6000 * (t / pk) ** 1.5, 6600 - 5000 * np.clip((t - pk) / (d - pk), 0, 1) ** 0.7)
        body = _lp(np, rng.standard_normal(len(t)), fc)
        body -= _lp(np, body, 400.0 if kind == "air" else 220.0)
        env = np.where(t < pk, np.sin(0.5 * np.pi * t / pk) ** 2, np.cos(0.5 * np.pi * np.clip((t - pk) / (d - pk), 0, 1)) ** 2)
        mono = body * env
        st = _reverb(np, np.stack([mono * (1 - 0.4 * t / d), mono * (0.6 + 0.4 * t / d)], 1), rng, 0.8, 0.25)
    elif kind in ("boom", "boom_soft"):
        d = 2.4 if kind == "boom" else 1.0
        t = T(d)
        f = 44 - 8 * t / d
        tone = np.sin(2 * np.pi * np.cumsum(f) / SR) + 0.35 * np.sin(2 * np.pi * np.cumsum(2 * f) / SR)
        rum = _lp(np, rng.standard_normal(len(t)), 120.0) * 3
        att = 0.25 if kind == "boom" else 0.01
        env = np.minimum(1, t / att) * np.exp(-np.maximum(0, t - att) / (0.9 if kind == "boom" else 0.25))
        mono = np.tanh((tone + rum) * env * 1.3)
        st = np.stack([mono, mono], 1)
    elif kind == "swipe":
        t = T(0.3)
        fc = 800 + 9000 * (t / 0.3) ** 0.8
        body = _lp(np, rng.standard_normal(len(t)), fc)
        body -= _lp(np, body, 700.0)
        mono = body * np.sin(np.pi * np.clip(t / 0.3, 0, 1)) ** 1.5
        st = _reverb(np, np.stack([mono * 0.8, mono], 1), rng, 0.5, 0.2)
    elif kind in ("pop", "pop_soft"):
        t = T(0.1)
        f0 = 950 if kind == "pop" else 720
        f = f0 * np.exp(-t / 0.03) + 320
        mono = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.028) * np.minimum(1, t / 0.001)
        st = _reverb(np, np.stack([mono, mono], 1), rng, 0.35, 0.15)
    elif kind == "riser":
        d = 0.8
        t = T(d)
        f = 180 * (6 ** (t / d))
        ton = np.sin(2 * np.pi * np.cumsum(f) / SR) + 0.5 * np.sin(2 * np.pi * np.cumsum(f * 1.5) / SR)
        noi = _lp(np, rng.standard_normal(len(t)), 400 + 7000 * (t / d) ** 2) * 1.2
        mono = (ton * 0.4 + noi) * (t / d) ** 2.4 * np.minimum(1, (d - t) / 0.02)
        st = _reverb(np, np.stack([mono, mono], 1), rng, 0.8, 0.25)
    elif kind == "hit":
        t = T(1.2)
        f = 40 + 30 * np.exp(-t / 0.08)
        boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.35)
        crack = _lp(np, rng.standard_normal(len(t)), 5000.0) * np.exp(-t / 0.02)
        mono = np.tanh((boom + crack * 0.8) * 1.4) * np.minimum(1, t / 0.002)
        st = _reverb(np, np.stack([mono, mono], 1), rng, 1.4, 0.35)
    elif kind == "shimmer":
        t = T(1.6)
        n = len(t)
        mono = np.zeros(n)
        for k, f in enumerate((2093, 2637, 3136, 3520, 4186)):
            off = int(k * 0.04 * SR)
            tt = t[: n - off]
            mono[off:] += np.sin(2 * np.pi * f * tt) * np.exp(-tt / 0.5) * np.minimum(1, tt / 0.01)
        st = _reverb(np, np.stack([mono, np.roll(mono, 300)], 1), rng, 1.4, 0.35)
    elif kind.startswith("pill"):
        # badge viên thuốc bật ra (chủ kênh 2026-09-30: cần nghe rõ): "bloop" 2 tầng + click mềm, mỗi viên cao hơn 4 nửa cung
        k = int(kind[4:] or 0)
        base = 560 * 2 ** (4 * k / 12)
        t = T(0.16)
        f = base * (1 + 0.55 * (1 - np.exp(-t / 0.025)))            # trượt lên
        ton = np.sin(2 * np.pi * np.cumsum(f) / SR) + 0.35 * np.sin(2 * np.pi * np.cumsum(f * 2) / SR)
        env = np.minimum(1, t / 0.004) * np.exp(-t / 0.05)
        click = _lp(np, rng.standard_normal(len(t)), 6000.0) * np.exp(-t / 0.003) * 0.4
        mono = ton * env + click
        st = _reverb(np, np.stack([mono * 0.9, mono], 1), rng, 0.45, 0.18)
    elif kind == "tick":
        t = T(0.05)
        mono = np.sin(2 * np.pi * 2400 * t) * np.exp(-t / 0.006)
        st = np.stack([mono, mono], 1)
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
        print(f"  (bỏ qua {f.name}: chỉ nhận WAV 16-bit)")
        return None
    x = np.frombuffer(raw, "<i2").astype(float).reshape(-1, ch) / 32768
    x = np.repeat(x, 2, 1)[:, :2] if ch == 1 else x[:, :2]
    if sr != SR:
        idx = np.arange(0, len(x), sr / SR)
        x = np.stack([np.interp(idx, np.arange(len(x)), x[:, c]) for c in range(2)], 1)
    return x / (np.abs(x).max() + 1e-9)


def build_sfx(events, dur, out_wav, volume=1.0):
    try:
        import numpy as np
    except ImportError:
        die("thiếu numpy: pip install numpy")
    rng = np.random.default_rng(11)
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
        g = SFX_GAIN.get(kind, SFX_GAIN.get(kind.replace("_soft", ""), 0.12) * 0.6)
        buf[i:j] += s[: j - i] * g * volume * (10 ** (SFX_MASTER_DB / 20))
    buf = np.tanh(buf[: int(dur * SR) + 1] * 1.1) / 1.1
    with wave.open(str(out_wav), "wb") as f:
        f.setnchannels(2)
        f.setsampwidth(2)
        f.setframerate(SR)
        f.writeframes((np.clip(buf, -1, 1) * 32767).astype("<i2").tobytes())


# ───────────────────────── plan → ASS ─────────────────────────
def load_plan(p):
    p = Path(p).resolve()          # ffmpeg chạy trong thư mục tạm → mọi đường dẫn phải tuyệt đối
    plan = json.loads(p.read_text(encoding="utf-8-sig"))
    plan["_dir"] = p.parent
    return plan


def rel(plan, f):
    fp = Path(f)
    return fp if fp.is_absolute() else plan["_dir"] / fp


def load_words(plan):
    wf = plan.get("words_file")
    if not wf:
        return []
    d = json.loads(rel(plan, wf).read_text(encoding="utf-8-sig"))
    ws = d["words"] if isinstance(d, dict) else d
    for w in ws:
        w["s"], w["e"] = float(w["s"]), float(w["e"])
        if w["w"].startswith("*") and w["w"].endswith("*") and len(w["w"]) > 2:
            w["b"] = True
    return ws


def build(video, plan, tmp):
    global W, H, REFW
    dur, vw, vh, has_a, fps = probe(video)
    W = 1920 if vw > vh else 1080
    H = round(W * vh / vw)
    REFW = min(W, H) if vw > vh else W
    if vw > vh:
        SUB.update(SUB_LAND)                      # bản ngang: sub 8–12 từ, 1 dòng ở đáy
    SUB.update(plan.get("sub", {}))
    SUB_ZONES[:] = plan.get("sub_zones", [])
    PROPER[:] = list(plan.get("proper_nouns", []))           # tên riêng riêng của video (viết hoa trong sub)
    CASE_LOG.clear()
    MOMENT_BOXES.clear()
    FACES_CACHE.clear()
    CV_CACHE.clear()
    global SRC_VIDEO
    SRC_VIDEO = video                              # để dò mặt thật trên khung gốc (cv_faces)
    # vùng an toàn 3:4 — chỉ khung dọc; plan "safe": false tắt, "safe": {x0,x1,y0,y1} đổi ô
    global SAFE_ON
    sf = plan.get("safe", True)
    SAFE_ON = vh > vw and sf is not False
    if isinstance(sf, dict):
        SAFE.update(sf)
    global THEME
    THEME = plan.get("theme", "vang")
    if THEME not in THEMES:
        die(f"theme không hợp lệ: {THEME} (chọn: {', '.join(THEMES)})")
    for k, v in plan.get("palette", {}).items():
        PAL[k] = v
    words = load_words(plan)
    global MASK
    PLACE_LOG.clear()
    SHOWN.clear()
    FACE_CACHE.clear()
    mk = plan.get("mask")
    MASK = MaskReader(rel(plan, mk)) if mk and rel(plan, mk).exists() else None
    A = Ass()
    sfx, blocks, images = [], [], []
    moments = sorted(plan.get("moments", []), key=lambda m: float(m.get("start", m.get("t", 0))))
    first = plan.get("hook_boom", True)
    for m in moments:
        typ = m.get("type", "text")
        blk = None
        if typ == "text":
            blk = do_text(A, m, words, sfx, first)
            first = False
        elif typ == "pills":
            blk = do_pills(A, m, sfx)
            for it in m["items"]:      # chữ trong viên thuốc cũng không sub lại
                toks = it["text"].split(" ")
                SHOWN.update(round(v, 2) for v in match_times(words, toks, float(it["t"]) - 0.1, float(m["end"]))[0])
        elif typ == "scatter":
            blk = do_scatter(A, m, sfx)
        elif typ == "bubble":
            blk = do_bubble(A, m, sfx)
            if m.get("avatar"):
                images.append(dict(file=str(rel(plan, m["avatar"])), start=float(m["start"]), end=float(m["end"]),
                                   x=float(m.get("avatar_x", float(m.get("x", 0.56)) - 0.30)), y=float(m.get("y", 0.50)),
                                   w=float(m.get("avatar_w", 0.075))))
        elif typ == "flash":
            do_flash(A, m, sfx)
        elif typ == "image":
            images.append(dict(file=str(rel(plan, m["file"])), start=float(m["start"]), end=float(m["end"]),
                               x=float(m.get("x", 0.5)), y=float(m.get("y", 0.4)), w=float(m.get("w", 0.3))))
            sfx.append((float(m["start"]), m.get("sfx", "pop")))
            if m.get("hide_subs", False):
                blocks.append((float(m["start"]), float(m["end"])))
        else:
            die(f"type không hợp lệ: {typ}")
        if blk:
            blocks.append(blk)
        for extra in m.get("sfx_add", []):
            sfx.append((float(extra[0]), extra[1]))
    if plan.get("subs", True):
        render_subs(A, words, blocks, dur)
    A.dump(Path(tmp) / "front.ass", "front")
    A.dump(Path(tmp) / "back.ass", "back")
    fx = [b for b in FX_BUCKETS if A.ev[b]]
    for b in fx:
        A.dump(Path(tmp) / f"{b}_a.ass", b, white=True)       # mặt nạ độ phủ
        if b.startswith("liq"):
            A.dump(Path(tmp) / f"{b}_c.ass", b)               # màu/gradient của chữ
    return dict(dur=dur, size=(vw, vh), fps=fps, has_audio=has_a, sfx=sorted(sfx), images=images,
                has_back=bool(A.ev["back"]) or any(b.endswith("back") for b in fx), fx=fx)


# ───────────────────────── ffmpeg ─────────────────────────
def stage(tmp):
    shutil.copytree(FONTS_DIR, Path(tmp) / "fonts")


def run_ff(args, cwd):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"] + args, cwd=cwd)
    if r.returncode != 0:
        die("ffmpeg thất bại (xem thông báo phía trên)")


def fx_stages(info, cur, which, ow, oh, t_off, fc):
    """lớp hiệu ứng trong chữ cho tầng `which` (back|front): ÂM BẢN rồi VÂN CHẢY. Trả nhãn luồng mới."""
    fps = info["fps"]
    d = 0.5 if t_off is not None else info["dur"] + 0.5
    sh = f",setpts=PTS+{t_off}/TB" if t_off is not None else ""
    src = f"color=c=black:s={ow}x{oh}:r={fps:.3f}:d={d:.2f},format=rgb24{sh}"
    for kind in ("inv", "liq"):
        b = f"{kind}_{which}"
        if b not in info["fx"]:
            continue
        fc.append(f"{src},ass={b}_a.ass:fontsdir=fonts,format=gray[{b}m]")
        if kind == "inv":
            # âm bản của chính khung hình, lộ ra qua hình chữ → chạy theo cảnh
            fc.append(f"[{cur}]split[{b}x][{b}y];[{b}y]negate,format=rgba[{b}n];[{b}n][{b}m]alphamerge[{b}p];"
                      f"[{b}x][{b}p]overlay=format=auto[{b}o]")
        else:
            # vân nước/kim loại chảy: sóng xám động (geq) phủ softlight lên màu chữ
            L = LIQUID
            f, sp, k = L["freq"], L["speed"], L["contrast"]
            # pha sóng uốn lượn theo thời gian → nền tối-sáng rộng + VỆT SÁNG MẢNH SẮC (lũy thừa 10) như mặt nước phản chiếu
            ph = (f"({0.060 * f:.4f}*X+{0.028 * f:.4f}*Y+2.4*sin({0.045 * f:.4f}*Y+{1.6 * sp:.3f}*T)"
                  f"+1.2*sin({0.030 * f:.4f}*X-{1.2 * sp:.3f}*T)+{2.6 * sp:.3f}*T)")
            lum = (f"clip(112+{48 * k:.0f}*sin({ph})"
                   f"+{150 * k:.0f}*pow(max(0,sin(2.3*{ph}+0.9)),10)"
                   f"-{40 * k:.0f}*pow(max(0,sin(1.7*{ph}-1.4)),6),0,255)")
            wave = (f"nullsrc=s=270x480:r={fps:.3f}:d={d:.2f}{sh},"
                    f"geq=lum='{lum}':cb=128:cr=128,scale={ow}:{oh}:flags=bicubic,format=gbrp")
            fc.append(f"{wave}[{b}w]")
            fc.append(f"{src},ass={b}_c.ass:fontsdir=fonts,format=gbrp[{b}c]")
            fc.append(f"[{b}c][{b}w]blend=all_mode=hardlight:all_opacity=0.85,format=gbrp[{b}t];[{b}t][{b}m]alphamerge,unpremultiply=inplace=1[{b}p];"
                      f"[{cur}][{b}p]overlay=format=auto[{b}o]")
        cur = f"{b}o"
    return cur


def graph(info, plan, out_size, t_off=None):
    """→ (inputs_extra, filter_complex) ; đầu vào 0 = video, 1 = mask (nếu có), rồi ảnh."""
    ow, oh = out_size
    sh = f",setpts=PTS+{t_off}/TB" if t_off is not None else ""
    ins, fc = [], []
    fc.append(f"[0:v]scale={ow}:{oh}{sh},format=yuv420p[v0]")
    cur = "v0"
    idx = 1
    mask = plan.get("mask")
    if info["has_back"]:
        if mask and rel(plan, mask).exists():
            ins += (["-ss", str(t_off)] if t_off is not None else []) + ["-i", str(rel(plan, mask))]
            fc.append(f"[{cur}]split[va][vb];[va]ass=back.ass:fontsdir=fonts[bk0]")
            bk = fx_stages(info, "bk0", "back", ow, oh, t_off, fc)
            fc.append(f"[{idx}:v]scale={ow}:{oh}{sh},format=gray[mk];[vb]format=rgba[vo];[vo][mk]alphamerge[pp];"
                      f"[{bk}][pp]overlay=format=auto[vc]")
            idx += 1
        else:
            if not info.get("_warned"):
                print("  CẢNH BÁO: có chữ 'behind' nhưng chưa có mask → chữ nằm TRƯỚC người. Chạy scripts/text3d/matte.py.")
                info["_warned"] = True
            fc.append(f"[{cur}]ass=back.ass:fontsdir=fonts[vc0]")
            fc_cur = fx_stages(info, "vc0", "back", ow, oh, t_off, fc)
            fc.append(f"[{fc_cur}]null[vc]")
        cur = "vc"
    for k, im in enumerate(info["images"]):
        iw = round(im["w"] * REFW / W * ow / 2) * 2
        ins += ["-loop", "1", "-framerate", f"{info['fps']:.3f}", "-t", f"{info['dur'] + 1:.2f}", "-i", im["file"]]
        a, b = im["start"], im["end"]
        fc.append(f"[{idx}:v]format=rgba,scale={iw}:-1{sh},fade=in:st={a}:d=0.15:alpha=1,"
                  f"fade=out:st={max(a, b - 0.2)}:d=0.2:alpha=1[im{k}]")
        x = f"{im['x'] * ow:.0f}-w/2"
        y = f"{im['y'] * oh:.0f}-h/2-{0.006 * oh:.1f}*(t-{a})"
        fc.append(f"[{cur}][im{k}]overlay=x='{x}':y='{y}':eval=frame:enable='between(t,{a},{b})'[vi{k}]")
        cur = f"vi{k}"
        idx += 1
    fc.append(f"[{cur}]ass=front.ass:fontsdir=fonts[fr0]")
    cur = fx_stages(info, "fr0", "front", ow, oh, t_off, fc)
    fc.append(f"[{cur}]format=yuv420p[v]")
    return ins, ";".join(fc), idx


def out_size(size, preview):
    vw, vh = size
    if preview and min(vw, vh) > 1080:
        k = 1080 / min(vw, vh)
        return round(vw * k / 2) * 2, round(vh * k / 2) * 2
    return vw, vh


# ───────────────────────── check ─────────────────────────
def cmd_check(a):
    plan = load_plan(a.plan)
    fonts_missing = [f[3] for f in FONTS.values() if not (FONTS_DIR / f[3]).exists()]
    if fonts_missing:
        die("thiếu font: " + ", ".join(fonts_missing) + " — xem fonts/README.md")
    with tempfile.TemporaryDirectory() as tmp:
        info = build(a.video, plan, tmp)
    dur = info["dur"]
    warn = []
    ms_ = sorted(plan.get("moments", []), key=lambda m: float(m.get("start", m.get("t", 0))))
    prev_end, prev_s = 0.0, 0.0
    tiers = {}
    spans = {"trên": [], "giữa": []}     # để bắt lỗi chữ sau đầu + cụm giữa cùng lúc (luật 3 khuôn)
    for m in ms_:
        s = float(m.get("start", m.get("t", 0)))
        e = float(m.get("end", s + 0.4))
        if e > dur + 0.05:
            warn.append(f"{m.get('style', m.get('type'))} @ {s:.1f}s kết thúc sau khi video hết.")
        if m.get("type") in ("pills", "scatter", "bubble"):
            spans["giữa"].append((s, e, m.get("type")))
        if m.get("type", "text") == "text":
            lines, pre = resolve_lines(m)
            y = float(m.get("y", pre.get("y", 0.5)))
            tier = "trên" if y < TOP_TIER else "giữa"
            if tier in tiers and s < tiers[tier] - 0.05:
                warn.append(f"{m.get('style')} @ {s:.1f}s chồng lên chữ khác ở tầng {tier} — chữ trước phải tắt hẳn rồi chữ sau mới vào.")
            tiers[tier] = e
            spans[tier].append((s, e, m.get("style")))
            for ln in lines:
                fs = fit_fs(ln)
                wpx = max([text_w(ln["text"], ln["font"], fs)] + [text_w(x["text"].upper() if ln.get("caps") else x["text"],
                                                                         ln["font"], fs) for x in ln.get("swap", [])])
                if wpx > 0.94 * W:
                    warn.append(f"Dòng '{ln['text']}' @ {s:.1f}s rộng {wpx / W:.0%} khung — tràn mép, giảm w/fs.")
                if fs > 380:
                    warn.append(f"Dòng '{ln['text']}' cỡ {fs:.0f} quá lớn — kiểm tra lại w.")
            if (m.get("behind", pre.get("behind")) and not (plan.get("mask") and rel(plan, plan["mask"]).exists())):
                warn.append(f"{m.get('style')} @ {s:.1f}s là chữ SAU NGƯỜI nhưng chưa có mask (plan['mask']).")
            if not 0.6 <= e - s <= 6:
                warn.append(f"{m.get('style')} @ {s:.1f}s dài {e - s:.1f}s (mẫu: 0.8–4s).")
        if s - prev_end > 6.5:
            warn.append(f"Khoảng {prev_end:.1f}–{s:.1f}s chỉ có sub trơn ({s - prev_end:.1f}s) — mẫu gốc ~2–3s lại có 1 điểm nhấn.")
        prev_end = max(prev_end, e)
    if dur - prev_end > 6.5:
        warn.append(f"Cuối video trống điểm nhấn {dur - prev_end:.1f}s — thêm CTA bubble?")
    for a0, a1, sa in spans["trên"]:
        for b0, b1, sb in spans["giữa"]:
            if min(a1, b1) - max(a0, b0) > 0.05:
                warn.append(f"RỐI MẮT: {sa} (sau đầu) @ {a0:.1f}s và {sb} (giữa) @ {b0:.1f}s hiện cùng lúc — "
                            f"mỗi câu chỉ 1 khuôn: ① chữ sau đầu + sub, ② cụm giữa, ③ điểm đặc biệt.")
    words = load_words(plan)
    if not words:
        warn.append("Chưa có words_file → không có sub.")
    for ch in build_chunks(sub_case(words) if words else []):
        t = " ".join(w["w"] for w in ch)
        if len(t) > SUB["max_chars"] + 4:
            warn.append(f"Cụm sub dài: '{t}'")
    if CASE_LOG:
        print("SUB VIẾT THƯỜNG (whisper viết hoa đầu câu): " + ", ".join(sorted(CASE_LOG)))
        print("  → tên riêng nào bị hạ nhầm thì thêm vào plan \"proper_nouns\".")
    if PLACE_LOG:
        print("CHỮ SAU NGƯỜI (luật: mỗi chữ cái che ≤50%, ≤2 chữ cái chạm):")
        for x in PLACE_LOG:
            print("  · " + x)
            if "KHÔNG ĐẠT" in x:
                warn.append(x)
    n = len(ms_)
    print(f"Video {dur:.1f}s · {n} điểm nhấn · TB {dur / max(1, n):.1f}s/điểm nhấn (mẫu gốc ≈ 2.2s) · {len(info['sfx'])} SFX")
    if warn:
        print("CẢNH BÁO:")
        for w in warn:
            print("  - " + w)
    else:
        print("OK — không có cảnh báo.")


# ───────────────────────── lệnh ─────────────────────────
def whisper_src(model):
    """Windows không tạo được symlink trong cache HF → tải thẳng vào ~/.cache/fw-<model>."""
    local = Path.home() / ".cache" / f"fw-{model}"
    if not (local / "model.bin").exists():
        from huggingface_hub import snapshot_download
        snapshot_download(f"Systran/faster-whisper-{model}", local_dir=str(local))
    return str(local)


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


def cmd_transcribe(a):
    _cuda_dlls()
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        die("thiếu faster-whisper: pip install faster-whisper")
    src = whisper_src(a.model)
    words, err = None, None
    # GPU có thể nạp mô hình được nhưng lỗi lúc chạy (thiếu cublas) → phải thử cả bước transcribe
    for dev, ct in (("cuda", "float16"), ("cpu", "int8")):
        try:
            m = WhisperModel(src, device=dev, compute_type=ct)
            segs, _ = m.transcribe(str(a.video), language=a.lang, word_timestamps=True, vad_filter=True)
            words = [{"w": w.word.strip(), "s": round(w.start, 3), "e": round(w.end, 3)}
                     for s in segs for w in (s.words or []) if w.word.strip()]
            break
        except Exception as e:
            err = e
    if words is None:
        die(f"nhận giọng thất bại: {err}")
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"words": words}, ensure_ascii=False, indent=0), encoding="utf-8")
    lines, cur, t0 = [], [], 0
    for w in words:
        if not cur:
            t0 = w["s"]
        cur.append(f"{w['w']}")
        if w["w"][-1] in ".?!" or len(cur) >= 12:
            lines.append(f"[{t0:6.2f}] " + " ".join(cur))
            cur = []
    if cur:
        lines.append(f"[{t0:6.2f}] " + " ".join(cur))
    out.with_suffix(".txt").write_text("\n".join(lines), encoding="utf-8")
    print(f"{len(words)} từ → {out}\nBản đọc → {out.with_suffix('.txt')}")


def cmd_snap(a):
    plan = load_plan(a.plan)
    video = Path(a.video).resolve()
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        stage(tmp)
        info = build(video, plan, tmp)
        osz = out_size(info["size"], True)
        for t in [float(x) for x in a.at.split(",")]:
            ins, fc, _ = graph(info, plan, osz, t_off=t)
            run_ff(["-ss", f"{t}", "-i", str(video)] + ins + ["-filter_complex", fc, "-map", "[v]", "-frames:v", "1",
                                                             str(out / f"snap_{t:07.2f}.png")], tmp)
    print(f"Ảnh QA → {out}")


def cmd_render(a):
    plan = load_plan(a.plan)
    video = Path(a.video).resolve()
    out = Path(a.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        stage(tmp)
        info = build(video, plan, tmp)
        build_sfx(info["sfx"], info["dur"], Path(tmp) / "sfx.wav", plan.get("sfx_volume", 1.0))
        osz = out_size(info["size"], a.preview)
        ins, fc, n_in = graph(info, plan, osz)
        ins += ["-i", "sfx.wav"]
        if info["has_audio"]:
            # chuẩn −14 LUFS / đỉnh −1.5 dBTP SAU khi trộn SFX (chủ kênh chốt; đo thật 30/9: alimiter cũ ra −11.3 LUFS, +0.2 dBTP → rè)
            fc += (f";[0:a][{n_in}:a]amix=inputs=2:duration=first:normalize=0,"
                   f"loudnorm=I=-14:LRA=7:TP=-1.5,aresample=48000[a]")
        else:
            fc += f";[{n_in}:a]anull[a]"
        if "h264_nvenc" in subprocess.run(["ffmpeg", "-hide_banner", "-encoders"], capture_output=True, text=True).stdout:
            enc = ["-c:v", "h264_nvenc", "-preset", "p4" if a.preview else "p6", "-rc", "vbr",
                   "-cq", "23" if a.preview else "18", "-b:v", "0"]
        else:   # Mac → VideoToolbox; còn lại libx264
            enc = _mac_vt(a.preview) or ["-c:v", "libx264"] + (["-preset", "veryfast", "-crf", "22"] if a.preview else ["-preset", "slow", "-crf", "17"])
        run_ff(["-i", str(video)] + ins + ["-filter_complex", fc, "-map", "[v]", "-map", "[a]", *enc,
                                           "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-t", f"{info['dur']:.3f}",
                                           str(out)], tmp)
    print(f"Xong → {out}  ({len(info['sfx'])} SFX, {len(info['images'])} ảnh, chữ sau người: {info['has_back']})")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("transcribe")
    p.add_argument("video")
    p.add_argument("-o", "--out", required=True)
    p.add_argument("--model", default="large-v3")   # small lệch mốc từ tới 0.6s → sub lệch giọng (THỬ THÁCH 90 NGÀY)
    p.add_argument("--lang", default="vi")
    p.set_defaults(f=cmd_transcribe)
    p = sp.add_parser("check")
    p.add_argument("video")
    p.add_argument("plan")
    p.set_defaults(f=cmd_check)
    p = sp.add_parser("snap")
    p.add_argument("video")
    p.add_argument("plan")
    p.add_argument("--at", required=True)
    p.add_argument("-o", "--out", required=True)
    p.set_defaults(f=cmd_snap)
    p = sp.add_parser("render")
    p.add_argument("video")
    p.add_argument("plan")
    p.add_argument("-o", "--out", required=True)
    p.add_argument("--preview", action="store_true")
    p.set_defaults(f=cmd_render)
    a = ap.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()

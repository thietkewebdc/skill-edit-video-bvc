#!/usr/bin/env python3
"""engine3d — bọc sm_overlay.py (cùng skill) để làm CHỮ CHÌM SAU NHÂN VẬT (3D). Dùng thay sm_overlay cho snap/render:
  python engine3d.py render <video> <plan_3d.json> -o <text_layer.mp4>
  python engine3d.py snap   <video> <plan_3d.json> --at 1,5 -o <qa>

Bổ sung cho engine:
  • fx "sync"   : từng chữ hiện ĐÚNG lúc được nói — "at" = mốc giây cho từng chữ (tách theo khoảng trắng)
                  "x","y" = tâm khối (tỉ lệ khung); "tw" = các dòng rộng BẰNG NHAU đúng tw × bề ngang
                  (cỡ chữ từng dòng tự đổi); "static": true = đứng yên từ frame đầu (dùng làm TIÊU ĐỀ)
  • zoom punch dạng cây if(lt(it,..)) — video dài có hàng trăm punch không làm ffmpeg lỗi
"""
import sys
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import sm_overlay as S  # noqa: E402


# ───────── zoom punch dạng cây ─────────
def _term(a, b, z):
    up = f"clip((it-{a:.3f})/0.22,0,1)"
    dn = f"clip(({b:.3f}-it)/0.35,0,1)"
    return f"1+{z - 1:.3f}*({up}*{up}*(3-2*{up}))*({dn}*{dn}*(3-2*{dn}))"


def _tree(ps):
    if len(ps) == 1:
        return _term(*ps[0])
    m = len(ps) // 2
    return f"if(lt(it,{ps[m][0]:.3f}),{_tree(ps[:m])},{_tree(ps[m:])})"


def punch_filter(punches, fps, size, t_offset=0.0):
    if not punches:
        return ""
    return (f"zoompan=z='{_tree(sorted(punches))}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:"
            f"s={size[0]}x{size[1]}:fps={fps:.3f},")


S.punch_filter = punch_filter


# ───────── dàn dòng BẰNG NHAU ─────────
def layout_equal(lines, target_w, cy):
    texts = ["".join(t for t, _ in ln) for ln in lines]
    fss = [100.0 * target_w / S.text_width(t, 100) for t in texts]
    cap = [S.CAP * f for f in fss]
    tops, cap_top, base = [], 0.0, 0.0
    for i, f in enumerate(fss):
        if i > 0:
            marks = any(m in unicodedata.normalize("NFD", texts[i]) for m in "̀́̃̉̂̆")
            cap_top = base + (S.LINE_GAP + (S.MARK_GAP if marks else 0)) * cap[i]
            if "̣" in unicodedata.normalize("NFD", texts[i - 1]):
                cap_top += S.DOT_GAP * cap[i - 1]
        top = cap_top - (S.WIN_ASC - S.CAP) * f
        base = top + S.WIN_ASC * f
        tops.append(top)
    total = base - (tops[0] + (S.WIN_ASC - S.CAP) * fss[0])
    shift = cy - total / 2 - (tops[0] + (S.WIN_ASC - S.CAP) * fss[0])
    return fss, [tp + shift + f / 2 for tp, f in zip(tops, fss)]


def sync_layout(e):
    """→ [(dòng, chữ, màu?, cx, cy, fs, rộng)] theo toạ độ ASS"""
    lines = S.split_accent_lines(e["text"])
    cy = S.H * e.get("y", S.BLOCK_Y)
    if e.get("tw"):
        fss, ys = layout_equal(lines, S.W * e["tw"], cy)
    else:
        fss, ys, _, _ = S.layout_block(lines, e.get("fs", 120), cy)
    X = S.W * e.get("x", 0.5)
    out = []
    for i, segs in enumerate(lines):
        fs, y = fss[i], ys[i]
        words = [(w, a) for t, a in segs for w in t.split()]
        wx = X - S.text_width(" ".join(w for w, _ in words), fs) / 2
        for w, a in words:
            ww = S.text_width(w, fs)
            out.append((i, w, a, wx + ww / 2, y, fs, ww))
            wx += ww + S.text_width(" ", fs)
    return out


_orig_emphasis = S.render_emphasis


def render_emphasis(A, e, events, punches, idx):
    if e.get("fx") != "sync":
        return _orig_emphasis(A, e, events, punches, idx)
    t0, t1 = float(e["start"]), float(e["end"])
    lay = sync_layout(e)
    at = list(e["at"]) if "at" in e else [t0] * len(lay)
    if len(at) != len(lay):
        S.die(f"sync @ {t0}: {len(lay)} chữ nhưng {len(at)} mốc 'at'")
    static = e.get("static", False)
    seen = {}
    for k, (i, w, a, cx, y, fs, ww) in enumerate(lay):
        ta = max(t0, float(at[k]))
        if static:
            S.emit_line(A, 11 + i * 4, ta, t1, cx, y, fs, [(w, a)])
        elif a:
            pre, anim = S.fx_alpha("slam")
            S.emit_line(A, 21 + i * 4 + k, ta, t1, cx, y, fs, [(w, a)], pre=pre, anim=anim)
        else:
            pre, anim = S.fx_alpha("rise")
            S.emit_line(A, 21 + i * 4 + k, ta, t1, cx, y, fs, [(w, a)], pre=pre, anim=anim, move=(cx, y + 24, 260))
        if w != "·":
            seen[round(ta, 2)] = seen.get(round(ta, 2)) or a
    if static:
        events += [(t0 + 0.02, "impact_soft"), (t1 - 0.3, "whoosh")]
        return (t0, t1)
    for ta, a in sorted(seen.items()):
        events.append((ta, "impact_soft" if a else "pop"))
    last = max(seen)
    S.fx_particles(A, last + 0.15, S.W * e.get("x", 0.5), lay[-1][4], 160, n=10, seed=idx + 3)
    if e.get("punch", False):
        punches.append((last - 0.05, t1, 1.05))
    return (t0, t1)


S.render_emphasis = render_emphasis

if __name__ == "__main__":
    S.main()

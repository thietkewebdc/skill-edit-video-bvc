#!/usr/bin/env python3
"""cut_qa — KIỂM DUYỆT MỐI CẮT bằng âm thanh thật (bổ sung cho cut_edit.py). Chủ kênh chốt 2026-09-26 sau khi
bắt lỗi: cắt dính âm thừa ở đầu, cụt chữ ở mối nối, mất "ba trăm" trong "336 triệu".

Lệnh (<work> = thư mục chứa cut.json, chunks.json, envelope.npy):
  medwords <video> <work>        nhận giọng LẠI các vùng giữ bằng model medium → <work>/med_words.json
                                 (mốc chữ chính xác hơn small — dùng để đặt mép cắt)
  wordsnap <work>                đọc keep_words / drop_words / pause_words trong cut.json → ghi keep_ranges /
                                 drop_ranges với MÉP NẰM TRONG KHOẢNG LẶNG THẬT sát chữ (in "!!" chỗ không có lặng)
  edges <work>                   rà mép các đoạn trong segments.json: mép nào đang cắt GIỮA TIẾNG
  lost <work> [--fix]            tiếng nói THẬT nằm trong vùng giữ nhưng bị analyze bỏ (coi là ồn lẻ) → --fix nới
                                 "trim" câu kề để nhập lại
  listen <work> [--video F]      NGHE LẠI video đã cắt (medium, không VAD, đệm 0.6s) → <work>/joints.txt:
                                 lời quanh từng mối nối, đánh dấu ‖
  try <video> t1,t2,...          nghe thử 2.2s từ nhiều điểm bắt đầu trên NGUỒN → chọn điểm sạch
  subs <work>                    dời mốc sub theo segments.json, KHÔNG bỏ chữ có mốc lọt vào khoảng lặng bị cắt
                                 (ghép vào chữ sau) → <work>/words_final.json
"""
import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

HOP = 0.01
PAD = 0.6            # đệm lặng trước khi nhận giọng (máy nghe hay bỏ chữ đầu file)


def load(work):
    w = Path(work)
    db = np.load(w / "envelope.npy")
    cj = json.loads((w / "chunks.json").read_text(encoding="utf-8"))
    return w, db, cj["threshold_db"], cj


def norm(s):
    return re.sub(r"[^\w]", "", s.lower())


def gaps(db, thr, a, b, min_gap=0.04):
    i0, i1 = max(0, int(a / HOP)), int(b / HOP)
    q = db[i0:i1] <= thr
    out, k = [], 0
    while k < len(q):
        if q[k]:
            j = k
            while j < len(q) and q[j]:
                j += 1
            if (j - k) * HOP >= min_gap:
                out.append(((i0 + k) * HOP, (i0 + j) * HOP))
            k = j
        else:
            k += 1
    return out


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


def model(size="medium"):
    """GPU nếu chạy được thật (thử nhận 1s im lặng để nạp cuBLAS), không thì CPU."""
    from faster_whisper import WhisperModel
    _cuda_dlls()
    try:
        m = WhisperModel(size, device="cuda", compute_type="float16")
        list(m.transcribe(np.zeros(16000, np.float32), language="vi", vad_filter=False)[0])
        return m
    except Exception:
        return WhisperModel(size, device="cpu", compute_type="int8")


def wav_of(src, out, ss=None, to=None, dur=None):
    cmd = ["ffmpeg", "-loglevel", "error", "-y"]
    if ss is not None:
        cmd += ["-ss", f"{ss:.3f}"]
    if to is not None:
        cmd += ["-to", f"{to:.3f}"]
    if dur is not None:
        cmd += ["-t", f"{dur:.3f}"]
    cmd += ["-i", str(src), "-af", f"adelay={int(PAD * 1000)}|{int(PAD * 1000)}", "-ac", "1", "-ar", "16000", str(out)]
    subprocess.run(cmd, check=True)


# ───────────── medwords ─────────────
def cmd_medwords(a):
    w = Path(a.work)
    cut = json.loads((w / "cut.json").read_text(encoding="utf-8"))
    spans = [(s - 4, e + 4) for s, e in cut.get("keep_ranges", [])]
    for k in ("keep_words",):
        for it in cut.get(k, []):
            spans.append((it[1] - 4, it[3] + 4))
    if not spans:
        cj = json.loads((w / "chunks.json").read_text(encoding="utf-8"))
        spans = [(0, cj["duration"])]
    spans.sort()
    merged = []
    for s, e in spans:
        if merged and s <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e))
        else:
            merged.append((max(0, s), e))
    m = model(a.model)
    words = []
    with tempfile.TemporaryDirectory() as tmp:
        for s, e in merged:
            wav = Path(tmp) / "m.wav"
            wav_of(a.video, wav, ss=s, to=e)
            segs, _ = m.transcribe(str(wav), language="vi", word_timestamps=True, vad_filter=False, temperature=0,
                                   condition_on_previous_text=False)
            words += [{"w": x.word.strip(), "s": round(s + x.start - PAD, 3), "e": round(s + x.end - PAD, 3)}
                      for sg in segs for x in (sg.words or []) if x.word.strip()]
            print(f"  vùng {s:.0f}–{e:.0f}s", flush=True)
    (w / "med_words.json").write_text(json.dumps({"words": words}, ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"{len(words)} từ → {w / 'med_words.json'}")


# ───────────── wordsnap ─────────────
def cmd_wordsnap(a):
    w, db, thr, _ = load(a.work)
    med = json.loads((w / "med_words.json").read_text(encoding="utf-8"))["words"]
    cut = json.loads((w / "cut.json").read_text(encoding="utf-8"))
    log = []

    def locate(word, t, after=None):
        if isinstance(word, (int, float)):
            return float(word), None
        x = norm(word)
        c = [i for i, m in enumerate(med) if norm(m["w"]) == x and abs(m["s"] - t) <= 1.0
             and (after is None or i > after)]
        if not c:
            c = [i for i, m in enumerate(med) if abs(m["s"] - t) <= 0.3]
        if not c:
            return t, None
        i = min(c, key=lambda i: abs(med[i]["s"] - t))
        return med[i]["s"], i

    def before(word, t, after=None):
        if isinstance(word, (int, float)):
            log.append(f"mốc cố định {word:.2f} (đã nghe thử)")
            return float(word), None
        o, i = locate(word, t, after)
        prev = med[i - 1]["s"] + 0.08 if i else o - 0.6
        g = gaps(db, thr, prev, o + 0.10)
        if g:
            x = sum(g[-1]) / 2
            log.append(f"trước '{word}'@{o:.2f}: lặng {g[-1][0]:.2f}–{g[-1][1]:.2f}")
        else:
            i0, i1 = int(prev / HOP), int((o + 0.05) / HOP)
            x = (i0 + int(np.argmin(db[i0:i1]))) * HOP
            log.append(f"!! trước '{word}'@{o:.2f}: KHÔNG có lặng → điểm âm thấp nhất {x:.2f} — nghe thử (try)")
        return round(x, 2), i

    def after_(word, t):
        if isinstance(word, (int, float)):
            log.append(f"mốc cố định {word:.2f} (đã nghe thử)")
            return float(word)
        o, i = locate(word, t)
        nxt = med[i + 1]["s"] if i is not None and i + 1 < len(med) else o + 1.0
        g = gaps(db, thr, o + 0.10, nxt + 0.08)
        if g:
            x = sum(g[-1]) / 2
            log.append(f"sau '{word}'@{o:.2f}: lặng {g[-1][0]:.2f}–{g[-1][1]:.2f}")
        else:
            i0, i1 = int((o + 0.12) / HOP), int((nxt + 0.05) / HOP)
            x = (i0 + int(np.argmin(db[i0:i1]))) * HOP
            log.append(f"!! sau '{word}'@{o:.2f}: KHÔNG có lặng → điểm âm thấp nhất {x:.2f} — nghe thử (try)")
        return round(x, 2)

    keep = [[before(w1, t1)[0], after_(w2, t2)] for w1, t1, w2, t2 in cut.get("keep_words", [])]
    drop = []
    for w1, t1, w2, t2 in cut.get("drop_words", []):
        s, i = before(w1, t1)
        e, _ = before(w2, t2, after=i)
        if e - s < 0.05:
            log.append(f"!! bỏ '{w1}'…'{w2}' rỗng (không tách được) → giữ nguyên, KHÔNG cắt giữa tiếng")
            continue
        drop.append([s, e])
    for w1, t1, w2, t2 in cut.get("pause_words", []):
        drop.append([after_(w1, t1), before(w2, t2)[0]])
    if keep:
        cut["keep_ranges"] = keep
    if cut.get("drop_words") is not None or cut.get("pause_words") is not None:
        cut["drop_ranges"] = drop
    (w / "cut.json").write_text(json.dumps(cut, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n".join(log))


# ───────────── edges ─────────────
def cmd_edges(a):
    w, db, thr, _ = load(a.work)
    segs = json.loads((w / "segments.json").read_text(encoding="utf-8"))
    bad = 0
    for k, g in enumerate(segs):
        for side, t in (("vào", g["src_s"]), ("ra ", g["src_e"])):
            # lỗi khi PHÍA BỊ BỎ sát mép (0.05s trước mép vào / sau mép ra) vẫn có tiếng = cắt mất âm
            i = int(round(t / HOP))
            cut_off = db[i - 8:i - 2] if side == "vào" else db[i + 2:i + 8]
            v = float(np.median(cut_off))
            if v > thr + 3:
                bad += 1
                prof = "".join("█" if x > thr + 6 else ("▒" if x > thr else "·")
                               for x in db[int((t - 0.4) / HOP):int((t + 0.4) / HOP):2])
                print(f"  !! đoạn {k + 1} {side} src {t:8.2f} ({v:5.1f} dB) CẮT GIỮA TIẾNG → phải nghe lại (listen/try) |{prof}|")
    print("edges:", "sạch" if not bad else f"{bad} mép cắt giữa tiếng — mỗi mép phải được xác nhận bằng listen / try")


# ───────────── lost ─────────────
def islands(db, thr, cut, segs):
    kept = np.zeros(len(db), bool)
    for s, e in cut.get("keep_ranges", []) or [[0, len(db) * HOP]]:
        kept[int(s / HOP):int(e / HOP)] = True
    for s, e in cut.get("drop_ranges", []):
        kept[int(s / HOP):int(e / HOP)] = False
    for c in cut.get("drop_chunks", []):
        pass
    for g in segs:
        kept[int(g["src_s"] / HOP):int(g["src_e"] / HOP)] = False
    loud = kept & (db > thr)
    out, i = [], 0
    while i < len(loud):
        if loud[i]:
            j = i
            while j < len(loud) and (loud[j] or (j + 5 < len(loud) and loud[j:j + 6].any())):
                j += 1
            if (j - i) * HOP >= 0.08:
                out.append((i * HOP, j * HOP))
            i = j
        else:
            i += 1
    return out


def cmd_lost(a):
    w, db, thr, cj = load(a.work)
    cut = json.loads((w / "cut.json").read_text(encoding="utf-8"))
    segs = json.loads((w / "segments.json").read_text(encoding="utf-8"))
    drop_chunks = set(cut.get("drop_chunks", []))
    chunks = [c for c in cj["chunks"] if c["i"] not in drop_chunks]
    isl = islands(db, thr, cut, segs)
    medp = w / "med_words.json"
    med = json.loads(medp.read_text(encoding="utf-8"))["words"] if medp.exists() else []
    for s, e in isl:
        near = " ".join(m["w"] for m in med if s - 0.4 <= m["s"] <= e + 0.2)
        print(f"  !! MẤT TIẾNG {s:.2f}–{e:.2f} ({e - s:.2f}s)  gần: {near}")
    print("lost:", "sạch" if not isl else f"{len(isl)} quãng tiếng bị bỏ")
    if not a.fix or not isl:
        return
    trim = {int(k): list(v) for k, v in cut.get("trim", {}).items()}
    for s, e in isl:
        prev = max((c for c in chunks if c["e"] <= s + 0.02), key=lambda c: c["e"], default=None)
        nxt = min((c for c in chunks if c["s"] >= e - 0.02), key=lambda c: c["s"], default=None)
        gp = s - trim.get(prev["i"], [prev["s"], prev["e"]])[1] if prev else 9
        gn = trim.get(nxt["i"], [nxt["s"], nxt["e"]])[0] - e if nxt else 9
        if gn <= gp:
            s0, e0 = trim.get(nxt["i"], [nxt["s"], nxt["e"]])
            trim[nxt["i"]] = [round(min(s0, s - 0.03), 2), e0]
            print(f"  → nhập {s:.2f}–{e:.2f} vào ĐẦU câu #{nxt['i']}")
        else:
            s0, e0 = trim.get(prev["i"], [prev["s"], prev["e"]])
            trim[prev["i"]] = [s0, round(max(e0, e + 0.03), 2)]
            print(f"  → nhập {s:.2f}–{e:.2f} vào CUỐI câu #{prev['i']}")
    cut["trim"] = {str(k): v for k, v in sorted(trim.items())}
    (w / "cut.json").write_text(json.dumps(cut, ensure_ascii=False, indent=1), encoding="utf-8")
    print("đã ghi trim → render lại rồi chạy lost lần nữa")


# ───────────── listen ─────────────
def cmd_listen(a):
    w = Path(a.work)
    v = Path(a.video) if a.video else next((w / n for n in ("cut_9x16_preview.mp4", "cut_16x9_preview.mp4",
                                                              "cut_9x16.mp4", "cut_16x9.mp4") if (w / n).exists()))
    segs = json.loads((w / "segments.json").read_text(encoding="utf-8"))
    m = model(a.model)
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "a.wav"
        wav_of(v, wav)
        ss, _ = m.transcribe(str(wav), language="vi", word_timestamps=True, vad_filter=False, temperature=0,
                             condition_on_previous_text=False)
        W = [(x.start - PAD, x.end - PAD, x.word.strip()) for s in ss for x in (s.words or []) if x.word.strip()]
    joints = [0.0] + [g["out_e"] for g in segs[:-1]] + [segs[-1]["out_e"]]
    lines = [f"##### {w.name}  ({v.name})"]
    for k, T in enumerate(joints):
        bef = [t for s, e, t in W if (s + e) / 2 < T][-9:]
        aft = [t for s, e, t in W if (s + e) / 2 >= T][:9]
        tag = "ĐẦU" if k == 0 else ("CUỐI" if k == len(joints) - 1 else f"nối {k}")
        lines.append(f"  [{tag:6s} @ {T:6.2f}s]  …{' '.join(bef)} ‖ {' '.join(aft)}…")
    lines.append("  SỐ LIỆU nghe được: " + " ".join(t for s, e, t in W if re.search(r"\d", t)))
    out = "\n".join(lines)
    (w / "joints.txt").write_text(out, encoding="utf-8")
    print(out)


# ───────────── try ─────────────
def cmd_try(a):
    m = model(a.model)
    with tempfile.TemporaryDirectory() as tmp:
        for t in map(float, a.times.split(",")):
            wav = Path(tmp) / "x.wav"
            wav_of(a.video, wav, ss=t, dur=2.2)
            ss, _ = m.transcribe(str(wav), language="vi", vad_filter=False, temperature=0,
                                 condition_on_previous_text=False)
            print(f"  từ {t:8.2f}: {' '.join(s.text.strip() for s in ss)[:100]}", flush=True)


# ───────────── subs ─────────────
def cmd_subs(a):
    w = Path(a.work)
    cut = json.loads((w / "cut.json").read_text(encoding="utf-8"))
    segs = json.loads((w / "segments.json").read_text(encoding="utf-8"))
    W = json.loads((w / cut.get("words", "src_words.json")).read_text(encoding="utf-8-sig"))["words"]
    drops = [tuple(r) for r in cut.get("drop_ranges", [])]
    lo, hi = min(g["src_s"] for g in segs), max(g["src_e"] for g in segs)
    out, orphan = [], None
    for x in W:
        s, e = x["s"], max(x["e"], x["s"] + 0.05)
        best = None
        for g in segs:
            ov = min(e, g["src_e"]) - max(s, g["src_s"])
            if ov > 0 and (best is None or ov > best[0]):
                best = (ov, g)
        if not best or (best[0] / (e - s) < 0.35 and best[0] < 0.12):
            in_drop = any(ds - 0.2 <= s and e <= de + 0.2 for ds, de in drops)
            orphan = (x["w"], e) if (lo < s < hi and not in_drop) else None
            continue
        g = best[1]
        a0 = max(s, g["src_s"]) - g["src_s"] + g["out_s"]
        b0 = min(e, g["src_e"]) - g["src_s"] + g["out_s"]
        txt = x["w"]
        if orphan and s - orphan[1] < 0.8:
            txt = orphan[0] + " " + txt
        orphan = None
        out.append({"w": txt, "s": round(a0, 3), "e": round(max(b0, a0 + 0.05), 3)})
    out.sort(key=lambda z: z["s"])
    (w / "words_final.json").write_text(json.dumps({"words": out}, ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"{len(out)} từ → {w / 'words_final.json'}  (plan.json: \"words_file\": \"words_final.json\")")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("medwords"); p.add_argument("video"); p.add_argument("work")
    p.add_argument("--model", default="medium"); p.set_defaults(f=cmd_medwords)
    p = sp.add_parser("wordsnap"); p.add_argument("work"); p.set_defaults(f=cmd_wordsnap)
    p = sp.add_parser("edges"); p.add_argument("work"); p.set_defaults(f=cmd_edges)
    p = sp.add_parser("lost"); p.add_argument("work"); p.add_argument("--fix", action="store_true")
    p.set_defaults(f=cmd_lost)
    p = sp.add_parser("listen"); p.add_argument("work"); p.add_argument("--video")
    p.add_argument("--model", default="medium"); p.set_defaults(f=cmd_listen)
    p = sp.add_parser("try"); p.add_argument("video"); p.add_argument("times")
    p.add_argument("--model", default="medium"); p.set_defaults(f=cmd_try)
    p = sp.add_parser("subs"); p.add_argument("work"); p.set_defaults(f=cmd_subs)
    a = ap.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()

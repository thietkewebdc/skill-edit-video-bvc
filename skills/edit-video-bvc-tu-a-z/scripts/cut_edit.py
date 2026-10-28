#!/usr/bin/env python3
"""cut_edit — GIAI ĐOẠN A của skill edit-video-bvc-tu-a-z: cắt ghép + zoom xen kẽ + căn khung.

Lệnh:
  analyze <video> <words.json> -o <work>     dò khoảng lặng (âm thanh thật), chia câu → chunks.txt / chunks.json,
                                             dò khuôn mặt suốt video → face.json
  plan    <work>/cut.json                    in danh sách đoạn sẽ giữ (sau khi gộp đoạn < 2s) để duyệt
  render  <video> <work>/cut.json -o <work> [--aspect both|16x9|9x16] [--preview]
                                             xuất cut_16x9.mp4 / cut_9x16.mp4 + words_cut.json + segments.json

Quy tắc (chủ kênh chốt):
  • mối nối: tổng khoảng lặng còn đúng GAP_TOTAL = 0.2s (0.1s cuối đoạn trước + 0.1s đầu đoạn sau)
  • khoảng lặng > MIN_PAUSE = 0.6s đều cắt; mọi đoạn giữ lại ≥ MIN_SEG = 2.0s (đoạn ngắn → không cắt
    khoảng lặng quanh nó, gộp với đoạn kề)
  • nội dung trùng → giữ lần nói SAU (đánh dấu trong cut.json bằng drop_chunks / drop_ranges)
  • đoạn 1, 3, 5… zoom 100% (giữ nguyên); đoạn 2, 4, 6… zoom 150%, căn khung: mặt giữa ngang, mắt trên đường 1/3
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

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

GAP_TOTAL = 0.20
PAD = GAP_TOTAL / 2
MIN_PAUSE = 0.60
MIN_SEG = 2.0
ZOOM_IN = 1.5
SR = 16000
HOP = 0.01                 # 10 ms / khung năng lượng
EYE_LINE = 1 / 3           # mắt nằm trên đường 1/3 từ trên xuống (chuẩn bố cục điện ảnh)
EYE_LINES = {}             # {zoom: đường mắt} ghi đè riêng từng mức zoom (cut.json "eye_line_base")
SMOOTH_SEC = 0.8           # làm mượt chuyển động khung (camera bám nhân vật nhẹ nhàng)
FACE_STEP = 0.2            # giây giữa 2 lần dò mặt
ISLAND = 0.15              # mẩu năng lượng ngắn hơn giữa khoảng lặng = tiếng ồn, không phải lời
END_TAIL = 0.50            # đuôi video: giữ thêm 0.5s sau chữ cuối (không dừng đột ngột); lẹm tiếng / đổi cảnh → ngắn hơn


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, **kw)


def probe(video):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height,r_frame_rate:format=duration", "-of", "json", video],
                         capture_output=True, text=True, check=True).stdout
    j = json.loads(out)
    s = j["streams"][0]
    n, d = s["r_frame_rate"].split("/")
    return int(s["width"]), int(s["height"]), float(n) / float(d), float(j["format"]["duration"])


# ───────────────────────── âm thanh ─────────────────────────
def envelope(video):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", video, "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
    hop = int(SR * HOP)
    n = len(x) // hop
    rms = np.sqrt(np.mean(x[: n * hop].reshape(n, hop) ** 2, axis=1) + 1e-10)
    db = 20 * np.log10(rms)
    k = 5                                   # làm mượt 50 ms
    db = np.convolve(db, np.ones(k) / k, mode="same")
    return db


def speech_mask(db):
    floor = np.percentile(db, 10)
    loud = np.percentile(db, 90)
    thr = floor + 0.30 * (loud - floor)      # ngưỡng thích nghi theo từng video
    mask = db > thr
    # tiếng ồn (xe, gió, quạt) hay vọt lên vài nhịp giữa chỗ ngừng → mẩu "tiếng" < ISLAND giây coi là lặng,
    # nếu không một chỗ ngừng 1.5s sẽ bị chặt thành nhiều mẩu < 0.6s và bị bỏ sót
    isl = int(ISLAND / HOP)
    i, n = 0, len(mask)
    while i < n:
        if mask[i]:
            j = i
            while j < n and mask[j]:
                j += 1
            if j - i < isl:
                mask[i:j] = False
            i = j
        else:
            i += 1
    return mask, thr, floor, loud


def pauses_from_mask(mask, min_len):
    out, i, n = [], 0, len(mask)
    while i < n:
        if not mask[i]:
            j = i
            while j < n and not mask[j]:
                j += 1
            if (j - i) * HOP >= min_len:
                out.append((i * HOP, j * HOP))
            i = j
        else:
            i += 1
    return out


# ───────────────────────── khuôn mặt ─────────────────────────
def face_track(video, step=FACE_STEP):
    import cv2
    cas = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    prof = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_profileface.xml")
    cap = cv2.VideoCapture(video)
    fps = cap.get(cv2.CAP_PROP_FPS)
    sw, sh = cap.get(cv2.CAP_PROP_FRAME_WIDTH), cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    every = max(1, round(step * fps))
    scale = 960 / sw
    pts, f, last = [], 0, None
    while True:
        if f % every:
            if not cap.grab():
                break
            f += 1
            continue
        ok, fr = cap.read()
        if not ok:
            break
        g = cv2.cvtColor(cv2.resize(fr, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY)
        g = cv2.equalizeHist(g)
        faces = list(cas.detectMultiScale(g, 1.1, 5, minSize=(24, 24)))
        if not faces:
            faces = list(prof.detectMultiScale(g, 1.1, 4, minSize=(24, 24)))
            faces += [(g.shape[1] - x - w, y, w, h) for x, y, w, h in prof.detectMultiScale(cv2.flip(g, 1), 1.1, 4, minSize=(24, 24))]
        if faces:
            cands = [((x + w / 2) / g.shape[1], (y + h / 2) / g.shape[0], w / g.shape[1], h / g.shape[0])
                     for x, y, w, h in faces]
            pts.append((f / fps, cands))
        f += 1
    cap.release()
    if not pts:
        return []
    # lượt 2: vị trí "mặt thật" = trung vị của mặt TO NHẤT mỗi lần dò → mỗi lần chọn ứng viên gần đó nhất,
    # bỏ phát hiện nhầm (tấm che nắng, ghế, áo hoa…) — trước đây bám nhầm 1 vật là lệch khung cả đoạn
    big = np.array([max(c, key=lambda p: p[2]) for _, c in pts])
    med = np.median(big, axis=0)
    out = []
    for t, cands in pts:
        best = min(cands, key=lambda p: abs(p[0] - med[0]) + abs(p[1] - med[1]) + abs(p[2] - med[2]) * 2)
        if abs(best[0] - med[0]) < 0.25 and abs(best[1] - med[1]) < 0.2 and best[2] > med[2] * 0.6:
            out.append((t, *best))
    return out


def smooth_track(pts, dur, fps):
    """→ mảng (N,4) theo từng frame nguồn: cx, cy, fw, fh (chuẩn hóa)."""
    n = int(round(dur * fps)) + 2
    t = np.arange(n) / fps
    if not pts:
        return np.tile([0.5, 0.35, 0.08, 0.14], (n, 1))
    a = np.array(pts)
    cols = [np.interp(t, a[:, 0], a[:, k]) for k in range(1, 5)]
    arr = np.stack(cols, 1)
    # lọc nhiễu: median 1s rồi Gaussian SMOOTH_SEC
    win = max(1, int(fps))
    pad = np.pad(arr, ((win, win), (0, 0)), mode="edge")
    med = np.stack([np.median(pad[i:i + 2 * win + 1], 0) for i in range(n)])
    sig = SMOOTH_SEC * fps
    k = np.exp(-0.5 * (np.arange(-3 * sig, 3 * sig + 1) / sig) ** 2)
    k /= k.sum()
    out = np.stack([np.convolve(np.pad(med[:, c], len(k) // 2, mode="edge"), k, mode="valid")[:n] for c in range(4)], 1)
    return out


# ───────────────────────── analyze ─────────────────────────
def cmd_analyze(a):
    work = Path(a.out)
    work.mkdir(parents=True, exist_ok=True)
    sw, sh, fps, dur = probe(a.video)
    db = envelope(a.video)
    mask, thr, floor, loud = speech_mask(db)
    raw_mask = db > thr
    pauses = pauses_from_mask(mask, MIN_PAUSE)
    words = json.loads(Path(a.words).read_text(encoding="utf-8-sig"))["words"]
    # khoảng lặng thật = không có chữ nào bên trong (lời nói nhỏ dưới ngưỡng / tiếng ồn che chỗ ngừng)
    # lõi mỗi chữ = [s, s+0.45] vì mốc kết thúc của máy nhận giọng hay kéo dài qua chỗ ngừng
    cores = sorted((w["s"], min(w["e"], w["s"] + 0.45)) for w in words)
    # chỉ chữ có tiếng THẬT tại mốc của nó mới "giữ" khoảng lặng lại (máy nhận giọng hay đặt mốc chữ lọt vào chỗ im)
    cores = [(cs, ce) for cs, ce in cores if raw_mask[int(cs / HOP):int(ce / HOP) + 1].any()]
    refined = []
    for ps, pe in pauses:
        segs = [(ps, pe)]
        for cs, ce in cores:
            if ce <= ps or cs >= pe:
                continue
            nxt = []
            for a0, b0 in segs:
                if ce <= a0 or cs >= b0:
                    nxt.append((a0, b0))
                else:
                    if cs > a0:
                        nxt.append((a0, cs))
                    if ce < b0:
                        nxt.append((ce, b0))
            segs = nxt
        refined += [(a0, b0) for a0, b0 in segs if b0 - a0 >= MIN_PAUSE]
    # chỗ ngừng bị tiếng ồn / hơi thở "lấp": khoảng cách giữa 2 chữ có tiếng RÕ > MIN_PAUSE cũng là khoảng lặng
    loud_thr = thr + 0.45 * (loud - thr)
    lc = []
    for w in sorted(words, key=lambda x: x["s"]):
        i0, i1 = int(w["s"] / HOP), int(min(w["e"], w["s"] + 0.6) / HOP) + 1
        on = np.flatnonzero(db[i0:i1] > loud_thr)
        if len(on):
            lc.append(((i0 + on[0]) * HOP, (i0 + on[-1] + 1) * HOP))
    gap_pauses = [(a[1], b[0]) for a, b in zip(lc, lc[1:]) if b[0] - a[1] >= MIN_PAUSE]
    allp = sorted(refined + gap_pauses)
    pauses = []
    for ps, pe in allp:
        if pauses and ps <= pauses[-1][1]:
            pauses[-1] = (pauses[-1][0], max(pauses[-1][1], pe))
        else:
            pauses.append((ps, pe))
    # bó mép câu theo tiếng RÕ ∪ lõi chữ → mép câu không kéo dài vào tiếng ồn, không lẹm chữ nhỏ
    mask = db > loud_thr
    for cs, ce in cores:
        mask[int(cs / HOP):int(ce / HOP) + 1] = True
    # câu = đoạn nói giữa 2 khoảng lặng > MIN_PAUSE
    edges = [0.0] + [x for p in pauses for x in p] + [len(db) * HOP]
    spans = [(edges[i], edges[i + 1]) for i in range(0, len(edges), 2)]
    chunks = []
    idx = np.flatnonzero(mask)
    for s, e in spans:
        # bó sát tiếng nói (quan trọng ở đầu/cuối file, nơi không có khoảng lặng chặn)
        inside = idx[(idx >= int(s / HOP)) & (idx < int(e / HOP))]
        if len(inside) == 0:
            continue
        s, e = inside[0] * HOP, (inside[-1] + 1) * HOP
        if e - s < 0.08:
            continue
        ws = [w for w in words if s - 0.15 <= (w["s"] + w["e"]) / 2 <= e + 0.15]
        chunks.append({"i": len(chunks), "s": round(s, 2), "e": round(e, 2),
                       "text": " ".join(w["w"] for w in ws)})
    np.save(work / "envelope.npy", db)
    (work / "chunks.json").write_text(json.dumps({"video": str(a.video), "fps": fps, "size": [sw, sh],
                                                   "duration": dur, "threshold_db": thr, "chunks": chunks},
                                                  ensure_ascii=False, indent=1), encoding="utf-8")
    lines = [f"#{c['i']:>3} [{c['s']:7.2f} → {c['e']:7.2f}] ({c['e'] - c['s']:4.1f}s)  {c['text']}" for c in chunks]
    (work / "chunks.txt").write_text("\n".join(lines), encoding="utf-8")
    print(f"Âm thanh: nền {floor:.1f} dB, lớn {loud:.1f} dB, ngưỡng {thr:.1f} dB → {len(pauses)} khoảng lặng > {MIN_PAUSE}s, {len(chunks)} câu")
    if not a.no_face:
        pts = face_track(a.video)
        (work / "face.json").write_text(json.dumps({"fps": fps, "points": pts}), encoding="utf-8")
        print(f"Khuôn mặt: {len(pts)} điểm dò được")
    print(f"→ {work / 'chunks.txt'}")


# ───────────────────────── retext ─────────────────────────
def cmd_retext(a):
    """Nhận giọng LẠI từng câu (âm thanh cắt đúng mép câu) → mốc từ chính xác cả ở vùng quay đi quay lại."""
    import tempfile
    sys.path.insert(0, str(Path(__file__).parent))
    from cut_qa import model as whisper_model
    work = Path(a.work)
    cj = json.loads((work / "chunks.json").read_text(encoding="utf-8"))
    model = whisper_model(a.model)   # GPU nếu chạy được thật, không thì CPU
    words = []
    with tempfile.TemporaryDirectory() as tmp:
        for c in cj["chunks"]:
            s, e = max(0, c["s"] - 0.05), c["e"] + 0.05
            wav = Path(tmp) / f"c{c['i']}.wav"
            run(["ffmpeg", "-v", "error", "-y", "-ss", f"{s:.3f}", "-to", f"{e:.3f}", "-i", cj["video"],
                 "-ac", "1", "-ar", "16000", str(wav)])
            segs, _ = model.transcribe(str(wav), language="vi", word_timestamps=True, vad_filter=False,
                                       condition_on_previous_text=False)
            ws = [{"w": w.word.strip(), "s": round(s + w.start, 3), "e": round(s + w.end, 3)}
                  for sg in segs for w in (sg.words or []) if w.word.strip()]
            c["text"] = " ".join(w["w"] for w in ws)
            words += ws
    out = work / (a.out or "src_words.json")
    out.write_text(json.dumps({"words": words}, ensure_ascii=False, indent=1), encoding="utf-8")
    (work / "chunks.json").write_text(json.dumps(cj, ensure_ascii=False, indent=1), encoding="utf-8")
    lines = [f"#{c['i']:>3} [{c['s']:7.2f} → {c['e']:7.2f}] ({c['e'] - c['s']:4.1f}s)  {c['text']}" for c in cj["chunks"]]
    (work / "chunks.txt").write_text("\n".join(lines), encoding="utf-8")
    print(f"{len(words)} từ (nhận lại theo từng câu, model {a.model}) → {out}")


# ───────────────────────── lập danh sách đoạn ─────────────────────────
def build_segments(cut):
    """cut.json → danh sách đoạn giữ [{s,e,src_parts}] theo thời gian nguồn (đã đệm PAD)."""
    cj = json.loads(Path(cut["_dir"], "chunks.json").read_text(encoding="utf-8"))
    chunks = cj["chunks"]
    drop = set(cut.get("drop_chunks", []))
    trims = {int(k): v for k, v in cut.get("trim", {}).items()}   # {"12": [s, e]} cắt bớt đầu/cuối 1 câu
    drop_ranges = [tuple(r) for r in cut.get("drop_ranges", [])]    # cắt giữa câu (không có khoảng lặng)
    keep_ranges = [tuple(r) for r in cut.get("keep_ranges", [])]    # tùy chọn: chỉ giữ các vùng này (mốc nguồn)
    envp = Path(cut["_dir"], "envelope.npy")
    if envp.exists():   # bám mối cắt vào điểm âm thấp nhất trong ±0.15s (không cắt đứt chữ)
        db = np.load(envp)
        w = int(0.15 / HOP)

        def snap(t, toward):
            # chỉ dời mối cắt VỀ PHÍA PHẦN BỊ BỎ (toward=+1: sau t, -1: trước t) → không bao giờ lẹm vào chữ được giữ
            i = int(round(t / HOP))
            lo, hi = (i, min(len(db), i + w + 1)) if toward > 0 else (max(0, i - w), i + 1)
            j = lo + int(np.argmin(db[lo:hi]))
            snap_thr = json.loads(Path(cut["_dir"], "chunks.json").read_text(encoding="utf-8")).get("threshold_db", -30)
            return j * HOP if db[j] <= snap_thr else t      # không có chỗ im thật → giữ mốc gốc
        drop_ranges = [(snap(s, +1), snap(e, -1)) for s, e in drop_ranges]
    # 1) các mảnh nói được giữ
    pieces = []
    for c in chunks:
        if c["i"] in drop:
            continue
        s, e = trims.get(c["i"], (c["s"], c["e"]))
        parts = [(s, e)]
        if keep_ranges:      # chỉ giữ phần câu nằm trong keep_ranges (mốc nguồn, không phụ thuộc số thứ tự câu)
            parts = [(max(s, ks), min(e, ke)) for ks, ke in keep_ranges if min(e, ke) - max(s, ks) > 0.05]
        for rs, re_ in drop_ranges:
            nxt = []
            for ps, pe in parts:
                if re_ <= ps or rs >= pe:
                    nxt.append((ps, pe))
                else:
                    if rs > ps:
                        nxt.append((ps, rs))
                    if re_ < pe:
                        nxt.append((re_, pe))
            parts = nxt
        for ps, pe in parts:
            # hard = mép do drop_ranges tạo ra (cắt giữa câu), khác mép khoảng lặng tự nhiên của câu
            pieces.append({"s": ps, "e": pe, "chunk": c["i"], "hard_in": ps > s, "hard_out": pe < e})
    # 2) mỗi mảnh = 1 đoạn; đệm PAD ở mép có khoảng lặng.
    #    Mép cắt giữa câu: bỏ phần lặng dính ở mép rồi cũng đệm PAD → tổng lặng ở mối nối luôn ≈ 0.2s
    thr = cj.get("threshold_db")
    segs = []
    for p in pieces:
        s0, e0 = p["s"], p["e"]
        if envp.exists() and thr is not None:
            if p["hard_in"]:
                i = int(s0 / HOP)
                while i < int(e0 / HOP) and db[i] <= thr:
                    i += 1
                s0 = i * HOP
            if p["hard_out"]:
                i = int(e0 / HOP) - 1
                while i > int(s0 / HOP) and db[i] <= thr:
                    i -= 1
                e0 = (i + 1) * HOP
        # mép giữa câu chỉ được đệm bằng phần lặng vừa bỏ (không lẹm sang chữ của đoạn bị cắt)
        s = s0 - (min(PAD, s0 - p["s"]) if p["hard_in"] else PAD)
        e = e0 + (min(PAD, p["e"] - e0) if p["hard_out"] else PAD)
        segs.append({"s": max(0.0, s), "e": e, "chunks": [p["chunk"]], "contig_prev": False})
    # mảnh liền kề trong nguồn (2 câu nối nhau không bị bỏ gì giữa) → có thể gộp
    for i in range(1, len(segs)):
        a, b = pieces[i - 1], pieces[i]
        same_flow = (b["chunk"] == a["chunk"] + 1 and a["chunk"] not in drop) or (b["chunk"] == a["chunk"])
        segs[i]["contig_prev"] = bool(same_flow and not a["hard_out"] and not b["hard_in"])
    # 3) gộp đoạn < MIN_SEG với đoạn kề liền mạch (giữ nguyên khoảng lặng giữa chúng — KHÔNG cắt)
    changed = True
    while changed:
        changed = False
        for i, sg in enumerate(segs):
            if sg["e"] - sg["s"] >= MIN_SEG:
                continue
            left = i > 0 and sg["contig_prev"]
            right = i + 1 < len(segs) and segs[i + 1]["contig_prev"]
            if not (left or right):
                continue
            if left and right:   # gộp về phía đoạn ngắn hơn
                j = i - 1 if (segs[i - 1]["e"] - segs[i - 1]["s"]) <= (segs[i + 1]["e"] - segs[i + 1]["s"]) else i + 1
            else:
                j = i - 1 if left else i + 1
            lo, hi = min(i, j), max(i, j)
            m = {"s": segs[lo]["s"], "e": segs[hi]["e"], "chunks": segs[lo]["chunks"] + segs[hi]["chunks"],
                 "contig_prev": segs[lo]["contig_prev"]}
            segs[lo:hi + 1] = [m]
            changed = True
            break
    if segs and envp.exists() and thr is not None:
        extend_tail(segs[-1], cj, db, thr, float(cut.get("end_tail", END_TAIL)))
    for k, sg in enumerate(segs):
        # "base_zoom" (VD 1.15): đoạn lẻ phóng nhẹ để đẩy mặt lên cao, chừa chỗ cho chữ nhấn dưới cằm
        sg["zoom"] = float(cut.get("base_zoom", 1.0)) if k % 2 == 0 else float(cut.get("zoom_in", ZOOM_IN))
        sg["short"] = sg["e"] - sg["s"] < MIN_SEG
    return segs, chunks


def scene_cut_in(video, t0, t1):
    """Mốc đổi cảnh (cắt cứng) đầu tiên trong (t0, t1] của nguồn; không có → None."""
    import re
    try:
        out = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t0:.3f}", "-t", f"{t1 - t0 + 0.05:.3f}", "-i", video,
                              "-vf", "scale=320:-1,select='gt(scene,0.3)',metadata=print:file=-", "-an", "-f", "null", "-"],
                             capture_output=True, text=True, timeout=120).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    ts = [t0 + float(x) for x in re.findall(r"pts_time:([\d.]+)", out)]
    ts = [t for t in ts if t0 + 0.02 < t <= t1]
    return min(ts) if ts else None


def extend_tail(sg, cj, db, thr, tail):
    """Đoạn CUỐI video: giữ thêm `tail` giây sau chữ cuối để không dừng đột ngột.
    Chỉ cắt sớm hơn khi trong khoảng đó có tiếng mới chen vào (chữ kế, ồn, vỗ tay) hoặc đổi cảnh."""
    n = len(db)
    i = min(int(round(sg["e"] / HOP)), n) - 1
    while i > int(sg["s"] / HOP) and db[i] <= thr:      # lùi về hết tiếng nói thật
        i -= 1
    i_end = i + 1
    speech_end = i_end * HOP
    base = speech_end + PAD                               # mép kiểu cũ (sát chữ)
    loud_thr = thr + 0.45 * (np.percentile(db, 90) - thr)  # tiếng RÕ (như lời nói), cùng ngưỡng với analyze/review
    end, why = speech_end + tail, ""
    j = i_end
    while j < min(n, i_end + 15) and db[j] > thr:          # tiếng ngân / hồi âm của chữ cuối tắt dần (≤ 0.15s)
        j += 1
    if j < n and j == i_end + 15 and db[j] > thr:
        end, why = base, "tiếng ồn liền sau chữ cuối → cắt sát"
    else:
        for k in range(j, min(n, int((speech_end + tail) / HOP))):
            # tiếng mới chen vào: tiếng rõ ≥ 30 ms, hoặc tiếng cao hơn ngưỡng 3 dB liên tục ≥ 0.1s
            # (ồn nền quay ngoài trời dao động QUANH ngưỡng → không tính; đo thật: short "lò xo" 2026-09-29)
            if (db[k:k + 3] > loud_thr).all() or (db[k:k + 10] > thr + 3).all():
                end, why = max(base, k * HOP - 0.05), f"lẹm tiếng ở {k * HOP:.2f}s → cắt trước"
                break
    if cj.get("duration"):
        end = min(end, cj["duration"])
    video = cj.get("video")
    if video and Path(video).exists():
        sc = scene_cut_in(video, speech_end, end)
        if sc is not None:
            end, why = sc, f"đổi cảnh ở {sc:.2f}s → cắt trước"
    sg["e"] = end
    sg["tail"] = f"đuôi {end - speech_end:.2f}s sau chữ cuối" + (f" ({why})" if why else "")


def load_cut(path):
    p = Path(path)
    cut = json.loads(p.read_text(encoding="utf-8-sig"))
    cut["_dir"] = str(p.parent)
    return cut


def cmd_plan(a):
    cut = load_cut(a.cut)
    segs, chunks = build_segments(cut)
    ctext = {c["i"]: c["text"] for c in chunks}
    t = 0.0
    for k, sg in enumerate(segs):
        d = sg["e"] - sg["s"]
        warn = "  ⚠ < 2s (không có đoạn kề liền mạch để gộp)" if sg["short"] else ""
        print(f"{k + 1:>3}. out {t:7.2f}  src {sg['s']:7.2f}→{sg['e']:7.2f} ({d:4.1f}s) zoom {int(sg['zoom'] * 100)}%{warn}")
        print("      " + " / ".join(ctext[c] for c in dict.fromkeys(sg["chunks"]))[:220])
        if sg.get("tail"):
            print(f"      ⏹ {sg['tail']}")
        t += d
    print(f"Tổng: {len(segs)} đoạn, {t:.1f}s")


# ───────────────────────── review (duyệt lần 2) ─────────────────────────
FILLERS = {"ờ", "à", "ừ", "ừm", "ờm", "ơ", "ư", "hừm", "ùm", "ậm"}


def cmd_review(a):
    """Duyệt bản cắt: chỗ ngừng còn sót, cụm lặp (quay lại / nhắc ý), nói vấp, từ đệm, chữ bị lẹm ở mép cắt."""
    import re
    cut = load_cut(a.cut)
    work = Path(cut["_dir"])
    segs, _ = build_segments(cut)
    cj = json.loads((work / "chunks.json").read_text(encoding="utf-8"))
    thr = cj.get("threshold_db", -30)
    db = np.load(work / "envelope.npy")
    words = json.loads((work / cut["words"]).read_text(encoding="utf-8-sig"))["words"]
    loud = np.percentile(db, 90)
    loud_thr = thr + 0.45 * (loud - thr)
    norm = lambda s: re.sub(r"[^\wÀ-ỹ]+", "", s.lower())
    kept, offs, off = [], [], 0.0      # (chữ, src_s, out_s, seg)
    for k, sg in enumerate(segs):
        offs.append(off)
        for w in words:
            if sg["s"] - 0.08 <= w["s"] < sg["e"] - 0.08:
                kept.append((w, w["s"], w["s"] - sg["s"] + off, k))
        off += sg["e"] - sg["s"]
    issues = []
    # 1) chỗ ngừng > MIN_PAUSE giữa 2 chữ có tiếng rõ, cùng một đoạn (chưa cắt)
    def lcore(w):
        i0, i1 = int(w["s"] / HOP), int(min(w["e"], w["s"] + 0.6) / HOP) + 1
        on = np.flatnonzero(db[i0:i1] > loud_thr)
        return None if not len(on) else ((i0 + on[0]) * HOP, (i0 + on[-1] + 1) * HOP)
    prev = None
    for w, s, o, k in kept:
        c = lcore(w)
        if c is None:
            continue
        if prev and prev[3] == k and c[0] - prev[1] > MIN_PAUSE:
            short = [i for i, sg in enumerate(segs) if i == k and len(sg["chunks"]) > 1]
            why = " (đoạn gộp vì mẩu < 2s → cân nhắc thay lần nói khác / bỏ mẩu ngắn)" if short else ""
            issues.append((prev[2], f"NGỪNG {c[0] - prev[1]:.2f}s  src {prev[1]:.2f}→{c[0]:.2f}  '{prev[4]} … {w['w']}'{why}"))
        prev = (c[0], c[1], o, k, w["w"])
    toks = [(norm(w["w"]), o, s) for w, s, o, k in kept]
    # 2) nói vấp: cùng 1–2 từ lặp liền nhau
    for i in range(1, len(toks)):
        if toks[i][0] and toks[i][0] == toks[i - 1][0] and toks[i][0] not in ("là", "và", "các", "nhiều"):
            issues.append((toks[i][1], f"VẤP/LẶP TỪ '{toks[i][0]} {toks[i][0]}'  src {toks[i - 1][2]:.2f}"))
        if i >= 3 and toks[i][0] and toks[i - 1][0] and (toks[i - 1][0], toks[i][0]) == (toks[i - 3][0], toks[i - 2][0]):
            issues.append((toks[i][1], f"VẤP/LẶP CỤM '{toks[i - 1][0]} {toks[i][0]}' ×2  src {toks[i - 3][2]:.2f}"))
    # 3) cụm ≥ 4 từ xuất hiện 2 lần trong 90s → quay lại / nhắc ý (lần TRƯỚC là ứng viên bỏ)
    # (cụm 5 từ trong 60s: quay lại thường sát nhau; chủ đề nhắc lại cách xa thì không báo)
    seen = {}
    n = 5
    reported = set()
    for i in range(len(toks) - n + 1):
        g = tuple(t[0] for t in toks[i:i + n])
        if not all(g):
            continue
        if g in seen and toks[i][1] - seen[g][1] < 60 and seen[g][0] not in reported:
            j = seen[g][0]
            issues.append((toks[j][1], f"TRÙNG CỤM '{' '.join(g)}'  lần 1 src {toks[j][2]:.2f} · lần 2 src {toks[i][2]:.2f} → xem có phải nói lại ý (giữ lần sau)"))
            reported.add(j)
        seen.setdefault(g, (i, toks[i][1]))
    # 4) từ đệm
    for t, o, s in toks:
        if t in FILLERS:
            issues.append((o, f"TỪ ĐỆM '{t}'  src {s:.2f}"))
    # 5) chữ vắt qua mối cắt (có thể bị lẹm)
    for k, sg in enumerate(segs):
        for w in words:
            c = lcore(w)                     # dùng TIẾNG THẬT của chữ (mốc máy nhận giọng hay kéo dài → báo nhầm)
            if c is None:
                continue
            ws, we = c
            for edge, kind in ((sg["s"], "đầu"), (sg["e"], "cuối")):
                if ws < edge < we and 0.06 < (edge - ws) and 0.06 < (we - edge):
                    issues.append((offs[k] + (0 if kind == "đầu" else sg["e"] - sg["s"]),
                                   f"CHỮ VẮT MÉP {kind} đoạn {k + 1}: '{w['w']}' src {ws:.2f}–{we:.2f} (cắt ở {edge:.2f})"))
    # 6) mẩu thừa ở mép đoạn: một mẩu tiếng ngắn (≤ 0.35s) rồi khoảng lặng ≥ 0.25s ngay đầu/cuối đoạn
    #    = đuôi/đầu của chữ bị cắt (VD còn sót "mà…" kéo dài trước lần nói lại)
    quiet = db <= thr
    for k, sg in enumerate(segs):
        i0, i1 = int(sg["s"] / HOP), int(sg["e"] / HOP)
        head = quiet[i0:min(i1, i0 + 80)]
        if len(head) and not head[0]:
            j = np.argmax(head) if head.any() else len(head)          # hết mẩu tiếng đầu
            run = 0
            while j + run < len(head) and head[j + run]:
                run += 1
            if 0 < j <= 35 and run >= 25:
                issues.append((offs[k], f"MẨU THỪA đầu đoạn {k + 1}: tiếng {j * HOP:.2f}s rồi lặng {run * HOP:.2f}s "
                                        f"(src {sg['s']:.2f}) → dời mốc cắt tới {(i0 + j + run) * HOP - PAD:.2f}"))
        tail = quiet[max(i0, i1 - 80):i1][::-1]
        if len(tail) and not tail[0]:
            j = np.argmax(tail) if tail.any() else len(tail)
            run = 0
            while j + run < len(tail) and tail[j + run]:
                run += 1
            if 0 < j <= 35 and run >= 25:
                issues.append((offs[k] + sg["e"] - sg["s"], f"MẨU THỪA cuối đoạn {k + 1}: lặng {run * HOP:.2f}s rồi tiếng "
                                                            f"{j * HOP:.2f}s (src {sg['e']:.2f}) → dời mốc cắt về {(i1 - j - run) * HOP + PAD:.2f}"))
    issues.sort()
    lines = [f"[out {o:7.2f}] {msg}" for o, msg in issues]
    (work / "review.txt").write_text("\n".join(lines) or "Sạch — không còn chỗ cần xem.", encoding="utf-8")
    print("\n".join(lines) if lines else "Sạch — không còn chỗ cần xem.")
    print(f"\n{len(issues)} mục cần xem · {len(segs)} đoạn · {off:.1f}s → {work / 'review.txt'}")


# ───────────────────────── render ─────────────────────────
def crop_rect(sw, sh, aspect, zoom, face):
    """face = (cx, cy, fw, fh) chuẩn hóa → (x, y, w, h) pixel nguồn."""
    if aspect == "16x9":
        bw, bh = sw, sh
    else:
        bh = sh
        bw = round(sh * 9 / 16)
    w, h = bw / zoom, bh / zoom
    cx, cy, fw, fh = face
    fx, fy, fhp = cx * sw, cy * sh, fh * sh
    eye = fy - 0.12 * fhp                      # mắt cao hơn tâm hộp mặt một chút
    x = fx - w / 2                             # mặt giữa khung theo chiều ngang
    y = eye - h * EYE_LINES.get(zoom, EYE_LINE) if zoom > 1 or h < sh else 0
    if aspect == "16x9" and zoom == 1:
        x, y = 0, 0                            # đoạn 100% khung ngang: giữ nguyên
    x = min(max(0, x), sw - w)
    y = min(max(0, y), sh - h)
    return x, y, w, h


def cmd_render(a):
    import cv2
    global EYE_LINE
    cut = load_cut(a.cut)
    EYE_LINE = float(cut.get("eye_line", EYE_LINE))   # VD 0.27: mặt cao hơn, chữ nhấn nằm dưới cằm
    if "eye_line_base" in cut:                         # đường mắt riêng cho đoạn lẻ (base_zoom)
        EYE_LINES[float(cut.get("base_zoom", 1.0))] = float(cut["eye_line_base"])
    work = Path(cut["_dir"])
    segs, _ = build_segments(cut)
    sw, sh, fps, dur = probe(a.video)
    fj = json.loads((work / "face.json").read_text()) if (work / "face.json").exists() else {"points": []}
    track = smooth_track(fj["points"], dur, fps)
    aspects = ["16x9", "9x16"] if a.aspect == "both" else [a.aspect]
    if sh > sw:                      # gốc quay dọc → chỉ xuất bản dọc (A6)
        aspects = ["9x16"]
    sizes = {"16x9": (1920, 1080) if (a.preview or sw < 1920) else (sw, sh),
             "9x16": (1080, 1920) if a.preview else (2160, 3840)}
    tag = "_preview" if a.preview else ""

    # âm thanh: ghép các đoạn, fade 8 ms ở mép để không lụp bụp
    parts = []
    for k, sg in enumerate(segs):
        parts.append(f"[0:a]atrim={sg['s']:.3f}:{sg['e']:.3f},asetpts=PTS-STARTPTS,"
                     f"afade=t=in:d=0.008,afade=t=out:st={sg['e'] - sg['s'] - 0.008:.3f}:d=0.008[a{k}]")
    fc = ";".join(parts) + ";" + "".join(f"[a{k}]" for k in range(len(segs))) + f"concat=n={len(segs)}:v=0:a=1[a]"
    wav = work / "cut_audio.wav"
    (work / "audio_fc.txt").write_text(fc, encoding="utf-8")
    run(["ffmpeg", "-v", "error", "-y", "-i", a.video, "-filter_complex_script", str(work / "audio_fc.txt"),
         "-map", "[a]", "-ar", "48000", str(wav)])

    # hình: đọc tuần tự, chọn frame thuộc đoạn giữ, crop + scale, đẩy vào ffmpeg
    # GPU NVIDIA → NVENC (nhanh, CPU rảnh cho bước crop/scale); không có thì libx264
    if "h264_nvenc" in subprocess.run(["ffmpeg", "-hide_banner", "-encoders"], capture_output=True, text=True).stdout:
        enc = ["-c:v", "h264_nvenc", "-preset", "p5", "-rc", "vbr", "-cq", "23" if a.preview else "16", "-b:v", "0"]
    else:   # Mac → VideoToolbox; còn lại libx264
        enc = _mac_vt(a.preview) or ["-c:v", "libx264"] + (["-preset", "veryfast", "-crf", "23"] if a.preview else ["-preset", "medium", "-crf", "15"])
    procs = {}
    for asp in aspects:
        ow, oh = sizes[asp]
        out = work / f"cut_{asp}{tag}.mp4"
        procs[asp] = subprocess.Popen(
            ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{ow}x{oh}",
             "-r", f"{fps}", "-i", "-", "-i", str(wav), "-map", "0:v", "-map", "1:a", *enc,
             "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(out)],
            stdin=subprocess.PIPE)
    ranges = [(round(sg["s"] * fps), round(sg["e"] * fps), sg["zoom"]) for sg in segs]
    cap = cv2.VideoCapture(a.video)
    f, ri, written = 0, 0, 0
    total = sum(b - a_ for a_, b, _ in ranges)
    while ri < len(ranges):
        fa, fb, z = ranges[ri]
        if f >= fb:
            ri += 1
            continue
        if f < fa:
            if not cap.grab():
                break
            f += 1
            continue
        ok, fr = cap.read()
        if not ok:
            break
        face = track[min(f, len(track) - 1)]
        for asp in aspects:
            ow, oh = sizes[asp]
            x, y, w, h = crop_rect(sw, sh, asp, z, face)
            x0, y0 = int(round(x)), int(round(y))
            sub = fr[y0:y0 + int(round(h)), x0:x0 + int(round(w))]
            interp = cv2.INTER_AREA if sub.shape[1] >= ow else cv2.INTER_LANCZOS4
            img = cv2.resize(sub, (ow, oh), interpolation=interp)
            procs[asp].stdin.write(img.tobytes())
        written += 1
        if written % 300 == 0:
            print(f"  {written}/{total} frame", flush=True)
        f += 1
    cap.release()
    for p in procs.values():
        p.stdin.close()
        p.wait()

    off = write_words(cut, segs, work)
    print(f"Xong: {len(segs)} đoạn, {off:.1f}s → " + ", ".join(str(work / f'cut_{x}{tag}.mp4') for x in aspects))
    print(f"Sub đã dời mốc → {work / 'words.json'}")


def write_words(cut, segs, work):
    """Sub cho video đã cắt: mỗi chữ thuộc về đoạn chứa PHẦN LỚN thời lượng của nó (mốc máy nhận giọng hay lệch
    sớm/kéo dài ở mép đoạn → gán theo điểm giữa làm rơi chữ đầu/cuối đoạn)."""
    words = json.loads(Path(cut["words"] if Path(cut["words"]).is_absolute() else work / cut["words"])
                       .read_text(encoding="utf-8-sig"))["words"]
    offs, off = [], 0.0
    for sg in segs:
        offs.append(off)
        off += sg["e"] - sg["s"]
    out_w = []
    for w in words:
        ws, we = w["s"], min(w["e"], w["s"] + 0.6)
        dur = max(0.05, we - ws)
        best = max(range(len(segs)), key=lambda k: min(we, segs[k]["e"]) - max(ws, segs[k]["s"]))
        sg = segs[best]
        if (min(we, sg["e"]) - max(ws, sg["s"])) / dur < 0.35:
            continue
        o = offs[best]
        out_w.append({"w": w["w"], "s": round(max(0, ws - sg["s"]) + o, 3),
                      "e": round(min(sg["e"] - sg["s"], w["e"] - sg["s"]) + o, 3)})
    out_w.sort(key=lambda x: x["s"])
    seg_out = [{"out_s": round(o, 3), "out_e": round(o + sg["e"] - sg["s"], 3), "src_s": round(sg["s"], 3),
                "src_e": round(sg["e"], 3), "zoom": sg["zoom"]} for o, sg in zip(offs, segs)]
    (work / "words.json").write_text(json.dumps({"words": out_w}, ensure_ascii=False, indent=1), encoding="utf-8")
    (work / "segments.json").write_text(json.dumps(seg_out, indent=1), encoding="utf-8")
    return off


def cmd_words(a):
    cut = load_cut(a.cut)
    segs, _ = build_segments(cut)
    off = write_words(cut, segs, Path(cut["_dir"]))
    print(f"Sub đã dời mốc ({len(segs)} đoạn, {off:.1f}s) → {Path(cut['_dir']) / 'words.json'}")


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(required=True)
    p = sp.add_parser("analyze")
    p.add_argument("video"); p.add_argument("words"); p.add_argument("-o", "--out", required=True)
    p.add_argument("--no-face", action="store_true")
    p.set_defaults(f=cmd_analyze)
    p = sp.add_parser("retext")
    p.add_argument("work"); p.add_argument("--model", default="medium"); p.add_argument("-o", "--out")
    p.set_defaults(f=cmd_retext)
    p = sp.add_parser("review")
    p.add_argument("cut")
    p.set_defaults(f=cmd_review)
    p = sp.add_parser("words")
    p.add_argument("cut")
    p.set_defaults(f=cmd_words)
    p = sp.add_parser("plan")
    p.add_argument("cut")
    p.set_defaults(f=cmd_plan)
    p = sp.add_parser("render")
    p.add_argument("video"); p.add_argument("cut"); p.add_argument("-o", "--out")
    p.add_argument("--aspect", default="both", choices=["both", "16x9", "9x16"])
    p.add_argument("--preview", action="store_true")
    p.set_defaults(f=cmd_render)
    a = ap.parse_args()
    a.f(a)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()

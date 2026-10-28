# Chèn footage B-roll toàn màn hình lên video nói chuyện — tiếng gốc chạy liên tục, footage tắt tiếng.
# Mọi mép tính theo SỐ FRAME (không theo giây) → không lọt 1 frame góc máy khác.
#
#   python broll.py split  <work>        → dò cắt cảnh file footage: broll_clips.json, foot_scenes.txt, qa/broll_index.jpg
#   python broll.py cuts   <work>        → dò điểm đổi góc máy video chính: main_scenes.txt
#   python broll.py check  <work>        → kiểm tra luật chèn + mép theo frame
#   python broll.py render <work> [--to 90]  → base_16x9.mp4 (hoặc base_test.mp4) — NVENC
#
#   python broll.py stable <work>        → độ rung từng footage + khúc ổn định nhất (broll_shake.npy, qa/broll_shake.txt)
#
# <work>/broll.json:
# {"main": "main_enh.mp4", "footage": "C:/.../30 footage.mp4",
#  "sched": [[24.5, 5, "auto", 6.0, "đủ nắng đủ gió"], ...]}  # [mốc video chính, footage #, vào từ giây | "auto", dài, lý do]
#  "auto" = tự chọn khúc ÍT RUNG nhất của footage (bỏ 0.5s đầu/cuối clip — lúc bấm/tắt máy hay rung)
import json, os, re, subprocess, sys

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

FPS_DEFAULT = 30
SNAP = 6          # mép footage cách điểm đổi góc ≤ 6 frame → bám đúng frame đổi góc
MIN_PIECE = 8     # mảnh hình thấy được (nói hoặc footage) phải ≥ 8 frame
FOOT_MARGIN = 0.2 # điểm vào footage cách vi cắt (điểm số ≥ 0.05) trong file footage ≥ 6 frame
PRE = 10          # tua sớm 10 frame rồi bỏ — frame đầu sau -ss hay bị lệch (giật 1 frame)
TALK_MIN, TALK_MAX = 6.5, 31.0   # đoạn nói giữa 2 khối footage (giây)
EDGE_SKIP = 0.5   # giây đầu/cuối mỗi clip footage: hay rung (bấm máy / tắt máy) → không chọn
SHAKE_SMOOTH = 15 # frame: chuyển động mượt (lia máy có chủ đích) = trung bình trượt; RUNG = phần lệch khỏi nó
SHAKE_WARN = 1.5  # khúc đang chọn rung gấp ≥ 1.5 lần khúc ổn định nhất của cùng footage → cảnh báo


def ff(*a):
    subprocess.run(["ffmpeg", "-hide_banner", *a], check=True)


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=r_frame_rate:format=duration", "-of", "json", path],
                         capture_output=True, text=True, check=True).stdout
    d = json.loads(out); n, m = d["streams"][0]["r_frame_rate"].split("/")
    return float(d["format"]["duration"]), round(int(n) / int(m))


def scenes(src, out, thr=0.06):
    """điểm cắt cảnh (frame đầu của cảnh mới) + điểm số → file metadata"""
    tmp = "scenes_tmp.txt"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-hwaccel", "auto", "-i", src, "-vf",
                    f"scale=320:-1,select='gt(scene,{thr})',metadata=print:file={tmp}", "-an", "-f", "null", "-"],
                   check=True)
    os.replace(tmp, out)


def shake_track(src):
    """độ rung từng frame (px ở khung 320×180): dịch chuyển toàn khung giữa 2 frame (phaseCorrelate)
    trừ phần chuyển động mượt → lia máy đều không bị tính là rung, tay run / bước chân thì có"""
    import cv2, numpy as np
    W, H = 320, 180
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-hwaccel", "auto", "-i", src, "-vf", f"scale={W}:{H}",
                          "-pix_fmt", "gray", "-f", "rawvideo", "-"], stdout=subprocess.PIPE)
    win = cv2.createHanningWindow((W, H), cv2.CV_32F)
    d, prev = [], None
    while True:
        buf = p.stdout.read(W * H)
        if len(buf) < W * H:
            break
        g = np.frombuffer(buf, np.uint8).reshape(H, W).astype(np.float32)
        d.append((0.0, 0.0) if prev is None else cv2.phaseCorrelate(prev, g, win)[0])
        prev = g
    p.wait()
    d = np.clip(np.array(d, dtype=np.float32), -20, 20)          # chỗ cắt cảnh cho số rác → chặn
    k = np.ones(SHAKE_SMOOTH) / SHAKE_SMOOTH
    sm = np.stack([np.convolve(np.pad(d[:, c], SHAKE_SMOOTH // 2, mode="edge"), k, mode="valid")[:len(d)]
                   for c in range(2)], 1)
    return np.hypot(*(d - sm).T)


def read_cuts(path, fps, min_score=0.0):
    txt = open(path, encoding="utf-8", errors="ignore").read()
    return [(round(float(t) * fps), float(s)) for t, s in
            re.findall(r"pts_time:([\d.]+)\s*\n\S*?scene_score=([\d.]+)", txt) if float(s) >= min_score]


class Job:
    def __init__(self, work):
        self.W = work
        self.cfg = json.load(open(os.path.join(work, "broll.json"), encoding="utf-8-sig"))
        self.main = os.path.join(work, self.cfg["main"])
        self.foot = self.cfg["footage"]
        self.dur, self.fps = probe(self.main)
        cp = os.path.join(work, "broll_clips.json")
        self.clips = {c["id"]: c for c in json.load(open(cp))} if os.path.exists(cp) else {}
        self.sched = [tuple(x[:4]) for x in self.cfg.get("sched", [])]

    # ── footage ──
    def split(self):
        scenes(self.foot, os.path.join(self.W, "foot_scenes.txt"))
        fdur, ffps = probe(self.foot)
        hard = [f / ffps for f, s in read_cuts(os.path.join(self.W, "foot_scenes.txt"), ffps, 0.3)]
        cuts, clips = [0.0] + hard + [fdur], []
        for a, b in zip(cuts, cuts[1:]):
            s, e = a + 0.1, b - 0.1
            if e - s >= 2.5:     # mẩu chuyển cảnh mờ → bỏ
                clips.append({"id": len(clips) + 1, "s": round(s, 3), "e": round(e, 3)})
        json.dump(clips, open(os.path.join(self.W, "broll_clips.json"), "w"), indent=1)
        os.makedirs(os.path.join(self.W, "qa"), exist_ok=True)
        if sys.platform == "darwin":
            font = "fontfile='/System/Library/Fonts/Supplemental/Arial Bold.ttf'"
        else:
            font = "fontfile='C\\:/Windows/Fonts/arialbd.ttf'"
        ins, fl = [], []
        for k, c in enumerate(clips):
            ins += ["-ss", str((c["s"] + c["e"]) / 2), "-i", self.foot]
            fl.append(f"[{k}:v]trim=end_frame=1,scale=400:-1,drawtext={font}:text='#{c['id']} {c['e']-c['s']:.0f}s'"
                      f":x=8:y=8:fontsize=34:fontcolor=yellow:box=1:boxcolor=black[v{k}]")
        n = len(clips)
        fl.append("".join(f"[v{k}]" for k in range(n)) + f"xstack=inputs={n}:layout=" +
                  "|".join(f"{(k % 6) * 400}_{(k // 6) * 225}" for k in range(n)) + ":fill=black[o]")
        ff("-loglevel", "error", "-y", *ins, "-filter_complex", ";".join(fl), "-map", "[o]", "-frames:v", "1",
           os.path.join(self.W, "qa", "broll_index.jpg"))
        print(n, "footage →", os.path.join(self.W, "qa", "broll_index.jpg"))
        print("⚠ Đếm lại với số footage người dùng nói; lệch → xem qa/broll_index.jpg, sửa broll_clips.json bằng tay.")
        self.clips = {c["id"]: c for c in clips}
        self.stable()

    # ── độ rung ──
    def shake(self):
        if not hasattr(self, "_sh"):
            import numpy as np
            p = os.path.join(self.W, "broll_shake.npy")
            if not os.path.exists(p):
                print("đo độ rung footage…", flush=True)
                np.save(p, shake_track(self.foot))
            self._sh = np.load(p)
            self._ffps = probe(self.foot)[1]
        return self._sh, self._ffps

    def win_score(self, a, d):
        """điểm rung của khúc [a, a+d] (giây nguồn footage): trung bình + nửa giây rung NHẤT trong khúc
        (1 cú giật ngắn ở đầu clip không bị trung bình cả khúc pha loãng) — càng thấp càng ổn định"""
        import numpy as np
        sh, ffps = self.shake()
        x = sh[round(a * ffps):round((a + d) * ffps)]
        if not len(x):
            return float("inf")
        n = max(1, min(len(x), round(0.5 * ffps)))
        worst = np.convolve(x, np.ones(n) / n, mode="valid").max()
        return float(0.5 * (x.mean() + worst))

    def stable_in(self, c, d, avoid=()):
        """khúc dài d ít rung nhất trong clip c, bỏ EDGE_SKIP đầu/cuối, tránh khúc đã dùng + vi cắt
        → (vào từ giây tính từ đầu clip, điểm rung)"""
        s, e = self.clips[c]["s"], self.clips[c]["e"]
        lo, hi = s + EDGE_SKIP, e - EDGE_SKIP - d
        if hi < lo:                      # clip ngắn: chia đều phần bỏ ở 2 đầu
            lo = hi = max(s, (s + e - d) / 2)
        cuts, best, fallback = self.foot_cuts(), None, None
        for k in range(int(round((hi - lo) / 0.1)) + 1):
            a = lo + k * 0.1
            if any(a - FOOT_MARGIN < t <= a + d + FOOT_MARGIN for t in cuts):
                continue
            sc = self.win_score(a, d)
            if fallback is None or sc < fallback[0]:
                fallback = (sc, a)
            if not any(a < ve and a + d > vs for vs, ve in avoid) and (best is None or sc < best[0]):
                best = (sc, a)
        sc, a = best or fallback or (self.win_score(lo, d), lo)
        return round(a - s, 2), sc

    def resolved(self):
        """lịch với 'auto' đã thay bằng điểm vào ít rung nhất; footage dùng lại → khúc khác, không trùng"""
        if not hasattr(self, "_res"):
            used = {}
            for t, c, o, d in self.sched:
                if o not in (None, "auto"):
                    used.setdefault(c, []).append((self.clips[c]["s"] + o, self.clips[c]["s"] + o + d))
            out = []
            for t, c, o, d in self.sched:
                if o in (None, "auto"):
                    o = self.stable_in(c, d, used.get(c, []))[0]
                    used.setdefault(c, []).append((self.clips[c]["s"] + o, self.clips[c]["s"] + o + d))
                out.append((t, c, o, d))
            self._res = out
        return self._res

    def stable(self):
        """bảng độ rung mỗi clip: đầu 0.5s · giữa · cuối 0.5s · khúc 6s ổn định nhất → qa/broll_shake.txt"""
        lines = ["#   dài   rung đầu  giữa  cuối   khúc 6s ổn định nhất (vào từ giây, tính từ đầu clip)"]
        for c, cl in sorted(self.clips.items()):
            s, e = cl["s"], cl["e"]
            L = e - s
            mid = self.win_score(s + EDGE_SKIP, max(0.1, L - 2 * EDGE_SKIP))
            o, sc = self.stable_in(c, min(6.0, L - 0.2))
            lines.append(f"#{c:<3}{L:5.1f}s  {self.win_score(s, EDGE_SKIP):6.2f} {mid:6.2f} "
                         f"{self.win_score(e - EDGE_SKIP, EDGE_SKIP):6.2f}   {o:5.2f}s (điểm {sc:.2f})")
        os.makedirs(os.path.join(self.W, "qa"), exist_ok=True)
        open(os.path.join(self.W, "qa", "broll_shake.txt"), "w", encoding="utf-8").write("\n".join(lines))
        print("\n".join(lines))
        print("→ lịch dùng \"auto\" ở cột 'vào từ giây' để tự lấy khúc ít rung nhất")

    def cuts(self):
        scenes(self.main, os.path.join(self.W, "main_scenes.txt"))
        c = read_cuts(os.path.join(self.W, "main_scenes.txt"), self.fps, 0.2)
        print(len(c), "điểm đổi góc:", " ".join(f"{f / self.fps:.3f}" for f, _ in c))

    # ── lịch theo frame ──
    def main_cuts(self):
        return [f for f, _ in read_cuts(os.path.join(self.W, "main_scenes.txt"), self.fps, 0.2)]

    def frame_plan(self):
        """→ [(F0, F1, src_in_giây, clip)] — F1 không tính; khối nối liền dùng chung mép; mép khối bám điểm đổi góc"""
        fps, cuts = self.fps, self.main_cuts()
        it = [[round(t * fps), round((t + d) * fps), self.clips[c]["s"] + o, c] for t, c, o, d in self.resolved()]
        for a, b in zip(it, it[1:]):
            if abs(a[1] - b[0]) <= 2:
                a[1] = b[0]
        starts = {i for i in range(len(it)) if i == 0 or it[i - 1][1] != it[i][0]}
        ends = {i for i in range(len(it)) if i == len(it) - 1 or it[i][1] != it[i + 1][0]}
        for idx, side in [(i, 0) for i in starts] + [(i, 1) for i in ends]:
            near = [c for c in cuts if abs(c - it[idx][side]) <= SNAP]
            if near:
                it[idx][side] = min(near, key=lambda c: abs(c - it[idx][side]))
        # file footage ghép sẵn thường có "vi cắt" 1–2 frame ở chỗ chuyển clip; tua (-ss) lệch ±1 frame
        # → điểm vào footage phải cách mọi vi cắt ≥ FOOT_MARGIN giây
        for x in it:
            for t in self.foot_cuts():
                if x[2] - FOOT_MARGIN < t <= x[2] + FOOT_MARGIN:
                    x[2] = t + FOOT_MARGIN
        return [tuple(x) for x in it]

    def foot_cuts(self):
        if not hasattr(self, "_fc"):
            p = os.path.join(self.W, "foot_scenes.txt")
            allc = read_cuts(p, self.fps, 0.05) if os.path.exists(p) else []
            hard = [f for f, s in allc if s >= 0.2]
            # cắt thật (≥ 0.2) + vi cắt sát cắt thật (≤ 12 frame); điểm thấp giữa cảnh = chuyển động → bỏ
            self._fc = [f / self.fps for f, s in allc if s >= 0.2 or any(abs(f - h) <= 12 for h in hard)]
        return self._fc

    def check(self):
        ok, fps = True, self.fps
        for t, c, o, d in self.sched:
            if not 4 <= d <= 8:
                print(f"   {t}: #{c} dài {d}s (ngoài 4–8s — chỉ được khi nối liền cảnh khác)")
        items = self.frame_plan()
        blocks, prev = [], 0
        for F0, F1, *_ in items:
            if blocks and blocks[-1][1] == F0:
                blocks[-1][1] = F1
            else:
                blocks.append([F0, F1])
        for F0, F1 in blocks:
            talk = (F0 - prev) / fps
            if talk < TALK_MIN or talk > TALK_MAX:
                print(f"!! đoạn nói {prev / fps:.1f}–{F0 / fps:.1f} dài {talk:.1f}s"); ok = ok and talk >= TALK_MIN
            prev = F1
        # mảnh hình thấy được: mép footage + điểm đổi góc KHÔNG bị footage che
        cuts = self.main_cuts()
        hidden = lambda c: any(a < c < b for a, b, *_ in items)
        vis = sorted({x for i in items for x in i[:2]} | {c for c in cuts if not hidden(c)} | {0, round(self.dur * fps)})
        for a, b in zip(vis, vis[1:]):
            if 0 < b - a < MIN_PIECE:
                print(f"!! mảnh {b - a} frame @ {a / fps:.3f}–{b / fps:.3f}s"); ok = False
        for F0, F1, src, c in items:
            n = F1 - F0
            inside = [round(t, 3) for t in self.foot_cuts() if src - FOOT_MARGIN < t <= src + (n + 1) / fps]
            if inside:
                print(f"!! footage #{c} @ {F0 / fps:.2f}s chứa điểm cắt cảnh ở nguồn {inside}"); ok = False
            if src + n / fps > self.clips[c]["e"] + 0.1:
                print(f"!! footage #{c} @ {F0 / fps:.2f}s thiếu {(src + n / fps - self.clips[c]['e']):.2f}s"); ok = False
        # độ rung: khúc đang dùng so với khúc ổn định nhất của cùng footage
        for (t, c, o, d), raw in zip(self.resolved(), self.sched):
            sc = self.win_score(self.clips[c]["s"] + o, d)
            best_o, best = self.stable_in(c, d)
            tag = "auto" if raw[2] in (None, "auto") else "tay"
            if sc > SHAKE_WARN * best + 0.05:
                print(f"!! rung: footage #{c} @ {t}s vào từ {o:.2f}s ({tag}) điểm {sc:.2f} — "
                      f"khúc ổn định nhất vào từ {best_o:.2f}s điểm {best:.2f} → đổi sang \"auto\" hoặc {best_o}")
            elif tag == "auto":
                print(f"   footage #{c} @ {t}s: auto vào từ {o:.2f}s (điểm rung {sc:.2f})")
        used = {c for _, c, _, _ in self.sched}
        print("footage chưa dùng:", sorted(set(self.clips) - used) or "không")
        print(f"{len(self.sched)} lần chèn · {len(blocks)} khối · {sum(d for *_, d in self.sched):.0f}s footage ·",
              "OK" if ok else "LỖI")
        return ok

    def render(self, to=None):
        if not self.check():
            sys.exit("sửa lịch footage trước khi render")
        fps = self.fps
        items = [x for x in self.frame_plan() if to is None or x[0] < to * fps]
        args = ["-y", "-i", self.main]
        fl, prev = [], "0:v"
        for k, (F0, F1, src, c) in enumerate(items, 1):
            # ⚠ frame ĐẦU TIÊN sau khi tua (-ss) bị giải mã lệch → tua sớm PRE frame rồi bỏ đi (trim=start_frame)
            # footage lấy dư 3 frame; chỉ hiện đúng frame F0..F1-1 của video chính — enable theo số frame n
            args += ["-ss", f"{src - PRE / fps:.4f}", "-t", f"{(F1 - F0 + PRE + 3) / fps:.4f}", "-an", "-i", self.foot]
            fl.append(f"[{k}:v]fps={fps},trim=start_frame={PRE},setpts=N/({fps}*TB)+{F0}/({fps}*TB)[b{k}]")
            fl.append(f"[{prev}][b{k}]overlay=eof_action=pass:repeatlast=0:enable='between(n,{F0},{F1 - 1})'[v{k}]")
            prev = f"v{k}"
        # GPU NVIDIA → NVENC; không có thì libx264
        if "h264_nvenc" in subprocess.run(["ffmpeg", "-hide_banner", "-encoders"], capture_output=True, text=True).stdout:
            enc = ["-c:v", "h264_nvenc", "-preset", "p5", "-rc", "vbr", "-cq", "16", "-b:v", "0"]
        else:   # Mac → VideoToolbox; còn lại libx264
            enc = _mac_vt(False) or ["-c:v", "libx264", "-preset", "medium", "-crf", "15"]
        args += ["-filter_complex", ";".join(fl), "-map", f"[{prev}]", "-map", "0:a", "-c:a", "copy",
                 *enc, "-pix_fmt", "yuv420p"]
        if to:
            args += ["-t", str(to)]
        out = os.path.join(self.W, "base_test.mp4" if to else "base_16x9.mp4")
        ff(*args, out)
        print("→", out)


if __name__ == "__main__":
    cmd, work = sys.argv[1], os.path.abspath(sys.argv[2])
    j = Job(work)
    if cmd == "split": j.split()
    elif cmd == "cuts": j.cuts()
    elif cmd == "stable": j.stable()
    elif cmd == "check": j.check()
    elif cmd == "render":
        j.render(float(sys.argv[sys.argv.index("--to") + 1]) if "--to" in sys.argv else None)

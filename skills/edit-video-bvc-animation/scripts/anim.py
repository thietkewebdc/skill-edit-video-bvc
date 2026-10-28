"""Video ANIMATION đồ họa phẳng từ voice over (phong cách kênh Hồ Mạnh Thắng, mẫu "Tôi không lười…", không logo).

Lệnh:
  transcribe VOICE -o WORK/words.json          nghe voice (faster-whisper large-v3, GPU)
  check  WORK/plan.json                        khớp lời, đo tràn khung, cảnh báo nhịp
  snap   WORK/plan.json --at 3.2,10 | --scenes 1-12 [--sheet]   chụp khung PNG để duyệt
  render WORK/plan.json -o OUT.mp4 [--preview] [--from 0 --to 30] [--workers 4] [--cpu]

Hình vẽ bằng HTML/CSS (runtime/engine.js) chạy trong Chrome headless — mọi chuyển động là
hàm thuần của thời gian nên chụp tuần tự từng khung, ghép bằng ffmpeg (NVENC nếu có).
"""
import argparse
import base64
import json
import math
import multiprocessing as mp
import os
import shutil
import subprocess
import sys
import tempfile
import time
import wave
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

SKILL = Path(__file__).resolve().parent.parent
RUNTIME = SKILL / "runtime" / "index.html"
SR = 48000

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def die(msg):
    print("LỖI: " + msg, file=sys.stderr)
    sys.exit(1)


# ───────────────────────── plan ─────────────────────────
def load_plan(p):
    p = Path(p).resolve()
    plan = json.loads(p.read_text(encoding="utf-8-sig"))
    work = p.parent
    audio = plan.get("audio")
    if not audio:
        die('plan thiếu "audio" (đường dẫn voice over).')
    ap = Path(audio)
    if not ap.is_absolute():
        ap = (work / ap).resolve()
    if not ap.exists():
        die(f"không thấy voice: {ap}")
    wf = Path(plan.get("words", "words.json"))
    if not wf.is_absolute():
        wf = work / wf
    words = json.loads(wf.read_text(encoding="utf-8-sig"))["words"] if wf.exists() else []
    if not words:
        print("CẢNH BÁO: chưa có words.json → không khớp được lời, mọi mục phải dùng \"at\".")
    size = plan.get("size", [1080, 1920])
    adur = probe_dur(ap)
    tail = float(plan.get("tail", 0.5))
    dur = adur
    if words:
        dur = min(adur + tail, words[-1]["e"] + tail) if plan.get("trim_end", True) else adur
        dur = max(dur, words[-1]["e"] + tail)
    return plan, words, ap, work, int(size[0]), int(size[1]), float(plan.get("fps", 30)), round(dur, 3)


def probe_dur(p):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                         capture_output=True, text=True).stdout.strip()
    try:
        return float(out)
    except ValueError:
        die(f"không đọc được độ dài: {p}")


# ───────────────────────── trình duyệt ─────────────────────────
def open_page(W, H, scale=1.0):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        die("thiếu playwright: pip install playwright")
    pw = sync_playwright().start()
    browser = None
    for ch in ("chrome", "msedge", None):
        try:
            browser = pw.chromium.launch(channel=ch, headless=True, args=["--force-color-profile=srgb", "--hide-scrollbars"]) if ch else pw.chromium.launch(headless=True)
            break
        except Exception:
            continue
    if browser is None:
        die("không mở được Chrome/Edge (cài Chrome hoặc chạy: python -m playwright install chromium)")
    page = browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=scale)
    page.goto(RUNTIME.as_uri())
    return pw, browser, page


def init_page(page, plan, words, work, W, H, dur):
    data = {"plan": plan, "words": words, "W": W, "H": H, "dur": dur, "base": work.as_uri() + "/"}
    return page.evaluate("d => ANIM.init(d)", data)


# ───────────────────────── check / snap ─────────────────────────
def cmd_check(a):
    plan, words, ap, work, W, H, fps, dur = load_plan(a.plan)
    pw, br, page = open_page(W, H, 0.25)
    try:
        rep = init_page(page, plan, words, work, W, H, dur)
        over = page.evaluate("() => ANIM.check()")
    finally:
        br.close(); pw.stop()
    sc = rep["scenes"]
    lens = [s["e"] - s["s"] for s in sc]
    print(f"Video {dur:.1f}s · {len(sc)} màn · trung bình {np.mean(lens):.2f}s/màn (mẫu ~2.5s) · {len(rep['events'])} SFX")
    for s in sc:
        print(f"  #{s['k']:>3} {s['s']:7.2f}–{s['e']:7.2f} ({s['e'] - s['s']:4.1f}s) {s['bg']:<7} {s['tr']:<6} {s['text']}")
    warns = rep["warns"] + over
    if warns:
        print("CẢNH BÁO:")
        for w in dict.fromkeys(warns):
            print("  - " + w)
    else:
        print("OK — không có cảnh báo.")


def cmd_snap(a):
    plan, words, ap, work, W, H, fps, dur = load_plan(a.plan)
    out = Path(a.out or (Path(a.plan).parent / "qa"))
    out.mkdir(parents=True, exist_ok=True)
    scale = a.scale
    pw, br, page = open_page(W, H, scale)
    shots = []
    try:
        rep = init_page(page, plan, words, work, W, H, dur)
        times = []
        if a.at:
            times = [(float(x), f"t{float(x):07.2f}") for x in a.at.split(",") if x.strip()]
        else:
            lo, hi = 1, len(rep["scenes"])
            if a.scenes:
                p = a.scenes.split("-")
                lo, hi = int(p[0]), int(p[-1])
            for s in rep["scenes"][lo - 1:hi]:
                t = s["s"] + min((s["e"] - s["s"]) * a.pos, a.max_in)
                times.append((t, f"m{s['k']:03d}"))
        for t, name in times:
            page.evaluate("t => ANIM.renderAt(t)", t)
            f = out / f"{name}.png"
            page.screenshot(path=str(f))
            shots.append((f, t, name))
    finally:
        br.close(); pw.stop()
    if a.sheet and shots:
        cols = a.cols
        sheet = out / "sheet.png"
        inputs = []
        for f, t, name in shots:
            inputs += ["-i", str(f)]
        n = len(shots)
        rows = math.ceil(n / cols)
        fl = "".join(f"[{i}:v]scale={int(W * 0.2)}:-1,pad=iw+6:ih+6:3:3:black[v{i}];" for i in range(n))
        lay ="|".join(f"{'+'.join(['w0'] * (i % cols)) or '0'}_{'+'.join(['h0'] * (i // cols)) or '0'}" for i in range(n))
        fl += "".join(f"[v{i}]" for i in range(n)) + f"xstack=inputs={n}:layout={lay}:fill=black" if n > 1 else "[v0]null"
        subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", fl, "-frames:v", "1", str(sheet)], check=False)
        print(f"Tờ duyệt → {sheet} ({n} khung, {rows} hàng)")
    print(f"{len(shots)} ảnh → {out}")


# ───────────────────────── render ─────────────────────────
def enc_args(cpu, preview):
    if not cpu and nvenc_ok():
        return ["-c:v", "h264_nvenc", "-preset", "p5", "-rc", "vbr", "-cq", "23" if preview else "18", "-b:v", "0", "-pix_fmt", "yuv420p"]
    vt = None if cpu else _mac_vt(preview)          # Mac → VideoToolbox
    if vt:
        return vt + ["-pix_fmt", "yuv420p"]
    return ["-c:v", "libx264", "-preset", "veryfast" if preview else "medium", "-crf", "23" if preview else "17", "-pix_fmt", "yuv420p"]


_NV = None


def nvenc_ok():
    global _NV
    if _NV is None:
        r = subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=black:s=256x256:d=0.1", "-c:v", "h264_nvenc", "-f", "null", "-"], capture_output=True)
        _NV = r.returncode == 0
    return _NV


def worker(job):
    (plan_path, f0, f1, seg, scale, cpu, preview, wid, q) = job
    plan, words, ap, work, W, H, fps, dur = load_plan(plan_path)
    pw, br, page = open_page(W, H, scale)
    ow, oh = int(round(W * scale)), int(round(H * scale))
    ow -= ow % 2; oh -= oh % 2
    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "image2pipe", "-framerate", str(fps), "-c:v", "mjpeg", "-i", "-",
                           "-vf", f"scale={ow}:{oh}:flags=bicubic", *enc_args(cpu, preview), "-r", str(fps), str(seg)], stdin=subprocess.PIPE)
    try:
        init_page(page, plan, words, work, W, H, dur)
        cdp = page.context.new_cdp_session(page)
        for f in range(f0, f1):
            page.evaluate("t => ANIM.renderAt(t)", f / fps)
            r = cdp.send("Page.captureScreenshot", {"format": "jpeg", "quality": 93, "optimizeForSpeed": True})
            ff.stdin.write(base64.b64decode(r["data"]))
            if q is not None and (f - f0) % 15 == 0:
                q.put((wid, f - f0))
        if q is not None:
            q.put((wid, f1 - f0))
    finally:
        ff.stdin.close(); ff.wait()
        br.close(); pw.stop()
    return str(seg)


def cmd_render(a):
    plan, words, ap, work, W, H, fps, dur = load_plan(a.plan)
    scale = 0.5 if a.preview else 1.0
    t0 = max(0.0, a.start or 0.0)
    t1 = min(dur, a.end) if a.end else dur
    F0, F1 = int(round(t0 * fps)), int(round(t1 * fps))
    total = F1 - F0
    # báo cáo + sự kiện SFX
    pw, br, page = open_page(W, H, 0.25)
    try:
        rep = init_page(page, plan, words, work, W, H, dur)
    finally:
        br.close(); pw.stop()
    if rep["warns"]:
        print(f"CẢNH BÁO ({len(rep['warns'])}) — chạy check để xem chi tiết.")
    nw = max(1, min(a.workers, total // 60 or 1))
    tmp = Path(tempfile.mkdtemp(prefix="anim_"))
    chunks = []
    step = math.ceil(total / nw)
    mgr = mp.Manager()
    q = mgr.Queue()
    jobs = []
    for i in range(nw):
        f0, f1 = F0 + i * step, min(F1, F0 + (i + 1) * step)
        if f0 >= f1:
            continue
        seg = tmp / f"seg{i:02d}.mp4"
        chunks.append(seg)
        jobs.append((str(Path(a.plan).resolve()), f0, f1, seg, scale, a.cpu, a.preview, i, q))
    print(f"Render {total} khung ({t1 - t0:.1f}s) · {len(jobs)} luồng · {'nháp 540p' if a.preview else 'full'} …")
    st = time.time()
    with mp.Pool(len(jobs)) as pool:
        res = pool.map_async(worker, jobs)
        done = {}
        last = 0
        while not res.ready():
            res.wait(1.0)
            while not q.empty():
                wid, n = q.get()
                done[wid] = n
            s = sum(done.values())
            if time.time() - last > 10 and s:
                el = time.time() - st
                print(f"  {s}/{total} khung · {s / el:.1f} khung/s · còn ~{(total - s) / max(s / el, 0.1):.0f}s", flush=True)
                last = time.time()
        res.get()
    print(f"Hình xong sau {time.time() - st:.0f}s ({total / max(time.time() - st, 0.1):.1f} khung/s).")
    lst = tmp / "list.txt"
    lst.write_text("".join(f"file '{c.as_posix()}'\n" for c in chunks), encoding="utf-8")
    vid = tmp / "video.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(vid)], check=True)
    # âm thanh
    sfx_wav = tmp / "sfx.wav"
    vol = float(plan.get("sfx_volume", 0.5))
    make_sfx(rep["events"] if plan.get("sfx", True) else [], dur, sfx_wav, vol)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    mix_audio(plan, ap, work, sfx_wav, vid, out, t0, t1)
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"Xong → {out}  ({t1 - t0:.1f}s, {time.time() - st:.0f}s tổng)")


def mix_audio(plan, voice, work, sfx_wav, vid, out, t0, t1):
    d = t1 - t0
    inputs = ["-i", str(vid), "-ss", f"{t0:.3f}", "-t", f"{d:.3f}", "-i", str(voice), "-ss", f"{t0:.3f}", "-t", f"{d:.3f}", "-i", str(sfx_wav)]
    fl = "[1:a]aresample=48000,aformat=channel_layouts=stereo,apad[v];[2:a]aformat=channel_layouts=stereo[s];"
    mix = "[v][s]"
    n = 2
    mus = plan.get("music")
    if mus:
        mp_ = Path(mus)
        if not mp_.is_absolute():
            mp_ = work / mp_
        if mp_.exists():
            inputs += ["-stream_loop", "-1", "-i", str(mp_)]
            mdb = float(plan.get("music_db", -24))
            fl += (f"[3:a]aresample=48000,aformat=channel_layouts=stereo,volume={mdb}dB,atrim=0:{d:.3f}[m0];"
                   "[v]asplit[v][vk];[m0][vk]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=400[m];")
            mix = "[v][s][m]"
            n = 3
        else:
            print(f"CẢNH BÁO: không thấy nhạc {mp_} → bỏ qua.")
    fl += f"{mix}amix=inputs={n}:normalize=0:duration=first,atrim=0:{d:.3f},loudnorm=I=-14:TP=-1.5:LRA=11[a]"
    subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", fl, "-map", "0:v", "-map", "[a]",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-t", f"{d:.3f}", "-movflags", "+faststart", str(out)], check=True)


# ───────────────────────── SFX tự tổng hợp ─────────────────────────
def _env(n, a, r):
    t = np.arange(n) / SR
    return np.minimum(1, t / max(a, 1e-4)) * np.exp(-t / max(r, 1e-4))


def _lp(x, k):
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc += k[i] * (x[i] - acc) if hasattr(k, "__len__") else k * (x[i] - acc)
        y[i] = acc
    return y


def synth(kind):
    rs = np.random.RandomState(abs(hash(kind)) % 2 ** 31)
    if kind == "whoosh":
        n = int(SR * 0.42)
        t = np.arange(n) / n
        noise = rs.randn(n)
        k = 0.02 + 0.25 * np.sin(np.pi * t) ** 2
        s = _lp(noise, k) - _lp(noise, 0.01)
        return s * np.sin(np.pi * t) ** 1.5 * 0.9
    if kind == "pop":
        n = int(SR * 0.09)
        t = np.arange(n) / SR
        f = 900 * np.exp(-t * 30) + 260
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * _env(n, 0.002, 0.025) * 0.6
    if kind == "tick":
        n = int(SR * 0.05)
        t = np.arange(n) / SR
        return (np.sin(2 * np.pi * 1850 * t) * 0.5 + np.sin(2 * np.pi * 2900 * t) * 0.2) * _env(n, 0.001, 0.012) * 0.55
    if kind == "ding":
        n = int(SR * 0.5)
        t = np.arange(n) / SR
        return (np.sin(2 * np.pi * 1318 * t) + 0.5 * np.sin(2 * np.pi * 1975 * t)) * _env(n, 0.002, 0.14) * 0.28
    if kind == "swipe":
        n = int(SR * 0.18)
        t = np.arange(n) / n
        s = _lp(rs.randn(n), 0.18) * np.sin(np.pi * t) ** 2
        return s * 0.5
    if kind == "thud":
        n = int(SR * 0.22)
        t = np.arange(n) / SR
        f = 140 * np.exp(-t * 12) + 55
        return (np.sin(2 * np.pi * np.cumsum(f) / SR) * _env(n, 0.002, 0.07) + _lp(rs.randn(n), 0.3) * _env(n, 0.001, 0.015) * 0.5) * 0.8
    if kind == "boom":
        n = int(SR * 0.7)
        t = np.arange(n) / SR
        f = 90 * np.exp(-t * 5) + 40
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * _env(n, 0.004, 0.22) * 0.75
    if kind == "burst":
        n = int(SR * 0.35)
        out = np.zeros(n)
        for i in range(9):
            o = int(rs.rand() * SR * 0.22)
            p = synth("tick")
            out[o:o + len(p)] += p[: n - o] * (0.4 + rs.rand() * 0.5)
        return out * 0.7
    return np.zeros(10)


def make_sfx(events, dur, path, vol):
    n = int(SR * (dur + 1))
    buf = np.zeros(n)
    cache = {}
    last = {}
    gain = {"whoosh": 0.55, "pop": 0.5, "tick": 0.5, "ding": 0.45, "swipe": 0.5, "thud": 0.7, "boom": 0.7, "burst": 0.6}
    for e in events:
        k, t = e["kind"], e["t"]
        if t < 0 or t >= dur:
            continue
        if t - last.get(k, -9) < 0.12:
            continue
        last[k] = t
        if k not in cache:
            cache[k] = synth(k)
        s = cache[k] * gain.get(k, 0.5)
        o = int(t * SR) - (int(0.2 * SR) if k == "whoosh" else 0)
        o = max(0, o)
        buf[o:o + len(s)] += s[: max(0, n - o)]
    buf *= vol * 0.5
    buf = np.clip(buf, -1, 1)
    st = np.repeat((buf * 32767).astype(np.int16)[:, None], 2, axis=1)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(st.tobytes())


# ───────────────────────── transcribe ─────────────────────────
def _cuda_dlls():
    import importlib
    for mod in ("nvidia.cublas", "nvidia.cudnn"):
        try:
            d = os.path.join(importlib.import_module(mod).__path__[0], "bin")
            os.add_dll_directory(d)
            os.environ["PATH"] = d + os.pathsep + os.environ.get("PATH", "")
        except (ImportError, OSError, AttributeError):
            pass


def whisper_src(model):
    local = Path.home() / ".cache" / f"fw-{model}"
    if not (local / "model.bin").exists():
        from huggingface_hub import snapshot_download
        snapshot_download(f"Systran/faster-whisper-{model}", local_dir=str(local))
    return str(local)


def cmd_transcribe(a):
    _cuda_dlls()
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        die("thiếu faster-whisper: pip install faster-whisper")
    src = whisper_src(a.model)
    words, err = None, None
    for dev, ct in ((("cpu", "int8"),) if a.cpu else (("cuda", "float16"), ("cpu", "int8"))):
        try:
            m = WhisperModel(src, device=dev, compute_type=ct)
            segs, _ = m.transcribe(str(a.voice), language=a.lang, word_timestamps=True, vad_filter=True)
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
        cur.append(w["w"])
        if w["w"][-1] in ".?!," and len(cur) >= 4 or len(cur) >= 12:
            lines.append(f"[{t0:7.2f}] " + " ".join(cur))
            cur = []
    if cur:
        lines.append(f"[{t0:7.2f}] " + " ".join(cur))
    out.with_suffix(".txt").write_text("\n".join(lines), encoding="utf-8")
    print(f"{len(words)} từ → {out}\nBản đọc → {out.with_suffix('.txt')}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("transcribe"); p.add_argument("voice"); p.add_argument("-o", "--out", required=True)
    p.add_argument("--lang", default="vi"); p.add_argument("--model", default="large-v3"); p.add_argument("--cpu", action="store_true")
    p = sp.add_parser("check"); p.add_argument("plan")
    p = sp.add_parser("snap"); p.add_argument("plan"); p.add_argument("--at"); p.add_argument("--scenes")
    p.add_argument("--pos", type=float, default=0.85, help="vị trí trong màn (0–1) khi chụp theo màn")
    p.add_argument("--max-in", dest="max_in", type=float, default=4.0, help="chụp tối đa N giây sau đầu màn")
    p.add_argument("--scale", type=float, default=0.5); p.add_argument("--sheet", action="store_true"); p.add_argument("--cols", type=int, default=6)
    p.add_argument("-o", "--out")
    p = sp.add_parser("render"); p.add_argument("plan"); p.add_argument("-o", "--out", required=True)
    p.add_argument("--preview", action="store_true"); p.add_argument("--from", dest="start", type=float); p.add_argument("--to", dest="end", type=float)
    p.add_argument("--workers", type=int, default=4); p.add_argument("--cpu", action="store_true")
    a = ap.parse_args()
    {"transcribe": cmd_transcribe, "check": cmd_check, "snap": cmd_snap, "render": cmd_render}[a.cmd](a)


if __name__ == "__main__":
    mp.freeze_support()
    main()

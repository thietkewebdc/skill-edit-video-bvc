#!/usr/bin/env python3
"""denoise — KHỬ TẠP ÂM cho giọng nói (quán cà phê, quạt, xe, người nói chuyện nền…) bằng RNNoise.

  python denoise.py <video|wav> -o <ra.mp4|wav> [--mix 0.85]     khử ồn (hình giữ nguyên, chỉ xử lý tiếng)
  python denoise.py <video|wav> --check                           đo mức ồn, KHUYẾN NGHỊ có nên khử không (không ghi file)

• --mix = tỉ lệ tiếng ĐÃ khử ồn (còn lại là tiếng gốc). Mặc định 0.85.
  Đã đo trên video quay trong quán cà phê (giọng chỉ hơn nền ~4 dB):
    mix 1.00 → nền −34→−60 dB nhưng GIỌNG MÉO (máy nghe lại chỉ khớp 46% chữ) — đừng dùng;
    mix 0.85 → nền −34→−49 dB, giọng −1.7 dB, nghe lại khớp 87% (gốc 90%) — mức khuyên dùng.
• Giữ nguyên số kênh/độ dài; xử lý 48 kHz.
• Lần đầu tự tạo môi trường riêng ~/.claude/hmt-denoise/venv (pip: pyrnnoise, soundfile; ~200 MB, cần mạng).
  Không cài được → tự dùng bộ lọc ffmpeg afftdn (yếu hơn, chỉ hợp ồn đều như quạt/điều hòa).
• Chạy TRƯỚC loudnorm (enhance.py --denoise gọi file này).
"""
import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
VENV = Path.home() / ".claude" / "hmt-denoise" / "venv"
VPY = VENV / "bin" / "python"


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, **kw)


def ensure_venv():
    """True nếu có RNNoise sẵn sàng (tự cài lần đầu)."""
    def ok():
        return VPY.exists() and subprocess.run([str(VPY), "-c", "from pyrnnoise.rnnoise import create"], capture_output=True).returncode == 0
    if ok():
        return True
    print("Lần đầu dùng khử ồn: đang cài RNNoise vào ~/.claude/hmt-denoise/venv (vài phút, cần mạng)…", flush=True)
    py = next((c for c in (sys.executable, "python3.12", "python3.11", "python3.10", "python3")
               if subprocess.run([c, "-c", "import sys;sys.exit(0 if sys.version_info>=(3,9) else 1)"], capture_output=True).returncode == 0), None)
    if not py:
        return False
    try:
        VENV.parent.mkdir(parents=True, exist_ok=True)
        run([py, "-m", "venv", str(VENV)])
        run([str(VPY), "-m", "pip", "install", "--quiet", "pyrnnoise", "soundfile"])
    except Exception as e:
        print("Không cài được RNNoise:", e)
        return False
    return ok()


def has_video(p):
    o = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=codec_type", "-of", "csv=p=0", p], capture_output=True, text=True).stdout
    return "video" in o


def extract(src, wav):
    run(["ffmpeg", "-v", "error", "-y", "-i", src, "-vn", "-map", "0:a:0", "-ar", "48000", "-c:a", "pcm_s16le", wav])


def check(src):
    import numpy as np
    with tempfile.TemporaryDirectory() as td:
        wav = os.path.join(td, "a.wav"); extract(src, wav)
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", wav, "-ac", "1", "-ar", "48000", "-f", "s16le", "-"], capture_output=True).stdout
    a = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
    n = len(a) // 2400
    f = np.array([20 * np.log10(np.sqrt((a[i * 2400:(i + 1) * 2400] ** 2).mean()) + 1e-9) for i in range(n)])
    f = f[f > -70]
    lo, hi = np.percentile(f, 10), np.percentile(f, 90)
    gap = hi - lo
    print(f"Nền (10% khung nhỏ nhất) {lo:.1f} dB · giọng (90% khung lớn nhất) {hi:.1f} dB · chênh {gap:.1f} dB")
    if gap < 20:
        print("→ NỀN ỒN (giọng chỉ hơn nền < 20 dB): KHUYẾN NGHỊ khử ồn  (denoise.py … --mix 0.85 hoặc enhance.py --denoise)")
    else:
        print("→ Nền khá sạch (giọng hơn nền ≥ 20 dB): không cần khử ồn.")


def worker_code():
    return r'''
import sys, numpy as np, soundfile as sf
from pyrnnoise.rnnoise import create, process_frame, destroy
src, dst, mix = sys.argv[1], sys.argv[2], float(sys.argv[3])
x, sr = sf.read(src, dtype="float32", always_2d=True); assert sr == 48000
out = np.zeros_like(x)
for ch in range(x.shape[1]):
    cur = x[:, ch]; n = len(cur)
    i16 = np.pad(np.clip(cur * 32768, -32768, 32767).astype(np.int16), (0, (-n) % 480)); st = [create()]; res = []
    for a in range(0, len(i16), 480):
        fr, _ = process_frame(st, i16[a:a + 480][None, :]); res.append(np.asarray(fr)[0])
    destroy(st[0])
    d = np.concatenate(res).astype(np.float32) / 32768
    out[:, ch] = mix * d[:n] + (1 - mix) * cur
sf.write(dst, out, sr, subtype="PCM_16")
'''


def denoise(src, dst, mix):
    video = has_video(src) and not str(dst).lower().endswith((".wav", ".m4a", ".mp3"))
    with tempfile.TemporaryDirectory() as td:
        wav, dn = os.path.join(td, "a.wav"), os.path.join(td, "dn.wav")
        extract(src, wav)
        if ensure_venv():
            code = os.path.join(td, "worker.py"); open(code, "w").write(worker_code())
            run([str(VPY), code, wav, dn, str(mix)])
            how = f"RNNoise mix {mix}"
        else:
            print("Dùng phương án dự phòng: ffmpeg afftdn (yếu hơn RNNoise).")
            run(["ffmpeg", "-v", "error", "-y", "-i", wav, "-af", "highpass=f=80,afftdn=nr=18:nf=-32:tn=1", dn]); how = "afftdn"
        if video:
            run(["ffmpeg", "-v", "error", "-y", "-i", src, "-i", dn, "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", dst])
        else:
            run(["ffmpeg", "-v", "error", "-y", "-i", dn, dst])
    print(f"Xong → {dst}  (khử ồn: {how})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src"); ap.add_argument("-o", "--out")
    ap.add_argument("--mix", type=float, default=0.85, help="tỉ lệ tiếng đã khử ồn 0–1 (mặc định 0.85)")
    ap.add_argument("--check", action="store_true", help="chỉ đo mức ồn và khuyến nghị")
    a = ap.parse_args()
    if a.check:
        return check(a.src)
    if not a.out:
        ap.error("cần -o <file ra> (hoặc dùng --check)")
    denoise(a.src, a.out, a.mix)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()

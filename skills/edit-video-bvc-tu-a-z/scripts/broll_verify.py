# Soát bản đã ghép footage: quanh MỖI mép footage, điểm khác biệt từng frame phải có đúng 1 cú nhảy lớn (tại mép)
# và không có cú nhảy phụ trong ±5 frame → không lọt frame lạ.
#   python broll_verify.py <work> [video]     (mặc định <work>/base_16x9.mp4)
import os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import broll

work = os.path.abspath(sys.argv[1])
j = broll.Job(work)
video = sys.argv[2] if len(sys.argv) > 2 else os.path.join(work, "base_16x9.mp4")
fps = j.fps
edges = sorted({x for it in j.frame_plan() for x in it[:2]})
bad = 0
for E in edges:
    t0 = max(0, (E - 10) / fps)   # 4 frame đầu sau khi tua bỏ qua (lỗi giải mã của chính lệnh soát)
    tmp = "_v.txt"   # tên tương đối (đường dẫn Windows có ":" phá cú pháp filter), chạy với cwd=work
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", f"{t0:.4f}", "-i", video, "-vf",
                    f"trim=end_frame=17,scale=320:-1,select='gte(scene,0)',metadata=print:key=lavfi.scene_score:file={tmp}",
                    "-an", "-f", "null", "-"], check=True, cwd=work)
    sc = [float(s) for s in re.findall(r"scene_score=([\d.]+)", open(os.path.join(work, tmp)).read())][4:]
    os.remove(os.path.join(work, tmp))
    big = [k for k, s in enumerate(sc) if s > 0.25]
    # frame NGAY SAU cú cắt luôn bị bộ đo scene của ffmpeg đội điểm (công thức có |mafd - mafd trước|) → bỏ qua
    jumps = [k for k, s in enumerate(sc) if s > 0.05 and not (big and k == big[0] + 1)]
    if len(big) != 1 or len(jumps) > 1:
        bad += 1
        print(f"!! mép {E / fps:9.3f}s  điểm: " + " ".join(f"{s:.2f}" for s in sc))
print(f"{len(edges)} mép · {bad} mép nghi lỗi", "→ trích frame xem tận mắt" if bad else "→ sạch")

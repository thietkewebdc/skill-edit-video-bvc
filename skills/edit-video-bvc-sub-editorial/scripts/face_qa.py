# Soát CHỮ ĐỤNG MẶT trên bản render thật: mặt dò bằng OpenCV trên video gốc, chữ = điểm ảnh khác nhau giữa bản render và gốc.
# python face_qa.py <goc.mp4> <render.mp4> [buoc_giay]  → in mốc có chữ phủ lên vùng mặt (trán → cằm)
import sys
import cv2
import numpy as np

src, out = sys.argv[1], sys.argv[2]
step = float(sys.argv[3]) if len(sys.argv) > 3 else 0.5
cas = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
a, b = cv2.VideoCapture(src), cv2.VideoCapture(out)
dur = b.get(cv2.CAP_PROP_FRAME_COUNT) / b.get(cv2.CAP_PROP_FPS)
W, H = int(b.get(cv2.CAP_PROP_FRAME_WIDTH)), int(b.get(cv2.CAP_PROP_FRAME_HEIGHT))
bad, last_face = [], None
t = 0.2
while t < dur - 0.1:
    a.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
    b.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
    ok1, fa = a.read()
    ok2, fb = b.read()
    if not (ok1 and ok2):
        break
    fa = cv2.resize(fa, (W, H), interpolation=cv2.INTER_AREA)
    g = cv2.equalizeHist(cv2.cvtColor(cv2.resize(fa, (W // 2, H // 2)), cv2.COLOR_BGR2GRAY))
    faces = cas.detectMultiScale(g, 1.1, 6, minSize=(60, 60))
    if len(faces):
        x, y, w, h = max(faces, key=lambda f: f[2] * f[3]) * 2
        last_face = (x, y, w, int(h * 1.08))          # khung vuông Haar gần tới cằm → nới 8% (giống engine cv_faces)
    if last_face is not None:
        x, y, w, h = last_face
        diff = cv2.absdiff(fa, fb).max(axis=2)
        if (diff > 60).mean() > 0.12:                 # khung CHỚP TRẮNG (flash, cả lúc đang mờ dần) → không phải chữ đè mặt
            t += step
            continue
        roi = diff[y:y + h, x:x + w] > 60                # điểm ảnh có chữ / quầng chữ đè lên
        frac = roi.mean()
        if frac > 0.004:
            ys = np.flatnonzero(roi.any(axis=1))
            where = "trán/mắt" if ys.min() < h * 0.45 else ("miệng" if ys.min() < h * 0.75 else "cằm")
            bad.append((t, frac, where, y / H, (y + h) / H))
    t += step
a.release(); b.release()
# gom các mốc liền nhau thành đoạn
seg = []
for t, f, wh, y0, y1 in bad:
    if seg and t - seg[-1][1] <= step + 0.01:
        seg[-1][1] = t; seg[-1][2] = max(seg[-1][2], f); seg[-1][3].add(wh)
    else:
        seg.append([t, t, f, {wh}, y0, y1])
for s0, s1, f, wh, y0, y1 in seg:
    print(f"  !! {s0:6.1f}–{s1:6.1f}s  chữ đè mặt {f:.1%}  ({', '.join(sorted(wh))})  mặt y {y0:.2f}–{y1:.2f}")
print(f"{len(seg)} đoạn chữ đụng mặt" if seg else "SẠCH — không chữ nào đụng mặt")

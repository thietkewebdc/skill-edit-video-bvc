# Đổi bản nhận giọng (VD small → large-v3) sau khi đã viết plan editorial: dời MỌI mốc trong "moments"
# (start/end/t, "at" + "t" của từng dòng/swap, "t" của từng item pills/scatter) sang dòng thời gian mới
# bằng cách dóng hàng từ giống nhau + nội suy tuyến tính.
#   python remap_plan.py <plan.json> <words_cũ.json> <words_mới.json>      (ghi đè plan, lưu bản cũ .bak)
import json, re, difflib, bisect, shutil, sys

plan_p, old_p, new_p = sys.argv[1:4]
n = lambda s: re.sub(r"[^\w]", "", s.lower())
load = lambda p: json.load(open(p, encoding="utf-8-sig"))["words"]
a, b = load(old_p), load(new_p)
sm = difflib.SequenceMatcher(None, [n(x["w"]) for x in a], [n(x["w"]) for x in b], autojunk=False)
pairs = sorted((a[i + d]["s"], b[j + d]["s"]) for i, j, k in sm.get_matching_blocks() for d in range(k))
xs, ys = [p[0] for p in pairs], [p[1] for p in pairs]


def m(t):
    if t <= 0:
        return t                                  # tiêu đề mở đầu ở 0s giữ nguyên
    k = bisect.bisect_left(xs, t)
    if k <= 0: return ys[0] + (t - xs[0])
    if k >= len(xs): return ys[-1] + (t - xs[-1])
    x0, x1, y0, y1 = xs[k - 1], xs[k], ys[k - 1], ys[k]
    return y0 if x1 == x0 else y0 + (t - x0) * (y1 - y0) / (x1 - x0)


r = lambda t: round(m(float(t)), 2)
shutil.copy(plan_p, plan_p + ".bak")
p = json.load(open(plan_p, encoding="utf-8-sig"))
mx = 0
for e in p.get("moments", []):
    for k in ("start", "end", "t"):
        if k in e:
            v0 = float(e[k]); e[k] = r(v0); mx = max(mx, abs(e[k] - v0))
    for ln in e.get("lines", []) + [s for ln in e.get("lines", []) if isinstance(ln, dict) for s in ln.get("swap", [])]:
        if isinstance(ln, dict):
            if "t" in ln and float(ln["t"]) > 0: ln["t"] = r(ln["t"])
            if "at" in ln: ln["at"] = [r(t) for t in ln["at"]]
            if "end" in ln: ln["end"] = r(ln["end"])
    for it in e.get("items", []):
        for k in ("t", "end"):
            if k in it: it[k] = r(it[k])
json.dump(p, open(plan_p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"{len(pairs)} cặp từ dóng · lệch lớn nhất {mx:.2f}s · bản cũ → {plan_p}.bak")

# Đổi bản nhận giọng (VD medium → large-v3) sau khi đã viết plan: dời mọi mốc chữ nhấn (start/end/at)
# sang dòng thời gian mới bằng cách dóng hàng từ giống nhau + nội suy.
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
    k = bisect.bisect_left(xs, t)
    if k <= 0: return ys[0] + (t - xs[0])
    if k >= len(xs): return ys[-1] + (t - xs[-1])
    x0, x1, y0, y1 = xs[k - 1], xs[k], ys[k - 1], ys[k]
    return y0 if x1 == x0 else y0 + (t - x0) * (y1 - y0) / (x1 - x0)


shutil.copy(plan_p, plan_p + ".bak")
p = json.load(open(plan_p, encoding="utf-8-sig"))
mx = 0
for e in p.get("emphasis", []) + p.get("illustrations", []):
    if e["start"] == 0:
        continue
    s0 = e["start"]
    e["start"], e["end"] = round(m(e["start"]), 2), round(m(e["end"]), 2)
    if "at" in e:
        e["at"] = [round(m(t), 2) for t in e["at"]]
    mx = max(mx, abs(e["start"] - s0))
json.dump(p, open(plan_p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"{len(pairs)} cặp từ dóng · lệch lớn nhất {mx:.2f}s · bản cũ → {plan_p}.bak")

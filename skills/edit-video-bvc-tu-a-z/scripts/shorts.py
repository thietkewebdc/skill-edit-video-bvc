#!/usr/bin/env python3
"""shorts — cắt 1 video dài thành NHIỀU SHORT dọc 9:16 theo chuẩn chủ kênh (chốt 2026-09-26, đóng gói 2026-09-29).
Gọi lại đúng các công cụ của skill (cut_edit, cut_qa, enhance, sm_overlay) cho TỪNG short, gom kết quả kiểm duyệt.

<work> = thư mục analyze của video GỐC (chunks.json, envelope.npy, face.json, src_words.json) + shorts.json.

  setup  <work> [--force]            shorts.json → mỗi short 1 thư mục con short_<id>/ (hardlink dữ liệu analyze)
                                     + cut.json (keep_words / drop_words / pause_words / _notes)
                                     + plan.json khởi đầu (tiêu đề, màu, tên riêng — chữ nhấn Claude viết sau)
  qa     <work> [--only 01,03] [--fix]
                                     mỗi short: medwords → wordsnap → plan (độ dài 60–90s) → review → render --preview
                                     → lost [--fix: nới trim, render lại] → listen (joints.txt) → edges
                                     → gom hết vào <work>/shorts_qa.txt — lặp tới khi MỌI short sạch
  render <work> [--only ..] [--preview]
                                     mỗi short: render 4K 9:16 → subs (words_final.json) → enhance −14 LUFS
                                     → sm_overlay check + render → short_<id>/<name>_9x16_final.mp4
                                     → bản cuối gom vào <work>/_SHORTS_FINAL/
                                     --preview: chỉ phủ chữ lên cut_9x16_preview.mp4 → preview_overlay.mp4 (gửi duyệt)
  status <work>                      bảng tiến độ từng short

shorts.json:
{"video": "D:/.../goc.mp4",            // tùy chọn — mặc định lấy từ chunks.json
 "accent": "cyan", "proper_nouns": ["Suối Mơ"],
 "shorts": [
   {"id": "01", "name": "ban-hang-online", "formula": 12, "message": "thông điệp",
    "title": "BÁN HÀNG ONLINE?|{SAI RỒI!}",
    "keep_words": [["cái", 193.4, "thu", 235.8]],       // cùng cú pháp cut.json (xem references/cut-schema.md)
    "drop_words": [], "pause_words": [], "end_tail": 0.5, "_notes": {"…": "lý do"}}]}
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

S = Path(__file__).resolve().parent
LINK = ["chunks.json", "chunks.txt", "envelope.npy", "face.json", "src_words.json", "src_words.txt"]
WORD_KEYS = ["keep_words", "drop_words", "pause_words"]
MIN_LEN, MAX_LEN = 60.0, 90.0
ENV = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")


def run(script, *args, quiet=False):
    """chạy 1 script của skill, in trực tiếp, trả về (mã thoát, toàn bộ output)"""
    p = subprocess.Popen([sys.executable, str(S / script), *map(str, args)], stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", env=ENV)
    out = []
    for line in p.stdout:
        out.append(line.rstrip("\n"))
        if not quiet:
            print("    " + line.rstrip("\n"), flush=True)
    return p.wait(), "\n".join(out)


def load_cfg(work):
    cfg = json.loads((work / "shorts.json").read_text(encoding="utf-8-sig"))
    if not cfg.get("video"):
        cfg["video"] = json.loads((work / "chunks.json").read_text(encoding="utf-8"))["video"]
    return cfg


def pick(cfg, only):
    ids = set(only.split(",")) if only else None
    return [s for s in cfg["shorts"] if ids is None or str(s["id"]) in ids]


def sdir(work, sh):
    return work / f"short_{sh['id']}"


def words_sig(cut):
    return hashlib.md5(json.dumps([cut.get(k) for k in WORD_KEYS], ensure_ascii=False).encode()).hexdigest()[:10]


def rjson(p):
    return json.loads(p.read_text(encoding="utf-8-sig"))


def wjson(p, obj):
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")


# ───────────── setup ─────────────
def cmd_setup(a):
    work = Path(a.work)
    cfg = load_cfg(work)
    for f in ("chunks.json", "envelope.npy", "src_words.json"):
        if not (work / f).exists():
            sys.exit(f"thiếu {work / f} — chạy transcribe + cut_edit analyze cho video GỐC trước")
    for sh in cfg["shorts"]:
        d = sdir(work, sh)
        d.mkdir(exist_ok=True)
        for f in LINK:
            src, dst = work / f, d / f
            if src.exists() and not dst.exists():
                try:
                    os.link(src, dst)          # hardlink: sửa chính tả src_words.json ở gốc → mọi short thấy ngay
                except OSError:
                    shutil.copy2(src, dst)
        cp = d / "cut.json"
        cut = {} if a.force or not cp.exists() else rjson(cp)
        old = words_sig(cut)
        cut["words"] = "src_words.json"
        for k in WORD_KEYS:
            if sh.get(k):
                cut[k] = sh[k]
            else:
                cut.pop(k, None)
        if "end_tail" in sh:
            cut["end_tail"] = sh["end_tail"]
        cut["_notes"] = sh.get("_notes", cut.get("_notes", {}))
        if words_sig(cut) != old and cut.get("trim"):
            cut.pop("trim")                    # đổi vùng giữ → "trim" cũ của lost --fix không còn đúng
            print(f"  short {sh['id']}: đổi vùng giữ → xóa trim cũ (chạy lại qa)")
        wjson(cp, cut)
        pp = d / "plan.json"
        if a.force or not pp.exists():
            wjson(pp, {"words_file": "words_final.json", "accent": sh.get("accent", cfg.get("accent", "yellow")),
                       "proper_nouns": cfg.get("proper_nouns", []) + sh.get("proper_nouns", []),
                       "title": {"start": 0, "end": 7.0, "lines": sh.get("title", "")},
                       "emphasis": [], "illustrations": [],
                       "_todo": "Claude: chỉnh title.end theo câu mở đầu, lên chữ nhấn/minh họa theo words_final.json"})
        print(f"short {sh['id']} → {d}")
    print(f"\n{len(cfg['shorts'])} short. Tiếp: python \"{S / 'shorts.py'}\" qa \"{work}\"")


# ───────────── qa ─────────────
def qa_one(work, cfg, sh, fix):
    d = sdir(work, sh)
    rep = [f"##### SHORT {sh['id']} · {sh.get('name', '')} · {sh.get('title', '')}"]
    cut = rjson(d / "cut.json")
    print(f"\n=== short {sh['id']}: medwords / wordsnap", flush=True)
    if cut.get("_med_for") != words_sig(cut) or not (d / "med_words.json").exists():
        run("cut_qa.py", "medwords", cfg["video"], d)
        cut = rjson(d / "cut.json")
        cut["_med_for"] = words_sig(cut)
        wjson(d / "cut.json", cut)
    _, out = run("cut_qa.py", "wordsnap", d)
    bang = [l for l in out.splitlines() if l.startswith("!!")]
    rep += ["  MÉP KHÔNG CÓ LẶNG (nghe thử bằng cut_qa try):"] + [f"    {l}" for l in bang] if bang else []

    print(f"=== short {sh['id']}: plan / review", flush=True)
    run("cut_edit.py", "review", d / "cut.json", quiet=True)
    rv = (d / "review.txt").read_text(encoding="utf-8").strip()
    rv_clean = rv.startswith("Sạch")
    rep.append("  REVIEW: sạch" if rv_clean else "  REVIEW:\n" + "\n".join("    " + l for l in rv.splitlines()))

    print(f"=== short {sh['id']}: render --preview / lost", flush=True)
    run("cut_edit.py", "render", cfg["video"], d / "cut.json", "--aspect", "9x16", "--preview")
    _, out = run("cut_qa.py", "lost", d)
    if fix and "lost: sạch" not in out:
        run("cut_qa.py", "lost", d, "--fix")
        run("cut_edit.py", "render", cfg["video"], d / "cut.json", "--aspect", "9x16", "--preview")
        _, out = run("cut_qa.py", "lost", d)
    lost_clean = "lost: sạch" in out
    rep.append("  LOST: sạch" if lost_clean else "  LOST:\n" + "\n".join(
        "    " + l.strip() for l in out.splitlines() if "MẤT TIẾNG" in l) + "\n    → chạy lại qa với --fix")
    # độ dài đo SAU lost --fix (nhập lại tiếng sót làm short dài thêm)
    _, out = run("cut_edit.py", "plan", d / "cut.json", quiet=True)
    m = re.search(r"Tổng: (\d+) đoạn, ([\d.]+)s", out)
    n, dur = (int(m.group(1)), float(m.group(2))) if m else (0, 0.0)
    ok_len = MIN_LEN <= dur <= MAX_LEN
    tail = next((l.strip() for l in out.splitlines() if "⏹" in l), "")
    short_w = [l.strip() for l in out.splitlines() if "< 2s" in l]
    rep.insert(1, f"  ĐỘ DÀI {dur:.1f}s ({n} đoạn) "
               f"{'OK' if ok_len else f'!! NGOÀI {MIN_LEN:.0f}–{MAX_LEN:.0f}s'}  {tail}")
    rep += [f"  !! {l}" for l in short_w]

    print(f"=== short {sh['id']}: listen / edges", flush=True)
    run("cut_qa.py", "listen", d, quiet=True)
    rep.append("  MỐI NỐI (đọc như người xem — dư/mất chữ? số liệu đúng lời gốc?):")
    rep += ["  " + l for l in (d / "joints.txt").read_text(encoding="utf-8").splitlines()[1:]]
    _, out = run("cut_qa.py", "edges", d, quiet=True)
    edge_bad = [l.strip() for l in out.splitlines() if "!!" in l]
    rep += (["  EDGES — mép cắt giữa tiếng (phải xác nhận bằng listen/try):"] + ["    " + l for l in edge_bad]) \
        if edge_bad else ["  EDGES: sạch"]
    auto_ok = ok_len and not short_w and rv_clean and lost_clean and not bang and not edge_bad
    rep.insert(1, f"  ⇒ {'MÁY KIỂM: SẠCH — còn đọc joints bằng mắt' if auto_ok else 'CẦN SỬA'}")
    return "\n".join(rep), auto_ok


def cmd_qa(a):
    work = Path(a.work)
    cfg = load_cfg(work)
    for sh in pick(cfg, a.only):
        r, ok = qa_one(work, cfg, sh, a.fix)
        wjson(sdir(work, sh) / "qa_report.json", {"ok": ok, "text": r})
    # báo cáo chung ghép từ báo cáo riêng của MỌI short (chạy --only vẫn giữ kết quả các short khác)
    reps = [(sh["id"], rjson(sdir(work, sh) / "qa_report.json")) for sh in cfg["shorts"]
            if (sdir(work, sh) / "qa_report.json").exists()]
    head = ("QA SHORTS — " + " · ".join(f"{i}: {'sạch' if r['ok'] else 'CẦN SỬA'}" for i, r in reps) +
            "\nLuật: 60–90s · mép theo chữ trong khoảng lặng thật · không cắt giữa 2 chữ dính liền · "
            "số nghe lệch = mất tiếng\n")
    p = work / "shorts_qa.txt"
    p.write_text(head + "\n" + "\n\n".join(r["text"] for _, r in reps), encoding="utf-8")
    print("\n" + head.splitlines()[0] + f"\n→ {p}")


# ───────────── render ─────────────
def has_fx(plan):
    return bool(plan.get("emphasis") or plan.get("illustrations"))


def cmd_render(a):
    work = Path(a.work)
    cfg = load_cfg(work)
    fin = work / "_SHORTS_FINAL"
    done = []
    for sh in pick(cfg, a.only):
        d = sdir(work, sh)
        name = sh.get("name") or f"short_{sh['id']}"
        plan = rjson(d / "plan.json")
        if a.preview:
            src = d / "cut_9x16_preview.mp4"
            if not src.exists():
                sys.exit(f"short {sh['id']}: chưa có {src.name} — chạy qa trước")
            run("cut_qa.py", "subs", d)
            run("sm_overlay.py", "check", src, d / "plan.json")
            run("sm_overlay.py", "render", src, d / "plan.json", "-o", d / "preview_overlay.mp4", "--preview")
            done.append(d / "preview_overlay.mp4")
            continue
        if not has_fx(plan) and not a.bare:
            print(f"!! short {sh['id']}: plan.json chưa có chữ nhấn/minh họa → bỏ qua (thêm --bare để render chỉ tiêu đề + sub)")
            continue
        print(f"\n=== short {sh['id']}: render 4K 9:16", flush=True)
        run("cut_edit.py", "render", cfg["video"], d / "cut.json", "--aspect", "9x16")
        run("cut_qa.py", "subs", d)                      # sub không mất chữ quanh mối cắt
        run("enhance.py", d / "cut_9x16.mp4", "-o", d / "cut_9x16_enh.mp4")
        run("sm_overlay.py", "check", d / "cut_9x16_enh.mp4", d / "plan.json")
        out = d / f"{name}_9x16_final.mp4"
        code, _ = run("sm_overlay.py", "render", d / "cut_9x16_enh.mp4", d / "plan.json", "-o", out)
        if code == 0 and out.exists():
            # SFX thêm vào sau bước chuẩn âm đẩy lên ~ −13 LUFS / đỉnh −0.4 dBTP (đo thật 2026-09-29)
            # → chuẩn lại −14 LUFS / −1.5 dBTP trên file cuối (hình copy nguyên)
            tmp = d / f"{name}_9x16_final_tmp.mp4"
            if run("enhance.py", out, "-o", tmp)[0] == 0 and tmp.exists():
                os.replace(tmp, out)
            fin.mkdir(exist_ok=True)
            dst = fin / f"{sh['id']}_{name}.mp4"
            if dst.exists():
                dst.unlink()
            try:
                os.link(out, dst)
            except OSError:
                shutil.copy2(out, dst)
            done.append(dst)
    print("\nXong:\n" + "\n".join(f"  {p}" for p in done))


# ───────────── status ─────────────
def cmd_status(a):
    work = Path(a.work)
    cfg = load_cfg(work)
    print(f"{'id':4} {'dài':>6}  cut  med  prev joints plan-fx final  tiêu đề")
    for sh in cfg["shorts"]:
        d = sdir(work, sh)
        name = sh.get("name") or f"short_{sh['id']}"
        dur = "-"
        if (d / "segments.json").exists():
            dur = f"{rjson(d / 'segments.json')[-1]['out_e']:.1f}s"
        cut = rjson(d / "cut.json") if (d / "cut.json").exists() else {}
        plan = rjson(d / "plan.json") if (d / "plan.json").exists() else {}
        f = lambda b: " ✓ " if b else " · "
        print(f"{sh['id']:4} {dur:>6} {f('keep_ranges' in cut)}  {f((d / 'med_words.json').exists())} "
              f"{f((d / 'cut_9x16_preview.mp4').exists())}  {f((d / 'joints.txt').exists())}   {f(has_fx(plan))}  "
              f"{f((d / f'{name}_9x16_final.mp4').exists())}  {sh.get('title', '')}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("setup"); p.add_argument("work"); p.add_argument("--force", action="store_true")
    p.set_defaults(f=cmd_setup)
    p = sp.add_parser("qa"); p.add_argument("work"); p.add_argument("--only"); p.add_argument("--fix", action="store_true")
    p.set_defaults(f=cmd_qa)
    p = sp.add_parser("render"); p.add_argument("work"); p.add_argument("--only")
    p.add_argument("--preview", action="store_true"); p.add_argument("--bare", action="store_true")
    p.set_defaults(f=cmd_render)
    p = sp.add_parser("status"); p.add_argument("work"); p.set_defaults(f=cmd_status)
    a = ap.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()

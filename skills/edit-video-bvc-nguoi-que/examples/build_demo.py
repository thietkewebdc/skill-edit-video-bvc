import json, sys
P = sys.argv[1]
plan = json.load(open(P, encoding="utf-8"))
plan["title"] = {"lines": ["GIA ĐÌNH", "HẠNH PHÚC NHẤT"], "dur": 2.6, "y": 0.36, "width": 0.7}
plan["cast"] = {
    "dad": {"kind": "man", "h": 0.62},
    "mom": {"kind": "woman", "h": 0.58, "dress": True},
    "son": {"kind": "boy", "h": 0.4, "sweater": True},
    "girl": {"kind": "girl", "h": 0.36},
    "a": {"kind": "man", "h": 0.62},
    "b": {"kind": "plain", "h": 0.6, "shirt": True},
    "old": {"kind": "old", "h": 0.64},
}
S = {}
S[1] = dict(bg={"type": "path", "horizon": 0.55, "road_x": 0.5}, tone="neutral", cam={"zoom": [1.0, 1.08]}, items=[
    {"type": "prop", "name": "mansion", "x": 0.22, "y": 0.5, "s": 0.42, "opacity": 0.85},
    {"type": "prop", "name": "house", "x": 0.8, "y": 0.52, "s": 0.3, "light": 0.8},
    {"id": "dad", "x": 0.5, "y": 0.86, "pose": "think", "expr": "worried", "face": 0.4, "do": ["breathe"],
     "keys": [{"t": "không đổ lỗi", "expr": "smile", "face": 0.8}]},
])
S[2] = dict(bg="hut", tone="warm", cam={"zoom": [1.02, 1.1]}, items=[
    {"type": "prop", "name": "lamp", "x": 0.74, "y": 0.9, "s": 0.12},
    {"id": "dad", "x": 0.38, "y": 0.83, "pose": "hug", "expr": "happy", "face": 0.4, "reach": {"arm": "R", "to": "mom.shoulder"}, "do": ["breathe"],
     "keys": [{"t": "nói chuyện", "do": ["talk"]}]},
    {"id": "mom", "x": 0.6, "y": 0.83, "expr": "happy", "face": -0.4, "reach": {"arm": "L", "to": "dad.shoulder"}, "do": ["breathe"]},
    {"id": "son", "x": 0.23, "y": 0.88, "expr": "joy", "face": 0.5, "reach": {"arm": "R", "to": "dad.belly"}, "do": ["bounce"]},
    {"id": "girl", "x": 0.52, "y": 0.92, "expr": "joy", "do": ["bounce"], "face": 0},
])
S[3] = dict(bg="floor", tone="warm", cam={"zoom": [1.0, 1.07], "from": [1.0, 0.5, 0.6]}, items=[
    {"type": "prop", "name": "vase", "x": 0.5, "y": 0.84, "s": 0.2, "broken": 1},
    {"id": "dad", "x": 0.28, "y": 0.84, "pose": "crouch", "expr": "worried", "face": 0.7,
     "keys": [{"t": "nhìn lại", "expr": "calm"}, {"t": "giải pháp", "expr": "smile"}]},
    {"id": "mom", "x": 0.74, "y": 0.84, "pose": "crouch", "expr": "worried", "face": -0.7,
     "keys": [{"t": "nhìn lại", "expr": "calm"}, {"t": "giải pháp", "expr": "smile"}]},
    {"type": "prop", "name": "tape", "x": 0.6, "y": 0.9, "s": 0.06},
])
S[4] = dict(bg={"type": "field", "horizon": 0.7, "sun": [0.78, 0.2, 0.18]}, tone="golden", cam={"zoom": [1.0, 1.06]}, items=[
    {"id": "dad", "x": 0.2, "y": 0.84, "expr": "happy", "glow": 0.8, "hold": "mom", "do": ["breathe"]},
    {"id": "mom", "x": 0.4, "y": 0.84, "expr": "happy", "glow": 0.8, "hold": ["dad", "son"], "do": ["breathe"]},
    {"id": "son", "x": 0.6, "y": 0.86, "expr": "joy", "glow": 0.8, "hold": ["mom", "girl"], "do": ["bounce"]},
    {"id": "girl", "x": 0.78, "y": 0.86, "expr": "joy", "glow": 0.8, "hold": "son", "do": ["bounce"]},
])
S[5] = dict(bg={"type": "outdoor", "horizon": 0.72}, tone="warm", cam={"zoom": [1.0, 1.08]}, fx=[{"name": "glow", "x": 0.5, "y": 0.2, "r": 0.9, "a": 0.4}], items=[
    {"type": "prop", "name": "sapling", "x": 0.52, "y": 0.84, "s": 0.34, "grow": 0.2, "keys": [{"t": 0.3, "grow": 1.0, "d": 4}], "vanish": "công việc"},
    {"id": "son", "x": 0.4, "y": 0.86, "expr": "joy", "face": 0.6, "reach": {"arm": "R", "to": [0.51, 0.72]}, "vanish": "công việc"},
    {"type": "prop", "name": "door", "x": 0.3, "y": 0.84, "s": 0.62, "appear": "công việc"},
    {"id": "son", "kind": "man", "sweater": False, "shirt": True, "h": 0.58, "x": 0.44, "y": 0.86, "expr": "happy", "face": 0.6, "appear": "công việc",
     "reach": {"arm": "R", "to": [0.58, 0.64]}, "hold_prop": {"name": "briefcase", "arm": "L", "s": 0.1}},
    {"id": "b", "x": 0.72, "y": 0.86, "expr": "smile", "face": -0.6, "appear": "công việc", "reach": {"arm": "L", "to": [0.59, 0.64]}},
])
angry = lambda i, x, y, face, tgt: {"id": i, "x": x, "y": y, "pose": "angry_point", "expr": "angry", "face": face, "do": ["shake", "talk"],
                                    "reach": {"arm": "R" if face > 0 else "L", "to": tgt + ".head"}}
S[6] = dict(bg="paper", tone="neutral", cam={"zoom": [1.0, 1.12]}, items=[
    angry("dad", 0.3, 0.74, 1, "mom"), angry("mom", 0.72, 0.74, -1, "dad"),
    angry("son", 0.25, 0.92, 1, "girl"), angry("girl", 0.75, 0.92, -1, "son"),
    {"type": "prop", "name": "lightning", "x": 0.5, "y": 0.42, "s": 0.16, "appear": "công kích"},
])
S[7] = dict(bg="floor", tone="cold", cam={"zoom": [1.08, 1.0]}, items=[
    {"id": "dad", "x": 0.18, "y": 0.8, "pose": "slump", "expr": "sad", "face": -0.8},
    {"id": "mom", "x": 0.82, "y": 0.8, "pose": "slump", "expr": "sad", "face": 0.8},
    {"type": "prop", "name": "heart", "x": 0.5, "y": 0.45, "s": 0.34, "broken": 0.2, "dark": 0.3, "keys": [{"t": 0.5, "broken": 1, "d": 2.0}]},
])
S[8] = dict(bg={"type": "doorway", "horizon": 0.66, "door_w": 0.5, "door_h": 0.46}, tone="dark", cam={"zoom": [1.0, 1.1], "from": [1, 0.5, 0.55]}, items=[
    angry("dad", 0.4, 0.66, 1, "mom") | {"h": 0.3}, angry("mom", 0.6, 0.66, -1, "dad") | {"h": 0.28},
    {"id": "son", "kind": "man", "h": 0.62, "x": 0.5, "y": 0.9, "expr": "sad", "dark": 0.9, "pose": "walk", "do": ["walk"], "walk_in_place": True, "face": 0.001},
])
S[9] = dict(bg="paper", tone="neutral", cam={"zoom": [1.0, 1.1], "from": [1.0, 0.5, 0.55]}, items=[
    {"id": "a", "x": 0.3, "y": 0.8, "pose": "angry_point", "expr": "shout", "face": 1, "do": ["jab", "shake"]},
    {"id": "b", "x": 0.72, "y": 0.8, "pose": "lean_back", "expr": "worried", "face": -1, "do": ["tremble"]},
    {"type": "prop", "name": "bubble", "x": 0.5, "y": 0.3, "s": 0.34, "spiky": True, "content": "angry", "tail": [-0.25, 0.5], "appear": "miệng độc"},
])
S[10] = dict(bg="paper", tone="neutral", cam={"zoom": [1.06, 1.16], "from": [1.06, 0.62, 0.5]}, items=[
    {"id": "a", "x": 0.22, "y": 0.8, "pose": "hips", "expr": "angry", "face": 1},
    {"id": "b", "x": 0.68, "y": 0.8, "pose": "hand_chest", "expr": "hurt", "face": -0.6, "crack": 0, "keys": [{"t": "người khác đau", "crack": 1, "d": 0.8}], "do": ["sob"]},
])
S[11] = dict(bg="paper", tone="warm", cam={"zoom": [1.0, 1.1], "from": [1.0, 0.5, 0.45]}, items=[
    {"type": "prop", "name": "heart", "x": 0.5, "y": 0.42, "s": 0.5, "crack": True, "broken": 0.05, "beat": 1},
    {"type": "prop", "name": "knife", "x": 0.72, "y": 0.2, "s": 0.4, "rot": 125, "keys": [{"t": "cắm vào", "x": 0.6, "y": 0.34, "d": 0.3}]},
    {"id": "b", "x": 0.5, "y": 0.86, "h": 0.42, "pose": "sit_knees", "expr": "cry", "face": 0},
])
S[12] = dict(bg={"type": "path", "horizon": 0.6, "road_x": 0.55, "trees": 2}, tone="golden", cam={"zoom": [1.0, 1.08]},
             fx=[{"name": "glow", "x": 0.5, "y": 0.58, "r": 0.8, "a": 0.5}], items=[
    *[{"type": "prop", "name": "frame", "x": x, "y": y, "s": 0.12, "rot": r, "oval": o, "keys": [{"t": 0, "y": y - 0.04, "d": 5.6}]}
      for x, y, r, o in [(0.12, 0.2, -12, False), (0.3, 0.12, 8, True), (0.52, 0.16, -5, False), (0.72, 0.1, 14, True), (0.9, 0.22, -8, False), (0.1, 0.4, 10, True), (0.9, 0.42, -14, True)]],
    {"id": "old", "x": 0.4, "y": 0.84, "pose": "cane", "expr": "smile", "face": 0.5, "hold": "son", "hold_prop": {"name": "cane", "arm": "L", "s": 0.3}},
    {"id": "son", "h": 0.34, "x": 0.6, "y": 0.86, "expr": "joy", "face": -0.3, "hold": "old", "do": ["bounce"]},
])
S[13] = dict(S[12], cam={"zoom": [1.08, 1.12]}, fx=[{"name": "darken", "a": 0.0}], items=[
    *[dict(it, keys=[{"t": "không có gia đình", "opacity": 0, "d": 1.5}]) if it.get("name") == "frame" else
      (dict(it, keys=[{"t": "không có gia đình", "dark": 1, "d": 1.2}]) if it.get("type", "fig") == "fig" else it) for it in S[12]["items"]]
])
S[14] = dict(bg="paper", tone="warm", cam={"zoom": [1.0, 1.08], "from": [1, 0.5, 0.6]}, items=[
    {"id": "a", "x": 0.35, "y": 0.8, "pose": "kneel2", "expr": "cry", "face": 0.6, "do": ["sob"]},
    {"id": "b", "x": 0.66, "y": 0.8, "pose": "kneel", "expr": "calm", "face": -0.6, "flip": True, "reach": {"arm": "L", "to": "a.shoulder"}},
])
S[15] = dict(bg="paper", tone="warm", cam={"zoom": [1.1, 1.18], "from": [1.1, 0.5, 0.62]}, items=[
    {"id": "a", "x": 0.36, "y": 0.8, "pose": "kneel2", "expr": "sad", "face": 0.6, "tears": 1, "keys": [{"t": "yếu đuối", "expr": "smile"}]},
    {"id": "b", "x": 0.64, "y": 0.8, "pose": "kneel", "expr": "smile", "face": -0.6, "flip": True, "reach": {"arm": "L", "to": [0.5, 0.63]}},
])
S[16] = dict(bg={"type": "room", "horizon": 0.6}, tone="neutral", cam={"zoom": [1.0, 1.1], "from": [1, 0.5, 0.62]}, items=[
    {"type": "prop", "name": "heart", "x": 0.5, "y": 0.74, "s": 0.44, "broken": 1, "keys": [{"t": "chấp nhận", "broken": 0.15, "d": 1.2}, {"t": "chấp nhận+1.2", "mend": 1, "d": 2.5}]},
    {"id": "dad", "x": 0.14, "y": 0.84, "pose": "crouch", "expr": "calm", "face": 1, "reach": {"arm": "R", "to": [0.36, 0.72]}},
    {"id": "mom", "x": 0.86, "y": 0.84, "pose": "crouch", "expr": "smile", "face": -1, "reach": {"arm": "L", "to": [0.64, 0.72]}},
    {"type": "prop", "name": "tape", "x": 0.18, "y": 0.9, "s": 0.07},
])
S[17] = dict(bg="floor", tone="warm", cam={"zoom": [1.0, 1.06]}, items=[
    {"type": "prop", "name": "wall", "x": 0.5, "y": 0.84, "s": 0.55, "width": 0.3, "vanish": "cùng nhau+0.6"},
    {"id": "dad", "x": 0.16, "y": 0.84, "pose": "hips", "expr": "angry", "face": 1, "do": ["walk"],
     "keys": [{"t": "cùng nhau+0.8", "x": 0.34, "d": 1.4, "expr": "smile", "pose": "walk"}, {"t": "cùng nhau+2.2", "pose": "reach", "d": 0.5}]},
    {"id": "mom", "x": 0.84, "y": 0.84, "pose": "hips", "expr": "angry", "face": -1, "do": ["walk"],
     "keys": [{"t": "cùng nhau+0.8", "x": 0.66, "d": 1.4, "expr": "smile", "pose": "walk"}, {"t": "cùng nhau+2.2", "pose": "reach", "d": 0.5}]},
])
S[18] = dict(bg="paper", tone="warm", cam={"zoom": [1.0, 1.08]}, fx=[{"name": "rings", "x": 0.5, "y": 0.56, "r": 0.8, "a": 0.8, "n": 3}], items=[
    {"type": "prop", "name": "house", "x": 0.5, "y": 0.78, "s": 0.8, "light": 1},
    {"id": "dad", "h": 0.2, "x": 0.42, "y": 0.77, "pose": "sit", "expr": "happy", "face": 0.5},
    {"id": "mom", "h": 0.19, "x": 0.6, "y": 0.77, "pose": "sit", "flip": True, "expr": "happy", "face": -0.5},
    {"id": "son", "h": 0.13, "x": 0.51, "y": 0.78, "expr": "joy", "do": ["bounce"]},
])
S[19] = dict(bg="hut", tone="golden", cam={"zoom": [1.05, 1.12]}, items=[
    {"type": "prop", "name": "lamp", "x": 0.5, "y": 0.86, "s": 0.14},
    {"id": "dad", "x": 0.2, "y": 0.86, "pose": "sit_cross", "expr": "happy", "face": 0.5, "h": 0.5},
    {"id": "mom", "x": 0.8, "y": 0.86, "pose": "sit_cross", "expr": "happy", "face": -0.5, "h": 0.48},
    {"id": "son", "x": 0.36, "y": 0.93, "pose": "sit_cross", "expr": "joy", "face": 0.4, "h": 0.34},
    {"id": "girl", "x": 0.64, "y": 0.93, "pose": "sit_cross", "expr": "joy", "face": -0.4, "h": 0.32},
])
S[20] = dict(panels=[
    {"rect": [0, 0, 0.5, 1], "bg": {"type": "paper"}, "tone": "golden",
     "fx": [{"name": "rings", "x": 0.5, "y": 0.55, "r": 0.9, "a": 0.8}],
     "items": [{"type": "prop", "name": "house", "x": 0.5, "y": 0.66, "s": 0.95, "light": 1},
               {"id": "dad", "h": 0.3, "x": 0.38, "y": 0.64, "pose": "sit", "expr": "happy", "face": 0.5},
               {"id": "mom", "h": 0.28, "x": 0.64, "y": 0.64, "pose": "sit", "flip": True, "expr": "happy", "face": -0.5}]},
    {"rect": [0.5, 0, 0.5, 1], "bg": {"type": "hall", "horizon": 0.55}, "tone": "cold", "enter": "slide_right",
     "items": [{"id": "dad", "h": 0.8, "x": 0.25, "y": 0.72, "dark": 1, "expr": "sad", "face": -1, "do": ["walk"], "keys": [{"t": "xa cách", "x": 0.12, "d": 2}]},
               {"id": "mom", "h": 0.76, "x": 0.72, "y": 0.72, "dark": 1, "expr": "sad", "face": 1, "do": ["walk"], "keys": [{"t": "xa cách", "x": 0.86, "d": 2}]},
               {"id": "son", "h": 0.5, "x": 0.5, "y": 0.74, "dark": 1, "expr": "sad", "pose": "slump"}]},
], cam={"zoom": [1.0, 1.04]})
S[21] = dict(bg="paper", tone="neutral", cam={"zoom": [1.0, 1.08]}, items=[
    {"id": "a", "x": 0.3, "y": 0.82, "pose": "angry_point", "expr": "angry", "face": 1, "do": ["talk"],
     "keys": [{"t": "tăng thêm", "pose": "arms_open", "expr": "smile"}]},
    {"id": "b", "x": 0.72, "y": 0.82, "pose": "defend", "expr": "worried", "face": -1, "keys": [{"t": "tăng thêm", "pose": "stand", "expr": "happy"}]},
    {"type": "prop", "name": "bubble", "x": 0.52, "y": 0.28, "s": 0.32, "spiky": True, "content": "angry", "vanish": "tăng thêm"},
    {"type": "prop", "name": "bubble", "x": 0.52, "y": 0.28, "s": 0.32, "content": "heart", "appear": "tăng thêm"},
])
S[22] = dict(bg="floor", tone="warm", cam={"zoom": [1.0, 1.08]}, items=[
    {"id": "b", "x": 0.62, "y": 0.84, "pose": "sit", "expr": "sad", "face": -0.5, "flip": True, "reach": {"arm": "L", "to": [0.47, 0.6]},
     "keys": [{"t": "tăng thêm", "pose": "stand", "expr": "happy", "d": 1.0}]},
    {"id": "a", "x": 0.3, "y": 0.84, "pose": "reach", "expr": "smile", "face": 1, "reach": {"arm": "R", "to": [0.47, 0.6]}},
])
S[23] = dict(bg={"type": "field", "horizon": 0.56}, tone="golden", cam={"zoom": [1.0, 1.1], "from": [1, 0.5, 0.55]},
             fx=[{"name": "glow", "x": 0.5, "y": 0.5, "r": 0.7, "a": 0.7}, {"name": "rays", "x": 0.5, "y": 0.52, "n": 14, "len": 1.4, "a": 0.4}], items=[
    {"type": "prop", "name": "tree", "x": 0.5, "y": 0.6, "s": 0.78, "leaves": 0.2, "keys": [{"t": "phát triển", "leaves": 1, "d": 2}], "glow": 0.6},
    {"type": "crowd", "layout": "circle", "cx": 0.5, "cy": 0.74, "rx": 0.44, "ry": 0.1, "n": 16, "h": 0.27, "hold": True, "expr": "happy",
     "exprs": ["happy", "joy", "smile"], "keys": [{"t": "ngày càng phát triển", "pose": "cheer", "do": ["cheer"]}]},
])
for sc in plan["scenes"]:
    spec = S.get(sc["i"], {})
    for k in ("items", "panels", "fx", "bg", "tone", "cam"):
        sc.pop(k, None)
    sc.update(spec)
    sc.setdefault("bg", "paper")
json.dump(plan, open(P, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("ok", len(plan["scenes"]))



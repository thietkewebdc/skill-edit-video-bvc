/* Engine animation kiểu "motion graphics phẳng" (phong cách kênh Hồ Mạnh Thắng, không logo).
   Mọi chuyển động là hàm thuần của thời gian t → renderAt(t) cho ra đúng 1 khung, chụp tuần tự. */
(() => {
'use strict';

// ───────────── bảng màu ─────────────
const TH = {
  dark:   { bg: '#1B1B1B', ink: '#FFFFFF', acc: '#F2C14E', ul: '#D9503F', d1: 'rgba(242,193,78,0.10)', d2: 'rgba(255,255,255,0.035)', mut: 'rgba(255,255,255,0.55)', pill: 'rgba(255,255,255,0.13)', light: false, num: '#F2C14E', cardStyle: 'dark' },
  green:  { bg: '#1F4630', ink: '#FFFFFF', acc: '#F2C14E', ul: '#D9503F', d1: 'rgba(242,193,78,0.11)', d2: 'rgba(0,0,0,0.13)', mut: 'rgba(255,255,255,0.6)', pill: 'rgba(255,255,255,0.13)', light: false, num: '#F2C14E', cardStyle: 'light' },
  red:    { bg: '#DD5840', ink: '#FFF8EE', acc: '#FAD25E', ul: '#A92D1E', d1: 'rgba(120,20,10,0.13)', d2: 'rgba(255,255,255,0.07)', mut: 'rgba(255,248,238,0.72)', pill: 'rgba(0,0,0,0.17)', light: false, num: '#1E2A22', cardStyle: 'light' },
  yellow: { bg: '#ECC24E', ink: '#1E2A22', acc: '#C8321F', ul: '#F8E6A8', d1: 'rgba(221,120,40,0.16)', d2: 'rgba(255,255,255,0.13)', mut: 'rgba(30,42,34,0.55)', pill: 'rgba(0,0,0,0.15)', light: true, num: '#1E2A22', cardStyle: 'light' },
  cream:  { bg: '#F2EDE1', ink: '#1E2A22', acc: '#D9503F', ul: '#F2C14E', d1: 'rgba(217,80,63,0.08)', d2: 'rgba(242,193,78,0.15)', mut: 'rgba(30,42,34,0.5)', pill: 'rgba(0,0,0,0.27)', light: true, num: '#D9503F', cardStyle: 'light' },
  white:  { bg: '#FBF9F4', ink: '#1E2A22', acc: '#D9503F', ul: '#F2C14E', d1: 'rgba(217,80,63,0.07)', d2: 'rgba(242,193,78,0.13)', mut: 'rgba(30,42,34,0.5)', pill: 'rgba(0,0,0,0.27)', light: true, num: '#D9503F', cardStyle: 'light' },
  mint:   { bg: '#D5EBDD', ink: '#1E4630', acc: '#2F8F57', ul: '#F2C14E', d1: 'rgba(47,143,87,0.10)', d2: 'rgba(255,255,255,0.32)', mut: 'rgba(30,70,48,0.55)', pill: 'rgba(0,0,0,0.22)', light: true, num: '#1E4630', cardStyle: 'light' },
  crimson:{ bg: '#AE2A22', ink: '#FFF8EE', acc: '#FAD25E', ul: '#6E1712', d1: 'rgba(0,0,0,0.12)', d2: 'rgba(255,255,255,0.05)', mut: 'rgba(255,248,238,0.7)', pill: 'rgba(0,0,0,0.2)', light: false, num: '#FAD25E', cardStyle: 'light' },
  sunset: { bg: '#2B4262', ink: '#FFFFFF', acc: '#FAD25E', ul: '#D9503F', d1: 'rgba(0,0,0,0)', d2: 'rgba(0,0,0,0)', mut: 'rgba(255,255,255,0.7)', pill: 'rgba(0,0,0,0.22)', light: false, num: '#FAD25E', cardStyle: 'light' },
};
const COLORS = { red: '#D9503F', yellow: '#F2C14E', green: '#2F8F57', dark: '#1E2A22', cream: '#FFF8EA', white: '#FFFFFF', gray: '#8A8A8A', orange: '#E8913A', blue: '#3E6FB0' };
const col = (c, dflt) => c == null ? dflt : (COLORS[c] || (TH[c] && TH[c].bg) || c);
const INK = '#1E2A22';

// ───────────── trạng thái ─────────────
let W = 1080, H = 1920, U = 1, DUR = 10, BASE = '';
let WORDS = [], NW = [], SW = [];
let PLAN = {}, SC = [], EV = [], WARN = [], CHAP = [];
let stage, progEl, chapEl, brandEl;
let lastLabel = null, labelT = -9;

// ───────────── tiện ích ─────────────
const clamp = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x));
const lerp = (a, b, p) => a + (b - a) * p;
const prog = (t, a, d) => d <= 0 ? (t >= a ? 1 : 0) : clamp((t - a) / d);
const E = {
  out: p => 1 - Math.pow(1 - p, 3),
  io: p => p < .5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2,
  back: p => { const c1 = 1.9, c3 = c1 + 1; return 1 + c3 * Math.pow(p - 1, 3) + c1 * Math.pow(p - 1, 2); },
  el: p => p === 0 || p === 1 ? p : Math.pow(2, -10 * p) * Math.sin((p * 10 - 0.75) * (2 * Math.PI) / 3) + 1,
};
const px = v => (v * U) + 'px';
function el(tag, css, cls, html) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (css) Object.assign(e.style, css);
  if (html != null) e.innerHTML = html;
  return e;
}
function svgEl(tag, attrs) {
  const e = document.createElementNS('http://www.w3.org/2000/svg', tag);
  for (const k in attrs || {}) e.setAttribute(k, attrs[k]);
  return e;
}
function rng(seed) {
  let a = (seed * 2654435761) >>> 0;
  return () => { a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ t >>> 15, t | 1); t ^= t + Math.imul(t ^ t >>> 7, t | 61); return ((t ^ t >>> 14) >>> 0) / 4294967296; };
}
const esc = s => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const vs16 = e => { e = String(e); return [...e].length === 1 && e.codePointAt(0) > 0x2000 ? e + '\uFE0F' : e; };
const emo = (e, size, css) => el('span', Object.assign({ fontSize: px(size) }, css || {}), 'emo', esc(vs16(e)));
const plain = s => String(s || '').replace(/\*/g, '').replace(/\n/g, ' ');
function fmtClock(sec) { sec = Math.max(0, Math.round(sec)); const m = Math.floor(sec / 60), s = sec % 60; return String(m).padStart(2, '0') + ':' + String(s).padStart(2, '0'); }
function parseClock(v) { if (typeof v === 'number') return v; const p = String(v).split(':').map(Number); return p.length === 2 ? p[0] * 60 + p[1] : p[0]; }

// ───────────── so khớp lời nói ─────────────
const norm = s => String(s).normalize('NFC').toLowerCase().replace(/[^\p{L}\p{N}]+/gu, '');
const strip = s => s.normalize('NFD').replace(/\p{M}/gu, '').replace(/đ/g, 'd');
function lev1(a, b) {
  if (a === b) return true;
  const la = a.length, lb = b.length;
  if (Math.abs(la - lb) > 1) return false;
  let i = 0, j = 0, ed = 0;
  while (i < la && j < lb) {
    if (a[i] === b[j]) { i++; j++; continue; }
    if (++ed > 1) return false;
    if (la > lb) i++; else if (lb > la) j++; else { i++; j++; }
  }
  return ed + (la - i) + (lb - j) <= 1;
}
function eqTok(a, b) {
  if (!a || !b) return false;
  if (a === b) return true;
  const sa = strip(a), sb = strip(b);
  if (sa === sb) return true;
  if (a.length < 3 || b.length < 3) return false;
  return lev1(a, b) || lev1(sa, sb);
}
const toks = s => String(s).split(/\s+/).map(norm).filter(Boolean);

function findSay(phrase, from, to) {
  const T = toks(phrase), n = T.length;
  if (!n || !NW.length) return null;
  let best = null;
  const end = Math.min(to, NW.length - 1);
  for (let i = Math.max(0, from); i <= end; i++) {
    if (!(eqTok(NW[i], T[0]) || (n > 1 && eqTok(NW[i], T[1])))) continue;
    let j = i, m = 0, first = -1, last = -1;
    for (let k = 0; k < n; k++) {
      for (let d = 0; d < 4 && j + d < NW.length; d++) {
        if (eqTok(NW[j + d], T[k])) { m++; if (first < 0) first = j + d; last = j + d; j = j + d + 1; break; }
      }
    }
    const sc = m / n;
    if (!best || sc > best.sc + 1e-9) best = { i0: first, i1: last, sc };
    if (sc === 1) break;
  }
  if (!best || best.sc < (n <= 2 ? 1 : 0.6)) return null;
  return Object.assign(best, { s: WORDS[best.i0].s, e: WORDS[best.i1].e });
}

// thời điểm cho 1 mục con: at (giây tính từ đầu màn) | say (cụm lời) | mặc định
function timeOf(o, sc, dflt, what) {
  if (o && o.at != null) return sc._s + Number(o.at);
  if (o && o.say) {
    const r = findSay(o.say, Math.max(0, sc._wi - 4), sc._wi + 260);
    if (r && r.s <= sc._e + 0.3) return Math.max(sc._s, r.s - 0.06);
    WARN.push(`Màn ${sc._k + 1}: không thấy lời "${o.say}"${what ? ' (' + what + ')' : ''} trong màn → dùng mốc mặc định.`);
  }
  return dflt;
}

// ───────────── chữ hiện từng từ ─────────────
const TSIZE = { xs: 40, s: 54, m: 72, l: 92, xl: 130, xxl: 180 };
function parseWords(s) {
  const out = [];
  let cur = null, space = true;
  String(s).split(/(\*[^*]+\*)/).forEach(seg => {
    if (!seg) return;
    const acc = seg.length > 2 && seg[0] === '*' && seg[seg.length - 1] === '*';
    const body = acc ? seg.slice(1, -1) : seg;
    body.split(/(\s+)/).forEach(pc => {
      if (!pc) return;
      if (/^\s+$/.test(pc)) {
        space = true;
        if (pc.includes('\n')) { out.push({ br: true }); cur = null; }
        return;
      }
      if (space || !cur) { cur = { parts: [] }; out.push(cur); }
      cur.parts.push({ t: pc, acc });
      space = false;
    });
  });
  return out;
}

function makeText(it, ctx) {
  const th = ctx.th, sc = ctx.sc;
  const size = typeof it.size === 'number' ? it.size : TSIZE[it.size || ctx.defSize || 'm'];
  const ink = col(it.color, th.ink), acc = col(it.acc, th.acc), ul = col(it.ul, th.ul);
  const box = el('div', { fontSize: px(size), color: ink, maxWidth: px(it.w || 930), textAlign: it.align || 'center', fontWeight: it.weight || 800, opacity: it.opacity != null ? it.opacity : 1 }, 'txt');
  const words = parseWords(it.text || '');
  const W8 = [];
  words.forEach((w, i) => {
    if (w.br) { box.appendChild(el('br')); return; }
    const sp = el('span', null, 'w');
    let hasAcc = false;
    const tx = el('span', null, 'tx');
    w.parts.forEach(p => {
      const s = el('span', p.acc ? { color: acc } : null, null, esc(p.t));
      if (p.acc) hasAcc = true;
      tx.appendChild(s);
    });
    let u = null;
    if (hasAcc && it.underline !== false) { u = el('span', { background: ul }, 'ul'); sp.appendChild(u); }
    sp.appendChild(tx);
    box.appendChild(sp);
    box.appendChild(document.createTextNode(' '));
    W8.push({ sp, u, key: norm(w.parts.map(p => p.t).join('')) });
  });
  // mốc từng từ
  const n = W8.length;
  const times = new Array(n).fill(null);
  let s0 = ctx.a, e0 = ctx.a + 0.13 * n, r = null;
  if (it.at == null || it.say) {
    r = findSay(it.say || plain(it.text).replace(/[“”"]/g, ''), Math.max(0, sc._wi - 4), sc._wi + 260);
    if (r && r.s > sc._e + 0.3) r = null;
    if (!r && it.say) WARN.push(`Màn ${sc._k + 1}: không thấy lời "${it.say}" cho chữ → hiện theo nhịp đều.`);
  }
  if (r) {
    // chữ trên màn thường là bản rút gọn của lời nói → dò rộng tới hết màn
    let jEnd = Math.max(r.i1, r.i0);
    while (jEnd + 1 < NW.length && WORDS[jEnd + 1].s < sc._e - 0.05) jEnd++;
    s0 = r.s; e0 = Math.max(r.e, WORDS[jEnd].e * 0.5 + r.e * 0.5, r.s + 0.1);
    let j = r.i0;
    for (let i = 0; i < n; i++) {
      for (let d = 0; d < 10 && j + d <= jEnd; d++) {
        if (eqTok(NW[j + d], W8[i].key)) { times[i] = WORDS[j + d].s; j = j + d + 1; break; }
      }
    }
  }
  const known = times.map((v, i) => v != null ? i : -1).filter(i => i >= 0);
  if (!known.length) for (let i = 0; i < n; i++) times[i] = lerp(s0, e0, n > 1 ? i / (n - 1) : 0) - (r ? 0 : 0);
  else {
    for (let i = 0; i < n; i++) {
      if (times[i] != null) continue;
      const prev = known.filter(k => k < i).pop(), next = known.find(k => k > i);
      if (prev == null) times[i] = lerp(s0, times[next], i / next);
      else if (next == null) times[i] = Math.min(e0, times[prev] + 0.16 * (i - prev));
      else times[i] = lerp(times[prev], times[next], (i - prev) / (next - prev));
    }
  }
  const floor = it.at != null && !it.say ? sc._s + Number(it.at) : sc._s + 0.02;
  for (let i = 0; i < n; i++) {
    times[i] = Math.max(times[i], floor, i ? times[i - 1] : -1e9);
    if (it.instant) times[i] = times[0];
  }
  ctx.a = n ? times[0] : ctx.a;
  const upd = t => {
    for (let i = 0; i < n; i++) {
      const w = W8[i], p = prog(t, times[i] - 0.06, 0.3);
      if (p <= 0) { w.sp.style.opacity = 0; continue; }
      const e = E.out(p);
      w.sp.style.opacity = e;
      w.sp.style.transform = p < 1 ? `translateY(${(1 - e) * 0.32}em)` : '';
      w.sp.style.filter = p < 1 ? `blur(${(1 - p) * 5 * U}px)` : '';
      if (w.u) { const q = E.out(prog(t, times[i] + 0.14, 0.32)); w.u.style.transform = `scaleX(${q})`; }
    }
  };
  return { el: box, upd, noEntry: true, times };
}

// ───────────── thành phần ─────────────
const C = {};

C.text = (it, ctx) => makeText(it, ctx);

C.emoji = (it, ctx) => {
  const size = it.size || 200;
  const wrap = el('div', { position: 'relative', display: 'flex', alignItems: 'center', justifyContent: 'center' });
  if (it.disc) {
    const d = size * (it.discScale || 1.55);
    Object.assign(wrap.style, { width: px(d), height: px(d), borderRadius: '50%', background: col(it.disc, it.disc) });
  }
  const e = emo(it.e, size);
  wrap.appendChild(e);
  const swaps = (it.swap || []).map((s, k) => ({ e: s.e, t: timeOf(s, ctx.sc, ctx.a + 1 + k, 'swap') }));
  swaps.forEach(s => ctx.ev(s.t, 'pop'));
  let cur = it.e;
  return {
    el: wrap, sfx: 'pop', upd: t => {
      let want = it.e, st = -9;
      swaps.forEach(s => { if (t >= s.t) { want = s.e; st = s.t; } });
      if (want !== cur) { e.textContent = want; cur = want; }
      const q = st > 0 ? prog(t, st, 0.35) : 1;
      e.style.transform = q < 1 ? `scale(${0.7 + 0.3 * E.back(q)})` : '';
    }
  };
};

function iconBadge(kind, th, size, k) {
  size = size || 46;
  const b = el('div', { width: px(size), height: px(size), borderRadius: '50%', flex: 'none', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 900, fontSize: px(size * 0.55), color: '#fff' });
  if (kind === 'check') { b.style.background = '#D9503F'; b.textContent = '✓'; }
  else if (kind === 'x') { b.style.background = '#D9503F'; b.textContent = '✕'; }
  else if (kind === 'ok') { b.style.background = '#2F8F57'; b.textContent = '✓'; }
  else if (kind === 'dash') { b.style.color = th; b.textContent = '–'; b.style.fontSize = px(size * 0.8); }
  else if (kind === 'dot') { b.appendChild(el('div', { width: px(size * 0.36), height: px(size * 0.36), borderRadius: '50%', background: '#D9503F' })); }
  else if (kind === 'num') { b.style.background = '#F2C14E'; b.style.color = INK; b.textContent = String(k + 1); }
  else { b.appendChild(emo(kind, size * 0.72)); }
  return b;
}

C.list = (it, ctx) => {
  const style = it.style || ctx.th.cardStyle;
  const light = style === 'light';
  const box = el('div', { display: 'flex', flexDirection: 'column', gap: px(it.gap || 20), alignItems: 'stretch', width: px(it.w || 800) });
  const rows = (it.items || []).map((r, k) => {
    if (typeof r === 'string') r = { t: r };
    const row = el('div', { display: 'flex', alignItems: 'center', gap: px(22), padding: `${px(22)} ${px(28)}`, borderRadius: px(18), fontSize: px(it.fs || 38), fontWeight: 700, lineHeight: 1.2, background: light ? '#FFF9EE' : 'rgba(255,255,255,0.08)', color: light ? INK : '#fff', boxShadow: light ? `0 ${px(10)} ${px(26)} rgba(0,0,0,0.12)` : 'none' });
    row.appendChild(iconBadge(r.icon || it.icon || 'check', light ? INK : '#fff', 48, k));
    row.appendChild(el('div', null, null, esc(r.t)));
    box.appendChild(row);
    const t0 = timeOf(r, ctx.sc, ctx.a + 0.5 * k, 'dòng ' + (k + 1));
    ctx.ev(t0, 'tick');
    return { row, t0 };
  });
  return {
    el: box, noSfx: true, upd: t => rows.forEach(({ row, t0 }) => {
      const p = prog(t, t0, 0.4), e = E.out(p);
      row.style.opacity = p <= 0 ? 0 : e;
      row.style.transform = p < 1 ? `translateX(${-(1 - e) * 140 * U}px) rotate(${-(1 - e) * 4}deg)` : '';
    })
  };
};

C.timer = (it, ctx) => {
  const D = it.d || 460, sw = 26, r = (D - sw) / 2, Cc = 2 * Math.PI * r;
  const wrap = el('div', { position: 'relative', width: px(D), height: px(D) });
  const svg = svgEl('svg', { width: D * U, height: D * U, viewBox: `0 0 ${D} ${D}` });
  const track = svgEl('circle', { cx: D / 2, cy: D / 2, r, fill: 'none', stroke: ctx.th.light ? 'rgba(0,0,0,0.09)' : 'rgba(255,255,255,0.1)', 'stroke-width': sw });
  const arc = svgEl('circle', { cx: D / 2, cy: D / 2, r, fill: 'none', stroke: col(it.color, '#D9503F'), 'stroke-width': sw, 'stroke-linecap': 'round', 'stroke-dasharray': Cc, transform: `rotate(-90 ${D / 2} ${D / 2})` });
  svg.appendChild(track); svg.appendChild(arc);
  wrap.appendChild(svg);
  const mid = el('div', { position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: px(6) });
  if (it.emoji !== false) mid.appendChild(emo(it.emoji || '⏱️', 58));
  const dig = el('div', { fontSize: px(it.fs || 104), fontWeight: 900, color: col(it.ink, ctx.th.ink), fontVariantNumeric: 'tabular-nums', letterSpacing: '-0.02em', lineHeight: 1 });
  mid.appendChild(dig);
  wrap.appendChild(mid);
  const v0 = parseClock(it.from != null ? it.from : 0), v1 = parseClock(it.to != null ? it.to : v0);
  const [f0, f1] = it.ring || [0.08, 0.32];
  const ts = timeOf(it.run || {}, ctx.sc, ctx.a + 0.2);
  const dur = it.dur || Math.max(0.6, ctx.sc._e - ts - 0.15);
  return {
    el: wrap, upd: t => {
      const p = E.io(prog(t, ts, dur));
      dig.textContent = it.fmt === 'num' ? String(Math.round(lerp(v0, v1, p))) : fmtClock(lerp(v0, v1, p));
      arc.setAttribute('stroke-dashoffset', Cc * (1 - lerp(f0, f1, p)));
    }
  };
};

C.usage = (it, ctx) => {
  const card = el('div', { width: px(it.w || 800), background: '#FFFFFF', borderRadius: px(26), padding: `${px(34)} ${px(42)}`, color: INK, boxShadow: `0 ${px(16)} ${px(40)} rgba(0,0,0,0.16)`, display: 'flex', flexDirection: 'column', gap: px(14) });
  card.appendChild(el('div', { fontSize: px(26), fontWeight: 700, color: 'rgba(30,42,34,0.6)' }, null, '⏳ ' + esc(it.title || 'Thời gian sử dụng')));
  const bigc = col(it.color, '#D9503F');
  const big = el('div', { display: 'flex', alignItems: 'baseline', gap: px(14), color: bigc });
  const num = el('span', { fontSize: px(it.fs || 130), fontWeight: 900, lineHeight: 1, fontVariantNumeric: 'tabular-nums' });
  big.appendChild(num);
  big.appendChild(el('span', { fontSize: px(48), fontWeight: 800 }, null, esc(it.unit || 'phút')));
  card.appendChild(big);
  if (it.note) card.appendChild(el('div', { fontSize: px(28), fontWeight: 700 }, null, esc(it.note)));
  const bars = [];
  const rowsBox = el('div', { display: 'grid', gridTemplateColumns: `${px(150)} 1fr ${px(70)}`, alignItems: 'center', columnGap: px(20), rowGap: px(14), marginTop: px(8) });
  (it.rows || []).forEach(r => {
    rowsBox.appendChild(el('div', { fontSize: px(26), fontWeight: 700 }, null, esc(r.label)));
    const tr = el('div', { height: px(18), borderRadius: px(9), background: '#ECE7DC', overflow: 'hidden' });
    const fl = el('div', { height: '100%', width: '0%', borderRadius: px(9), background: col(r.color || it.barColor, '#F2C14E') });
    tr.appendChild(fl); rowsBox.appendChild(tr);
    rowsBox.appendChild(el('div', { fontSize: px(24), fontWeight: 700, textAlign: 'right' }, null, esc(r.v || '')));
    bars.push({ fl, f: r.fill != null ? r.fill : 0.5 });
  });
  if (bars.length) card.appendChild(rowsBox);
  const dec = (String(it.to).split('.')[1] || '').length;
  const from = +(it.from || 0), to = +it.to;
  const ts = timeOf(it.run || {}, ctx.sc, ctx.a + 0.25), dur = it.dur || 1.4;
  return {
    el: card, sfx: 'pop', upd: t => {
      const p = E.out(prog(t, ts, dur));
      num.textContent = lerp(from, to, p).toFixed(dec) + (p >= 1 && it.suffix ? it.suffix : '');
      bars.forEach(b => { b.fl.style.width = (b.f * 100 * p) + '%'; });
    }
  };
};

C.battery = (it, ctx) => {
  const ink = col(it.ink, ctx.th.ink);
  const wrap = el('div', { display: 'flex', flexDirection: 'column', alignItems: 'center', gap: px(28) });
  const row = el('div', { display: 'flex', alignItems: 'center' });
  const body = el('div', { width: px(460), height: px(210), border: `${px(14)} solid ${ink}`, borderRadius: px(36), padding: px(12) });
  const fill = el('div', { height: '100%', borderRadius: px(20) });
  body.appendChild(fill);
  row.appendChild(body);
  row.appendChild(el('div', { width: px(24), height: px(84), background: ink, borderRadius: `0 ${px(12)} ${px(12)} 0` }));
  wrap.appendChild(row);
  const lab = el('div', { fontSize: px(80), fontWeight: 900, color: ink, fontVariantNumeric: 'tabular-nums' });
  wrap.appendChild(lab);
  const v0 = it.from != null ? it.from : 100, v1 = it.to != null ? it.to : 14;
  const ts = timeOf(it.drain || {}, ctx.sc, ctx.a + 0.4), dur = it.dur || 1.3;
  return {
    el: wrap, upd: t => {
      const v = lerp(v0, v1, E.io(prog(t, ts, dur)));
      fill.style.width = clamp(v / 100, 0.03, 1) * 100 + '%';
      fill.style.background = v > 50 ? '#3DD06A' : v > 22 ? '#F2C14E' : '#D9503F';
      lab.textContent = Math.round(v) + '%';
    }
  };
};

C.vs = (it, ctx) => {
  const box = el('div', { position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column' });
  const halves = ['top', 'bottom'].map((k, i) => {
    const d = it[k] || {};
    const th = TH[d.bg || (i ? 'yellow' : 'white')] || TH.white;
    const h = el('div', { flex: 1, background: th.bg, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: px(14), paddingTop: px(i ? 60 : 110), color: th.ink });
    const inner = el('div', { display: 'flex', flexDirection: 'column', alignItems: 'center', gap: px(14) });
    if (d.cap) inner.appendChild(el('div', { fontSize: px(28), fontWeight: 800, letterSpacing: '0.12em', color: th.mut, textTransform: 'uppercase' }, null, esc(d.cap)));
    if (d.e) inner.appendChild(emo(d.e, d.size || 150));
    if (d.t) inner.appendChild(el('div', { fontSize: px(d.fs || 66), fontWeight: 800, textAlign: 'center', maxWidth: px(900) }, null, esc(d.t)));
    h.appendChild(inner);
    box.appendChild(h);
    const t0 = i ? timeOf(d, ctx.sc, ctx.a + 0.9, 'vs dưới') : timeOf(d, ctx.sc, ctx.a, 'vs trên');
    ctx.ev(t0, 'pop');
    return { inner, t0 };
  });
  const vs = el('div', { position: 'absolute', left: '50%', top: '50%', width: px(124), height: px(124), marginLeft: px(-62), marginTop: px(-62), borderRadius: '50%', background: '#D9503F', color: '#fff', fontSize: px(46), fontWeight: 900, display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: `0 ${px(8)} ${px(20)} rgba(0,0,0,0.18)` }, null, 'VS');
  box.appendChild(vs);
  const tv = halves[1].t0 - 0.25;
  return {
    el: box, abs: true, noEntry: true, noSfx: true, upd: t => {
      halves.forEach(h => { const p = prog(t, h.t0, 0.45); h.inner.style.opacity = clamp(p * 2.5); h.inner.style.transform = `scale(${p <= 0 ? 0.6 : 0.6 + 0.4 * E.back(p)})`; });
      const q = prog(t, tv, 0.4);
      vs.style.transform = `scale(${q <= 0 ? 0 : E.back(q)})`;
    }
  };
};

C.phone = (it, ctx) => {
  const Wp = it.w || 400, Hp = Wp * 1.95;
  const frame = el('div', { width: px(Wp), height: px(Hp), borderRadius: px(Wp * 0.14), background: '#161616', padding: px(14), boxShadow: `0 ${px(24)} ${px(50)} rgba(0,0,0,0.3)`, position: 'relative' });
  const scr = el('div', { position: 'absolute', inset: px(14), borderRadius: px(Wp * 0.11), overflow: 'hidden', background: '#222' });
  frame.appendChild(scr);
  const feed = (it.feed || [{ e: '😂', cap: 'Clip hài' }]).map((f, k) => {
    const s = el('div', { position: 'absolute', left: 0, right: 0, height: '100%', background: `linear-gradient(180deg, ${col(f.bg, ['#D9503F', '#2F6B45', '#1E3A28', '#C8452F'][k % 4])} 0%, rgba(0,0,0,0.55) 130%)`, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: px(10), color: '#fff' });
    s.appendChild(emo(f.e, Wp * 0.34));
    s.appendChild(el('div', { fontSize: px(Wp * 0.075), fontWeight: 800, textAlign: 'center' }, null, esc(f.cap || '')));
    const side = el('div', { position: 'absolute', right: px(Wp * 0.04), top: '52%', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: px(10), fontSize: px(Wp * 0.035), fontWeight: 700 });
    [['❤️', f.likes || ((51 + k * 17) + 'K')], ['💬', (6 + k * 3) + 'K'], ['🔁', (4 + k) + 'K']].forEach(([i, v]) => { const c = el('div', { display: 'flex', flexDirection: 'column', alignItems: 'center' }); c.appendChild(emo(i, Wp * 0.07)); c.appendChild(el('div', null, null, v)); side.appendChild(c); });
    s.appendChild(side);
    scr.appendChild(s);
    return s;
  });
  scr.appendChild(el('div', { position: 'absolute', top: px(20), left: 0, right: 0, textAlign: 'center', fontSize: px(Wp * 0.045), fontWeight: 800, color: '#fff' }, null, esc(it.header || 'Dành cho bạn')));
  scr.appendChild(el('div', { position: 'absolute', top: px(8), left: '50%', width: px(Wp * 0.26), height: px(10), marginLeft: px(-Wp * 0.13), borderRadius: px(6), background: '#000' }));
  const hand = it.hand === false ? null : emo('👆', Wp * 0.24, { position: 'absolute', left: '50%', top: '58%', marginLeft: px(-Wp * 0.1), opacity: 0 });
  if (hand) frame.appendChild(hand);
  const t0 = timeOf(it.run || {}, ctx.sc, ctx.a + 0.6);
  const every = it.every || Math.max(0.7, (ctx.sc._e - t0 - 0.3) / Math.max(1, feed.length - 1));
  const sw = feed.slice(1).map((_, k) => t0 + every * k + every * 0.6);
  sw.forEach(s => ctx.ev(s, 'swipe'));
  const tilt = it.tilt != null ? it.tilt : -3;
  return {
    el: frame, sfx: 'pop', upd: t => {
      let pos = 0;
      sw.forEach(s => { pos += E.io(prog(t, s, 0.35)); });
      feed.forEach((s, k) => { s.style.transform = `translateY(${(k - pos) * 100}%)`; });
      frame.style.transform = `rotate(${tilt + Math.sin(t * 1.3) * 1.2}deg)`;
      if (hand) {
        let o = 0, dy = 0;
        sw.forEach(s => { const p = prog(t, s - 0.35, 0.8); if (p > 0 && p < 1) { o = Math.sin(p * Math.PI); dy = p < 0.45 ? 0 : -(p - 0.45) * 2 * Wp * 0.45; } });
        hand.style.opacity = o; hand.style.transform = `translateY(${dy * U}px)`;
      }
    }
  };
};

C.chapter = (it, ctx) => {
  const th = ctx.th;
  const box = el('div', { display: 'flex', flexDirection: 'column', alignItems: 'center', gap: px(26) });
  const num = el('div', { fontSize: px(it.fs || 320), fontWeight: 900, letterSpacing: '-0.05em', lineHeight: 0.9, color: col(it.color, th.num) }, null, esc(it.num || '01'));
  box.appendChild(num);
  const pill = el('div', { fontSize: px(26), fontWeight: 900, padding: `${px(8)} ${px(20)}`, borderRadius: px(30), background: col(it.color, th.num), color: th.bg, letterSpacing: '0.06em' }, 'pill', esc(it.label || ('PHẦN ' + (it.num || '01'))));
  box.appendChild(pill);
  const tctx = Object.assign({}, ctx, { a: ctx.a + 0.3 });
  const title = makeText({ text: it.title || '', size: it.size || 76, at: tctx.a - ctx.sc._s }, tctx);
  box.appendChild(title.el);
  CHAP.push({ t: ctx.sc._s, label: it.chap || `${it.num || ''} · ${plain(it.title)}` });
  ctx.ev(ctx.a, 'boom');
  return {
    el: box, noEntry: true, noSfx: true, upd: t => {
      const p = prog(t, ctx.a, 0.55), e = E.back(p);
      num.style.opacity = clamp(p * 3); num.style.transform = `translateY(${(1 - E.out(p)) * 120 * U}px) scale(${0.8 + 0.2 * e})`;
      const q = prog(t, ctx.a + 0.25, 0.35);
      pill.style.opacity = q; pill.style.transform = `scale(${q <= 0 ? 0.5 : 0.5 + 0.5 * E.back(q)})`;
      title.upd(t);
    }
  };
};

C.quote = (it, ctx) => {
  const box = el('div', { display: 'flex', flexDirection: 'column', alignItems: 'flex-start', width: px(it.w || 920), gap: px(10) });
  const mark = el('div', { fontSize: px(260), fontWeight: 900, lineHeight: 0.8, height: px(150), color: col(it.mark, ctx.th.light ? '#D9503F' : ctx.th.acc) }, null, '“');
  box.appendChild(mark);
  const tx = makeText({ text: it.text, size: it.size || 'l', align: 'left', w: it.w || 920, say: it.say }, ctx);
  tx.el.style.textWrap = 'pretty';
  box.appendChild(tx.el);
  let by = null;
  if (it.by) { by = el('div', { fontSize: px(32), fontWeight: 700, color: ctx.th.mut, marginTop: px(16) }, null, '— ' + esc(it.by)); box.appendChild(by); }
  const tb = it.by ? timeOf(it.bySay ? { say: it.bySay } : {}, ctx.sc, (tx.times[tx.times.length - 1] || ctx.a) + 0.5) : 0;
  return {
    el: box, noEntry: true, upd: t => {
      const p = prog(t, ctx.a - 0.1, 0.4);
      mark.style.opacity = p; mark.style.transform = `scale(${p <= 0 ? 0.4 : 0.4 + 0.6 * E.back(p)})`;
      tx.upd(t);
      if (by) by.style.opacity = prog(t, tb, 0.4);
    }
  };
};

C.polaroid = (it, ctx) => {
  const w = it.w || 440;
  const card = el('div', { width: px(w), background: '#FFFFFF', padding: `${px(22)} ${px(22)} ${px(26)}`, boxShadow: `0 ${px(18)} ${px(40)} rgba(0,0,0,0.22)`, position: 'relative', transform: `rotate(${it.rot != null ? it.rot : -4}deg)` });
  const pic = el('div', { height: px(w - 44), background: it.bg ? col(it.bg) : 'linear-gradient(160deg,#F0A35A,#C8452F)', display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'hidden' });
  if (it.src) pic.appendChild(el('img', { width: '100%', height: '100%', objectFit: 'cover' })).src = BASE + it.src;
  else pic.appendChild(emo(it.e || '🕹️', (w - 44) * 0.5));
  card.appendChild(pic);
  card.appendChild(el('div', { fontSize: px(30), fontWeight: 700, fontStyle: 'italic', color: '#3a3a3a', textAlign: 'center', marginTop: px(16) }, null, esc(it.cap || '')));
  card.appendChild(el('div', { position: 'absolute', top: px(-22), left: '50%', width: px(150), height: px(46), marginLeft: px(-75), background: 'rgba(242,193,78,0.85)', transform: 'rotate(-3deg)' }));
  return { el: card, sfx: 'pop', inKind: 'drop' };
};

C.cycle = (it, ctx) => {
  const S = it.d || 760, R = S * 0.34;
  const box = el('div', { position: 'relative', width: px(S), height: px(S) });
  const svg = svgEl('svg', { width: S * U, height: S * U, viewBox: `0 0 ${S} ${S}` });
  svg.appendChild(svgEl('circle', { cx: S / 2, cy: S / 2, r: R, fill: 'none', stroke: ctx.th.light ? 'rgba(0,0,0,0.25)' : 'rgba(255,255,255,0.35)', 'stroke-width': 4, 'stroke-dasharray': '14 14' }));
  box.appendChild(svg);
  const dot = el('div', { position: 'absolute', width: px(30), height: px(30), borderRadius: '50%', background: col(it.dot, '#2F8F57'), marginLeft: px(-15), marginTop: px(-15) });
  box.appendChild(dot);
  const center = emo(it.center || '🔄', it.csize || 170, { position: 'absolute', left: '50%', top: '50%' });
  box.appendChild(center);
  const nodes = (it.nodes || []).map((n, k, arr) => {
    const ang = -Math.PI / 2 + k * 2 * Math.PI / arr.length;
    const p = el('div', { position: 'absolute', left: px(S / 2 + Math.cos(ang) * R), top: px(S / 2 + Math.sin(ang) * R), fontSize: px(it.fs || 34), fontWeight: 800, padding: `${px(10)} ${px(20)}`, borderRadius: px(16), background: '#FFFDF6', color: INK, boxShadow: `0 ${px(6)} ${px(16)} rgba(0,0,0,0.15)`, whiteSpace: 'nowrap' }, null, esc(n));
    box.appendChild(p);
    return p;
  });
  const per = it.per || 0.75;
  return {
    el: box, sfx: 'pop', upd: t => {
      const lt = t - ctx.a;
      const act = lt < 0.4 ? -1 : Math.floor((lt - 0.4) / per) % Math.max(1, nodes.length);
      nodes.forEach((p, k) => {
        const q = prog(t, ctx.a + 0.15 + k * 0.12, 0.35);
        const on = k === act;
        p.style.opacity = q;
        p.style.background = on ? '#F2C14E' : '#FFFDF6';
        p.style.transform = `translate(-50%,-50%) scale(${(q <= 0 ? 0.5 : 0.5 + 0.5 * E.back(q)) * (on ? 1.08 : 1)})`;
      });
      const a = -Math.PI / 2 + Math.max(0, lt) * 2 * Math.PI / (per * Math.max(1, nodes.length));
      dot.style.left = px(S / 2 + Math.cos(a) * R); dot.style.top = px(S / 2 + Math.sin(a) * R);
      center.style.transform = `translate(-50%,-50%) rotate(${Math.max(0, lt) * (it.spin != null ? it.spin : 60)}deg)`;
    }
  };
};

C.timeline = (it, ctx) => {
  const box = el('div', { position: 'relative', width: px(it.w || 820), display: 'flex', flexDirection: 'column', gap: px(34), paddingLeft: px(70) });
  const line = el('div', { position: 'absolute', left: px(24), top: px(16), width: px(5), background: '#D9503F', transformOrigin: 'top', borderRadius: px(3) });
  box.appendChild(line);
  const steps = (it.steps || []).map((s, k) => {
    const row = el('div', { position: 'relative', display: 'flex', flexDirection: 'column', gap: px(10) });
    row.appendChild(el('div', { position: 'absolute', left: px(-60), top: px(4), width: px(34), height: px(34), borderRadius: '50%', background: '#F2C14E', border: `${px(6)} solid #D9503F` }));
    row.appendChild(el('div', { fontSize: px(32), fontWeight: 800, color: '#D9503F' }, null, esc(s.when || '')));
    row.appendChild(el('div', { fontSize: px(34), fontWeight: 700, background: '#FFFFFF', color: INK, padding: `${px(16)} ${px(22)}`, borderRadius: px(14), boxShadow: `0 ${px(8)} ${px(20)} rgba(0,0,0,0.1)` }, null, esc(s.t || '')));
    box.appendChild(row);
    const t0 = timeOf(s, ctx.sc, ctx.a + 0.8 * k, 'mốc ' + (k + 1));
    ctx.ev(t0, 'tick');
    return { row, t0 };
  });
  return {
    el: box, noSfx: true, upd: t => {
      let lastY = 0;
      steps.forEach(({ row, t0 }) => {
        const p = prog(t, t0, 0.4), e = E.out(p);
        row.style.opacity = e; row.style.transform = `translateX(${(1 - e) * 60 * U}px)`;
        if (p > 0) lastY = row.offsetTop + row.offsetHeight * 0.3 * e;
      });
      line.style.height = Math.max(0, lastY - 16 * U) + 'px';
    }
  };
};

C.chart = (it, ctx) => {
  const Wc = it.w || 820, Hc = it.h || 520;
  const card = el('div', { width: px(Wc), height: px(Hc), background: ctx.th.light ? '#FFFFFF' : '#242424', borderRadius: px(30), position: 'relative', boxShadow: `0 ${px(16)} ${px(36)} rgba(0,0,0,0.2)`, color: ctx.th.light ? INK : '#fff' });
  const pw = Wc - 100, ph = Hc - 150;
  const svg = svgEl('svg', { width: pw * U, height: ph * U, viewBox: `0 0 ${pw} ${ph}`, style: `position:absolute;left:${50 * U}px;top:${50 * U}px` });
  for (let g = 0; g <= 4; g++) svg.appendChild(svgEl('line', { x1: 0, x2: pw, y1: ph * g / 4, y2: ph * g / 4, stroke: ctx.th.light ? 'rgba(0,0,0,0.06)' : 'rgba(255,255,255,0.06)', 'stroke-width': 2 }));
  const pts = it.points || [0.02, 0.05, 0.05, 0.1, 0.1, 0.17, 0.17, 0.26, 0.3, 0.42, 0.55, 0.75, 1];
  const P = pts.map((v, k) => [pw * k / (pts.length - 1), ph - v * ph * 0.95]);
  const d = 'M' + P.map(p => p.join(',')).join(' L');
  const cid = 'cl' + Math.floor(Math.random() * 1e9);
  const clip = svgEl('clipPath', { id: cid }); const cr = svgEl('rect', { x: 0, y: -20, width: 0, height: ph + 40 }); clip.appendChild(cr); svg.appendChild(clip);
  const area = svgEl('path', { d: d + ` L${pw},${ph} L0,${ph} Z`, fill: col(it.color, '#F2C14E'), opacity: 0.22, 'clip-path': `url(#${cid})` });
  const path = svgEl('path', { d, fill: 'none', stroke: col(it.color, '#F2C14E'), 'stroke-width': 7, 'stroke-linejoin': 'round', 'stroke-linecap': 'round' });
  svg.appendChild(area); svg.appendChild(path);
  const head = svgEl('circle', { r: 11, fill: col(it.color, '#F2C14E') });
  svg.appendChild(head);
  card.appendChild(svg);
  const lab = el('div', { position: 'absolute', left: px(50), right: px(50), bottom: px(34), display: 'flex', justifyContent: 'space-between', fontSize: px(24), fontWeight: 700, opacity: 0.6 });
  lab.appendChild(el('span', null, null, esc(it.xl || ''))); lab.appendChild(el('span', null, null, esc(it.xr || '')));
  card.appendChild(lab);
  let L = null;
  const ts = timeOf(it.run || {}, ctx.sc, ctx.a + 0.35);
  const dur = it.dur || Math.max(0.8, Math.min(2.5, ctx.sc._e - ts - 0.2));
  return {
    el: card, upd: t => {
      if (L == null) { L = path.getTotalLength(); path.setAttribute('stroke-dasharray', L); }
      const p = E.io(prog(t, ts, dur));
      path.setAttribute('stroke-dashoffset', L * (1 - p));
      const pt = path.getPointAtLength(L * p);
      head.setAttribute('cx', pt.x); head.setAttribute('cy', pt.y);
      cr.setAttribute('width', pt.x);
    }
  };
};

C.notify = (it, ctx) => {
  const box = el('div', { display: 'flex', flexDirection: 'column', gap: px(18), width: px(it.w || 800) });
  const rows = (it.items || []).map((n, k) => {
    const r = el('div', { display: 'flex', alignItems: 'center', gap: px(22), background: '#FFF9EE', color: INK, borderRadius: px(22), padding: `${px(20)} ${px(24)}`, boxShadow: `0 ${px(10)} ${px(24)} rgba(0,0,0,0.14)` });
    const ic = el('div', { width: px(70), height: px(70), borderRadius: '50%', background: '#F3EBDA', display: 'flex', alignItems: 'center', justifyContent: 'center', flex: 'none' });
    ic.appendChild(emo(n.e || '🔔', 38));
    r.appendChild(ic);
    const tx = el('div', { display: 'flex', flexDirection: 'column', gap: px(4) });
    tx.appendChild(el('div', { fontSize: px(32), fontWeight: 800 }, null, esc(n.t || '')));
    if (n.sub) tx.appendChild(el('div', { fontSize: px(22), fontWeight: 600, opacity: 0.55 }, null, esc(n.sub)));
    r.appendChild(tx);
    box.appendChild(r);
    const t0 = timeOf(n, ctx.sc, ctx.a + 0.35 * k, 'thông báo ' + (k + 1));
    ctx.ev(t0, 'ding');
    return { r, t0 };
  });
  return {
    el: box, noSfx: true, upd: t => rows.forEach(({ r, t0 }) => {
      const p = prog(t, t0, 0.45);
      r.style.opacity = clamp(p * 2); r.style.transform = `translateY(${-(1 - E.back(p)) * 80 * U}px) scale(${0.92 + 0.08 * E.out(p)})`;
    })
  };
};

C.chat = (it, ctx) => {
  const card = el('div', { width: px(it.w || 780), minHeight: px(it.h || 560), background: '#FFFFFF', borderRadius: px(26), overflow: 'hidden', boxShadow: `0 ${px(16)} ${px(36)} rgba(0,0,0,0.16)`, display: 'flex', flexDirection: 'column' });
  const head = el('div', { background: '#D9503F', color: '#fff', padding: `${px(20)} ${px(26)}`, display: 'flex', alignItems: 'center', gap: px(16), fontSize: px(it.fs ? it.fs * 0.8 : 30), fontWeight: 800 });
  head.appendChild(el('div', { width: px(30), height: px(30), borderRadius: '50%', background: '#F2C14E' }));
  head.appendChild(el('div', null, null, esc(it.title || 'Tin nhắn')));
  card.appendChild(head);
  const body = el('div', { padding: px(26), display: 'flex', flexDirection: 'column', gap: px(18) });
  card.appendChild(body);
  const msgs = (it.msgs || []).map((m, k) => {
    const b = el('div', { alignSelf: m.me ? 'flex-end' : 'flex-start', maxWidth: '78%', fontSize: px(it.fs || 30), fontWeight: 700, padding: `${px(14)} ${px(22)}`, borderRadius: px(20), background: m.me ? '#2F6B45' : '#EFEBE3', color: m.me ? '#fff' : INK }, null, esc(m.t));
    body.appendChild(b);
    const t0 = timeOf(m, ctx.sc, ctx.a + 0.6 * k, 'tin ' + (k + 1));
    ctx.ev(t0, 'pop');
    return { b, t0, me: m.me };
  });
  return {
    el: card, upd: t => msgs.forEach(({ b, t0, me }) => {
      const p = prog(t, t0, 0.35);
      b.style.opacity = clamp(p * 2); b.style.transform = `scale(${p <= 0 ? 0.5 : 0.5 + 0.5 * E.back(p)})`; b.style.transformOrigin = me ? 'right bottom' : 'left bottom';
    })
  };
};

C.neq = (it, ctx) => {
  const box = el('div', { display: 'flex', flexDirection: 'column', gap: px(28), alignItems: 'center' });
  const rows = (it.items || []).map((r, k) => {
    const c = el('div', { width: px(it.w || 740), background: '#FFF8EA', color: INK, borderRadius: px(24), padding: `${px(26)} ${px(30)}`, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: px(8), boxShadow: `0 ${px(12)} ${px(28)} rgba(0,0,0,0.18)` });
    c.appendChild(el('div', { fontSize: px(58), fontWeight: 800 }, null, esc(r.a)));
    const bw = el('div', { fontSize: px(38), fontWeight: 700, color: '#D9503F', display: 'flex', gap: px(12), alignItems: 'center' });
    bw.appendChild(el('span', null, null, '≠'));
    const word = el('span', { position: 'relative', opacity: 0.8 }, null, esc(r.b));
    const strike = el('span', { position: 'absolute', left: '-4%', width: '108%', top: '52%', height: px(5), background: '#D9503F', transformOrigin: 'left' });
    word.appendChild(strike); bw.appendChild(word); c.appendChild(bw);
    box.appendChild(c);
    const t0 = timeOf(r, ctx.sc, ctx.a + 1.2 * k, 'thẻ ' + (k + 1));
    const ts = timeOf(r.strike || {}, ctx.sc, t0 + 0.6);
    ctx.ev(t0, 'pop'); ctx.ev(ts, 'tick');
    return { c, strike, t0, ts };
  });
  return {
    el: box, noSfx: true, upd: t => rows.forEach(r => {
      const p = prog(t, r.t0, 0.45);
      r.c.style.opacity = clamp(p * 2); r.c.style.transform = `translateY(${(1 - E.out(p)) * 70 * U}px) scale(${0.9 + 0.1 * E.back(p)})`;
      r.strike.style.transform = `scaleX(${E.out(prog(t, r.ts, 0.3))})`;
    })
  };
};

C.radial = (it, ctx) => {
  const S = it.d || 760, R = S * 0.38;
  const box = el('div', { position: 'relative', width: px(S), height: px(S) });
  box.appendChild(el('div', { position: 'absolute', left: '50%', top: '50%', width: px(R * 2), height: px(R * 2), marginLeft: px(-R), marginTop: px(-R), borderRadius: '50%', border: `${px(3)} solid ${ctx.th.light ? 'rgba(0,0,0,0.1)' : 'rgba(255,255,255,0.1)'}` }));
  const btn = el('div', { position: 'absolute', left: '50%', top: '50%', width: px(230), height: px(230), marginLeft: px(-115), marginTop: px(-115), borderRadius: '50%', background: '#F2C14E', border: `${px(8)} solid ${ctx.th.light ? '#1E2A22' : '#2A2A2A'}`, boxShadow: `0 0 0 ${px(10)} rgba(242,193,78,0.25)`, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: px(48), fontWeight: 900, color: INK }, null, esc(it.center || 'CHẠM'));
  box.appendChild(btn);
  const ts = timeOf(it.burst || {}, ctx.sc, ctx.a + 0.5);
  const items = (it.around || ['🎮', '🎬', '✈️', '🍔', '💬', '🛒']).map((e, k, arr) => {
    const a = -Math.PI / 2 + k * 2 * Math.PI / arr.length;
    const s = emo(e, it.esize || 84, { position: 'absolute', left: '50%', top: '50%' });
    box.appendChild(s);
    return { s, a, t0: ts + k * 0.1 };
  });
  ctx.ev(ts, 'pop');
  return {
    el: box, sfx: 'pop', upd: t => {
      const press = prog(t, ts - 0.15, 0.3);
      btn.style.transform = `scale(${1 - Math.sin(press * Math.PI) * 0.1 + Math.sin(t * 4) * 0.015})`;
      items.forEach(({ s, a, t0 }) => {
        const p = prog(t, t0, 0.5), e = E.back(p);
        s.style.opacity = clamp(p * 3);
        s.style.transform = `translate(-50%,-50%) translate(${Math.cos(a) * R * e * U}px, ${Math.sin(a) * R * e * U}px) scale(${0.4 + 0.6 * E.out(p)})`;
      });
    }
  };
};

C.map = (it, ctx) => {
  const Wm = it.w || 800, Hm = it.h || 900;
  const box = el('div', { position: 'relative', width: px(Wm), height: px(Hm) });
  const svg = svgEl('svg', { width: Wm * U, height: Hm * U, viewBox: `0 0 ${Wm} ${Hm}` });
  const d = it.path || `M${Wm * 0.25},${Hm * 0.08} C${Wm * 0.1},${Hm * 0.35} ${Wm * 0.95},${Hm * 0.35} ${Wm * 0.8},${Hm * 0.6} S${Wm * 0.15},${Hm * 0.8} ${Wm * 0.35},${Hm * 0.95}`;
  const path = svgEl('path', { d, fill: 'none', stroke: col(it.line, ctx.th.light ? 'rgba(30,42,34,0.55)' : 'rgba(255,255,255,0.8)'), 'stroke-width': 6, 'stroke-dasharray': '16 14', 'stroke-linecap': 'round' });
  const mid = 'mk' + Math.floor(Math.random() * 1e9);
  const mk = svgEl('mask', { id: mid, maskUnits: 'userSpaceOnUse', x: -50, y: -50, width: Wm + 100, height: Hm + 100 });
  const mask = svgEl('path', { d, fill: 'none', stroke: '#fff', 'stroke-width': 16 });
  mk.appendChild(mask); svg.appendChild(mk);
  path.setAttribute('mask', `url(#${mid})`);
  svg.appendChild(path);
  box.appendChild(svg);
  const pin = el('div', { position: 'absolute', display: 'flex', flexDirection: 'column', alignItems: 'center', transform: 'translate(-50%,-100%)' });
  pin.appendChild(el('div', { background: '#fff', color: INK, fontSize: px(32), fontWeight: 800, padding: `${px(8)} ${px(18)}`, borderRadius: px(14), marginBottom: px(4) }, null, esc(it.from || 'Hà Nội')));
  pin.appendChild(emo('📍', 64));
  box.appendChild(pin);
  const car = emo(it.car || '🚗', 80, { position: 'absolute' });
  box.appendChild(car);
  const tags = (it.tags || []).map((g, k) => {
    const e = el('div', { position: 'absolute', background: col(g.bg, '#F2C14E'), color: INK, fontSize: px(30), fontWeight: 800, padding: `${px(10)} ${px(20)}`, borderRadius: px(30), whiteSpace: 'nowrap' }, null, esc(g.t));
    box.appendChild(e);
    const t0 = timeOf(g, ctx.sc, ctx.a + 0.8 + k * 0.9, 'nhãn ' + (k + 1));
    ctx.ev(t0, 'pop');
    return { e, t0, pos: g.pos != null ? g.pos : (k + 1) / ((it.tags || []).length + 1) };
  });
  let L = null;
  const ts = timeOf(it.run || {}, ctx.sc, ctx.a + 0.3), dur = it.dur || Math.max(1, ctx.sc._e - ts - 0.2);
  return {
    el: box, upd: t => {
      if (L == null) {
        L = path.getTotalLength();
        mask.setAttribute('stroke-dasharray', L);
        const p0 = path.getPointAtLength(0);
        pin.style.left = px(p0.x); pin.style.top = px(p0.y);
        tags.forEach(g => { const q = path.getPointAtLength(L * g.pos); g.e.style.left = px(q.x + 40); g.e.style.top = px(q.y - 30); });
      }
      const p = E.io(prog(t, ts, dur));
      mask.setAttribute('stroke-dashoffset', L * (1 - p));
      const q = path.getPointAtLength(L * p), q2 = path.getPointAtLength(Math.min(L, L * p + 2));
      const ang = Math.atan2(q2.y - q.y, q2.x - q.x) * 180 / Math.PI;
      car.style.left = px(q.x); car.style.top = px(q.y);
      car.style.transform = `translate(-50%,-50%) ${Math.abs(ang) > 90 ? 'scaleX(1)' : 'scaleX(-1)'}`;
      tags.forEach(g => { const r = prog(t, g.t0, 0.35); g.e.style.opacity = r; g.e.style.transform = `scale(${r <= 0 ? 0.5 : 0.5 + 0.5 * E.back(r)})`; });
    }
  };
};

C.confetti = (it, ctx) => {
  const box = el('div', { position: 'absolute', inset: 0, pointerEvents: 'none' });
  const R = rng(ctx.sc._k * 31 + 7);
  const pal = (it.colors || ['#F2C14E', '#E8913A', '#D9503F', '#9BD35A', '#F6E27A']).map(c => col(c));
  const ts = timeOf(it, ctx.sc, ctx.a);
  const cx = W / 2, cy = H * (it.y || 0.5);
  const bits = Array.from({ length: it.n || 46 }, () => {
    const s = (18 + R() * 26) * U;
    const b = el('div', { position: 'absolute', left: 0, top: 0, width: s + 'px', height: s + 'px', background: pal[Math.floor(R() * pal.length)], borderRadius: px(4) });
    box.appendChild(b);
    const a = R() * Math.PI * 2, v = (380 + R() * 620) * U;
    return { b, vx: Math.cos(a) * v, vy: Math.sin(a) * v - 250 * U, rot: (R() - 0.5) * 720, s };
  });
  ctx.ev(ts, 'burst');
  return {
    el: box, abs: true, noEntry: true, noSfx: true, upd: t => {
      const lt = t - ts;
      bits.forEach(b => {
        if (lt < 0) { b.b.style.opacity = 0; return; }
        const k = 1 - Math.exp(-lt * 2.2);
        const x = cx + b.vx * k / 2.2, y = cy + b.vy * k / 2.2 + 260 * U * lt * lt;
        b.b.style.opacity = clamp(1.6 - lt * 0.5);
        b.b.style.transform = `translate(${x - b.s / 2}px, ${y - b.s / 2}px) rotate(${b.rot * k}deg)`;
      });
    }
  };
};

C.grid = (it, ctx) => {
  const rows = it.rows || 6, cols = it.cols || 6, s = it.cell || 92, g = 10;
  const box = el('div', { position: 'relative', width: px(cols * s + (cols - 1) * g), height: px(rows * s + (rows - 1) * g) });
  const tiles = [];
  const R = rng(ctx.sc._k * 13 + 3);
  const ts = timeOf(it.break || { at: 99999 }, ctx.sc, 1e9);
  for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) {
    const f = (r / (rows - 1 || 1)) * 0.6 + (c / (cols - 1 || 1)) * 0.4;
    const hue = 22 + f * 70;
    const e = el('div', { position: 'absolute', left: px(c * (s + g)), top: px(r * (s + g)), width: px(s), height: px(s), borderRadius: px(10), background: `hsl(${hue},78%,${58 + f * 6}%)` });
    box.appendChild(e);
    const a = R() * Math.PI * 2;
    tiles.push({ e, d: (r + c) * 0.035, vx: Math.cos(a) * (300 + R() * 500), vy: Math.sin(a) * (300 + R() * 500), rot: (R() - 0.5) * 540 });
  }
  let lab = null;
  if (it.label) { lab = el('div', { position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: px(it.fs || 70), fontWeight: 900, color: '#fff', textShadow: `0 ${px(4)} ${px(14)} rgba(0,0,0,0.35)` }, null, esc(it.label)); box.appendChild(lab); }
  if (it.break) ctx.ev(ts, 'burst');
  return {
    el: box, sfx: 'pop', upd: t => {
      const lb = t - ts;
      tiles.forEach(tl => {
        const p = prog(t, ctx.a + tl.d, 0.35);
        if (lb > 0) {
          const k = 1 - Math.exp(-lb * 2.5);
          tl.e.style.opacity = clamp(1.5 - lb * 0.8);
          tl.e.style.transform = `translate(${tl.vx * k / 2.5 * U}px, ${(tl.vy * k / 2.5 + 200 * lb * lb) * U}px) rotate(${tl.rot * k}deg) scale(${1 - 0.4 * k})`;
        } else { tl.e.style.opacity = clamp(p * 2); tl.e.style.transform = `scale(${p <= 0 ? 0.3 : 0.3 + 0.7 * E.back(p)})`; }
      });
      if (lab) lab.style.opacity = lb > 0 ? clamp(1 - lb * 3) : prog(t, ctx.a + 0.4, 0.3);
    }
  };
};

C.notebook = (it, ctx) => {
  const Wn = it.w || 640, Hn = it.h || 600, n = it.lines || 6;
  const card = el('div', { width: px(Wn), height: px(Hn), background: '#FFFDF6', borderRadius: px(10), position: 'relative', boxShadow: `0 ${px(16)} ${px(34)} rgba(0,0,0,0.22)`, backgroundImage: `repeating-linear-gradient(180deg, transparent 0 ${px(58)}, #D8E3F0 ${px(58)} ${px(61)})`, backgroundPosition: `0 ${px(40)}` });
  card.appendChild(el('div', { position: 'absolute', left: px(80), top: 0, bottom: 0, width: px(3), background: '#E8A0A0' }));
  const svg = svgEl('svg', { width: Wn * U, height: Hn * U, viewBox: `0 0 ${Wn} ${Hn}`, style: 'position:absolute;left:0;top:0' });
  card.appendChild(svg);
  const R = rng(ctx.sc._k * 7 + 1);
  const paths = Array.from({ length: n }, (_, k) => {
    const y = 40 + 61 * (k + 1) - 18, x0 = 110, x1 = Wn - 60 - (k === n - 1 ? 200 : R() * 80);
    let d = `M${x0},${y}`;
    for (let x = x0; x < x1; x += 18) d += ` q9,${-14 + R() * 4} 18,0`;
    const p = svgEl('path', { d, fill: 'none', stroke: '#2B3F7A', 'stroke-width': 4, 'stroke-linecap': 'round' });
    svg.appendChild(p);
    return p;
  });
  const pen = emo('✏️', 80, { position: 'absolute', left: 0, top: 0 });
  card.appendChild(pen);
  const ts = timeOf(it.run || {}, ctx.sc, ctx.a + 0.3), dur = it.dur || Math.max(1, ctx.sc._e - ts - 0.2);
  let Ls = null;
  return {
    el: card, upd: t => {
      if (!Ls) { Ls = paths.map(p => p.getTotalLength()); paths.forEach((p, k) => p.setAttribute('stroke-dasharray', Ls[k])); }
      const p = prog(t, ts, dur) * n;
      let hx = 110, hy = 80;
      paths.forEach((pa, k) => {
        const f = clamp(p - k);
        pa.setAttribute('stroke-dashoffset', Ls[k] * (1 - f));
        if (f > 0) { const q = pa.getPointAtLength(Ls[k] * f); hx = q.x; hy = q.y; }
      });
      pen.style.transform = `translate(${(hx - 6) * U}px, ${(hy - 76) * U}px) rotate(${Math.sin(t * 20) * 4}deg)`;
    }
  };
};

C.plant = (it, ctx) => {
  const Wp = it.w || 720;
  const box = el('div', { position: 'relative', width: px(Wp), height: px(it.h || 560), display: 'flex', alignItems: 'flex-end', justifyContent: 'center' });
  const soil = el('div', { position: 'absolute', left: 0, right: 0, bottom: 0, height: px(it.soil || 250), background: '#6B4A2E', borderRadius: px(26), overflow: 'hidden' });
  box.appendChild(soil);
  const svg = svgEl('svg', { width: Wp * U, height: (it.soil || 250) * U, viewBox: `0 0 ${Wp} ${it.soil || 250}`, style: 'position:absolute;left:0;top:0' });
  soil.appendChild(svg);
  const cx = Wp / 2;
  const roots = it.roots === false ? [] : ['M0,0 C-10,60 -70,90 -150,120', 'M0,0 C10,70 60,110 140,140', 'M0,0 C-4,80 4,150 -10,210', 'M-60,70 C-90,110 -120,150 -170,170', 'M50,80 C80,120 110,150 170,160'].map(d => {
    const p = svgEl('path', { d, transform: `translate(${cx},10)`, fill: 'none', stroke: '#F3E9D8', 'stroke-width': 5, 'stroke-linecap': 'round' });
    svg.appendChild(p); return p;
  });
  const pl = emo(it.e || '🌱', it.size || 190, { position: 'absolute', left: '50%', bottom: px((it.soil || 250) - 18), transformOrigin: 'bottom center' });
  box.appendChild(pl);
  let tool = null;
  if (it.tool) { tool = emo(it.tool, 120, { position: 'absolute', right: px(40), bottom: px((it.soil || 250) + 40) }); box.appendChild(tool); }
  const swaps = (it.swap || []).map((s, k) => ({ e: s.e, t: timeOf(s, ctx.sc, ctx.a + 1 + k) }));
  const tr = timeOf(it.rootsAt || {}, ctx.sc, ctx.a + 0.4);
  let Ls = null, cur = it.e || '🌱';
  return {
    el: box, upd: t => {
      if (!Ls) { Ls = roots.map(p => p.getTotalLength()); roots.forEach((p, k) => p.setAttribute('stroke-dasharray', Ls[k])); }
      roots.forEach((p, k) => p.setAttribute('stroke-dashoffset', Ls[k] * (1 - E.out(prog(t, tr + k * 0.12, 0.9)))));
      let want = it.e || '🌱', st = -9;
      swaps.forEach(s => { if (t >= s.t) { want = s.e; st = s.t; } });
      if (want !== cur) { pl.textContent = want; cur = want; }
      const g = prog(t, ctx.a + 0.15, 0.6), q = st > 0 ? prog(t, st, 0.5) : 1;
      pl.style.transform = `translateX(-50%) scale(${(g <= 0 ? 0 : E.back(g)) * (0.8 + 0.2 * E.back(q))}) rotate(${Math.sin(t * 1.6) * 2}deg)`;
      if (tool) tool.style.transform = `translateY(${Math.sin(t * 3) * 12 * U}px) rotate(${-10 + Math.sin(t * 3) * 6}deg)`;
    }
  };
};

C.pill = (it, ctx) => {
  const bg = col(it.bg, '#2F8F57');
  const p = el('div', { fontSize: px(it.fs || 30), fontWeight: 800, padding: `${px(10)} ${px(24)}`, borderRadius: px(40), background: bg, color: col(it.color, (it.bg === 'yellow' || it.bg === 'cream' || it.bg === 'white') ? INK : '#fff'), letterSpacing: it.caps ? '0.06em' : '0', textTransform: it.caps ? 'uppercase' : 'none', transform: `rotate(${it.rot || 0}deg)` }, 'pill', esc(it.t || ''));
  return { el: p, sfx: 'pop', inKind: 'pop' };
};

C.screen = (it, ctx) => {
  const Ws = it.w || 820, Hs = it.h || 520;
  const fr = el('div', { width: px(Ws), height: px(Hs), background: '#1A1A1A', borderRadius: px(30), padding: px(16), boxShadow: `0 ${px(18)} ${px(40)} rgba(0,0,0,0.3)`, position: 'relative' });
  const sc = el('div', { position: 'absolute', inset: px(16), borderRadius: px(18), overflow: 'hidden', background: it.bg || 'linear-gradient(180deg,#2E3A6B 0%,#B8577A 55%,#F2A65A 100%)' });
  fr.appendChild(sc);
  const inner = el('div', { position: 'absolute', inset: 0 });
  sc.appendChild(inner);
  const pos = [[0.33, 0.55], [0.66, 0.68], [0.5, 0.4]];
  const actors = (it.e || ['🦸', '🏙️']).map((e, k) => { const a = emo(e, (it.esize || 150) * (k ? 0.8 : 1), { position: 'absolute', left: (pos[k % 3][0] * 100) + '%', top: (pos[k % 3][1] * 100) + '%' }); inner.appendChild(a); return a; });
  if (it.blur) inner.style.filter = `blur(${(it.blur === true ? 6 : it.blur) * U}px)`;
  if (it.badge) fr.appendChild(el('div', { position: 'absolute', right: px(36), top: px(32), background: col(it.badgeBg, it.badge === '4K' ? '#F2C14E' : '#2A2A2A'), color: it.badge === '4K' ? INK : '#fff', fontSize: px(30), fontWeight: 900, padding: `${px(6)} ${px(16)}`, borderRadius: px(10) }, null, esc(it.badge)));
  const R = rng(ctx.sc._k * 5 + 11);
  const stamps = (it.stamps || []).map((s, k) => {
    const e = el('div', { position: 'absolute', left: (15 + R() * 50) + '%', top: (15 + R() * 55) + '%', border: `${px(5)} solid #D9503F`, color: '#D9503F', background: 'rgba(255,240,235,0.85)', fontSize: px(42), fontWeight: 900, padding: `${px(4)} ${px(16)}`, borderRadius: px(8), letterSpacing: '0.04em' }, null, esc(s.t || 'SPOILER'));
    sc.appendChild(e);
    const t0 = timeOf(s, ctx.sc, ctx.a + 0.5 + k * 0.35, 'dấu ' + (k + 1));
    ctx.ev(t0, 'thud');
    return { e, t0, rot: (R() - 0.5) * 30 };
  });
  return {
    el: fr, sfx: 'pop', upd: t => {
      actors.forEach((a, k) => { a.style.transform = `translate(-50%,-50%) translate(${Math.sin(t * 1.2 + k) * 14 * U}px, ${Math.cos(t * 1.5 + k) * 10 * U}px)`; });
      stamps.forEach(s => { const p = prog(t, s.t0, 0.3); s.e.style.opacity = p > 0 ? 1 : 0; s.e.style.transform = `rotate(${s.rot}deg) scale(${p <= 0 ? 2 : 2 - E.out(p)})`; });
    }
  };
};

C.ghost = (it, ctx) => {
  const g = el('div', { position: 'absolute', left: 0, right: 0, top: (it.y != null ? it.y : 0.12) * 100 + '%', textAlign: 'center', fontSize: px(it.size || 220), fontWeight: 900, color: col(it.color, ctx.th.light ? 'rgba(0,0,0,0.08)' : 'rgba(255,255,255,0.07)'), letterSpacing: '-0.03em', fontVariantNumeric: 'tabular-nums' }, null, esc(it.t || ''));
  return { el: g, abs: true, noSfx: true, inKind: 'fade' };
};

C.image = (it, ctx) => {
  const img = el('img', { width: px(it.w || 800), height: it.h ? px(it.h) : 'auto', borderRadius: px(it.radius != null ? it.radius : 24), objectFit: it.fit || 'cover', boxShadow: it.shadow === false ? 'none' : `0 ${px(16)} ${px(36)} rgba(0,0,0,0.22)` });
  img.src = BASE + it.src;
  return { el: img, sfx: 'pop', inKind: 'up' };
};

C.spacer = it => ({ el: el('div', { height: px(it.h || 40), width: '1px' }), noSfx: true, noEntry: true });

C.row = (it, ctx) => {
  const box = el('div', { display: 'flex', alignItems: it.align || 'flex-end', justifyContent: 'center', gap: px(it.gap || 40), position: 'relative', paddingBottom: it.shelf ? px(24) : 0 });
  if (it.shelf) box.appendChild(el('div', { position: 'absolute', left: px(-40), right: px(-40), bottom: 0, height: px(12), borderRadius: px(6), background: ctx.th.light ? 'rgba(0,0,0,0.18)' : 'rgba(255,255,255,0.25)' }));
  const kids = (it.items || []).map((c, k) => buildItem(c, ctx.sc, ctx.th, k, ctx.defSize));
  kids.forEach(k => box.appendChild(k.wrap));
  return { el: box, noEntry: true, noSfx: true, upd: t => kids.forEach(k => k.upd(t)) };
};

// ───────────── khung chung cho mỗi mục ─────────────
const DEF_IN = { text: 'none', emoji: 'pop', list: 'none', timer: 'pop', usage: 'up', battery: 'pop', phone: 'up', polaroid: 'drop', cycle: 'pop', timeline: 'none', chart: 'up', notify: 'none', chat: 'up', neq: 'none', radial: 'pop', map: 'fade', grid: 'none', notebook: 'up', plant: 'up', pill: 'pop', screen: 'up', image: 'up', quote: 'none', chapter: 'none' };
const DEF_IDLE = { emoji: 'bob', polaroid: 'sway' };

function entry(kind, p) {
  const e = E.out(p), b = E.back(p);
  switch (kind) {
    case 'pop': return [clamp(p * 3), `scale(${0.45 + 0.55 * b})`];
    case 'up': return [e, `translateY(${(1 - e) * 90 * U}px)`];
    case 'down': case 'drop': return [clamp(p * 2), `translateY(${-(1 - b) * 160 * U}px) rotate(${(1 - e) * -8}deg)`];
    case 'left': return [e, `translateX(${-(1 - e) * 200 * U}px)`];
    case 'right': return [e, `translateX(${(1 - e) * 200 * U}px)`];
    case 'tilt': return [e, `translate(${(1 - e) * 260 * U}px, ${(1 - e) * 60 * U}px) rotate(${(1 - e) * 14}deg)`];
    case 'zoom': return [e, `scale(${1.35 - 0.35 * e})`];
    case 'fade': return [e, ''];
    default: return [1, ''];
  }
}
function idle(kind, t, ph) {
  switch (kind) {
    case 'bob': return `translateY(${Math.sin(t * 2.2 + ph) * 8 * U}px)`;
    case 'float': return `translateY(${Math.sin(t * 1.4 + ph) * 16 * U}px) rotate(${Math.sin(t * 1.1 + ph) * 3}deg)`;
    case 'sway': return `rotate(${Math.sin(t * 1.5 + ph) * 2.5}deg)`;
    case 'shake': return `translateX(${Math.sin(t * 38) * 5 * U}px) rotate(${Math.sin(t * 31) * 3}deg)`;
    case 'pulse': return `scale(${1 + Math.sin(t * 5 + ph) * 0.045})`;
    case 'spin': return `rotate(${t * 90}deg)`;
    case 'wobble': return `rotate(${Math.sin(t * 6 + ph) * 7}deg)`;
    default: return '';
  }
}

function buildItem(it, sc, th, k, defSize) {
  const type = it.type || (it.text != null ? 'text' : it.e ? 'emoji' : null);
  if (!C[type]) { WARN.push(`Màn ${sc._k + 1}: thành phần không có "${type}".`); return { wrap: el('div'), upd: () => { }, abs: false }; }
  const a0 = type === 'text' || type === 'quote' ? sc._s + 0.05 : sc._s + 0.08 + 0.12 * k;
  const ctx = { sc, th, defSize, a: timeOf(type === 'text' || type === 'quote' ? { at: it.at } : it, sc, a0, type), ev: (t, kind) => EV.push({ t, kind, k: sc._k }) };
  if ((type === 'text' || type === 'quote') && it.at == null) ctx.a = a0;
  const comp = C[type](it, ctx);
  const a = ctx.a;
  const wrap = el('div', null, 'it');
  const inner = el('div', { display: 'flex', flexDirection: 'column', alignItems: 'center' });
  inner.appendChild(comp.el);
  wrap.appendChild(inner);
  if (comp.abs) { wrap.style.position = 'absolute'; wrap.style.inset = 0; inner.style.position = 'absolute'; inner.style.inset = 0; }
  if (it.dx || it.dy) wrap.style.translate = `${(it.dx || 0) * U}px ${(it.dy || 0) * U}px`;
  if (it.mt) wrap.style.marginTop = px(it.mt);
  const inKind = it.in || comp.inKind || DEF_IN[type] || 'up';
  const idleKind = it.idle || DEF_IDLE[type] || '';
  const outT = it.out ? timeOf(it.out, sc, sc._e, 'out') : null;
  const mv = it.move ? { t: timeOf(it.move, sc, a + 0.6, 'move'), to: it.move.to || [0, 0], d: it.move.dur || 0.6, rot: it.move.rot || 0 } : null;
  const sfx = it.sfx !== undefined ? it.sfx : (comp.noSfx ? null : (comp.sfx || (type === 'text' ? null : 'pop')));
  if (sfx) EV.push({ t: a, kind: sfx, k: sc._k });
  const ph = k * 1.7;
  const upd = t => {
    if (comp.noEntry || inKind === 'none') { wrap.style.opacity = 1; }
    else {
      const p = prog(t, a, inKind === 'pop' ? 0.45 : 0.5);
      if (p <= 0) { wrap.style.opacity = 0; return; }
      const [o, tf] = entry(inKind, p);
      wrap.style.opacity = o; wrap.style.transform = tf;
    }
    let tf2 = idle(idleKind, t, ph);
    if (mv) { const q = E.io(prog(t, mv.t, mv.d)); tf2 = `translate(${mv.to[0] * q * U}px, ${mv.to[1] * q * U}px) rotate(${mv.rot * q}deg) ` + tf2; }
    inner.style.transform = tf2;
    if (outT != null) { const q = prog(t, outT, 0.3); if (q > 0) wrap.style.opacity = (parseFloat(wrap.style.opacity) || 1) * (1 - q); }
    if (comp.upd) comp.upd(t);
  };
  return { wrap, upd, abs: comp.abs, type, a };
}

// ───────────── nền ─────────────
function buildDeco(sc, th, k) {
  const d = el('div', { background: th.bg }, 'deco');
  const kinds = [].concat(sc.deco || (sc._chapter ? ['circles', 'stripes'] : sc.bg === 'sunset' ? ['sunset'] : ['circles']));
  const R = rng(k * 97 + 5);
  const movers = [];
  if (kinds.includes('sunset')) {
    d.appendChild(el('div', { position: 'absolute', left: 0, right: 0, top: 0, height: '56%', background: 'linear-gradient(180deg,#6E6BA6 0%,#B7789A 45%,#F0A070 85%,#F7C66E 100%)' }));
    const sun = el('div', { position: 'absolute', left: '50%', top: '56%', width: px(300), height: px(300), marginLeft: px(-150), marginTop: px(-150), borderRadius: '50%', background: '#F9D46B', boxShadow: `0 0 ${px(80)} rgba(249,212,107,0.7)` });
    d.appendChild(sun);
    const sea = el('div', { position: 'absolute', left: 0, right: 0, top: '56%', bottom: 0, background: 'linear-gradient(180deg,#46668F 0%,#2A4262 60%,#1D2F47 100%)', overflow: 'hidden' });
    d.appendChild(sea);
    for (let i = 0; i < 9; i++) {
      const ln = el('div', { position: 'absolute', left: 0, top: (4 + i * 11) + '%', height: px(4 + i * 0.6), width: '140%', background: `repeating-linear-gradient(90deg, rgba(255,255,255,${0.12 + 0.02 * i}) 0 ${px(160 + R() * 200)}, transparent 0 ${px(260 + R() * 200)})` });
      sea.appendChild(ln);
      movers.push(t => { ln.style.transform = `translateX(${-((t * (18 + i * 6)) % 300) * U}px)`; });
    }
  }
  if (kinds.includes('circles')) {
    const n = 3;
    for (let i = 0; i < n; i++) {
      const s = (360 + R() * 420) * U, x = R() * W, y = (i === 0 ? R() * 0.3 : i === 1 ? 0.35 + R() * 0.3 : 0.7 + R() * 0.3) * H;
      const outline = i === 2 && R() < 0.5;
      const c = el('div', { width: s + 'px', height: s + 'px', left: (x - s / 2) + 'px', top: (y - s / 2) + 'px', background: outline ? 'none' : (i % 2 ? th.d2 : th.d1), border: outline ? `${px(2)} solid ${th.light ? 'rgba(0,0,0,0.08)' : 'rgba(255,255,255,0.07)'}` : 'none' }, 'circ');
      d.appendChild(c);
      const ph = R() * 6, amp = (20 + R() * 30) * U;
      movers.push(t => { c.style.transform = `translate(${Math.sin(t * 0.35 + ph) * amp}px, ${Math.cos(t * 0.28 + ph) * amp}px) scale(${1 + Math.sin(t * 0.5 + ph) * 0.04})`; });
    }
  }
  if (kinds.includes('stripes')) {
    const s = el('div', { position: 'absolute', inset: '-20%', background: `repeating-linear-gradient(135deg, ${th.light ? 'rgba(0,0,0,0.05)' : 'rgba(255,255,255,0.05)'} 0 ${px(46)}, transparent ${px(46)} ${px(92)})` });
    d.appendChild(s);
    movers.push(t => { s.style.transform = `translateX(${((t * 30) % 130) * U}px)`; });
  }
  if (kinds.includes('lines')) {
    for (let i = 0; i < 12; i++) {
      const w = (160 + R() * 380) * U, y = R() * H;
      const ln = el('div', { position: 'absolute', top: y + 'px', left: 0, width: w + 'px', height: px(4), borderRadius: px(2), background: th.light ? 'rgba(0,0,0,0.06)' : 'rgba(255,255,255,0.06)' });
      d.appendChild(ln);
      const sp = (500 + R() * 700) * U, off = R() * (W + w);
      movers.push(t => { ln.style.transform = `translateX(${W - ((t * sp + off) % (W + w * 2))}px)`; });
    }
  }
  if (kinds.includes('dots')) d.style.backgroundImage = `radial-gradient(${th.light ? 'rgba(0,0,0,0.07)' : 'rgba(255,255,255,0.06)'} ${px(2)}, transparent ${px(2.5)})`, d.style.backgroundSize = `${px(36)} ${px(36)}`;
  return { el: d, upd: t => movers.forEach(m => m(t)) };
}

// ───────────── chuyển màn ─────────────
const TRANS_AUTO = ['tilt', 'blinds', 'circle', 'split', 'slide', 'wipe'];
function applyTrans(node, kind, p) {
  const e = E.io(p);
  node.style.transform = ''; node.style.clipPath = ''; node.style.webkitMaskImage = ''; node.style.opacity = 1; node.style.boxShadow = '';
  if (p >= 1) return;
  switch (kind) {
    case 'fade': node.style.opacity = E.out(p); break;
    case 'tilt': node.style.transform = `translate(${(1 - e) * 105}%, ${(1 - e) * 10}%) rotate(${(1 - e) * 12}deg)`; node.style.boxShadow = `0 0 ${px(60)} rgba(0,0,0,0.45)`; break;
    case 'slide': node.style.transform = `translateY(${(1 - e) * 100}%)`; break;
    case 'blinds': { const sw = W / 8, x = e * sw; node.style.webkitMaskImage = `repeating-linear-gradient(90deg, #000 0 ${x}px, transparent ${x}px ${sw}px)`; break; }
    case 'circle': node.style.clipPath = `circle(${e * Math.hypot(W, H) * 0.55}px at 50% 50%)`; break;
    case 'split': node.style.clipPath = `inset(0 ${(1 - e) * 50}% 0 ${(1 - e) * 50}%)`; break;
    case 'wipe': node.style.clipPath = `inset(0 0 0 ${(1 - e) * 100}%)`; break;
    case 'zoom': node.style.transform = `scale(${1.25 - 0.25 * e})`; node.style.opacity = E.out(p); break;
    default: break;
  }
}

// ───────────── dựng toàn bộ ─────────────
function firstText(sc) {
  for (const it of sc.items || []) {
    if (it.text != null && (it.type == null || it.type === 'text' || it.type === 'quote')) return plain(it.text).replace(/[“”"]/g, '');
    if (it.type === 'chapter') return plain(it.title);
  }
  return null;
}

async function init(data) {
  PLAN = data.plan; WORDS = data.words || []; W = data.W; H = data.H; DUR = data.dur; BASE = data.base || '';
  U = Math.min(W, H) / 1080;
  NW = WORDS.map(w => norm(w.w));
  SC = []; EV = []; WARN = []; CHAP = [];
  stage = document.getElementById('stage');
  stage.innerHTML = '';
  Object.assign(stage.style, { width: W + 'px', height: H + 'px' });
  document.body.style.width = W + 'px'; document.body.style.height = H + 'px';

  // 1) mốc từng màn
  const scenes = PLAN.scenes || [];
  let cursor = 0, prevS = -1;
  scenes.forEach((s, k) => {
    s = Object.assign({}, s);
    if (s.text != null) s.items = [{ type: 'text', text: s.text, size: s.size, say: s.textSay }].concat(s.items || []);
    s.items = s.items || [];
    s._k = k;
    s._chapter = s.items.some(i => i.type === 'chapter');
    let start, wi = cursor;
    if (s.at != null) {
      start = Number(s.at);
      wi = Math.max(0, WORDS.findIndex(w => w.s >= start - 0.05)); if (wi < 0) wi = WORDS.length - 1;
      cursor = wi;
    } else {
      const say = s.say || firstText(s);
      const r = say ? findSay(say, cursor, cursor + 320) : null;
      if (!r) {
        WARN.push(`Màn ${k + 1}: không tìm thấy lời mở màn "${say || '(trống)'}" → đặt tạm sau màn trước 2.5s. Thêm "say" hoặc "at".`);
        start = prevS < 0 ? 0 : prevS + 2.5;
      } else { start = r.s - (s.lead != null ? s.lead : 0.12); wi = r.i0; cursor = r.i0 + 1; }
    }
    if (k === 0) start = 0;
    start = Math.max(start, prevS + 0.25);
    s._s = start; s._wi = wi; prevS = start;
    SC.push(s);
  });
  SC.forEach((s, k) => { s._e = k + 1 < SC.length ? SC[k + 1]._s : DUR; });

  // 2) dựng DOM từng màn
  SC.forEach((s, k) => {
    const th = TH[s.bg] || TH.dark;
    if (!TH[s.bg]) s.bg = s.bg ? (WARN.push(`Màn ${k + 1}: nền "${s.bg}" không có → dùng dark.`), 'dark') : 'dark';
    s._th = th;
    const node = el('div', { zIndex: k + 1, display: 'none' }, 'scene');
    const deco = buildDeco(s, th, k);
    node.appendChild(deco.el);
    const top = s.top != null ? s.top : 200, bot = s.bottom != null ? s.bottom : 160;
    const content = el('div', { left: px(60), right: px(60), top: px(top), bottom: px(bot), gap: px(s.gap != null ? s.gap : 56), justifyContent: s.valign === 'top' ? 'flex-start' : s.valign === 'bottom' ? 'flex-end' : 'center', paddingTop: s.valign === 'top' ? px(60) : 0 }, 'content');
    node.appendChild(content);
    const onlyText = s.items.every(i => (i.type || 'text') === 'text' || i.type === 'ghost' || i.type === 'confetti' || i.type === 'spacer');
    const built = s.items.map((it, i) => {
      const b = buildItem(it, s, th, i, onlyText ? 'l' : 'm');
      (b.abs ? node : content).appendChild(b.wrap);
      if (b.abs && b.type !== 'confetti') node.insertBefore(b.wrap, content);
      return b;
    });
    s._node = node; s._deco = deco; s._built = built; s._content = content;
    let tr = s.trans;
    if (!tr) tr = k === 0 ? 'cut' : (SC[k - 1].bg === s.bg && !s._chapter) ? 'fade' : TRANS_AUTO[(k * 7 + 3) % TRANS_AUTO.length];
    s._tr = tr; s._td = s.td || (tr === 'fade' ? 0.25 : tr === 'cut' ? 0 : 0.45);
    if (k > 0 && tr !== 'cut' && tr !== 'fade') EV.push({ t: s._s, kind: 'whoosh', k });
    const dur = s._e - s._s;
    if (dur < 0.7) WARN.push(`Màn ${k + 1}: chỉ ${dur.toFixed(2)}s — quá ngắn, gộp với màn kề.`);
    if (dur > 9) WARN.push(`Màn ${k + 1}: đứng ${dur.toFixed(1)}s — mẫu đổi màn mỗi 2–4s, nên tách hoặc thêm mục bật theo lời.`);
    stage.appendChild(node);
  });

  // 3) lớp phủ: thanh tiến độ + nhãn phần (KHÔNG logo)
  const ov = el('div', null, null); ov.id = 'ov';
  progEl = el('div', { height: px(7), background: '#F2C14E', width: 0 }); progEl.id = 'prog';
  ov.appendChild(progEl);
  const pillCss = { position: 'absolute', top: px(76), fontSize: px(26), fontWeight: 700, padding: `${px(10)} ${px(20)}`, borderRadius: px(14), color: '#fff', whiteSpace: 'nowrap' };
  chapEl = el('div', Object.assign({ right: px(50) }, pillCss));
  ov.appendChild(chapEl);
  brandEl = PLAN.brand ? el('div', Object.assign({ left: px(50), letterSpacing: '0.06em', fontWeight: 900 }, pillCss), null, esc(PLAN.brand)) : null;
  if (brandEl) ov.appendChild(brandEl);
  if (PLAN.progress === false) progEl.style.display = 'none';
  stage.appendChild(ov);
  const extra = (PLAN.chapters || []).map(c => {
    let t = c.at != null ? Number(c.at) : null;
    if (t == null && c.say) { const r = findSay(c.say, 0, NW.length); if (r) t = r.s - 0.1; else WARN.push(`Nhãn phần "${c.label}": không thấy lời "${c.say}".`); }
    return t == null ? null : { t, label: c.label };
  }).filter(Boolean);
  CHAP = [{ t: -1, label: PLAN.intro_label != null ? PLAN.intro_label : 'Mở đầu' }].concat(CHAP, extra).sort((a, b) => a.t - b.t);

  await document.fonts.ready;
  EV.sort((a, b) => a.t - b.t);
  return report();
}

function sceneAt(t) {
  let k = 0;
  while (k + 1 < SC.length && SC[k + 1]._s <= t) k++;
  return k;
}

function renderAt(t) {
  const k = sceneAt(t);
  SC.forEach((s, i) => {
    let vis = i === k || (i === k - 1 && t < SC[k]._s + SC[k]._td);
    if (!vis) { if (s._shown) { s._node.style.display = 'none'; s._shown = false; } return; }
    if (!s._shown) { s._node.style.display = 'block'; s._shown = true; }
    const lt = t;
    s._deco.upd(lt);
    s._built.forEach(b => b.upd(lt));
    if (i === k) applyTrans(s._node, s._tr, s._td ? prog(t, s._s, s._td) : 1);
    else applyTrans(s._node, 'none', 1);
  });
  // lớp phủ
  progEl.style.width = (clamp(t / DUR) * W) + 'px';
  const cur = SC[k], th = (cur && cur._td && t < cur._s + cur._td * 0.5 && k > 0) ? SC[k - 1]._th : cur._th;
  let label = '', lt0 = -9;
  CHAP.forEach(c => { if (t >= c.t) { label = c.label; lt0 = c.t; } });
  if (PLAN.chapter_pill === false) label = '';
  if (label !== lastLabel) { chapEl.textContent = label; lastLabel = label; }
  chapEl.style.display = label ? 'block' : 'none';
  chapEl.style.background = th.pill;
  chapEl.style.opacity = lt0 > 0 ? prog(t, lt0, 0.35) : 1;
  if (brandEl) brandEl.style.background = th.pill;
  return k;
}

function report() {
  return {
    dur: DUR,
    scenes: SC.map(s => ({ k: s._k + 1, s: +s._s.toFixed(3), e: +s._e.toFixed(3), bg: s.bg, tr: s._tr, text: (firstText(s) || (s.items[0] && s.items[0].type) || '').slice(0, 60) })),
    events: EV.map(e => ({ t: +e.t.toFixed(3), kind: e.kind })),
    warns: WARN.slice(),
  };
}

// đo tràn khung: chụp trạng thái cuối mỗi màn
function check() {
  const out = [];
  const safe = { l: 36 * U, r: W - 36 * U, t: 140 * U, b: H - 90 * U };
  SC.forEach(s => {
    const tEnd = Math.max(s._s + 0.05, s._e - 0.05);
    renderAt(tEnd);
    s._built.forEach((b, i) => {
      if (b.abs) return;
      const r = b.wrap.getBoundingClientRect();
      if (r.width === 0) return;
      const name = b.type + (s.items[i].text ? ` "${plain(s.items[i].text).slice(0, 30)}"` : '');
      if (r.left < safe.l - 1 || r.right > safe.r + 1) out.push(`Màn ${s._k + 1}: ${name} tràn ngang (${Math.round(r.left)}–${Math.round(r.right)}px).`);
      if (r.top < safe.t - 1 || r.bottom > safe.b + 1) out.push(`Màn ${s._k + 1}: ${name} tràn dọc (${Math.round(r.top)}–${Math.round(r.bottom)}px) — bớt mục/giảm cỡ.`);
      if (b.type === 'text') {
        const fs = parseFloat(b.wrap.querySelector('.txt').style.fontSize);
        const lines = Math.round(b.wrap.querySelector('.txt').offsetHeight / (fs * 1.2));
        if (lines > 4) out.push(`Màn ${s._k + 1}: chữ ${lines} dòng — mẫu ≤ 3 dòng, rút gọn câu.`);
      }
      if (b.a > s._e - 0.15) out.push(`Màn ${s._k + 1}: ${b.type} bật lúc ${b.a.toFixed(2)}s, sau khi màn đã hết (${s._e.toFixed(2)}s).`);
    });
  });
  return out;
}

window.ANIM = { init, renderAt, check, report };
})();

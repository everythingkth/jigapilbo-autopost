#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""지갑일보 카드뉴스·대표 이미지 확장 레이아웃 (brand.py 위에 얹어 씀).

brand.py의 색·폰트·마스트헤드·푸터·줄바꿈 함수를 그대로 쓰고, 아래만 더해요.
- 긴 표: 열 너비 비율, 칸 안 줄바꿈, 열별 글꼴, 세로 가운데 정렬
- 자동 맞춤: 내용이 푸터 선(H-150)을 넘으면 본문 전체 크기를 조금씩 줄여 다시 그림(최소 비율 제한)
- 표지·마지막 장·대표 이미지의 제목 줄 자동 맞춤(한 줄이 폭을 넘지 않는 가장 큰 크기)
- 렌더 기록(report): 장마다 최종 비율, 가장 작은 글자 크기, 본문 끝 y, 넘침 여부

사용: python3 cardkit.py cards spec.json OUT_DIR  /  python3 cardkit.py thumb spec.json out.png
"""
import json
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import brand as B  # noqa: E402

W, H, M = 1080, 1350, 72
BOTTOM = H - 150          # 푸터 선(H-120)과 30px 이상 띄움
MIN_SCALE = 0.70
MIN_BODY_PX = 28          # 모바일 가독 하한(1080px 카드 기준)

REPORT = []


class Meter:
    """그린 글자 크기 중 최솟값을 기록."""
    def __init__(self):
        self.min_px = 999

    def use(self, px):
        self.min_px = min(self.min_px, int(px))
        return int(px)


def F(meter, name, px):
    return B.font(name, meter.use(px))


def fit_px(d, lines, name, start, stop, max_w):
    """lines: 문자열 또는 parts 리스트. 모두 max_w 안에 들어가는 가장 큰 크기."""
    for px in range(start, stop - 1, -2):
        f = B.font(name, px)
        ok = True
        for ln in lines:
            text = ln if isinstance(ln, str) else "".join(p[0] for p in ln)
            if B.tw(d, text, f)[0] > max_w:
                ok = False
                break
        if ok:
            return px
    return stop


def parts_of(line):
    """head 한 줄: 문자열이면 검정, 리스트면 [(text,color,hl)]."""
    if isinstance(line, str):
        return [(line, B.INK, False)]
    return [tuple(p) for p in line]


# ------------------------------------------------------------------ 블록 그리기
def draw_items(d, y, blk, k, mt, start_no=1):
    fnum = F(mt, "black", 44 * k)
    fh = F(mt, "xbold", 50 * k)
    fs = F(mt, "med", 38 * k)
    indent = int(84 * k)
    gap = int(blk.get("gap", 52) * k)
    for i, it in enumerate(blk["items"]):
        head, sub = (it.split("|", 1) + [""])[:2]
        no = blk.get("start", start_no) + i
        d.text((M, y + int(4 * k)), f"{no:02d}", font=fnum, fill=B.ACCENT)
        y = B.text_block(d, (M + indent, y), head, fh, B.INK, W - 2 * M - indent, gap=1.25)
        if sub:
            for para in sub.split("\n"):
                y = B.text_block(d, (M + indent, y + int(6 * k)), para, fs, B.INK_SOFT, W - 2 * M - indent, gap=1.4)
        y += gap
    return y - gap + int(40 * k)


def draw_table(d, y, blk, k, mt):
    cols = len(blk["head"])
    ws = blk.get("widths") or [1] * cols
    tot = sum(ws)
    tw_ = W - 2 * M
    cw = [tw_ * w / tot for w in ws]
    xs = [M + sum(cw[:j]) for j in range(cols)]
    pad = int(blk.get("pad", 18) * k)
    lsp = blk.get("line", 1.28)
    fhd = F(mt, "bold", blk.get("head_px", 32) * k)
    col_fonts = blk.get("col_fonts") or [["xbold", 36]] + [["med", 34]] * (cols - 2) + [["black", 44]]
    fonts = [F(mt, n, p * k) for n, p in col_fonts]
    align = blk.get("align") or ["l"] + ["l"] * (cols - 2) + ["c"]
    accent = blk.get("accent_col", cols - 1)

    # 머리줄
    hl = [B.wrap(d, h, fhd, cw[j] - 2 * pad) for j, h in enumerate(blk["head"])]
    lh = int(fhd.size * 1.3)
    rh = max(len(x) for x in hl) * lh + 2 * pad
    d.rectangle([M, y, W - M, y + rh], fill=B.INK)
    for j, lines in enumerate(hl):
        yy = y + (rh - len(lines) * lh) / 2
        for ln in lines:
            w_, _ = B.tw(d, ln, fhd)
            x = xs[j] + pad if align[j] == "l" else xs[j] + (cw[j] - w_) / 2
            d.text((x, yy), ln, font=fhd, fill=B.PAPER)
            yy += lh
    y += rh
    # 본문 줄
    for r, row in enumerate(blk["rows"]):
        wrapped = []
        for j, cell in enumerate(row):
            f = fonts[j]
            segs = []  # (line, font, color)
            main = cell["t"] if isinstance(cell, dict) else cell
            color = B.ACCENT if j == accent else B.INK
            for para in main.split("\n"):
                segs += [(ln, f, color) for ln in B.wrap(d, para, f, cw[j] - 2 * pad)]
            if isinstance(cell, dict) and cell.get("sub"):
                fs_ = F(mt, "bold", cell.get("sub_px", 28) * k)
                segs += [(ln, fs_, color) for ln in B.wrap(d, cell["sub"], fs_, cw[j] - 2 * pad)]
            wrapped.append(segs)
        heights = [sum(int(sf.size * lsp) for _, sf, _ in segs) for segs in wrapped]
        rh = max(heights) + 2 * pad + int(4 * k)
        bg = B.PAPER if r % 2 == 0 else B.PAPER_DARK
        d.rectangle([M, y, W - M, y + rh], fill=bg)
        for j, segs in enumerate(wrapped):
            yy = y + (rh - heights[j]) / 2
            for ln, sf, color in segs:
                w_, _ = B.tw(d, ln, sf)
                x = xs[j] + pad if align[j] == "l" else xs[j] + (cw[j] - w_) / 2
                d.text((x, yy), ln, font=sf, fill=color)
                yy += int(sf.size * lsp)
        y += rh
    d.rectangle([M, y, W - M, y + 3], fill=B.INK)
    return y + int(34 * k)


def draw_note(d, y, blk, k, mt):
    f = F(mt, "med", blk.get("px", 34) * k)
    for para in blk["text"].split("\n"):
        y = B.text_block(d, (M, y), para, f, B.INK_SOFT, W - 2 * M, gap=1.42)
    return y + int(18 * k)


def draw_box(d, y, blk, k, mt):
    """테두리 상자: label(주황 굵게) + 줄들."""
    pad = int(28 * k)
    fl = F(mt, "xbold", blk.get("label_px", 34) * k)
    fb = F(mt, "med", blk.get("px", 32) * k)
    inner = W - 2 * M - 2 * pad
    lines = []
    for para in blk["lines"]:
        lines.append(B.wrap(d, para, fb, inner - int(30 * k)))
    lh = int(fb.size * 1.4)
    h = pad + int(fl.size * 1.35) + sum(len(x) for x in lines) * lh + int(8 * k) * len(lines) + pad
    d.rectangle([M, y, W - M, y + h], outline=B.INK, width=max(2, int(3 * k)))
    yy = y + pad
    d.text((M + pad, yy), blk["label"], font=fl, fill=B.ACCENT)
    yy += int(fl.size * 1.35)
    for ls in lines:
        bullet = blk.get("bullet", "·")
        d.text((M + pad, yy), bullet, font=fb, fill=B.INK)
        for ln in ls:
            d.text((M + pad + int(30 * k), yy), ln, font=fb, fill=B.INK)
            yy += lh
        yy += int(8 * k)
    return y + h + int(30 * k)


BLOCKS = {"items": draw_items, "table": draw_table, "note": draw_note, "box": draw_box}


# ------------------------------------------------------------------ 장 단위
def render_slide(spec, s, idx, total, k):
    mt = Meter()
    im, d = B.card_base(W, H, spec, idx, total)
    B.plan_pill(d, W, 150, spec.get("plan"), size=26)
    tpx = fit_px(d, [s["title"]], "xbold", int(76 * k), int(60 * k), W - 2 * M)
    ft = F(mt, "xbold", tpx)
    y = B.text_block(d, (M, int(200 * k) if k < 1 else 210), s["title"], ft, B.INK, W - 2 * M, gap=1.2)
    d.rectangle([M, y + int(18 * k), M + 110, y + int(30 * k)], fill=B.ACCENT)
    y += int(s.get("title_gap", 84) * k)
    for blk in s["blocks"]:
        y = BLOCKS[blk["type"]](d, y, blk, k, mt)
    B.footer(d, W, H, s.get("footer", spec.get("footer_left", "저장해 두면 나중에 편해요")))
    return im, y, mt.min_px


def render_cover(spec, k=1.0):
    mt = Meter()
    im, d = B.card_base(W, H, spec, 1, 2 + len(spec["slides"]))
    c = spec["cover"]
    fk = F(mt, "bold", 34)
    kw, _ = B.tw(d, c["kicker"], fk)
    d.rounded_rectangle([M, 200, M + kw + 44, 262], radius=31, fill=B.INK)
    d.text((M + 22, 209), c["kicker"], font=fk, fill=B.PAPER)
    B.plan_pill(d, W, 200, spec.get("plan"), size=30)
    heads = [parts_of(x) for x in c["head"]]
    px = fit_px(d, heads, "black", int(c.get("head_max", 142) * k), 72, W - 2 * M)
    fh = F(mt, "black", px)
    y = 310
    for line in heads:
        B.rich_line(d, (M, y), line, fh)
        y += int(px * 1.21)
    fs = F(mt, "med", 40 * k)
    y = B.text_block(d, (M, y + 26), c["sub"], fs, B.INK_SOFT, W - 2 * M, gap=1.4)
    if c.get("basis"):
        fb = F(mt, "med", 30)
        B.text_block(d, (M, H - 120 - 30 - int(fb.size * 1.4) * len(B.wrap(d, c["basis"], fb, W - 2 * M))),
                     c["basis"], fb, B.INK_SOFT, W - 2 * M, gap=1.4)
        lim = H - 120 - 30 - int(fb.size * 1.4) * len(B.wrap(d, c["basis"], fb, W - 2 * M)) - 20
    else:
        lim = BOTTOM
    B.footer(d, W, H, "넘겨서 1분 만에 확인 →")
    return im, y, mt.min_px, lim


def render_cta(spec, k=1.0):
    mt = Meter()
    total = 2 + len(spec["slides"])
    im, d = B.card_base(W, H, spec, total, total)
    B.plan_pill(d, W, 150, spec.get("plan"), size=26)
    cta = spec["cta"]
    px = fit_px(d, cta["lines"], "black", int(78 * k), 56, W - 2 * M)
    fl = F(mt, "black", px)
    y = int(210 * k) if k < 1 else 220
    for line in cta["lines"]:
        y = B.text_block(d, (M, y), line, fl, B.INK, W - 2 * M, gap=1.18)
    y += int(30 * k)
    for blk in cta.get("blocks", []):
        y = BLOCKS[blk["type"]](d, y, blk, k, mt)
    fk = F(mt, "bold", 38 * k)
    label = "프로필 링크에서 전체 글 보기 ↗"
    kw, _ = B.tw(d, label, fk)
    ph = int(80 * k)
    d.rounded_rectangle([M, y, M + kw + 60, y + ph], radius=ph // 2, fill=B.ACCENT)
    d.text((M + 30, y + (ph - fk.size) / 2 - 4), label, font=fk, fill="#FFFFFF")
    y += ph + int(40 * k)
    d.rectangle([M, y, W - M, y + 2], fill=B.INK)
    y += int(24 * k)
    fsrc = F(mt, "med", cta.get("fine_px", 31))
    y = B.text_block(d, (M, y), "출처  " + cta["sources"], fsrc, B.INK_SOFT, W - 2 * M, gap=1.5)
    for extra in cta.get("fine", []):
        y = B.text_block(d, (M, y + 10), extra, fsrc, B.INK_SOFT, W - 2 * M, gap=1.5)
    B.footer(d, W, H, B.TAGLINE)
    return im, y, mt.min_px


def fit_and_save(fn, path, label, lim=BOTTOM):
    k = 1.0
    while True:
        res = fn(k)
        im, y, mpx = res[0], res[1], res[2]
        lim_ = res[3] if len(res) > 3 else lim
        if y <= lim_ or k <= MIN_SCALE:
            break
        k = round(k - 0.03, 3)
    im.save(path)
    REPORT.append({"file": os.path.basename(path), "card": label, "scale": k, "min_font_px": mpx,
                   "content_bottom_y": int(y), "limit_y": int(lim_), "overflow": y > lim_,
                   "below_min_font": mpx < MIN_BODY_PX})
    return path


def render_cards(spec, out_dir, prefix=""):
    os.makedirs(out_dir, exist_ok=True)
    total = 2 + len(spec["slides"])
    paths = [fit_and_save(lambda k: render_cover(spec, k), os.path.join(out_dir, f"{prefix}01.png"), "cover")]
    for i, s in enumerate(spec["slides"], start=2):
        paths.append(fit_and_save(lambda k, s=s, i=i: render_slide(spec, s, i, total, k),
                                  os.path.join(out_dir, f"{prefix}{i:02d}.png"), s["title"]))
    paths.append(fit_and_save(lambda k: render_cta(spec, k), os.path.join(out_dir, f"{prefix}{total:02d}.png"), "cta"))
    return paths


# ------------------------------------------------------------------ 대표 이미지 1280x720
def thumbnail(spec, path):
    TW, TH = 1280, 720
    mt = Meter()
    im = Image.new("RGB", (TW, TH), B.PAPER)
    d = ImageDraw.Draw(im)
    B.masthead_bar(d, TW, spec["date"], spec["section"])
    fk = F(mt, "bold", 34)
    kw, _ = B.tw(d, spec["kicker"], fk)
    d.rounded_rectangle([M, 176, M + kw + 40, 176 + 58], radius=29, fill=B.INK)
    d.text((M + 20, 184), spec["kicker"], font=fk, fill=B.PAPER)
    B.plan_pill(d, TW, 176, spec.get("plan"), size=32)
    heads = [parts_of(x) for x in spec["head"]]
    px = fit_px(d, heads, "black", spec.get("head_max", 118), 72, TW - 2 * M)
    fh = F(mt, "black", px)
    y = 262
    for line in heads:
        B.rich_line(d, (M, y), line, fh)
        y += int(px * 1.22)
    fs_px = 40
    while True:
        fs = B.font("med", fs_px)
        n = len(B.wrap(d, spec["sub"], fs, TW - 2 * M))
        if y + 22 + n * int(fs_px * 1.35) <= TH - 36 or fs_px <= 30:
            break
        fs_px -= 2
    fs = F(mt, "med", fs_px)
    yb = B.text_block(d, (M, y + 22), spec["sub"], fs, B.INK_SOFT, TW - 2 * M, gap=1.35)
    d.rectangle([M, TH - 22, TW - M, TH - 17], fill=B.INK)
    im.save(path)
    REPORT.append({"file": os.path.basename(path), "card": "thumbnail", "scale": 1.0, "min_font_px": mt.min_px,
                   "content_bottom_y": int(yb), "limit_y": TH - 36, "overflow": yb > TH - 36,
                   "below_min_font": mt.min_px < MIN_BODY_PX})
    return path


if __name__ == "__main__":
    if len(sys.argv) >= 4 and sys.argv[1] == "cards":
        sp = json.load(open(sys.argv[2], encoding="utf-8"))
        for p in render_cards(sp, sys.argv[3]):
            print(p)
    elif len(sys.argv) >= 4 and sys.argv[1] == "thumb":
        sp = json.load(open(sys.argv[2], encoding="utf-8"))
        print(thumbnail(sp, sys.argv[3]))
    else:
        print(__doc__)
    print(json.dumps(REPORT, ensure_ascii=False, indent=1))

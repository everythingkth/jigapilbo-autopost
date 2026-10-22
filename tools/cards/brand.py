#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""지갑일보 브랜드 자산 + 인스타 카드뉴스 생성기.

python3 brand.py assets              # 프로필·블로그 타이틀·썸네일 예시
python3 brand.py cards spec.json OUT  # 카드뉴스 세트 (spec 형식은 아래 render_cards 참고)
"""
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FD = os.path.join(HERE, "fonts")

PAPER = "#F3EDE0"
PAPER_DARK = "#E6DDCB"
INK = "#161616"
INK_SOFT = "#4A4640"
ACCENT = "#FF5B26"
HILITE = "#FFE45C"

BRAND = "지갑일보"
HANDLE = "@jigapilbo"
TAGLINE = "내 지갑에 닿는 뉴스만, 매일 아침"


def font(name, size):
    files = {
        "mast": "NanumMyeongjo-ExtraBold.ttf",
        "black": "Pretendard-Black.otf",
        "xbold": "Pretendard-ExtraBold.otf",
        "bold": "Pretendard-Bold.otf",
        "med": "Pretendard-Medium.otf",
    }
    return ImageFont.truetype(os.path.join(FD, files[name]), size)


def tw(draw, text, f):
    b = draw.textbbox((0, 0), text, font=f)
    return b[2] - b[0], b[3] - b[1]


def wrap(draw, text, f, max_w):
    """한국어 줄바꿈: 공백 단위로 채우고, 너무 긴 단어는 글자 단위로 자른다."""
    lines = []
    for para in text.split("\n"):
        words, cur = para.split(" "), ""
        for w in words:
            cand = (cur + " " + w).strip()
            if tw(draw, cand, f)[0] <= max_w:
                cur = cand
                continue
            if cur:
                lines.append(cur)
            cur = ""
            for ch in w:
                if tw(draw, cur + ch, f)[0] <= max_w:
                    cur += ch
                else:
                    lines.append(cur)
                    cur = ch
        lines.append(cur)
    return lines


def text_block(draw, xy, text, f, fill, max_w, gap=1.28):
    x, y = xy
    lh = int(f.size * gap)
    for line in wrap(draw, text, f, max_w):
        draw.text((x, y), line, font=f, fill=fill)
        y += lh
    return y


def rich_line(draw, xy, parts, f):
    """parts: [(text, color, hilite?)] 를 한 줄에 이어 그린다."""
    x, y = xy
    for text, color, hl in parts:
        w, h = tw(draw, text, f)
        if hl:
            pad = int(f.size * 0.06)
            draw.rectangle([x - pad, y + f.size * 0.55, x + w + pad, y + f.size * 1.12], fill=HILITE)
        draw.text((x, y), text, font=f, fill=color)
        x += w
    return x


def double_rule(draw, y, x0, x1, color=INK, thick=6, thin=2, gap=6):
    draw.rectangle([x0, y, x1, y + thick], fill=color)
    draw.rectangle([x0, y + thick + gap, x1, y + thick + gap + thin], fill=color)
    return y + thick + gap + thin


def masthead_bar(draw, W, date_label, section, page=None):
    m = 72
    draw.text((m, 58), BRAND, font=font("mast", 46), fill=INK)
    right = f"{date_label}  ·  {section}"
    if page:
        right += f"  ·  {page}"
    f = font("med", 26)
    w, _ = tw(draw, right, f)
    draw.text((W - m - w, 70), right, font=f, fill=INK_SOFT)
    return double_rule(draw, 128, m, W - m)


def plan_pill(draw, W, y, text, size=30, m=72):
    """정부안·계획 단계 표시용 주황 알약(오른쪽 정렬)."""
    if not text:
        return
    f = font("xbold", size)
    w, h = tw(draw, text, f)
    padx, pady = int(size * 0.7), int(size * 0.38)
    x1 = W - m
    x0 = x1 - w - 2 * padx
    draw.rounded_rectangle([x0, y, x1, y + size + 2 * pady + 4], radius=(size + 2 * pady) // 2, fill=ACCENT)
    draw.text((x0 + padx, y + pady - 2), text, font=f, fill="#FFFFFF")


def footer(draw, W, H, left, right=HANDLE):
    m = 72
    draw.rectangle([m, H - 120, W - m, H - 118], fill=INK)
    f = font("bold", 28)
    draw.text((m, H - 92), left, font=f, fill=INK)
    w, _ = tw(draw, right, f)
    draw.text((W - m - w, H - 92), right, font=f, fill=INK_SOFT)


# ------------------------------------------------------------------ 브랜드 자산
def profile(path):
    S = 1080
    im = Image.new("RGB", (S, S), INK)
    d = ImageDraw.Draw(im)
    f = font("mast", 300)
    w0, _ = tw(d, "지갑", f)
    x0 = (S - w0) / 2 - 30
    for i, t in enumerate(["지갑", "일보"]):
        d.text((x0, 150 + i * 330), t, font=f, fill=PAPER)
    b = d.textbbox((x0, 480), "일보", font=f)
    r = 34
    cx, cy = b[2] + 34 + r, b[3] - r
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=ACCENT)
    im.save(path)


def blog_title(path):
    W, H = 966, 300
    im = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(im)
    m = 40
    double_rule(d, 26, m, W - m, thick=5, thin=2, gap=5)
    f = font("mast", 122)
    w, h = tw(d, BRAND, f)
    d.text(((W - w) / 2, 52), BRAND, font=f, fill=INK)
    d.ellipse([(W + w) / 2 + 12, 76, (W + w) / 2 + 40, 104], fill=ACCENT)
    y = 214
    d.rectangle([m, y, W - m, y + 2], fill=INK)
    f2 = font("med", 22)
    left = "생활경제 · 경제 · 주식 · 금융 · 기술"
    right = TAGLINE
    d.text((m, y + 18), left, font=f2, fill=INK_SOFT)
    w2, _ = tw(d, right, f2)
    d.text((W - m - w2, y + 18), right, font=f2, fill=INK)
    d.rectangle([m, H - 22, W - m, H - 17], fill=INK)
    im.save(path)


def thumbnail(path, kicker, head_parts, sub, date_label, section, plan=None):
    """블로그 대표 이미지 1280x720. head_parts: 줄 리스트, 각 줄은 [(text, color, hilite)]"""
    W, H = 1280, 720
    im = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(im)
    masthead_bar(d, W, date_label, section)
    m = 72
    fk = font("bold", 34)
    kw, _ = tw(d, kicker, fk)
    d.rounded_rectangle([m, 180, m + kw + 40, 180 + 58], radius=29, fill=INK)
    d.text((m + 20, 188), kicker, font=fk, fill=PAPER)
    plan_pill(d, W, 180, plan, size=32)
    fh = font("black", 118)
    y = 276
    for line in head_parts:
        rich_line(d, (m, y), line, fh)
        y += 146
    text_block(d, (m, y + 26), sub, font("med", 42), INK_SOFT, W - 2 * m)
    im.save(path)


# ------------------------------------------------------------------ 카드뉴스
def card_base(W, H, spec, idx, total):
    im = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(im)
    masthead_bar(d, W, spec["date"], spec["section"], f"{idx}/{total}")
    return im, d


def render_cards(spec, out_dir):
    """spec = {date, section, cover:{kicker, head:[[...]], sub}, slides:[{title, items:[...]} | {title, table:{head, rows}, note}], cta:{lines, sources, disclaimer}}"""
    os.makedirs(out_dir, exist_ok=True)
    W, H, m = 1080, 1350, 72
    total = 2 + len(spec["slides"])
    paths = []

    # 표지
    im, d = card_base(W, H, spec, 1, total)
    c = spec["cover"]
    fk = font("bold", 34)
    kw, _ = tw(d, c["kicker"], fk)
    d.rounded_rectangle([m, 200, m + kw + 44, 262], radius=31, fill=INK)
    d.text((m + 22, 209), c["kicker"], font=fk, fill=PAPER)
    plan_pill(d, W, 200, spec.get("plan"), size=30)
    fh = font("black", 142)
    y = 320
    for line in c["head"]:
        rich_line(d, (m, y), line, fh)
        y += 172
    text_block(d, (m, y + 30), c["sub"], font("med", 40), INK_SOFT, W - 2 * m, gap=1.4)
    footer(d, W, H, "넘겨서 1분 만에 확인 →")
    p = os.path.join(out_dir, "01.png"); im.save(p); paths.append(p)

    # 본문
    for i, s in enumerate(spec["slides"], start=2):
        im, d = card_base(W, H, spec, i, total)
        plan_pill(d, W, 150, spec.get("plan"), size=26)
        ft = font("xbold", 76)
        y = text_block(d, (m, 210), s["title"], ft, INK, W - 2 * m, gap=1.2)
        d.rectangle([m, y + 22, m + 110, y + 34], fill=ACCENT)
        y += 110
        if "items" in s:
            fb = font("xbold", 52)
            fsub = font("med", 40)
            for k, it in enumerate(s["items"]):
                head, *rest = it.split("|")
                num = f"{k + 1:02d}"
                d.text((m, y + 4), num, font=font("black", 44), fill=ACCENT)
                y = text_block(d, (m + 84, y), head, fb, INK, W - 2 * m - 84, gap=1.25)
                if rest:
                    y = text_block(d, (m + 84, y + 6), rest[0], fsub, INK_SOFT, W - 2 * m - 84, gap=1.42)
                y += 64
        if "table" in s:
            t = s["table"]
            cols = len(t["head"])
            cw = (W - 2 * m) / cols
            rh = 128 if len(t["rows"]) <= 3 else 100
            d.rectangle([m, y, W - m, y + rh], fill=INK)
            fth = font("bold", 40)
            for j, h in enumerate(t["head"]):
                w, _ = tw(d, h, fth)
                d.text((m + cw * j + (cw - w) / 2, y + 40), h, font=fth, fill=PAPER)
            y += rh
            ftd = font("xbold", 52)
            for r, row in enumerate(t["rows"]):
                bg = PAPER if r % 2 == 0 else PAPER_DARK
                d.rectangle([m, y, W - m, y + rh], fill=bg)
                for j, cell in enumerate(row):
                    color = ACCENT if (j == cols - 1 and t.get("accent_last", True)) else INK
                    w, _ = tw(d, cell, ftd)
                    d.text((m + cw * j + (cw - w) / 2, y + 34), cell, font=ftd, fill=color)
                y += rh
            d.rectangle([m, y, W - m, y + 3], fill=INK)
            y += 40
        if s.get("big"):
            fbg = font("black", 150)
            y = text_block(d, (m, y + 10), s["big"], fbg, ACCENT, W - 2 * m, gap=1.1)
            y += 20
        if s.get("note"):
            text_block(d, (m, y + 10), s["note"], font("med", 38), INK_SOFT, W - 2 * m, gap=1.45)
        footer(d, W, H, spec.get("footer_left", "저장해 두면 나중에 편해요"))
        p = os.path.join(out_dir, f"{i:02d}.png"); im.save(p); paths.append(p)

    # 마지막: 블로그 유도
    im, d = card_base(W, H, spec, total, total)
    plan_pill(d, W, 150, spec.get("plan"), size=26)
    cta = spec["cta"]
    y = 230
    for line in cta["lines"]:
        y = text_block(d, (m, y), line, font("black", 78), INK, W - 2 * m, gap=1.2)
    y += 40
    fk = font("bold", 40)
    label = "프로필 링크에서 전체 글 보기 ↗"
    kw, _ = tw(d, label, fk)
    d.rounded_rectangle([m, y, m + kw + 60, y + 84], radius=42, fill=ACCENT)
    d.text((m + 30, y + 18), label, font=fk, fill="#FFFFFF")
    y += 150
    d.rectangle([m, y, W - m, y + 2], fill=INK)
    y += 28
    y = text_block(d, (m, y), "출처  " + cta["sources"], font("med", 28), INK_SOFT, W - 2 * m, gap=1.5)
    text_block(d, (m, y + 16), cta["disclaimer"], font("med", 28), INK_SOFT, W - 2 * m, gap=1.5)
    footer(d, W, H, TAGLINE)
    p = os.path.join(out_dir, f"{total:02d}.png"); im.save(p); paths.append(p)
    return paths


def main():
    if len(sys.argv) >= 2 and sys.argv[1] == "assets":
        out = os.path.join(HERE, "brand")
        os.makedirs(out, exist_ok=True)
        profile(os.path.join(out, "profile_1080.png"))
        blog_title(os.path.join(out, "blog_title_966x300.png"))
        print("ok")
    elif len(sys.argv) >= 4 and sys.argv[1] == "cards":
        spec = json.load(open(sys.argv[2], encoding="utf-8"))
        for p in render_cards(spec, sys.argv[3]):
            print(p)
    elif len(sys.argv) >= 4 and sys.argv[1] == "thumb":
        spec = json.load(open(sys.argv[2], encoding="utf-8"))
        thumbnail(sys.argv[3], spec["kicker"], spec["head"], spec["sub"], spec["date"], spec["section"], spec.get("plan"))
        print(sys.argv[3])
    else:
        print(__doc__)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""깨알이 캐릭터 — 힉스필드 시안(0·1번, 툰 스티커)을 설계도로 삼아 직접 그린 벡터 버전.
expr(name) → SVG 문자열. 표정·소품을 코드로 바꿔 매일 재사용한다."""
OUT = '#4A2E1B'; BODY = '#FFE6A8'; SHADE = '#F6D48A'; BLUSH = '#F4A08A'; STAR = '#F7C33F'; NAVY = '#24346B'; COIN = '#F5B82E'

def star(cx, cy, r, fill=STAR, sw=6):
    p = f"M{cx},{cy-r} Q{cx+r*0.18},{cy-r*0.18} {cx+r},{cy} Q{cx+r*0.18},{cy+r*0.18} {cx},{cy+r} Q{cx-r*0.18},{cy+r*0.18} {cx-r},{cy} Q{cx-r*0.18},{cy-r*0.18} {cx},{cy-r}Z"
    return f'<path d="{p}" fill="{fill}" stroke="{OUT}" stroke-width="{sw}" stroke-linejoin="round"/>'

def sparkle(cx, cy, r):
    return star(cx, cy, r, STAR, 3)

def coin(cx, cy, r, tilt=0):
    return (f'<g transform="rotate({tilt} {cx} {cy})"><ellipse cx="{cx}" cy="{cy}" rx="{r}" ry="{r}" fill="{COIN}" stroke="{OUT}" stroke-width="8"/>'
            f'<ellipse cx="{cx}" cy="{cy}" rx="{r*0.74}" ry="{r*0.74}" fill="none" stroke="#D99A1C" stroke-width="6"/>'
            f'<ellipse cx="{cx-r*0.35}" cy="{cy-r*0.4}" rx="{r*0.22}" ry="{r*0.12}" fill="#FFE7A0" transform="rotate(-35 {cx-r*0.35} {cy-r*0.4})"/>'
            f'<circle cx="{cx}" cy="{cy}" r="{r*0.08}" fill="#D99A1C"/></g>')

def eyes(kind):
    L, R, y = 245, 355, 335
    if kind == 'open':
        return ''.join(f'<ellipse cx="{x}" cy="{y}" rx="19" ry="23" fill="#1B1210"/><circle cx="{x+6}" cy="{y-9}" r="7" fill="#fff"/><circle cx="{x-6}" cy="{y+8}" r="3.5" fill="#fff"/>' for x in (L, R))
    if kind == 'big':
        return ''.join(f'<ellipse cx="{x}" cy="{y}" rx="24" ry="30" fill="#1B1210"/><circle cx="{x+8}" cy="{y-12}" r="9" fill="#fff"/><circle cx="{x-8}" cy="{y+10}" r="4.5" fill="#fff"/>' for x in (L, R))
    if kind == 'happy':
        return ''.join(f'<path d="M{x-20},{y+6} Q{x},{y-18} {x+20},{y+6}" fill="none" stroke="#1B1210" stroke-width="9" stroke-linecap="round"/>' for x in (L, R))
    if kind == 'closed':
        return ''.join(f'<path d="M{x-20},{y} Q{x},{y+14} {x+20},{y}" fill="none" stroke="#1B1210" stroke-width="8" stroke-linecap="round"/>' for x in (L, R))
    if kind == 'wink':
        return (f'<ellipse cx="{L}" cy="{y}" rx="19" ry="23" fill="#1B1210"/><circle cx="{L+6}" cy="{y-9}" r="7" fill="#fff"/>'
                f'<path d="M{R-20},{y+4} Q{R},{y-16} {R+20},{y+4}" fill="none" stroke="#1B1210" stroke-width="9" stroke-linecap="round"/>')
    if kind == 'cry':
        return ''.join(f'<path d="M{x-20},{y-4} Q{x},{y+12} {x+20},{y-4}" fill="none" stroke="#1B1210" stroke-width="8" stroke-linecap="round"/>'
                       f'<path d="M{x-4},{y+12} Q{x-14},{y+60} {x-2},{y+95} Q{x+10},{y+60} {x+4},{y+12}Z" fill="#8FD0FF" stroke="#4FA3E0" stroke-width="3" opacity=".95"/>' for x in (L, R))
    if kind == 'dots':
        return ''.join(f'<circle cx="{x}" cy="{y}" r="9" fill="#1B1210"/>' for x in (L, R))
    if kind == 'spiral':
        return ''.join(f'<path d="M{x},{y} m-2,0 a4,4 0 1,1 6,3 a9,9 0 1,1 -12,-8 a14,14 0 1,1 20,14" fill="none" stroke="#1B1210" stroke-width="5" stroke-linecap="round"/>' for x in (L, R))
    return ''

def mouth(kind):
    c, y = 300, 375
    if kind == 'w':
        return f'<path d="M{c-22},{y-4} Q{c-11},{y+12} {c},{y-2} Q{c+11},{y+12} {c+22},{y-4}" fill="none" stroke="{OUT}" stroke-width="7" stroke-linecap="round"/>'
    if kind == 'open':
        return f'<path d="M{c-18},{y-6} Q{c},{y+30} {c+18},{y-6} Z" fill="#7A2E2A" stroke="{OUT}" stroke-width="6" stroke-linejoin="round"/><path d="M{c-9},{y+8} Q{c},{y+18} {c+9},{y+8}" fill="#F07C7C"/>'
    if kind == 'o':
        return f'<ellipse cx="{c}" cy="{y+6}" rx="13" ry="17" fill="#7A2E2A" stroke="{OUT}" stroke-width="6"/>'
    if kind == 'wobble':
        return f'<path d="M{c-24},{y+6} q8,-10 16,0 q8,10 16,0 q8,-10 16,0" fill="none" stroke="{OUT}" stroke-width="6" stroke-linecap="round"/>'
    if kind == 'flat':
        return f'<path d="M{c-14},{y+4} L{c+14},{y+4}" stroke="{OUT}" stroke-width="7" stroke-linecap="round"/>'
    if kind == 'sleep':
        return f'<ellipse cx="{c}" cy="{y+4}" rx="8" ry="6" fill="#7A2E2A"/>'
    return ''

def body(extra_front='', arms='hug', blush=True):
    b = ('<path d="M300,118 C372,176 470,262 470,392 C470,492 398,540 300,540 C202,540 130,492 130,392 C130,262 228,176 300,118 Z" '
         f'fill="{BODY}" stroke="{OUT}" stroke-width="11" stroke-linejoin="round"/>'
         f'<path d="M150,420 C160,500 230,528 300,528 C370,528 440,500 450,420 C430,480 370,505 300,505 C230,505 170,480 150,420Z" fill="{SHADE}" opacity=".7"/>'
         '<ellipse cx="228" cy="230" rx="26" ry="44" fill="#fff" opacity=".55" transform="rotate(32 228 230)"/>')
    feet = f'<ellipse cx="248" cy="540" rx="30" ry="18" fill="{BODY}" stroke="{OUT}" stroke-width="9"/><ellipse cx="352" cy="540" rx="30" ry="18" fill="{BODY}" stroke="{OUT}" stroke-width="9"/>'
    cheeks = (f'<ellipse cx="212" cy="378" rx="25" ry="15" fill="{BLUSH}" opacity=".75"/><ellipse cx="388" cy="378" rx="25" ry="15" fill="{BLUSH}" opacity=".75"/>' if blush else '')
    freck = sparkle(410, 335, 10) + sparkle(428, 312, 6)
    lanyard = (f'<path d="M178,415 Q300,470 422,415" fill="none" stroke="{NAVY}" stroke-width="9" stroke-linecap="round"/>'
               f'<rect x="300" y="452" width="8" height="16" fill="#9AA3B5"/><rect x="270" y="466" width="62" height="44" rx="7" fill="#fff" stroke="{OUT}" stroke-width="6"/>'
               f'<rect x="282" y="478" width="22" height="20" rx="3" fill="#CFE3FF"/><rect x="309" y="481" width="14" height="5" rx="2" fill="#B7BCC8"/><rect x="309" y="491" width="14" height="5" rx="2" fill="#B7BCC8"/>')
    return feet + b + cheeks + freck + lanyard, extra_front

def arms_svg(kind):
    if kind == 'hug':
        return (f'<ellipse cx="238" cy="458" rx="26" ry="20" fill="{BODY}" stroke="{OUT}" stroke-width="9" transform="rotate(-20 238 458)"/>'
                f'<ellipse cx="362" cy="458" rx="26" ry="20" fill="{BODY}" stroke="{OUT}" stroke-width="9" transform="rotate(20 362 458)"/>')
    if kind == 'up':
        return (f'<ellipse cx="150" cy="300" rx="22" ry="30" fill="{BODY}" stroke="{OUT}" stroke-width="9" transform="rotate(-30 150 300)"/>'
                f'<ellipse cx="450" cy="300" rx="22" ry="30" fill="{BODY}" stroke="{OUT}" stroke-width="9" transform="rotate(30 450 300)"/>')
    if kind == 'down':
        return (f'<ellipse cx="146" cy="440" rx="20" ry="28" fill="{BODY}" stroke="{OUT}" stroke-width="9" transform="rotate(20 146 440)"/>'
                f'<ellipse cx="454" cy="440" rx="20" ry="28" fill="{BODY}" stroke="{OUT}" stroke-width="9" transform="rotate(-20 454 440)"/>')
    if kind == 'cheek':
        return (f'<ellipse cx="190" cy="395" rx="24" ry="20" fill="{BODY}" stroke="{OUT}" stroke-width="9"/>'
                f'<ellipse cx="410" cy="395" rx="24" ry="20" fill="{BODY}" stroke="{OUT}" stroke-width="9"/>')
    return ''

PRESETS = {
  # name: (eyes, mouth, arms, prop, effects)
  'basic':   ('open', 'w', 'hug', 'coin_hug', ''),
  'happy':   ('happy', 'open', 'up', 'coin_up', 'sparkles'),
  'cry':     ('cry', 'wobble', 'down', '', 'sweat'),
  'shock':   ('big', 'o', 'cheek', '', 'shock'),
  'broke':   ('spiral', 'flat', 'down', 'empty', 'fly'),
  'payday':  ('happy', 'open', 'hug', 'coin_hug', 'sparkles_big'),
  'calc':    ('dots', 'flat', 'hug', 'calc', 'sweat'),
  'proud':   ('wink', 'open', 'up', 'coin_up', 'sparkles'),
  'sleep':   ('closed', 'sleep', 'hug', '', 'zzz'),
}

def prop_svg(p):
    if p == 'coin_hug':
        return coin(300, 452, 54)
    if p == 'coin_up':
        return coin(300, 70, 58, -10)
    if p == 'empty':
        return (f'<g transform="rotate(-8 300 445)"><rect x="232" y="408" width="136" height="80" rx="12" fill="#B9774A" stroke="{OUT}" stroke-width="8"/>'
                f'<path d="M232,430 L368,430" stroke="{OUT}" stroke-width="6"/><circle cx="350" cy="452" r="7" fill="{STAR}" stroke="{OUT}" stroke-width="4"/></g>')
    if p == 'calc':
        return (f'<rect x="246" y="398" width="108" height="128" rx="14" fill="#5B6A86" stroke="{OUT}" stroke-width="8"/><rect x="260" y="412" width="80" height="28" rx="5" fill="#CFE8C8"/>'
                + ''.join(f'<rect x="{262+c*27}" y="{450+r*22}" width="20" height="15" rx="3" fill="#EDEFF4"/>' for r in range(3) for c in range(3)))
    return ''

def fx_svg(f):
    if f == 'sparkles':
        return sparkle(150, 200, 18) + sparkle(470, 180, 22) + sparkle(110, 300, 10)
    if f == 'sparkles_big':
        return sparkle(130, 190, 26) + sparkle(480, 200, 30) + sparkle(100, 330, 14) + sparkle(505, 360, 14) + sparkle(200, 120, 12)
    if f == 'sweat':
        return f'<path d="M430,250 Q446,280 430,296 Q414,280 430,250Z" fill="#9FD8FF" stroke="#4FA3E0" stroke-width="4"/>'
    if f == 'shock':
        return f'<path d="M478,170 L488,240" stroke="{OUT}" stroke-width="9" stroke-linecap="round"/><circle cx="491" cy="265" r="7" fill="{OUT}"/><path d="M120,210 l-25,-20 M110,250 l-32,-4 M128,175 l-12,-28" stroke="{OUT}" stroke-width="7" stroke-linecap="round"/>'
    if f == 'fly':
        return (f'<g opacity=".9">{coin(480,200,24,20)}{coin(130,170,18,-20)}</g>'
                f'<path d="M462,230 q-10,20 -30,26 M150,196 q12,16 30,20" fill="none" stroke="{OUT}" stroke-width="5" stroke-dasharray="6 8" stroke-linecap="round"/>')
    if f == 'zzz':
        return f'<text x="400" y="200" font-family="Pretendard, sans-serif" font-weight="900" font-size="54" fill="{NAVY}">Z</text><text x="450" y="150" font-family="Pretendard, sans-serif" font-weight="900" font-size="40" fill="{NAVY}">z</text><text x="490" y="112" font-family="Pretendard, sans-serif" font-weight="900" font-size="30" fill="{NAVY}">z</text>'
    return ''

def expr(name, size=600):
    e, m, a, p, f = PRESETS[name]
    head_star = '' if p == 'coin_up' else star(300, 80, 26)
    base, _ = body()
    behind = fx_svg(f) if f in ('fly',) else ''
    front_fx = '' if f in ('fly',) else fx_svg(f)
    arms_front = a in ('hug',)
    parts = [behind, base, eyes(e), mouth(m), head_star]
    if p in ('coin_hug', 'empty', 'calc'):
        parts += [prop_svg(p), arms_svg(a)]
    else:
        parts += [arms_svg(a), prop_svg(p)]
    parts.append(front_fx)
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 600" width="{size}" height="{size}">{"".join(parts)}</svg>'

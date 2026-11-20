#!/usr/bin/env python3
"""릴스 배경음 — 저작권 걱정 없는 짧은 로파이 루프를 코드로 직접 합성한다.

사용: python tools/reels/music.py out.wav --dur 14 [--seed 3]
seed 마다 코드 진행·템포가 조금씩 달라진다(같은 소리 반복 방지).
"""
import argparse, wave
import numpy as np

SR = 44100
PROGS = [
    [[53, 57, 60, 64], [52, 55, 59, 62], [50, 53, 57, 60], [48, 52, 55, 59]],  # Fmaj7 Em7 Dm7 Cmaj7
    [[57, 60, 64, 67], [53, 57, 60, 64], [48, 52, 55, 59], [55, 59, 62, 65]],  # Am7 Fmaj7 Cmaj7 G7
    [[50, 53, 57, 60], [55, 59, 62, 65], [48, 52, 55, 59], [57, 60, 64, 67]],  # Dm7 G7 Cmaj7 Am7
]


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def keys(freq, dur):
    t = np.arange(int(SR * dur)) / SR
    env = np.exp(-t * 1.8) * (1 - np.exp(-t * 60))
    tone = sum(a * np.sin(2 * np.pi * freq * k * t) for k, a in ((1, 1.0), (2, 0.35), (3, 0.12), (4, 0.05)))
    trem = 1 + 0.08 * np.sin(2 * np.pi * 4.5 * t)
    return tone * env * trem


def kick(dur=0.35):
    t = np.arange(int(SR * dur)) / SR
    f = 110 * np.exp(-t * 18) + 45
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9)


def hat(rng, dur=0.06):
    n = int(SR * dur)
    x = rng.standard_normal(n)
    x = np.diff(np.concatenate([[0], x]))  # 고역만
    return x * np.exp(-np.arange(n) / SR * 70) * 0.25


def make(dur, seed=0):
    rng = np.random.default_rng(seed)
    prog = PROGS[seed % len(PROGS)]
    bpm = 82 + (seed % 3) * 4
    beat = 60 / bpm
    n = int(SR * (dur + 1))
    mix = np.zeros(n)
    bar = beat * 4
    t0 = 0.0
    i = 0
    while t0 < dur:
        chord = prog[i % len(prog)]
        for j, m in enumerate(chord):  # 살짝 흘려 치기
            s = int(SR * (t0 + j * 0.018))
            v = keys(hz(m), bar * 0.98) * 0.16
            mix[s:s + len(v)] += v[:max(0, n - s)]
        b = keys(hz(chord[0] - 12), bar * 0.9) * 0.22  # 베이스
        s = int(SR * t0)
        mix[s:s + len(b)] += b[:max(0, n - s)]
        for k in range(4):
            tb = t0 + k * beat
            if k in (0, 2):
                kk = kick() * 0.45
                s = int(SR * tb); mix[s:s + len(kk)] += kk[:max(0, n - s)]
            for off in (0, beat / 2):
                hh = hat(rng) * (1.0 if off else 0.6)
                s = int(SR * (tb + off + rng.uniform(0, 0.012)))
                mix[s:s + len(hh)] += hh[:max(0, n - s)]
        t0 += bar
        i += 1
    mix = mix[:int(SR * dur)]
    # 부드럽게: 간단한 저역통과 + 페이드
    k = np.ones(6) / 6
    mix = np.convolve(mix, k, mode="same")
    fade = int(SR * 0.8)
    mix[:int(SR * 0.05)] *= np.linspace(0, 1, int(SR * 0.05))
    mix[-fade:] *= np.linspace(1, 0, fade)
    mix = mix / (np.max(np.abs(mix)) + 1e-9) * 0.5
    return mix


def save(path, x):
    st = np.stack([x, x], axis=1)
    pcm = (st * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(pcm.tobytes())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("out"); ap.add_argument("--dur", type=float, default=14); ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    save(a.out, make(a.dur, a.seed))

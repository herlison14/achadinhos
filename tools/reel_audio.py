"""Trilha e efeitos sonoros ORIGINAIS (sintetizados aqui, sem amostra de terceiros: livres de direitos autorais).

sintetizar(duracao, bpm, sfx) -> array int16 estéreo 44,1 kHz; salvar(wav, audio) grava o arquivo.
sfx: lista de (tempo_em_segundos, nome) com nome em {"whoosh", "pop", "cha", "brilho"}.
Batida house leve: bumbo em todo tempo, palma nos tempos 2 e 4, chimbal no contratempo, baixo e arpejo em Lá menor (Am-F-C-G).
"""
import wave
import numpy as np

SR = 44100
RNG = np.random.default_rng(7)


def _t(n):
    return np.arange(n) / SR


def _caixa(x, k):
    return np.convolve(x, np.ones(k) / k, mode='same')


def bumbo():
    t = _t(int(0.38 * SR)); f = 46 + 110 * np.exp(-t * 32)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 8.5) + 0.25 * np.sin(2 * np.pi * 1800 * t) * np.exp(-t * 300)


def chimbal(aberto=False):
    n = int((0.22 if aberto else 0.06) * SR); r = np.diff(RNG.standard_normal(n + 1))
    return r * np.exp(-_t(n) * (16 if aberto else 80)) * 0.55


def palma():
    n = int(0.2 * SR); r = RNG.standard_normal(n); r = r - _caixa(r, 12)
    env = np.exp(-_t(n) * 24) + 0.7 * np.exp(-np.maximum(_t(n) - 0.012, 0) * 60) * (_t(n) > 0.012) + 0.5 * np.exp(-np.maximum(_t(n) - 0.024, 0) * 60) * (_t(n) > 0.024)
    return r * env * 0.6


def nota_baixo(freq, dur):
    n = int(dur * SR); t = _t(n)
    x = np.sin(2 * np.pi * freq * t) + 0.45 * np.sin(4 * np.pi * freq * t) + 0.18 * np.sin(6 * np.pi * freq * t)
    return x * np.minimum(1, t * 400) * np.exp(-t * 3.2) * np.minimum(1, (dur - t) * 60)


def pluck(freq, dur=0.22):
    n = int(dur * SR); t = _t(n)
    x = np.sin(2 * np.pi * freq * t) + 0.5 * np.sin(4 * np.pi * freq * t) * np.exp(-t * 18) + 0.25 * np.sin(6 * np.pi * freq * t) * np.exp(-t * 30)
    return x * np.minimum(1, t * 600) * np.exp(-t * 14)


def whoosh(dur=0.45):
    n = int(dur * SR); r = RNG.standard_normal(n); r = _caixa(r, 40) * 6
    t = np.linspace(0, 1, n); return r * np.sin(np.pi * t) ** 2 * 0.9


def pop():
    n = int(0.14 * SR); t = _t(n); f = 520 + 700 * np.exp(-t * 40)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 22)


def cha():
    n = int(0.9 * SR); t = _t(n); y = np.zeros(n)
    for atraso, fr in ((0.0, 1568.0), (0.09, 2093.0)):
        i = int(atraso * SR); tt = t[: n - i]
        y[i:] += (np.sin(2 * np.pi * fr * tt) + 0.4 * np.sin(2 * np.pi * fr * 2.76 * tt)) * np.exp(-tt * 7) * 0.55
    return y


def brilho():
    n = int(1.2 * SR); t = _t(n); y = np.zeros(n)
    for k, fr in enumerate((1047, 1319, 1568, 2093, 2637)):
        i = int(k * 0.07 * SR); tt = t[: n - i]; y[i:] += np.sin(2 * np.pi * fr * tt) * np.exp(-tt * 5) * 0.4
    return y


def _somar(dst, src, inicio, ganho):
    i = int(inicio * SR)
    if i >= len(dst): return
    f = min(len(src), len(dst) - i); dst[i:i + f] += src[:f] * ganho


def sintetizar(duracao, bpm=120, sfx=()):
    n = int(duracao * SR); m = np.zeros(n)
    beat = 60.0 / bpm; compasso = 4 * beat
    acordes = [(55.0, (220.0, 261.63, 329.63)), (43.65, (174.61, 220.0, 261.63)), (65.41, (261.63, 329.63, 392.0)), (49.0, (196.0, 246.94, 293.66))]
    kik, ham, hco, pal = bumbo(), chimbal(), chimbal(True), palma()
    for b in range(int(duracao / beat) + 1):
        t = b * beat
        _somar(m, kik, t, 0.95)
        _somar(m, hco, t + beat / 2, 0.30)
        if b % 4 in (1, 3): _somar(m, pal, t, 0.50)
        _somar(m, ham, t + beat / 4, 0.12); _somar(m, ham, t + 3 * beat / 4, 0.12)
    for c in range(int(duracao / compasso) + 1):
        raiz, tri = acordes[c % 4]; t0 = c * compasso
        for k, (pos, osc) in enumerate(((0, 1), (0.75, 1), (1.5, 1), (2.0, 2), (2.75, 1), (3.5, 1))):
            _somar(m, nota_baixo(raiz * osc, beat * 0.45), t0 + pos * beat, 0.55)
        pad = (0, 1, 2, 1, 0, 1, 2, 1, 2, 1, 0, 1, 2, 1, 0, 1)
        for s, idx in enumerate(pad):
            _somar(m, pluck(tri[idx] * (2 if s % 8 == 7 else 1)), t0 + s * beat / 4, 0.20)
    gen = {'whoosh': whoosh, 'pop': pop, 'cha': cha, 'brilho': brilho}
    ganho = {'whoosh': 0.55, 'pop': 0.7, 'cha': 0.65, 'brilho': 0.55}
    for tempo, nome in sfx:
        _somar(m, gen[nome](), tempo, ganho[nome])
    fim = int(0.6 * SR); m[-fim:] *= np.linspace(1, 0, fim)
    ini = int(0.01 * SR); m[:ini] *= np.linspace(0, 1, ini)
    m = np.tanh(m * 0.9) / np.tanh(0.9); m = m / max(1e-9, np.max(np.abs(m))) * 0.68
    est = np.stack([m, np.roll(m, 30) * 0.98], axis=1)   # leve defasagem: sensação de espaço
    return (est * 32767).astype(np.int16)


def salvar(caminho, audio):
    with wave.open(caminho, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(audio.tobytes())

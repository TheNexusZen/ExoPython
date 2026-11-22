import audioop
import cmath
import math
import os
import shutil
import struct
import subprocess
import tempfile
import wave
from typing import List, Optional, Tuple, Union
from . import scripts as exoscript
from . import variables as exovar

_NOTE_OFFSETS = {
    "C": 0, "C#": 1, "DB": 1,
    "D": 2, "D#": 3, "EB": 3,
    "E": 4,
    "F": 5, "F#": 6, "GB": 6,
    "G": 7, "G#": 8, "AB": 8,
    "A": 9, "A#": 10, "BB": 10,
    "B": 11,
}


def note_to_midi(note: Union[str, int]) -> int:
    if isinstance(note, int):
        return note
    s = str(note).strip().upper()
    if len(s) >= 2 and s[1] in ("#", "B"):
        pitch_cls, octave_str = s[:2], s[2:]
    else:
        pitch_cls, octave_str = s[:1], s[1:]
    if pitch_cls not in _NOTE_OFFSETS or not octave_str.lstrip("-").isdigit():
        raise ValueError(f"Invalid note name: {note!r}")
    return (int(octave_str) + 1) * 12 + _NOTE_OFFSETS[pitch_cls]


def note_to_semitones(note: Union[str, int], root: Union[str, int] = "C4") -> float:
    return float(note_to_midi(note) - note_to_midi(root))


def freq_to_semitones(freq_hz: float, base_freq_hz: float = 261.625565) -> float:
    if freq_hz <= 0.0:
        return 0.0
    return 12.0 * math.log2(freq_hz / base_freq_hz)


def _fft_magnitudes(samples: List[float]) -> List[float]:
    n = len(samples)
    if n <= 1:
        return [abs(x) for x in samples]

    j = 0
    a = [complex(x, 0.0) for x in samples]
    for i in range(1, n):
        bit = n >> 1
        while j & bit:
            j ^= bit
            bit >>= 1
        j ^= bit
        if i < j:
            a[i], a[j] = a[j], a[i]

    length = 2
    while length <= n:
        ang = -2.0 * math.pi / length
        wlen = complex(math.cos(ang), math.sin(ang))
        for i in range(0, n, length):
            w = 1.0 + 0.0j
            half = length >> 1
            for k in range(half):
                u = a[i + k]
                v = a[i + k + half] * w
                a[i + k] = u + v
                a[i + k + half] = u - v
                w *= wlen
        length <<= 1

    return [abs(a[k]) for k in range(n // 2)]


def _read_pcm_mono(filepath: str, target_rate: int = 16000) -> Tuple[int, List[float]]:
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Audio file not found: {filepath}")

    ext = os.path.splitext(filepath)[1].lower()
    wav_path = filepath
    tmp_wav = None

    if ext != ".wav":
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            raise RuntimeError(
                f"Cannot decode {ext!r} without ffmpeg installed; convert to .wav or install ffmpeg."
            )
        fd, tmp_wav = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        subprocess.run(
            [ffmpeg, "-y", "-i", filepath, "-ac", "1", "-ar", str(target_rate), "-f", "wav", tmp_wav],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        wav_path = tmp_wav

    try:
        with wave.open(wav_path, "rb") as wf:
            channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            framerate = wf.getframerate()
            raw = wf.readframes(wf.getnframes())
    finally:
        if tmp_wav and os.path.exists(tmp_wav):
            os.remove(tmp_wav)

    if channels > 1:
        raw = audioop.tomono(raw, sampwidth, 0.5, 0.5)
    if framerate != target_rate:
        raw, _ = audioop.ratecv(raw, sampwidth, 1, framerate, target_rate, None)
        framerate = target_rate

    if sampwidth == 1:
        ints = [b - 128 for b in raw]
        scale = 128.0
    elif sampwidth == 2:
        count = len(raw) // 2
        ints = struct.unpack(f"<{count}h", raw)
        scale = 32768.0
    elif sampwidth == 4:
        count = len(raw) // 4
        ints = struct.unpack(f"<{count}i", raw)
        scale = 2147483648.0
    else:
        raw16 = audioop.lin2lin(raw, sampwidth, 2)
        count = len(raw16) // 2
        ints = struct.unpack(f"<{count}h", raw16)
        scale = 32768.0

    samples = [x / scale for x in ints]
    return framerate, samples


def analyze_audio(
    filepath: str,
    *,
    step_sec: float = 0.06,
    base_freq_hz: float = 261.625565,
    min_freq_hz: float = 65.0,
    max_freq_hz: float = 2093.0,
    silence_threshold: float = 0.03,
    quantize_semitones: bool = True,
    max_duration: Optional[float] = None,
) -> List[Tuple[float, Optional[float], float]]:
    """
    Analyze an audio file into `(wait_sec, semitones_or_None, volume)` frames.
    Consecutive frames with identical quantized pitch and similar volume are merged
    to keep the generated Exoracer script compact.
    """
    rate, samples = _read_pcm_mono(filepath, target_rate=16000)
    if max_duration is not None:
        samples = samples[: int(float(max_duration) * rate)]

    hop = max(1, int(round(step_sec * rate)))
    win_size = 1024
    hann = [0.5 * (1.0 - math.cos(2.0 * math.pi * i / (win_size - 1))) for i in range(win_size)]

    peak_amp = max((abs(s) for s in samples), default=1.0) or 1.0
    raw_frames: List[Tuple[float, Optional[float], float]] = []

    for start in range(0, len(samples), hop):
        chunk = samples[start : start + win_size]
        if not chunk:
            break
        rms = math.sqrt(sum(x * x for x in chunk) / len(chunk)) / peak_amp
        if rms < silence_threshold:
            raw_frames.append((step_sec, None, 0.0))
            continue

        padded = [
            (chunk[i] if i < len(chunk) else 0.0) * hann[i]
            for i in range(win_size)
        ]
        mags = _fft_magnitudes(padded)
        min_bin = max(1, int(min_freq_hz * win_size / rate))
        max_bin = min(len(mags) - 2, int(max_freq_hz * win_size / rate))

        best_bin = max(range(min_bin, max_bin + 1), key=lambda k: mags[k])
        # Parabolic interpolation around peak FFT bin for sub-bin pitch accuracy
        y0, y1, y2 = mags[best_bin - 1], mags[best_bin], mags[best_bin + 1]
        denom = y0 - 2.0 * y1 + y2
        delta = 0.5 * (y0 - y2) / denom if abs(denom) > 1e-12 else 0.0
        freq = (best_bin + delta) * rate / win_size

        semi = freq_to_semitones(freq, base_freq_hz=base_freq_hz)
        semi = max(-36.0, min(36.0, semi))
        if quantize_semitones:
            semi = round(semi, 1)
        else:
            semi = round(semi, 2)
        vol = round(min(1.0, max(0.1, rms * 1.6)), 2)
        raw_frames.append((step_sec, semi, vol))

    # Merge adjacent identical notes / rests so scripts stay small and clean
    merged: List[Tuple[float, Optional[float], float]] = []
    for dur, semi, vol in raw_frames:
        if merged:
            prev_dur, prev_semi, prev_vol = merged[-1]
            if semi is None and prev_semi is None:
                merged[-1] = (round(prev_dur + dur, 4), None, 0.0)
                continue
            if semi is not None and prev_semi is not None and abs(semi - prev_semi) <= 0.25 and abs(vol - prev_vol) <= 0.12:
                merged[-1] = (round(prev_dur + dur, 4), prev_semi, prev_vol)
                continue
        merged.append((round(dur, 4), semi, vol))
    return merged


def audio_to_script(
    filepath: str,
    sound_id: str = "blip",
    *,
    name: str = "CustomAudio",
    activator: Optional[int] = 0,
    step_sec: float = 0.06,
    base_freq_hz: float = 261.625565,
    volume_scale: float = 1.0,
    loop: int = 0,
    max_duration: Optional[float] = None,
    pack: bool = True,
):
    """
    Convert an audio file directly into a native Exoracer Script using `PlaySound`
    + `FloatSemitones` pitch modulation.
    """
    events = analyze_audio(
        filepath,
        step_sec=step_sec,
        base_freq_hz=base_freq_hz,
        max_duration=max_duration,
    )
    sc = exoscript.create(name)
    if activator is not None:
        sc.on(activator)

    blk = exoscript.block()
    for dur, semi, vol in events:
        if semi is not None and vol > 0.0:
            v = round(min(1.0, vol * float(volume_scale)), 3)
            blk.play_sound(sound_id, volume=v, pitch=exovar.semitones(semi))
        if dur > 0.0:
            blk.wait(dur)

    if loop > 0:
        sc.repeat(int(loop), blk, wait=True)
    else:
        sc.actions.extend(blk.actions)
    return sc.pack() if pack else sc


def audio_to_python(
    filepath: str,
    sound_id: str = "blip",
    *,
    var_name: str = "custom_audio",
    script_name: str = "CustomAudio",
    activator: int = 0,
    step_sec: float = 0.06,
    base_freq_hz: float = 261.625565,
    volume_scale: float = 1.0,
    loop: int = 0,
    max_duration: Optional[float] = None,
    out_py: Optional[str] = None,
) -> str:
    """
    Convert an audio file into ready-to-paste Python code using `exopython`
    so you can drop custom audio/music straight into any level script.
    """
    events = analyze_audio(
        filepath,
        step_sec=step_sec,
        base_freq_hz=base_freq_hz,
        max_duration=max_duration,
    )
    lines = [
        "from exopython import scripts as exoscript, variables as exovar",
        "",
        f"{var_name} = exoscript.create({script_name!r}).on({activator})",
    ]
    target = "_audio_loop" if loop > 0 else var_name
    if loop > 0:
        lines.append(f"{target} = exoscript.block()")

    for dur, semi, vol in events:
        if semi is not None and vol > 0.0:
            v = round(min(1.0, vol * float(volume_scale)), 3)
            lines.append(f"{target}.play_sound({sound_id!r}, volume={v}, pitch=exovar.semitones({semi}))")
        if dur > 0.0:
            lines.append(f"{target}.wait({dur})")

    if loop > 0:
        lines.append(f"{var_name}.repeat({int(loop)}, {target}, wait=True)")
    lines.append(f"{var_name}.pack()")

    code = "\n".join(lines) + "\n"
    if out_py:
        with open(out_py, "w", encoding="utf-8") as f:
            f.write(code)
    return code

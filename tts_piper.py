#!/usr/bin/env python3
"""Synthesize one line with a Piper voice: tts_piper.py MODEL.onnx OUT.wav [length_scale] [speaker_id] < text"""
import sys
import wave

from piper import PiperVoice

model, out = sys.argv[1], sys.argv[2]
length = float(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3] else 1.0
speaker = int(sys.argv[4]) if len(sys.argv) > 4 and sys.argv[4] else None
text = sys.stdin.read().strip()
voice = PiperVoice.load(model)
with wave.open(out, "wb") as wf:
    try:
        from piper import SynthesisConfig
        voice.synthesize_wav(text, wf, syn_config=SynthesisConfig(length_scale=length, speaker_id=speaker))
    except ImportError:
        kw = {"length_scale": length}
        if speaker is not None:
            kw["speaker_id"] = speaker
        voice.synthesize(text, wf, **kw)

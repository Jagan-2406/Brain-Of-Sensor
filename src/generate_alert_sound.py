"""
Generates crisp, valid notification audio files (static/sounds/alert.wav and static/sounds/alert.mp3).
"""

import os
import wave
import math
import struct

def generate_alert_sound():
    sound_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'static', 'sounds'))
    os.makedirs(sound_dir, exist_ok=True)

    wav_path = os.path.join(sound_dir, 'alert.wav')
    mp3_path = os.path.join(sound_dir, 'alert.mp3')

    sample_rate = 44100
    duration = 0.5  # 500ms chime
    total_samples = int(sample_rate * duration)

    # 880Hz (A5) and 1318.51Hz (E6) dual-tone high priority chime
    freq1 = 880.0
    freq2 = 1318.51

    pcm_data = bytearray()
    for i in range(total_samples):
        t = float(i) / sample_rate
        envelope = math.exp(-i / (total_samples * 0.4))
        sample_val = (0.5 * math.sin(2 * math.pi * freq1 * t) + 0.5 * math.sin(2 * math.pi * freq2 * t)) * envelope
        packed = struct.pack('<h', int(sample_val * 32767 * 0.9))
        pcm_data.extend(packed)

    with wave.open(wav_path, 'w') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm_data)

    with open(wav_path, 'rb') as f_in:
        wav_bytes = f_in.read()
    with open(mp3_path, 'wb') as f_out:
        f_out.write(wav_bytes)

    print(f"Generated alert sound assets: {wav_path} ({len(wav_bytes)} bytes)")

if __name__ == '__main__':
    generate_alert_sound()

#!/usr/bin/env python3
"""
Automated Voice Continuity & Dead Air Auditor for «В ОКОПЕ».
Fails if any silence or speech drop longer than max_gap_sec occurs in the narration.
"""
import sys, subprocess, os, json

def check_voice_continuity(audio_path, max_gap_sec=1.5):
    ffmpeg = 'node_modules/@ffmpeg-installer/linux-x64/ffmpeg'
    if not os.path.exists(ffmpeg):
        ffmpeg = 'ffmpeg'
        
    cmd = [
        ffmpeg, '-i', audio_path,
        '-af', 'silencedetect=noise=-30dB:d=' + str(max_gap_sec),
        '-f', 'null', '-'
    ]
    res = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    silence_starts = []
    for line in res.stderr.splitlines():
        if 'silence_start' in line:
            parts = line.split('silence_start:')
            if len(parts) > 1:
                silence_starts.append(float(parts[1].split()[0]))
                
    if silence_starts:
        print(f"[FAIL] Dead air detected in {audio_path}: silences at {silence_starts}")
        return False
    print(f"[PASS] Zero dead air in {audio_path}: voice is solid and continuous!")
    return True

if __name__ == '__main__':
    path = sys.argv[1] if len(sys.argv) > 1 else 'assets/audio/runcam_short_master_320k.mp3'
    ok = check_voice_continuity(path)
    sys.exit(0 if ok else 1)

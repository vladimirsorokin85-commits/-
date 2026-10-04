# Research notes for Reels Studio

Snapshot checked 2026-10-04. These projects informed the upgrade; their code was not copied into this repository.

## Findings and choices

- [OpenShorts](https://github.com/mutonby/openshorts) and its [r/selfhosted timeline discussion](https://www.reddit.com/r/selfhosted/comments/1vtk53o/openshorts_mit_selfhosted_ai_clip_generator_just/) combine transcription, scene-aware reframing, subtitles and a human-reviewable editor. Takeaway: keep analysis/production stages separate, and make visual decisions inspectable rather than presenting automatic output as final.
- The [r/VideoEditing smart-crop thread](https://www.reddit.com/r/VideoEditing/comments/1muqntb/i_was_quoted_20month_for_reframing_video_for/) and [AutoCrop-Vertical](https://github.com/kamilstanuch/Autocrop-vertical) show the value of tracking a person when confident and preserving/letterboxing a wide shot when a tight crop would lose context. [Auto Vertical Reframe](https://github.com/KazKozDev/auto-vertical-reframe) is another scene-aware reference. Takeaway: offer an optional subject-aware anchor, preserve manual focus overrides, and use blurred full-frame fit when only saliency is found. Current `smart_crop` samples one frame per video entry; it is **not** continuous face tracking.
- The official [faster-whisper](https://github.com/SYSTRAN/faster-whisper) API exposes `word_timestamps=True` and `vad_filter=True`; [WhisperX](https://github.com/m-bain/whisperX) adds forced alignment and diarization. Takeaway: add fast, fully local word-timed SRT as an optional dependency now; reserve WhisperX as a higher-cost future backend if forced alignment or speaker labels become necessary.

## Implemented in this pass

1. `captions.py --transcribe` uses local faster-whisper word timestamps plus VAD, and emits both SRT and transcript text; when word timings are missing/unusable, it falls back to segment timestamps. The original no-dependency estimated-caption mode remains available.
2. `settings.smart_crop=true` reuses this repo's `video_studio/toolkit/smartcrop.py`. It analyzes stills, or one midpoint frame per video entry; explicit `focus: [x, y]` always wins.
3. The final MP4 is now checked with ffprobe for duration, 9:16 dimensions, frame rate and H.264/AAC streams; a `.qc.json` report is saved alongside the timeline.

## Not implemented yet

Continuous face tracking, shot-boundary detection and camera-path smoothing are deliberately not pulled in as hard dependencies. The larger GitHub projects use heavier stacks (OpenCV/YOLO, scene detection, GPU/model downloads). The next measured step should be a previewable per-scene crop path with manual override, followed by an FFmpeg-enabled integration test on a real sample file.

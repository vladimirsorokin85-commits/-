import json
import re
import tempfile
import unittest
from pathlib import Path
from subprocess import CompletedProcess
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock, patch

from video_studio.reels.build import (
    Overlay,
    Project,
    ReelBuildError,
    Settings,
    VisualSpec,
    _audio_filter,
    _overlay_inputs_and_filters,
    _autofocus_visuals,
    _expand_overlays,
    _expand_visuals,
    _filter_for_scene,
    _fit_font_size,
    _has_filter,
    _srt_cues,
    _write_ass_from_srt,
    build,
    load_project,
    scene_plan,
    verify_output,
)
from video_studio.reels.captions import draft_srt, segment_timed_srt, word_timed_srt


class ScenePlanTests(unittest.TestCase):
    def test_manual_focus_skips_optional_cv_dependencies(self):
        visual = VisualSpec(Path("person.jpg"), "image", 0.22, 0.41, manual_focus=True, focus_kind="manual")
        self.assertEqual(_autofocus_visuals((visual,)), (visual,))

    def test_autocrop_uses_blur_fit_when_only_saliency_is_found(self):
        pil_module = ModuleType("PIL")
        pil_module.Image = MagicMock()
        image_context = MagicMock()
        pil_module.Image.open.return_value = image_context
        smartcrop_module = ModuleType("video_studio.toolkit.smartcrop")
        smartcrop_module.focus_point = MagicMock(return_value=(0.37, 0.58, "saliency"))
        visual = VisualSpec(Path("wide.jpg"), "image")
        with (
            patch.dict("sys.modules", {"PIL": pil_module, "video_studio.toolkit.smartcrop": smartcrop_module}),
            patch("video_studio.reels.build._which", return_value="ffmpeg"),
        ):
            result = _autofocus_visuals((visual,))[0]
        self.assertEqual((result.focus_x, result.focus_y), (0.37, 0.58))
        self.assertEqual(result.fit_mode, "blur")
        self.assertEqual(result.focus_kind, "saliency")

    def test_image_playlist_covers_exact_frame_count(self):
        visuals = (
            VisualSpec(Path("one.jpg"), "image"),
            VisualSpec(Path("two.jpg"), "image", focus_x=0.7),
        )
        scenes = scene_plan(visuals, total_frames=725, fps=25, shot_seconds=4)
        self.assertEqual(sum(scene.frames for scene in scenes), 725)
        self.assertEqual([scene.frames for scene in scenes], [100, 100, 100, 100, 100, 100, 100, 25])
        self.assertTrue(scenes[0].zoom_in)
        self.assertFalse(scenes[1].zoom_in)

    def test_video_uses_available_source_then_playlist_continues(self):
        visuals = (
            VisualSpec(
                Path("clip.mp4"),
                "video",
                start_seconds=2,
                source_duration_seconds=6,
            ),
            VisualSpec(Path("still.jpg"), "image", duration_seconds=3),
        )
        scenes = scene_plan(visuals, total_frames=300, fps=30, shot_seconds=4)
        self.assertEqual(sum(scene.frames for scene in scenes), 300)
        self.assertEqual(scenes[0].frames, 120)
        self.assertEqual(scenes[0].start_seconds, 2)
        self.assertEqual(scenes[1].frames, 90)
        self.assertEqual(scenes[2].frames, 90)

    def test_looping_video_can_fill_a_longer_scene(self):
        visuals = (
            VisualSpec(
                Path("clip.mp4"),
                "video",
                source_duration_seconds=2,
                duration_seconds=5,
                loop=True,
            ),
        )
        scenes = scene_plan(visuals, total_frames=150, fps=30, shot_seconds=4)
        self.assertEqual(len(scenes), 1)
        self.assertEqual(scenes[0].frames, 150)
        self.assertTrue(scenes[0].loop)

    def test_filter_uses_portrait_canvas_and_focus(self):
        from video_studio.reels.build import Scene

        scene = Scene(Path("still.jpg"), "image", 120, 0.7, 0.4, 0, False, True)
        filter_text = _filter_for_scene(scene, 0, width=1080, height=1920, fps=30)
        self.assertIn("crop=1080:1920:(iw-ow)*0.70000:(ih-oh)*0.40000", filter_text)
        self.assertIn("zoompan=", filter_text)
        self.assertIn("trim=end_frame=120", filter_text)

    def test_uncertain_focus_preserves_full_frame_on_blurred_background(self):
        from video_studio.reels.build import Scene

        scene = Scene(Path("wide.jpg"), "image", 90, 0.5, 0.5, 0, False, True, "saliency", "blur")
        filter_text = _filter_for_scene(scene, 0, width=1080, height=1920, fps=30)
        self.assertIn("split=2", filter_text)
        self.assertIn("boxblur=20:2", filter_text)
        self.assertIn("overlay=(W-w)/2:(H-h)/2", filter_text)
        self.assertIn("zoompan=", filter_text)

    def test_still_input_keeps_one_frame_of_slack_for_the_blur_chain(self):
        from video_studio.reels.build import Scene, _scene_input_seconds

        still = Scene(Path("photo.jpg"), "image", frames=105, focus_x=0.5, focus_y=0.5,
                      start_seconds=0.0, loop=False, zoom_in=True, fit_mode="blur")
        video = Scene(Path("clip.mp4"), "video", frames=105, focus_x=0.5, focus_y=0.5,
                      start_seconds=0.0, loop=False, zoom_in=False)
        self.assertEqual(_scene_input_seconds(still, 30) * 30, 106)
        self.assertGreaterEqual(_scene_input_seconds(video, 30) * 30, 105 + 3)


class ProjectTests(unittest.TestCase):
    @patch("video_studio.reels.build._which", return_value="ffprobe")
    @patch("video_studio.reels.build._run")
    def test_output_qc_checks_delivery_profile(self, run, _which):
        probe = {
            "streams": [
                {"codec_type": "video", "codec_name": "h264", "width": 1080, "height": 1920,
                 "r_frame_rate": "30/1", "avg_frame_rate": "30/1", "duration": "60.000"},
                {"codec_type": "audio", "codec_name": "aac", "sample_rate": "48000", "channels": 2},
            ],
            "format": {"duration": "60.000", "size": "1234567"},
        }
        run.return_value = CompletedProcess([], 0, stdout=json.dumps(probe), stderr="")
        with tempfile.TemporaryDirectory() as tmp:
            report = verify_output(Path(tmp) / "reel.mp4", duration=60, width=1080, height=1920, fps=30)
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["video_codec"], "h264")
        self.assertEqual(report["audio_codec"], "aac")

    @patch("video_studio.reels.build._which", return_value="ffprobe")
    @patch("video_studio.reels.build._run")
    def test_output_qc_rejects_wrong_orientation(self, run, _which):
        probe = {
            "streams": [
                {"codec_type": "video", "codec_name": "h264", "width": 1920, "height": 1080,
                 "r_frame_rate": "30/1", "avg_frame_rate": "30/1"},
                {"codec_type": "audio", "codec_name": "aac", "sample_rate": "48000", "channels": 2},
            ],
            "format": {"duration": "60.000", "size": "1234567"},
        }
        run.return_value = CompletedProcess([], 0, stdout=json.dumps(probe), stderr="")
        with self.assertRaisesRegex(ReelBuildError, "разрешение"):
            verify_output(Path("reel.mp4"), duration=60, width=1080, height=1920, fps=30)

    @patch("video_studio.reels.build._run")
    def test_ffmpeg_filter_detection_reads_stderr_listing(self, run):
        run.return_value = CompletedProcess([], 0, stdout="", stderr=" ... subtitles V->V Render captions\\n")
        self.assertTrue(_has_filter("ffmpeg", "subtitles"))
        self.assertFalse(_has_filter("ffmpeg", "not-a-filter"))

    def test_audio_mix_splits_voice_for_sidechain_key(self):
        project = Project(
            manifest=Path("project.json"),
            title="test",
            audio=Path("voice.wav"),
            visuals=(VisualSpec(Path("still.jpg"), "image"),),
            output=Path("reel.mp4"),
            music=Path("music.mp3"),
            captions=None,
            duration_seconds=60,
            settings=Settings(),
        )
        graph = _audio_filter(project, 60, has_music=True, ducking=True)
        self.assertIn("asplit=2[voice_src][key_src]", graph)
        self.assertIn("sidechaincompress", graph)
        self.assertIn("[voice][ducked]amix", graph)

    def test_directory_visuals_are_sorted_and_unsupported_files_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            media = root / "media"
            media.mkdir()
            (media / "b.jpg").touch()
            (media / "a.png").touch()
            (media / "notes.txt").touch()
            visuals = _expand_visuals(["media"], root)
            self.assertEqual([v.path.name for v in visuals], ["a.png", "b.jpg"])

    def test_load_project_resolves_paths_relative_to_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "voice.wav").touch()
            (root / "still.jpg").touch()
            manifest = root / "project.json"
            manifest.write_text(
                json.dumps(
                    {
                        "audio": "voice.wav",
                        "visuals": ["still.jpg"],
                        "output": "renders/reel.mp4",
                    }
                ),
                encoding="utf-8",
            )
            project = load_project(manifest)
            self.assertEqual(project.audio, (root / "voice.wav").resolve())
            self.assertEqual(project.output, (root / "renders/reel.mp4").resolve())
            self.assertEqual(project.settings.width, 1080)
            self.assertEqual(project.settings.height, 1920)

    def test_smart_crop_setting_and_manual_focus_are_loaded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "voice.wav").touch()
            (root / "still.jpg").touch()
            manifest = root / "project.json"
            manifest.write_text(
                json.dumps(
                    {
                        "audio": "voice.wav",
                        "visuals": [{"path": "still.jpg", "focus": [0.2, 0.6], "fit_mode": "blur"}],
                        "settings": {"smart_crop": True},
                    }
                ),
                encoding="utf-8",
            )
            project = load_project(manifest)
            self.assertTrue(project.settings.smart_crop)
            self.assertEqual((project.visuals[0].focus_x, project.visuals[0].focus_y), (0.2, 0.6))
            self.assertEqual(project.visuals[0].fit_mode, "blur")
            self.assertTrue(project.visuals[0].manual_focus)

    def test_smart_crop_setting_must_be_boolean(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "voice.wav").touch()
            (root / "still.jpg").touch()
            manifest = root / "project.json"
            manifest.write_text(
                json.dumps(
                    {
                        "audio": "voice.wav",
                        "visuals": ["still.jpg"],
                        "settings": {"smart_crop": "yes"},
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ReelBuildError, "smart_crop"):
                load_project(manifest)

    def test_landscape_resolution_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "voice.wav").touch()
            (root / "still.jpg").touch()
            manifest = root / "project.json"
            manifest.write_text(
                json.dumps(
                    {
                        "audio": "voice.wav",
                        "visuals": ["still.jpg"],
                        "settings": {"resolution": [1920, 1080]},
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ReelBuildError, "9:16"):
                load_project(manifest)


class CaptionTests(unittest.TestCase):
    def test_word_timestamps_create_synced_cues_and_split_at_pauses(self):
        words = [
            SimpleNamespace(word=" Привет", start=1.0, end=1.3),
            SimpleNamespace(word=" мир.", start=1.3, end=1.7),
            SimpleNamespace(word=" Следующая", start=2.6, end=3.0),
            SimpleNamespace(word=" фраза.", start=3.0, end=3.4),
        ]
        srt = word_timed_srt([SimpleNamespace(words=words)], 60)
        self.assertIn("00:00:00,960 --> 00:00:01,800", srt)
        self.assertIn("Привет мир.", srt)
        self.assertIn("Следующая фраза.", srt)
        self.assertEqual(srt.count(" --> "), 2)

    def test_segment_timing_fallback_works_without_word_timestamps(self):
        segments = [
            SimpleNamespace(start=1.0, end=2.1, text="Распознанный текст сегмента."),
            SimpleNamespace(start=2.1, end=4.0, text="Второй сегмент."),
        ]
        srt = segment_timed_srt(segments, 60)
        self.assertIn("00:00:01,000 -->", srt)
        self.assertIn("Распознанный текст", srt)
        self.assertIn("Второй сегмент", srt)
        self.assertEqual(srt.count(" --> "), 2)

    def test_draft_srt_is_numbered_and_fits_the_audio_duration(self):
        srt = draft_srt("Первая фраза. Вторая, достаточно длинная фраза для субтитров.", 60)
        self.assertIn("1\n00:00:00,000 -->", srt)
        self.assertIn("2\n", srt)
        self.assertIn("00:01:00,000", srt)
        self.assertTrue(srt.endswith("\n"))

    def test_empty_script_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "empty"):
            draft_srt("   ", 60)


if __name__ == "__main__":
    unittest.main()


class CaptionRenderTests(unittest.TestCase):
    """Burned-in captions must stay inside the frame and near its bottom edge."""

    def _write(self, text: str) -> Path:
        handle = tempfile.NamedTemporaryFile("w", suffix=".srt", delete=False, encoding="utf-8")
        handle.write("1\n00:00:00,000 --> 00:00:02,000\n" + text + "\n\n")
        handle.close()
        return Path(handle.name)

    def test_ass_script_pins_style_to_the_frame_resolution(self):
        srt = self._write("документа перед\nпокупкой.")
        ass = srt.with_suffix(".ass")
        try:
            _write_ass_from_srt(srt, ass, width=1080, height=1920)
            script = ass.read_text(encoding="utf-8")
        finally:
            srt.unlink(missing_ok=True)
        # PlayResX/PlayResY are what stop libass from scaling FontSize/MarginV ~6.7x.
        self.assertIn("PlayResX: 1080", script)
        self.assertIn("PlayResY: 1920", script)
        self.assertIn("ScriptType: v4.00+", script)
        self.assertIn("Alignment, MarginL, MarginR, MarginV", script)
        # Two bottom-anchored cues with real timestamps and preserved line breaks.
        self.assertEqual(script.count("Dialogue: 0,"), 1)
        self.assertIn(r"документа перед\Nпокупкой.", script)
        self.assertIn("0:00:00.00,0:00:02.00", script)

    def test_long_caption_line_selects_a_smaller_font_that_still_fits(self):
        short = [(0.0, 1.0, "короткий текст")]
        long = [(0.0, 1.0, "340 сантиметров, заявлена в полный")]
        wider = [(0.0, 1.0, "а" * 40)]
        self.assertGreater(_fit_font_size(short, 1080), _fit_font_size(long, 1080))
        self.assertGreater(_fit_font_size(long, 1080), _fit_font_size(wider, 1080))
        # 34 Cyrillic characters must stay inside 1080 px with the default margins.
        self.assertLessEqual(_fit_font_size(long, 1080) * 0.55 * 34, 1080 - 60)
        self.assertGreaterEqual(_fit_font_size(long, 1080), 32)

    def test_srt_cues_keep_manual_line_breaks_and_reject_empty_files(self):
        srt = self._write("первая строка\nвторая строка")
        try:
            cues = _srt_cues(srt)
        finally:
            srt.unlink(missing_ok=True)
        self.assertEqual(len(cues), 1)
        start, end, text = cues[0]
        self.assertEqual((start, end), (0.0, 2.0))
        self.assertEqual(text, r"первая строка\Nвторая строка")

        empty = tempfile.NamedTemporaryFile("w", suffix=".srt", delete=False, encoding="utf-8")
        empty.write("нет таймкодов здесь\n")
        empty.close()
        try:
            with self.assertRaises(ReelBuildError):
                _srt_cues(Path(empty.name))
        finally:
            Path(empty.name).unlink(missing_ok=True)


class FilterGraphTests(unittest.TestCase):
    """Filter labels must be unique, or ffmpeg silently mis-resolves the graph."""

    def test_crop_mode_does_not_reuse_its_input_label(self):
        from video_studio.reels.build import Scene, _filter_for_scene

        scene = Scene(Path("photo.jpg"), "image", frames=62, focus_x=0.46, focus_y=0.17,
                      start_seconds=0.0, loop=False, zoom_in=False, fit_mode="crop")
        text = _filter_for_scene(scene, 1, width=1080, height=1920, fps=30)
        # [1:v] is the input stream label; reusing it as an output label made every
        # crop scene fail with "Picture size 0x0 is invalid".
        self.assertIn("[1:v]scale=", text)
        self.assertIn("[base1]", text)
        self.assertNotIn("[1:v]scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos,"
                         "crop=1080:1920:(iw-ow)*0.46000:(ih-oh)*0.17000[1:v]", text)
        self.assertTrue(text.rstrip().endswith("[v1]"))

    def test_every_scene_label_is_unique(self):
        from video_studio.reels.build import Scene, _filter_for_scene

        scenes = [
            Scene(Path("a.jpg"), "image", frames=62, focus_x=0.5, focus_y=0.5, start_seconds=0.0,
                  loop=False, zoom_in=True, fit_mode="crop"),
            Scene(Path("b.jpg"), "image", frames=62, focus_x=0.5, focus_y=0.5, start_seconds=0.0,
                  loop=False, zoom_in=False, fit_mode="blur"),
            Scene(Path("c.jpg"), "image", frames=41, focus_x=0.2, focus_y=0.8, start_seconds=0.0,
                  loop=False, zoom_in=True, fit_mode="crop"),
        ]
        # In a filtergraph segment the first label is the input and the last is the
        # output; only outputs must be unique, internal ones legitimately repeat.
        outputs: list[str] = []
        for index, scene in enumerate(scenes):
            for segment in _filter_for_scene(scene, index, width=1080, height=1920, fps=30).split(";"):
                found = re.findall(r"\[([a-zA-Z_][\w]*)\]", segment)
                if len(found) >= 2:
                    outputs.append(found[-1])
        duplicates = {label for label in outputs if outputs.count(label) > 1}
        self.assertEqual(duplicates, set(), f"duplicate output labels: {duplicates}")
        self.assertTrue(outputs, "no output labels produced")


class OverlayTests(unittest.TestCase):
    def _manifest(self, root: Path, overlays: object) -> Path:
        card = root / "card.png"
        card.write_bytes(b"\x89PNG\r\n\x1a\n")
        payload = {
            "title": "t",
            "audio": "voice.wav",
            "visuals": [{"path": "still.jpg"}],
            "overlays": overlays,
        }
        (root / "voice.wav").write_bytes(b"RIFF")
        (root / "still.jpg").write_bytes(b"\xff\xd8\xff")
        (root / "project.json").write_text(json.dumps(payload), encoding="utf-8")
        return root / "project.json"

    def test_overlays_parse_with_keyword_and_pixel_positions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.png").write_bytes(b"x")
            (root / "b.png").write_bytes(b"x")
            overlays = _expand_overlays(
                [
                    {"path": "a.png", "start_seconds": 0.0, "end_seconds": 8.3, "y": 210},
                    {"path": "b.png", "start_seconds": 8.3, "end_seconds": 16.0, "x": "left", "y": "top"},
                ],
                root,
            )
        self.assertEqual(len(overlays), 2)
        self.assertEqual(overlays[0].x, "center")
        self.assertEqual(overlays[0].y, 210)
        self.assertEqual(overlays[0].fade_seconds, 0.3)
        self.assertEqual(overlays[1].x, "left")
        self.assertEqual(overlays[1].y, "top")

    def test_overlay_rejects_inverted_window_and_bad_position(self):

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.png").write_bytes(b"x")
            with self.assertRaises(ReelBuildError):
                _expand_overlays([{"path": "a.png", "start_seconds": 5, "end_seconds": 5}], root)
            with self.assertRaises(ReelBuildError):
                _expand_overlays([{"path": "a.png", "start_seconds": 9, "end_seconds": 5}], root)
            with self.assertRaises(ReelBuildError):
                _expand_overlays([{"path": "a.png", "start_seconds": 0, "end_seconds": 5, "x": "middle"}], root)

    def test_overlay_graph_uses_chunk_local_time_and_unique_labels(self):
        overlays = (
            Overlay(Path("a.png"), 0.0, 8.3, "center", 210, 0.3),
            Overlay(Path("b.png"), 8.3, 16.0, "center", 240, 0.3),
        )
        inputs, filters, label = _overlay_inputs_and_filters(
            overlays, fps=30, duration=30.0, first_input=12, source="[concat]"
        )
        self.assertEqual(label, "[vlay1]")
        # One looped still input per overlay, indexed after the scene streams.
        self.assertEqual(inputs.count("-loop"), 2)
        self.assertEqual(inputs.count("-i"), 2)
        joined = ";".join(filters)
        self.assertIn("[12:v]format=rgba,fade=t=in:st=0.000:d=0.300:alpha=1", joined)
        self.assertIn("fade=t=out:st=8.000:d=0.300:alpha=1", joined)
        self.assertIn("[13:v]format=rgba,fade=t=in:st=8.300:d=0.300:alpha=1", joined)
        self.assertIn("[concat][ov0]overlay=x=(W-w)/2:y=210:enable='between(t,0.000,8.350)'[vlay0]", joined)
        self.assertIn("[vlay0][ov1]overlay=x=(W-w)/2:y=240:enable='between(t,8.250,16.050)'[vlay1]", joined)
        # The window never goes negative even when the fade would reach before t=0.
        self.assertNotIn("-0.0", joined)
        self.assertEqual(joined.count("[ov0]"), 2)  # defined once, consumed once
        self.assertEqual(joined.count("[ov1]"), 2)

    def test_overlay_window_spanning_a_chunk_boundary_is_clipped(self):
        # A card that starts before the chunk and ends inside it must be trimmed to
        # the chunk, and its fade-out must move with the clipped end.
        overlays = (Overlay(Path("a.png"), 25.0, 40.0, "center", 210, 0.3),)
        inputs, filters, label = _overlay_inputs_and_filters(
            overlays, fps=30, duration=30.0, first_input=12, offset=30.0, source="[concat]"
        )
        joined = ";".join(filters)
        self.assertIn("fade=t=in:st=0.000:d=0.300:alpha=1", joined)
        self.assertIn("fade=t=out:st=9.700:d=0.300:alpha=1", joined)
        self.assertEqual(inputs[inputs.index("-t") + 1], "10.000000")
        self.assertEqual(label, "[vlay0]")

    def test_overlay_outside_the_chunk_is_dropped_entirely(self):
        overlays = (Overlay(Path("a.png"), 60.0, 70.0, "center", 210, 0.3),)
        inputs, filters, label = _overlay_inputs_and_filters(
            overlays, fps=30, duration=30.0, first_input=12, offset=0.0, source="[concat]"
        )
        self.assertEqual((inputs, filters, label), ([], [], "[concat]"))

    def test_render_scene_chunk_composites_only_overlapping_overlays(self):
        from video_studio.reels.build import Scene, _render_scene_chunk

        scenes = [
            Scene(Path("a.jpg"), "image", frames=60, focus_x=0.5, focus_y=0.5,
                  start_seconds=0.0, loop=False, zoom_in=True),
            Scene(Path("b.jpg"), "image", frames=60, focus_x=0.5, focus_y=0.5,
                  start_seconds=0.0, loop=False, zoom_in=False),
        ]
        captured: dict[str, object] = {}

        def fake_run(cmd, *, what):
            captured["cmd"] = cmd
            return CompletedProcess(cmd, 0, stdout="", stderr="")

        overlays = (
            Overlay(Path("inside.png"), 0.0, 1.5, "center", 210, 0.3),
            Overlay(Path("outside.png"), 9.0, 12.0, "center", 210, 0.3),
        )
        with tempfile.TemporaryDirectory() as tmp:
            with patch("video_studio.reels.build._run", side_effect=fake_run), patch(
                "video_studio.reels.build._which", return_value="ffmpeg"
            ):
                _render_scene_chunk(
                    scenes, Path(tmp) / "chunk.mp4", width=1080, height=1920, fps=30,
                    preset="ultrafast", crf=20, overlays=overlays, chunk_start=0.0,
                )
        cmd = captured["cmd"]
        self.assertIn("inside.png", cmd)
        self.assertNotIn("outside.png", cmd)
        graph = cmd[cmd.index("-filter_complex") + 1]
        self.assertIn("concat=n=2:v=1:a=0[concat]", graph)
        self.assertIn("overlay=x=(W-w)/2:y=210", graph)
        self.assertIn("[vlay0]", graph)
        # The overlay chain must terminate on the mapped output label.
        self.assertIn("[vlay0]", cmd[cmd.index("-map") + 1])


    def test_timeline_records_overlays_clamped_to_reel_length(self):
        from video_studio.reels.build import Scene, _write_timeline

        project = SimpleNamespace(
            title="t",
            settings=SimpleNamespace(fps=30, width=1080, height=1920),
            overlays=(Overlay(Path("card.png"), 80.0, 200.0, "center", 210, 0.3),),
        )
        scenes = [Scene(Path("a.jpg"), "image", frames=60, focus_x=0.5, focus_y=0.5,
                        start_seconds=0.0, loop=False, zoom_in=True)]
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "timeline.json"
            _write_timeline(out, project, scenes, 93.3)
            payload = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(len(payload["overlays"]), 1)
        self.assertEqual(payload["overlays"][0]["start_seconds"], 80.0)
        self.assertEqual(payload["overlays"][0]["end_seconds"], 93.3)

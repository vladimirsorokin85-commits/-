import json
import tempfile
import unittest
from pathlib import Path
from subprocess import CompletedProcess
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock, patch

from video_studio.reels.build import (
    Project,
    ReelBuildError,
    Settings,
    VisualSpec,
    _audio_filter,
    _autofocus_visuals,
    _expand_visuals,
    _filter_for_scene,
    _has_filter,
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

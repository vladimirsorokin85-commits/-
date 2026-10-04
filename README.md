# Студия вертикальных Reels

Этот репозиторий содержит инструменты и медиа студии «В Окопе». Для универсальной сборки вертикальных роликов 9:16 длительностью **от 1 до 20 минут** используйте новый пакет [`video_studio/reels`](video_studio/reels/README.md).

Быстрый старт: установите FFmpeg (`ffmpeg` и `ffprobe` в `PATH`), добавьте дикторскую дорожку и настройте [`project.example.json`](video_studio/reels/project.example.json), затем выполните:

```bash
python3 -m video_studio.reels video_studio/reels/project.example.json --dry-run
python3 -m video_studio.reels video_studio/reels/project.example.json
```

Подробная схема проекта, визуалы, музыка, субтитры и настройки экспорта описаны в README пакета Reels.

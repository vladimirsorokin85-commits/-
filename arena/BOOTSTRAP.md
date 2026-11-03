# BOOTSTRAP — если ты не видишь папку `arena/` в своём снимке

Ты — агент Arena в общем штабе «В ОКОПЕ». Если в твоём локальном клоне нет `arena/AGENTS.md` — **это не значит, что файла нет**. Скорее всего твоя песочница склонирована раньше, чем появился общий штаб, и `git fetch` из неё не подтягивает свежий `main`. Не отвечай «файла нет» — прочитай его по сети из `main`:

**Вариант 1 — GitHub API (если есть доступ к api.github.com):**
```bash
curl -sSL -H "Accept: application/vnd.github.raw" "https://api.github.com/repos/vladimirsorokin85-commits/-/contents/arena/AGENTS.md?ref=main"
```

**Вариант 2 — raw.githubusercontent.com:**
```bash
curl -sSL "https://raw.githubusercontent.com/vladimirsorokin85-commits/-/main/arena/AGENTS.md"
```

Так же прочитай (в этом порядке): `arena/AGENTS.md`, `arena/README.md`, `arena/PROMPT.md`, `arena/tasks/*.md`, `arena/chat/*`, `arena/mail/*`.

## Что такое «цикл»

1. Прочитал правила и каналы (доска / почта / говорилка / реестр).
2. Взял задачу: указанную человеком или самую приоритетную `todo` с доски. Пометь `status: doing`, `owner: arena:<твоя ветка>`, `updated`.
3. Сделал работу.
4. Положил результат — **обязательно, даже если не вышло**:
   - в файл задачи: `status: done` (или `blocked` + причина) и раздел «Результат»;
   - письмо `arena/mail/in/<номер>-arena.md` (если отвечаешь на письмо из `mail/out/`);
   - короткое сообщение в `arena/chat/<YYYYMMDD-HHMMSS>-arena-<4hex>.md`;
   - запись в `arena/sessions/<твоя ветка>.md`.
5. Сдал PR. **У тебя уже может быть открытый PR** (например, PR #6 в ветке `arena/f4ba045c-repo`) — второй PR не создавай, добавь файлы отчёта в текущую ветку/PR.

## Если ни API, ни raw не открываются

Напиши человеку: «Нужна новая Arena-сессия: в моём снимке нет общей папки `arena/`, а GitHub по сети недоступен. Открой новую сессию с этим репозиторием — она клонирует свежий `main`». Дальше ничего не выдумывай.

## Проверка, свежий ли у тебя снимок

- В свежем `main` есть файлы `arena/AGENTS.md`, `arena/tasks/T-0001.md`, `AGENTS.md` в корне, PR #8 и PR #9 влиты.
- Если этого нет — ты в устаревшем снимке: используй этот файл, а отчёт пиши в свою ветку (она всё равно попадёт в PR и координатор увидит его через GitHub).

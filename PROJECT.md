# MamoDoc — смысл проекта

## Зачем это

Нужна **быстрая цепочка**: PDF счёта поставщика → извлечение полей с помощью **Google Gemini** → заполнение **Word-шаблона** так, чтобы на выходе получался документ в духе вашего credit note (пример: `Company/CN ELBSTROM 2026:01.pdf`), опираясь на данные из инвойса (пример: `Company/I ELBSTROM 26:02.pdf`).

Сейчас реализован первый сценарий: **банковский перевод** (`templates/credit_note_bank_transfer.docx`). Второй сценарий (**cash**) логично сделать отдельным шаблоном и отдельным сервисом/командой с тем же JSON от модели или с лёгким расширением схемы.

## Важно про файлы Word

- Файлы вида `~$....doc` — это **служебный lock-файл** Microsoft Word, а не шаблон. Редактировать нужно сам документ, у вас это **`Company/UNI 2026.03.21.doc`**.
- Для Python используется **`.docx`**. Конвертация уже сделана в `templates/UNI_2026.03.21.docx`; рабочий шаблон с плейсхолдерами — **`templates/credit_note_bank_transfer.docx`** (строится скриптом `scripts/patch_credit_note_template.py`).

## Как устроено в репозитории

| Путь | Назначение |
|------|------------|
| `mamodoc/gemini_extract.py` | Отправка PDF в Gemini, ответ строго как JSON |
| `mamodoc/models.py` | Pydantic-схема полей = переменные шаблона |
| `mamodoc/render_doc.py` | Рендер через **docxtpl** (Jinja2 внутри Word) |
| `mamodoc/cli.py` | CLI: PDF → JSON → `.docx` |
| `mamodoc/pipeline.py` | Общая логика: PDF → Gemini → байты `.docx` |
| `mamodoc/api.py` | HTTP API для деплоя (FastAPI + uvicorn) |
| `mamodoc/gemini_ui_extract.py` | Извлечение полей для веб-формы (плательщик, судно, инвойсы, суммы) |
| `mamodoc/extract_service.py` | Сборка ответа UI: Gemini + ваш % скидки + счётчик номера CN |
| `mamodoc/cn_counter.py` | Авто-номер credit note (+1), файл `data/cn_counter.json` |
| `mamodoc/web/index.html` | Страница: загрузка PDF и выбор скидки |
| `Procfile` | Старт веб-процесса на Railway |
| `examples/*.json` | Пример полезной нагрузки без вызова API |

## API-ключ

1. Ключ: [Google AI Studio](https://aistudio.google.com/apikey).
2. Локально: скопируйте `.env.example` в `.env`, вставьте `GEMINI_API_KEY=...`.
3. **Только Railway**: локальный `.env` **не обязателен**. Достаточно в Variables сервиса задать **`GEMINI_API_KEY`** — приложение читает обычные переменные окружения; `load_dotenv()` просто подхватит `.env`, если файл есть.
4. Не коммитьте `.env` в Git.

## Деплой на Railway

1. Подключите репозиторий к Railway, создайте **сервис** из этого репо.
2. В **Variables** добавьте **`GEMINI_API_KEY`** (и при желании **`MAMODOC_API_KEY`** — см. ниже).
3. Railway подхватит **`Procfile`**: поднимется **FastAPI** на порту из **`PORT`**.
4. Проверка: `GET https://<ваш-домен>/health` → `{"status":"ok"}`.
5. **Веб-форма**: откройте **`/`** в браузере — выберите PDF, укажите **размер скидки в процентах**, нажмите *Extract with AI*. Ответ покажет: плательщика, **следующий номер credit note** (каждый запрос +1 к сохранённому), дату, **название судна**, по каждому инвойсу отдельную сумму, **сумму до скидки**, **сумму скидки** и **итог после скидки** (скидка считается на сервере от вашего процента).
6. JSON-метаданные эндпоинтов: `GET /api`.
7. Генерация Word: `POST /v1/credit-note/bank-transfer`, тело **`multipart/form-data`**, поле **`file`** = PDF. Опционально формы: `cn_number`, `cn_date`, `model`. Query: `include_json=true` — ответ JSON с `docx_base64` и полями модели.

**Номер credit note на сервере**: пишется в `data/cn_counter.json` (в Git не попадает). На Railway без **volume** файл сбрасывается при деплое — задайте **`CN_COUNTER_LAST`** (последний уже выданный номер, целое) или **`CN_INITIAL_NEXT`** / подсказку от модели при первом запуске; для постоянства смонтируйте том и **`CN_COUNTER_PATH`** (см. `.env.example`).

Пример (без защиты `MAMODOC_API_KEY`):

```bash
curl -sS -X POST "https://YOUR_APP.up.railway.app/v1/credit-note/bank-transfer" \
  -F "file=@Company/I ELBSTROM 26:02.pdf" \
  -o credit_note.docx
```

Если задан **`MAMODOC_API_KEY`**, добавьте заголовок: **`Authorization: Bearer <тот же секрет>`** — так публичный URL не остаётся полностью открытым.

## Команды

```bash
cd /path/to/MamoDoc
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

**Только рендер без Gemini** (удобно отладить шаблон):

```bash
python -m mamodoc --from-json examples/elbstrom_from_cn_reference.json -o output/out.docx
```

**Полный цикл** (нужен ключ в `.env`):

```bash
python -m mamodoc "Company/I ELBSTROM 26:02.pdf" --dump-json output/last_payload.json -o output/cn.docx
```

Переопределить номер/дату credit note:

```bash
python -m mamodoc "Company/I ELBSTROM 26:02.pdf" --cn-number "UNI 261093" --cn-date "April 03, 2026" -o output/cn.docx
```

## Шаблон и переменные

В `credit_note_bank_transfer.docx` используются поля `{{ ... }}`, совпадающие с ключами в `CreditNoteGeminiPayload` (см. `mamodoc/models.py`). Второй блок инвойса в шаблоне обёрнут в `{%p if has_second_invoice %}` — при одном счёте он скрывается.

Если поменяли оформление в Word, перегенерируйте шаблон:

```bash
python scripts/patch_credit_note_template.py
```

(Исходник патча — `templates/UNI_2026.03.21.docx`, который получают из `.doc` через macOS `textutil` или аналог.)

## Фото вместо PDF

Сейчас в API уходит **PDF как бинарный ввод** (удобно и точно). Если нужны **фото**, расширение простое: передавать `image/jpeg` частями в `generate_content` и оставить тот же текст промпта — схема JSON не обязана меняться.

## Примечание по SDK

Пакет `google-generativeai` помечен как устаревающий в пользу `google-genai`. На работу текущего кода это не влияет; при желании позже можно переписать один модуль `gemini_extract.py` под новый SDK без смены остальной архитектуры.

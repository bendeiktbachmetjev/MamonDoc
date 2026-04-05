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
| `examples/*.json` | Пример полезной нагрузки без вызова API |

## API-ключ

1. Ключ: [Google AI Studio](https://aistudio.google.com/apikey).
2. Локально: скопируйте `.env.example` в `.env`, вставьте `GEMINI_API_KEY=...`.
3. **GitHub / Railway**: не коммитьте `.env`; в Railway задайте переменную окружения `GEMINI_API_KEY` в настройках сервиса.

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

# Документация JacRed

Исходники сайта документации для [JacRed](https://github.com/jacred-fdb/jacred) — самохостируемого агрегатора торрент-трекеров с FileDB и API Jackett, Torznab и Prowlarr. Операторские гайды публикуются на [docs.jacred.stream](https://docs.jacred.stream).

Сайт построен на [Mintlify](https://mintlify.com). Основная конфигурация находится в `docs.json`, страницы — в MDX-файлах.

Публичный [DeepWiki](https://deepwiki.com/jacred-fdb/jacred) — английский code-wiki. Его рулит [`.devin/wiki.json`](https://github.com/jacred-fdb/jacred/blob/main/.devin/wiki.json). Не копируйте MDX в wiki.json.

## Локальная разработка

Установите Mintlify CLI и запустите предпросмотр из каталога `docs`:

```bash
npm install --global mint
cd docs
mint dev
```

Сайт откроется по адресу `http://localhost:3000`.

## Проверки

Перед отправкой изменений выполните:

```bash
cd docs
mint validate
mint broken-links --check-anchors
mint a11y
```

## Источники данных

- Код приложения, `Configuration/AppOptions.cs`, `Configuration/Schema/ConfigSchema.cs`, `Data/crontab`, `Data/init.yaml`, `Data/example.yaml` — источник правды.
- OpenAPI: канонический файл `../web/public/openapi.yaml`, копия для Mintlify `openapi/openapi.yaml`.
- Брендинг: канонические файлы в `../web/public/img/`, копии для Mintlify в `favicon.png`, `logo/` и `images/`.
- Постоянные инструкции агента: `docs/AGENTS.md`.

Mintlify не разрешает символические ссылки за пределы каталога `docs`. После изменения OpenAPI или бренд-ассетов обновите соответствующие копии вручную. Не добавляйте скрипт или workflow для синхронизации.

Различайте значения по умолчанию в `AppOptions.cs`, шаблон `Data/init.yaml` и полный пример `Data/example.yaml`. Процесс читает `init.yaml` из рабочей директории, а не из `Data/`.

## Правила контента

- Пишите по-русски, в активном залоге и обращайтесь к читателю на «вы».
- Используйте корневые внутренние ссылки без расширения: `/configuration/overview`.
- Не копируйте секреты, токены, cookie или реальные ключи из конфигурационных файлов.
- Проверяйте технические утверждения по коду и каноническому конфигу, а не по DeepWiki.

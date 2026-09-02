# Документация JacRed

Исходники сайта документации для [JacRed](https://github.com/jacred-fdb/jacred) — самохостируемого агрегатора торрент-трекеров с FileDB и API Jackett, Torznab и Prowlarr.

Сайт построен на [Mintlify](https://mintlify.com). Основная конфигурация находится в `docs.json`, страницы — в MDX-файлах.

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
mint broken-links --check-redirects
mint a11y
```

## Источники данных

- Код и операторская документация: [`jacred-fdb/jacred`](https://github.com/jacred-fdb/jacred)
- OpenAPI: канонический файл `../web/public/openapi.yaml`, копия для Mintlify `openapi/openapi.yaml`
- Брендинг: канонические файлы в `../web/public/img/`, копии для Mintlify в `favicon.png`, `logo/` и `images/`
- Расписание парсеров: `../Data/crontab`
- Схема конфигурации: `../Configuration/Schema/ConfigSchema.cs`

Mintlify не разрешает символические ссылки за пределы каталога `docs`. После изменения OpenAPI или бренд-ассетов обновите соответствующие копии вручную. Не добавляйте скрипт или workflow для синхронизации.

## Правила контента

- Пишите по-русски, в активном залоге и обращайтесь к читателю на «вы».
- Используйте корневые внутренние ссылки без расширения: `/configuration/overview`.
- Не копируйте секреты, токены, cookie или реальные ключи из конфигурационных файлов.
- Проверяйте технические утверждения по исходному коду JacRed и OpenAPI.

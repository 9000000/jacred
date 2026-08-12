# Docker

Образ можно запускать через **Docker** или **Docker Compose**. Конфигурация (`init.yaml` или `init.conf`) и данные (база fdb, логи) хранятся в томах или bind-монтированных каталогах. При первом запуске конфиг по умолчанию копируется автоматически (поддерживаются и named volumes, и bind mounts).

## Docker Run

```bash
docker run -d \
  --name jacred \
  -p 9117:9117 \
  -v jacred-config:/app/config \
  -v jacred-data:/app/Data \
  --restart unless-stopped \
  ghcr.io/jacred-fdb/jacred:latest
```

## Docker Compose

**Вариант с named volumes** (рекомендуется):

```yaml
name: jacred

services:
  jacred:
    image: ghcr.io/jacred-fdb/jacred:latest
    container_name: jacred
    restart: unless-stopped
    ports:
      - "9117:9117"
    volumes:
      - jacred-config:/app/config
      - jacred-data:/app/Data
    environment:
      - TZ=Europe/London
      - UMASK=0027
    healthcheck:
      test: ["CMD", "curl", "-f", "-s", "--max-time", "10", "http://127.0.0.1:9117/health"]
      interval: 30s
      timeout: 15s
      retries: 3
      start_period: 45s
    deploy:
      resources:
        limits:
          memory: 2048M

volumes:
  jacred-config:
  jacred-data:
```

**Вариант с bind mounts** (удобно для доступа к файлам на хосте) — замените блок `volumes` в сервисе на:

```yaml
volumes:
  - ./config:/app/config
  - ./data:/app/Data
```

Готовый пример: [**`docker-compose.example.yml`**](../docker-compose.example.yml) (JacRed + FlareSolverr, named volumes).

**Полезно:**

- **Конфиг:** после первого запуска настройте **`init.yaml`** или **`init.conf`** в томе `jacred-config` или каталоге `./config` (при bind mount). Конфиг автоматически копируется из `/app/config/` в `/app/` при старте контейнера. Для Rutracker в compose задайте `flaresolverr.url: http://flaresolverr:8191/v1`.
- **Порты:** веб-интерфейс и API доступны на порту **9117** (при необходимости измените маппинг `ports` и `listenport` в конфиге). Порт FlareSolverr **8191** в примере не публикуется наружу — только внутренняя сеть Compose.
- **Память:** JacRed + FlareSolverr (~1 GiB) — ориентир **≥4 GiB** на сервис JacRed в примере compose; при большой базе увеличьте лимит.
- **Тома:**
  - `jacred-config` — хранит конфигурацию (`init.yaml` или `init.conf`)
  - `jacred-data` — хранит базу данных (`fdb/`), логи (`log/`), временные файлы (`temp/`) и треки (`tracks/`)
- **Healthcheck:** контейнер включает встроенный healthcheck, проверяющий доступность `/health` эндпоинта.
- **Сборка своего образа:** в корне репозитория выполните `docker build -t jacred .` и в примерах выше замените образ на `jacred:latest`.
- **Переменные окружения:** поддерживаются `TZ` (часовой пояс) и `UMASK` (права на файлы, по умолчанию `0027`).

## Самостоятельный парсинг и расписание (cron) в Docker

В образе **нет** планировщика **cron** (и **нет** установки заданий в crontab внутри контейнера). Фоновые циклы приложения (синхронизация по `syncapi`, статистика и т.д.) работают сами; **периодический вызов HTTP-эндпоинтов** `/cron/...` и **`/jsondb/save`** нужно организовать **снаружи** контейнера.

**Типовые варианты:**

1. **Cron на хосте** (чаще всего) — установить crontab из [`Data/crontab`](../Data/crontab) (вызовы [`Data/run-job.sh`](../Data/run-job.sh)) или вручную дергать `curl` на опубликованный порт (например `http://127.0.0.1:9117/...`). Запрос с хоста в контейнер обычно приходит с адреса из **приватной подсети** (в т.ч. шлюз Docker `172.x`), что удовлетворяет проверке «локальная/приватная сеть» в приложении.
2. **Отдельный контейнер с cron** — маленький образ (например `curl` + `cron`), в том же Docker Compose, который по расписанию дергает сервис JacRed по **внутреннему** имени и порту (например `http://jacred:9117/...`). Убедитесь, что с точки зрения JacRed IP источника остаётся в приватном диапазоне (типично так и есть в user-defined bridge-сети).
3. **Kubernetes CronJob**, **systemd timer** на хосте — по сути то же, что п.1: периодический HTTP-запрос к JacRed.

**Ориентир по расписанию:** в репозитории лежит пример [`Data/crontab`](../Data/crontab) (парсинг по трекерам через `Data/run-job.sh`, `cloudflare-warmup` перед `rutracker-parse`, daily anistar/leproduction/viruseproject/anifilm, hourly anibelka/korsars/ultradox/rudub + ParseLatest, knaben parse/backfill, и `*/5 * * * *` для **`/jsondb/save`**). Скопируйте нужные строки в свой crontab на хосте (или в свой шаблон для контейнера с cron) и:

- при использовании `run-job.sh` убедитесь, что скрипт доступен по пути из crontab (в релизе — `/opt/jacred/Data/run-job.sh`); либо замените строки на прямой `curl`;
- замените хост/порт в URL на ваши (`127.0.0.1:9117` или имя сервиса в Compose);
- если в **`init.yaml` / `init.conf`** задан **`apikey`** — добавьте в каждый URL `?apikey=...` (или в `curl` `-H "X-Api-Key: ..."`), иначе запросы к `/cron/*` и `/jsondb/save` получат **401**;
- если задан **`devkey`** и запрос считается «локальным» — добавьте `?devkey=...` или `-H "X-Dev-Key: ..."`.

Подробнее про ключи для `/cron/*` — в [Парсинг трекеров](api.md#парсинг-трекеров).

**Синхронизация вместо своего парсинга:** можно указать **`syncapi`** и не вызывать `/cron/*` вовсе; тогда достаточно конфигурации и встроенных циклов приложения (плюс при необходимости **`/jsondb/save`** по расписанию, если вы ведёте локальную запись БД).

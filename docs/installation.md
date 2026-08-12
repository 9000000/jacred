# Установка

Установка одной командой (запускать от любого пользователя, при необходимости запросится sudo):

```bash
curl -s https://raw.githubusercontent.com/jacred-fdb/jacred/main/jacred.sh | bash
```

Скрипт устанавливает приложение в **`/opt/jacred`**, создаёт пользователя и systemd-сервис `jacred`, добавляет cron для сохранения БД и при первом запуске по желанию скачивает готовую базу.

**Опции:**

| Опция | Описание |
| --- | --- |
| `--no-download-db` | Не скачивать и не распаковывать базу (только при установке) |
| `--pre-release` | Установить или обновить из последнего pre-release (например, 2.0.0-dev1) |
| `--update` | Обновить приложение с последнего релиза (сохранить БД, заменить файлы, перезапустить) |
| `--remove` | Полностью удалить JacRed (сервис, cron, каталог приложения) |
| `-h`, `--help` | Показать справку |

**Примеры:**

```bash
# Обычная установка (одна команда)
curl -s https://raw.githubusercontent.com/jacred-fdb/jacred/main/jacred.sh | sudo bash

# Установка без загрузки базы (одна команда)
curl -s https://raw.githubusercontent.com/jacred-fdb/jacred/main/jacred.sh | sudo bash -s -- --no-download-db

# Скачать скрипт и запустить с аргументами
curl -s https://raw.githubusercontent.com/jacred-fdb/jacred/main/jacred.sh -o jacred.sh
chmod +x jacred.sh
sudo ./jacred.sh --no-download-db

# Установка pre-release версии
curl -s https://raw.githubusercontent.com/jacred-fdb/jacred/main/jacred.sh | bash -s -- --pre-release

# Или скачать и запустить pre-release
curl -s https://raw.githubusercontent.com/jacred-fdb/jacred/main/jacred.sh -o jacred.sh
chmod +x jacred.sh
sudo ./jacred.sh --pre-release

# Обновление уже установленного приложения
sudo /opt/jacred/jacred.sh --update

# Обновление до pre-release версии
sudo /opt/jacred/jacred.sh --update --pre-release

# Удаление
sudo /opt/jacred/jacred.sh --remove
```

Установка/обновление/удаление под конкретным пользователем (cron будет добавлен или удалён для этого пользователя):

```bash
sudo -u myservice ./jacred.sh
sudo -u myservice ./jacred.sh --update
sudo -u myservice ./jacred.sh --remove
```

После установки:

- Настройте конфиг: **`/opt/jacred/init.yaml`** или **`/opt/jacred/init.conf`**, либо через веб-редактор **`/settings`** (LAN или `devkey` — см. [Безопасность](security.md))
- Веб-интерфейс: **`http://127.0.0.1:9117/`** (поиск), **`/stats`**, **`/settings`**
- Перезапуск: `systemctl restart jacred`
- Полный crontab для парсинга: `crontab /opt/jacred/Data/crontab`

> **Важно:** по умолчанию синхронизация отключена: скрипт установки скачивает базу, парсинг — по cron (`Data/crontab`). Чтобы подтягивать базу с внешнего сервера, укажите `syncapi` и включите нужные опции синхронизации в конфиге.

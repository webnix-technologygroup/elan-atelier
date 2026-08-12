# Portfolio checklist

## Подтверждено локально

- [x] Black проходит
- [x] Python compileall проходит
- [x] Node syntax проходит для трёх JS-файлов
- [x] Migration drift отсутствует
- [x] Все 41 Django-тест проходят
- [x] Seed повторяется без дублей основных сущностей
- [x] Development и production collectstatic проходят
- [x] Локальный runserver отдаёт source static без предварительного collectstatic
- [x] `check --deploy` проходит без warnings
- [x] Success и `.ics` требуют session владельца
- [x] Customerless и foreign Booking не раскрываются
- [x] Booking к конкретному мастеру проходит в браузере
- [x] Booking «любой мастер» проходит в мобильном браузерном сценарии
- [x] Console и Network без неожиданных ошибок в финальных booking flows
- [x] Wizard header, progress и review уплотнены после визуальной обратной связи
- [x] Review использует полную ширину и переносит длинные значения
- [x] Horizontal overflow устранён на desktop/tablet/mobile
- [x] Focus wizard переходит на заголовок активного шага
- [x] FAQ содержит необходимые ARIA relationships
- [x] README, case study, audit и manual steps присутствуют
- [x] Финальная поставка исключает `.venv`, `.env`, БД, `staticfiles`, caches и `.pyc`

## Требует внешнего подтверждения

- [ ] Ruff проходит в среде с установленными dev dependencies
- [ ] GitHub Actions зелёный после push
- [ ] Docker image собирается в доступном Docker runtime
- [ ] PostgreSQL concurrency проверен
- [ ] SMTP и Telegram проверены только при наличии реальных credentials
- [ ] Короткий ручной Chrome/Edge audit завершён на Windows
- [ ] Добавлены финальные portfolio screenshots
- [ ] Live demo доступен по HTTPS

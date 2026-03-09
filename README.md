# Pet Compatibility Service

REST API сервис для оценки совместимости пользователя с питомцем.

## Запуск локально

```bash
# Установить зависимости
pip install -e ".[dev]"

# Запустить сервер
uvicorn app.main:app --reload
```

## Запуск через Docker

```bash
docker compose up --build
```

Сервис будет доступен на `http://localhost:8000`.

## API

### POST /evaluate

Оценка совместимости с питомцем.

```bash
curl -X POST http://localhost:8000/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "pet_type": "dog",
    "housing": "apartment",
    "budget_usd": 100,
    "has_children": true,
    "hours_free_per_day": 1
  }'
```

Ответ:
```json
{
  "compatible": false,
  "risk_level": "high",
  "reasons": [
    "Собака требует от $200/мес на питание и ветеринара",
    "Собака требует минимум 3 часа внимания в день",
    "Собакам нужно пространство — дом или квартира с двором"
  ],
  "alternatives": [
    {"pet_type": "hamster", "why": "Хомяк подходит вам по всем параметрам"}
  ]
}
```

### POST /rules/reload

Перезагрузка правил с диска без рестарта сервиса.

```bash
curl -X POST http://localhost:8000/rules/reload
```

### GET /health

```bash
curl http://localhost:8000/health
```

## Тесты

```bash
pytest -v
```

## Добавление нового типа питомца

Отредактируйте `rules.yaml`, добавив новый блок:

```yaml
pets:
  parrot:
    label: "Попугай"
    group: domestic
    conditions:
      - field: budget_usd
        operator: gte
        value: 50
        risk_weight: 2
        reason: "Попугай требует от $50/мес на корм и клетку"
      - field: hours_free_per_day
        operator: gte
        value: 2
        risk_weight: 3
        reason: "Попугаю нужно минимум 2 часа общения в день"
    alternatives_if_rejected: [fish, hamster]
```

Затем вызовите `POST /rules/reload` — новый тип сразу станет доступен.

## Документация API

Автоматическая OpenAPI документация доступна по адресу: `http://localhost:8000/docs`

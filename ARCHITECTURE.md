# Pet Compatibility Service — Architecture Decision Record

---

## Overview

REST API сервис на Python для оценки совместимости пользователя с питомцем.  
Ключевой принцип: **бизнес-логика полностью отделена от кода** и живёт в конфигурации,
управляемой не-инженерами.

---

## Project Structure

```
pet-compatibility-service/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI entrypoint, lifespan, routers
│   ├── api/
│   │   ├── __init__.py
│   │   ├── evaluate.py      # POST /evaluate handler
│   │   └── rules.py         # POST /rules/reload handler
│   ├── core/
│   │   ├── __init__.py
│   │   ├── engine.py        # RulesEngine — чтение, валидация, матчинг
│   │   └── models.py        # Pydantic schemas (Request / Response)
│   └── dependencies.py      # FastAPI DI: get_rules_engine()
├── tests/
│   ├── conftest.py
│   ├── test_evaluate.py
│   ├── test_rules_reload.py
│   └── test_engine.py
├── rules.yaml               # Конфигурация правил (редактируется без деплоя)
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── README.md
└── ARCHITECTURE.md
```

**Принцип разбивки:** `api/` — только HTTP-слой (stateless хэндлеры), `core/` — чистая бизнес-логика без зависимости от FastAPI. Это позволяет тестировать движок правил изолированно, без поднятия HTTP-сервера.

---

## Tech Stack

| Компонент   | Выбор               | Обоснование                                            |
|-------------|---------------------|--------------------------------------------------------|
| Framework   | **FastAPI**         | Async-ready, нативный Pydantic, auto OpenAPI docs      |
| Rules format| **YAML**            | Читаем для не-инженеров, поддерживает комментарии      |
| Validation  | **Pydantic v2**     | Строгая типизация, понятные ошибки на входе            |
| Tests       | **pytest + httpx**  | Стандарт отрасли, async-совместим                      |
| Container   | **Docker multi-stage** | Минимальный образ, отдельные слои зависимостей      |

### Почему YAML, а не база данных или JSON?

Это осознанный выбор для текущей стадии продукта, а не единственно возможный вариант.

**YAML выбран потому, что** правила на старте меняются редко (раз в несколько дней), их объём мал (десятки записей), а главная аудитория редактора — продакт-менеджер или аналитик, а не инженер. YAML читается как текст, поддерживает комментарии (JSON — нет), и хранится в Git, что даёт историю изменений и code review бесплатно. Нет смысла поднимать PostgreSQL ради файла, который в production меняет один человек раз в неделю.

**JSON** отпал по одной причине: отсутствие комментариев делает невозможным объяснить прямо в файле, *почему* выставлено то или иное значение (`risk_weight: 4 # критично — без этого собака разрушит квартиру`). Для конфига, который редактирует не-инженер, это неприемлемо.

**База данных становится оправданной**, когда выполняется хотя бы одно из условий: правила меняются несколько раз в день (нужен UI без деплоя), появляется несколько реплик сервиса (нужна единая точка правды), или требуется A/B тестирование правил на разных сегментах пользователей. В этот момент `rules.yaml` заменяется на таблицу `rules` в PostgreSQL, а `RulesEngine` получает новый адаптер — изменение в одном файле (`engine.py`), остальной код не трогается.

---

## API Response Schema

### `POST /evaluate`

**Request:**
```json
{
  "pet_type": "dog",
  "housing": "apartment",
  "budget_usd": 150,
  "has_children": true,
  "hours_free_per_day": 2
}
```

**Response:**
```json
{
  "compatible": false,
  "risk_level": "high",
  "reasons": [
    "Собака требует от $200/мес на питание и ветеринара",
    "Собака требует минимум 3 часа внимания в день"
  ],
  "alternatives": ["cat", "hamster"]
}
```

| Поле          | Тип              | Описание                                             |
|---------------|------------------|------------------------------------------------------|
| `compatible`  | `bool`           | Итоговый вердикт                                     |
| `risk_level`  | `low/medium/high`| Агрегированный уровень риска по нарушенным условиям  |
| `reasons`     | `list[str]`      | Human-readable объяснения каждого нарушения          |
| `alternatives`| `list[str]`      | Альтернативные питомцы из конфига текущего животного |

Поля `reasons` и `alternatives` возвращаются всегда (пустой список если не применимо),
чтобы клиент мог рендерить UI без дополнительных null-проверок.

---

## Rules Engine Design

Правила хранятся в `rules.yaml`. Каждый тип животного — набор **условий** (conditions)
с логическими операторами и **весами риска**.

```yaml
version: "1.0.0"

pets:
  dog:
    label: "Собака"
    group: domestic
    conditions:
      - field: budget_usd
        operator: gte
        value: 200
        risk_weight: 3
        reason: "Собака требует от $200/мес на питание и ветеринара"
      - field: hours_free_per_day
        operator: gte
        value: 3
        risk_weight: 4
        reason: "Собака требует минимум 3 часа внимания в день"
      - field: housing
        operator: in
        value: ["house", "apartment_with_yard"]
        risk_weight: 2
        reason: "Крупным собакам нужно пространство"
    alternatives_if_rejected: [cat, hamster]

  cat:
    label: "Кошка"
    group: domestic
    conditions:
      - field: budget_usd
        operator: gte
        value: 80
        risk_weight: 2
        reason: "Кошка требует от $80/мес"
    alternatives_if_rejected: [hamster, fish]

  hamster:
    label: "Хомяк"
    group: small
    conditions:
      - field: budget_usd
        operator: gte
        value: 20
        risk_weight: 1
        reason: "Минимальный бюджет для хомяка — $20/мес"
    alternatives_if_rejected: [fish]
```

**Поддерживаемые операторы:** `gte`, `lte`, `eq`, `neq`, `in`, `not_in`

**Уровни риска** считаются как сумма `risk_weight` нарушенных условий:

| Сумма | Уровень  |
|-------|----------|
| 0     | `low`    |
| 1–4   | `medium` |
| 5+    | `high`   |

---

## Hot-Reload: Thread-Safety

`POST /rules/reload` перечитывает файл с диска и атомарно заменяет движок в памяти.

```
[Request: POST /rules/reload]
        │
        ▼
  Читаем новый YAML с диска
        │
        ▼
  Валидируем схему (Pydantic)  ──→  ошибка? → 422, старый движок остаётся
        │
        ▼
  async with self._lock:       ──→  asyncio.Lock только на момент замены
      self._rules = new_rules  ──→  атомарный replace (Python GIL + immutable dict)
        │
        ▼
  200 OK {"version": "1.1.0", "pets_loaded": 5}
```

**Почему чтение не требует Lock:**  
После замены `self._rules` все новые запросы видят новый объект. Старые in-flight запросы
держат ссылку на предыдущий объект до завершения — это корректно, так как объект immutable.
`asyncio.Lock` нужен только для того, чтобы два одновременных `/rules/reload` не создали
race condition при самой замене ссылки.

---

## Scaling to 50+ Pet Types

Добавление нового вида — **только правка YAML, без деплоя:**

1. Добавить блок с `conditions` и `alternatives_if_rejected`
2. Указать `group` для фильтрации в будущем (например, `exotic`, `farm`, `aquatic`)
3. Вызвать `POST /rules/reload` или перезапустить сервис

Для организационного масштабирования (команды, CI):

- `version` в YAML даёт аудит изменений в Git blame
- Добавить `make lint-rules` — валидацию YAML-схемы в CI до мержа
- При необходимости — вынести `rules.yaml` в отдельный репозиторий с правами доступа для продукт-менеджеров

---

## Trade-offs & Limitations

### ✅ Что выиграли

- Zero-code изменение бизнес-логики
- Полная тестируемость каждого условия изолированно
- Понятный аудит: git diff на rules.yaml = история решений
- Нет зависимости от БД для базового сценария

### ⚠️ Ограничения

| Ограничение | Описание | Путь к решению |
|---|---|---|
| **Single-instance hot-reload** | При нескольких репликах каждая держит свой `rules.yaml` в памяти. Reload одной реплики не распространяется на остальные | Shared storage (S3/Git) + event bus (Redis pub/sub) для fan-out |
| **Нет истории версий** | YAML не хранит историю изменений из коробки | Git-хранение + webhook на push для auto-reload |
| **Ограниченный operator set** | Сложные условия («если A и (B или C)») требуют вложенной логики, которой сейчас нет | Ввести `all_of` / `any_of` блоки в следующей версии схемы |
| **ML-предикторы не поддерживаются** | Вероятностная логика (аллергии, поведенческие паттерны) в YAML не описать | Точка расширения: отдельный scoring-сервис, результат которого подаётся как поле профиля |
| **Нет персистентности запросов** | История оценок не сохраняется | Добавить опциональный слой БД (PostgreSQL + SQLAlchemy) при необходимости аналитики |

---

## Risk Analysis

| Риск | Вероятность | Impact | Митигация |
|---|---|---|---|
| Невалидный YAML при hot-reload | Средняя | Высокий | Валидация Pydantic-схемой перед применением, rollback при ошибке |
| Race condition при concurrent reload | Низкая | Средний | `asyncio.Lock` на операцию замены движка |
| Рост сложности правил (50+ видов) | Высокая | Низкий | `lint`-команда + схема валидации в CI |
| Drift между репликами при горизонтальном масштабировании | Средняя | Высокий | Централизованное хранилище правил + pub/sub |

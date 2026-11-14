# Task_GBC


## Задание 
[Текст самого задания тут](https://github.com/kr1st1na0/Task_GBC/blob/main/TASK.md)

<!-- сделать: -->
<!-- - тесты на pytest  -->
<!-- - повторная загрузка того же файла не создаёт новую работу -->


## Структура:

```
app/
|-- routers/            # эндпоинты
|   |-- job.py
|-- schemas/            # модели
|   ├-- order.py
|   |-- job.py
|-- services/           # внешнее
|   |-- rates.py
|-- storage/            # хранилище
|   |-- database.py
|-- tasks/
|   |-- broker.py
|   |-- processor.py    # обработка файла + финал
|   |-- summary.py      # сводка по файлу 
|-- config.py           # настройки
|-- main.py
data/
|-- orders.json         # файл из задания
|-- small_orders.json   # файл, на котором тестила битые заказы + дубликаты
tests/
|-- test_summary.py     # тест сборки сводки
```


## Стек (выбор инструментов):

- **Брокер:** Redis (чтобы не разворачивать второй сервис... + поддерживает подтверждения (если упадет, задача не потеряется) + нагрузка тут не такая большая)

- **Очередь задач:** TaskIQ (лучше работает с FastApi, async поддерживает сам по себе. Умеет спокойно запускать как синхронные, так и асинхронные функции)

- **Хранилище:** Redis (Достаем задачу по ключу (а redis key-value). Хранит статус, прогресс и сами данные, быстрый доступ.. А какие-то сложные аналитические запросы к БД не нужны)

- **Сводка:** pandas (привычнее, популярнее... Нагрузка тут не такая большая)


## Запуск:

- первый запуск
```bash
docker compose up --build
```

- запуск
```bash
docker compose up 
```

- посмотреть redis:
```bash
docker exec -it redis_storage redis-cli
```
- очистить redis:
```bash
docker exec -it redis_storage redis-cli FLUSHALL
```


## Общая логика:
<!-- больше для себя... -->

"1 файл = 1 job = 1 задача в очереди задач", а внутри задачи последовательно (циклом) обрабатываются записи (заказы). И после этой задачи (обработки записей одного файла), еще есть финальная задачка (тоже в очередь задач идет) по сводке.
1. Асинхронно (Event Loop, без блокировок): 
    - ```POST /jobs```, ```GET /jobs/{job_id}```, ```GET /jobs/{job_id}/result``` - ручки (async def)
    - ```await process_orders.kiq()```: отправка задачи в очередь (API отправляет задачу и не ждет, пока она выполнится)
    - Внутри TAskIQ - асинхронное общение с Redis (использует redis.asyncio для общения с брокером)
    - ```process_orders```: сама задача (async def) (выполняется в Event Loop воркера)
    - Взаимодействие с Redis (redis.asyncio)
    - ```get_rate_to_usd```: получение курсов валют, запрос к API (async def)

2. Синхронно (в отдельных потоках через asyncio.to_thread):
    - ```build_summary``` (pandas): CPU-bound задача
    - ```_generate_csv``` (csv): CPU-bound (в API, при запросе ?format=csv)


## Обработка дубликатов:
1. **Единый запуск:**

Если встречаем заказ с таким же ```order_id```, какой уже видели (проверяем через множество ```local_seen_ids``` - только для текущего запуска), то кладем в ```errors``` c причиной ```"duplicate order"```

тут все норм:

файл с заказами ```[1, 2, 1, 1, 3]```
| order_id | local_seen_ids | all_seen_ids | результат |
|-|-|-|-|
| 1 |  {} -> {1} | {} -> {1} | обработали |
| 2 | {1} -> {1, 2} | {1} -> {1, 2} | обработали |
| 1 | {1, 2} -> {1, 2} | {1, 2} -> {1, 2} | дубликат |
| 1 | {1, 2} -> {1, 2} | {1, 2} -> {1, 2} | дубликат |
| 3 | {1, 2} -> {1, 2, 3} | {1, 2} -> {1, 2, 3} | обработали |

Итог: 

```processed_orders = [1, 2, 3]```

```errors = [{1, "duplicate order"}, {1, "duplicate order"}]```

```total = 5```

```processed = 3```

```failed = 2```

2. **Retry запуск:** 

Храним в Redis ```all_seen_ids``` - хранятся все ```order_id```, которые когда-либо видели (предыдущие запуски + текущий запуск). Так как, если у нас что-то упало, и задача запустилась еще раз - нужно, чтобы не было лишнего ничего (смотреть файл начинаем заново и нужно skip то, что уже видели).

<!-- БЫЛА ПРОБЛЕМА: если у нас произошел retry, мы пропустим дубликаты заказов, обработанных в предыдущем запуске. крч я с этим намучалась жестко, один дубликат ловит, еще один нет... -->

Пусть оно упало после order_id = 2 (после второй записи), и мы запустили retry:

файл с заказами ```[1, 2, 1, 1, 3, 4, 5]```
| order_id | local_seen_ids | all_seen_ids | результат |
|-|-|-|-|
| 1 |  {} -> {1} | {1, 2} -> {1, 2} | skip (обработали в 1-м запуске) |
| 2 | {1} -> {1, 2} | {1, 2} - > {1, 2} | skip (unknown currency в 1-м запуске) |
| 1 | {1, 2} -> {1, 2} | {1, 2} -> {1, 2} | дубликат |
| 1 | {1, 2} -> {1, 2} | {1, 2} -> {1, 2} | дубликат |
| 3 | {1, 2} -> {1, 2, 3} | {1, 2} -> {1, 2, 3} | нет amount |
| 4 | {1, 2, 3} -> {1, 2, 3, 4} | {1, 2, 3} -> {1, 2, 3, 4} | обработали |
| 5 | {1, 2, 3, 4} -> {1, 2, 3, 4, 5} | {1, 2, 3, 4} -> {1, 2, 3, 4, 5} | обработали |

Итог: 

```processed_orders = [1, 4, 5]```

```errors = [{2, "unknown currency: XYZ"}, {1, "duplicate order"}, {1, "duplicate order"}, {3, "Field required"}]```

```total = 7```

```processed = 3```

```failed = 4```

**Summary:** Если ```order_id in local_seen_ids``` (уже был при текущем запуске), то кидаем его в ```errors``` с пометкой дубликат + в ```all_seen_ids``` его добавляем (тк это множество - все ок будет, даже если этот заказ уже добавлен). Если после этого ```order_id in all_seen_ids```, то мы skip, тк не считаем считаем дубликатом то, что обработали в прошлом запуске (и соответственно в текущем).


___

```processed_orders```:

```JSON
[
  {
    "order_id": 1,
    "customer": "alex",
    "product": "Война и мир",
    "amount": 20.77,
    "currency": "USD",
    "order_date": "2026-10-18",
    "review": "Плохое качество печати, страницы рваные, разочарован",
    "amount_usd": 20.77
  },
  {
    "order_id": 4,
    "customer": "maria",
    "product": "1984",
    "amount": 11.75,
    "currency": "EUR",
    "order_date": "2024-09-25",
    "review": "Обычная книга, ничего особенного",
    "amount_usd": 13.15
  },
  {
    "order_id": 5,
    "customer": "elena",
    "product": "Война и мир",
    "amount": 11.75,
    "currency": "EUR",
    "order_date": "2026-10-05",
    "review": "Обычная книга, ничего особенного",
    "amount_usd": 13.14
  }
]
```

```GET /jobs/{job_id}/result```

```JSON
{
  "job_id": "5033c5ee-85a1-4473-a86c-8765a837e1bc",
  "status": "done",
  "total": 7,
  "processed": 3,
  "failed": 4,
  "summary": {
    "customer_x_currency": [
      {
        "customer": "alex",
        "currency": "USD",
        "amount_usd": 20.77
      },
      {
        "customer": "elena",
        "currency": "EUR",
        "amount_usd": 13.14
      },
      {
        "customer": "maria",
        "currency": "EUR",
        "amount_usd": 13.15
      }
    ],
    "top3_customers": [
      {
        "customer": "alex",
        "amount_usd": 20.77
      },
      {
        "customer": "maria",
        "amount_usd": 13.15
      },
      {
        "customer": "elena",
        "amount_usd": 13.14
      }
    ],
    "weekly_usd": [
      {
        "week": "2024-09-23/2024-09-29",
        "amount_usd": 13.15
      },
      {
        "week": "2026-10-05/2026-10-11",
        "amount_usd": 13.14
      },
      {
        "week": "2026-10-12/2026-10-18",
        "amount_usd": 20.77
      }
    ],
    "total_usd": 47.06,
    "avg_check_usd": 15.69
  },
  "errors": [
    {
      "order_id": 2,
      "reason": "unknown currency: XYZ"
    },
    {
      "order_id": 1,
      "reason": "duplicate order"
    },
    {
      "order_id": 1,
      "reason": "duplicate order"
    },
    {
      "order_id": 3,
      "reason": "Field required"
    }
  ]
}
```

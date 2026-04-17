# Simple AI Weather Agent (LLM + MCP)

## Описание

Данный проект представляет собой простой AI-агент, который обрабатывает пользовательские запросы с помощью локальной языковой модели и самостоятельно принимает решение о необходимости вызова внешних инструментов. Агент интегрирует локальную LLM (через Ollama) с инструментами, реализованными через Model Context Protocol (MCP). При необходимости вызывается внешний API погоды, после чего пользователю возвращается структурированный ответ.

Проект демонстрирует базовую архитектуру AI-агентов:
- локальная LLM
- вызов инструментов (tool calling)
- протокол MCP

## Используемые технологии

- FastAPI
- Pydantic
- httpx
- Ollama (qwen2.5:3b)
- MCP (Model Context Protocol)
- OpenWeather API

## Установка и запуск

1. Создание виртуального окружения
python -m venv .venv
.venv\Scripts\activate

2. Установка зависимостей
pip install -r requirements.txt

3. Установка Ollama
https://ollama.com

4. Загрузка модели
ollama pull qwen2.5:3b

5. Создание .env
OPENWEATHER_API_KEY=your_api_key

6. Запуск
uvicorn main:app --reload

7. Документация
http://127.0.0.1:8000/docs

## Пример запроса

{
  "message": "Какая погода в Берлине?"
}

## Как работает система

1. Пользователь отправляет запрос
2. LLM получает запрос и инструменты
3. LLM решает: нужен ли tool
4. MCP вызывает инструмент
5. Получаются данные из API
6. Backend возвращает ответ


## Добавление инструмента, который работает с внешним API

Для добавления нового tool, который обращается к внешнему источнику через API, нужно выполнить следующие шаги.

1. Добавить новый API ключ в `.env`, если внешний сервис требует авторизацию.

Пример:
EXCHANGE_API_KEY=your_api_key

2. Прочитать ключ в `weather_mcp_server.py` или вынести tools в отдельный MCP server файл.

Пример:
EXCHANGE_API_KEY = os.getenv("EXCHANGE_API_KEY", "")

3. Создать новую функцию с декоратором `@mcp.tool()`.

Пример инструмента для получения курса валют:

@mcp.tool()
async def get_exchange_rate(base: str, target: str) -> dict:
    if not EXCHANGE_API_KEY:
        return {"error": "EXCHANGE_API_KEY is not set"}

    url = "https://api.example.com/rates"
    params = {
        "base": base,
        "target": target,
        "apikey": EXCHANGE_API_KEY
    }

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

        return {
            "base": base,
            "target": target,
            "rate": data.get("rate")
        }

    except httpx.HTTPStatusError as e:
        return {"error": f"HTTP error: {e.response.status_code}"}
    except Exception as e:
        return {"error": str(e)}

4. Использовать простые аргументы в сигнатуре функции: `str`, `int`, `float`, `bool`.
   Это упрощает генерацию аргументов для LLM.

5. Возвращать `dict`, а не строку.
   Так результат проще обрабатывать в `main.py`.

6. Обрабатывать ошибки внутри tool и возвращать их в виде:
   {"error": "описание ошибки"}

7. После добавления tool не нужно менять `main.py`, если в нем уже используется динамическая загрузка через `mcp.tools()`.
   Новый инструмент автоматически попадет в список доступных tools для LLM.

## Как агент начинает использовать новый tool

После запуска приложения `main.py` получает список всех инструментов через `mcp.tools()`.
Этот список передается в локальную LLM.
Если модель понимает, что пользовательский запрос относится к новому инструменту, она формирует вызов нужной функции.
Затем `main.py` вызывает tool через `mcp.call(...)`, получает результат и возвращает ответ пользователю.

Пример:
- пользователь пишет: "Какой сейчас курс доллара к рублю?"
- LLM выбирает `get_exchange_rate`
- MCP вызывает tool
- tool обращается к внешнему API
- backend возвращает результат

## Обработка ошибок

- Ollama не запущена
- отсутствует API ключ
- ошибка JSON

## Итог

- LLM принимает решения
- инструменты выполняют действия
- backend управляет процессом


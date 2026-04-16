import sys
import json
import httpx
from pathlib import Path
from fastapi import FastAPI
from pydantic import BaseModel
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

app = FastAPI()

BASE_DIR = Path(__file__).parent
MCP_PATH = str(BASE_DIR / "weather_mcp_server.py")


class MCP:
    def __init__(self):
        self.session = None
        self.ctx = None
        self.stdio = None

    async def connect(self):
        params = StdioServerParameters(
            command=sys.executable,
            args=[MCP_PATH],
        )

        self.stdio = stdio_client(params)
        read, write = await self.stdio.__aenter__()

        self.ctx = ClientSession(read, write)
        self.session = await self.ctx.__aenter__()
        await self.session.initialize()

    async def call(self, name, args):
        return await self.session.call_tool(name, args)

    async def tools(self):
        result = await self.session.list_tools()
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": getattr(t, "description", ""),
                    "parameters": getattr(
                        t,
                        "inputSchema",
                        {
                            "type": "object",
                            "properties": {},
                        },
                    ),
                },
            }
            for t in result.tools
        ]


mcp = MCP()


class ChatRequest(BaseModel):
    message: str


async def ollama_chat(messages, tools=None):
    timeout = httpx.Timeout(180.0, connect=10.0)

    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.post(
            "http://localhost:11434/api/chat",
            json={
                "model": "qwen2.5:3b",
                "messages": messages,
                "tools": tools,
                "stream": False,
                "options": {
                    "temperature": 0
                }
            },
        )
        r.raise_for_status()
        return r.json()


def parse_tool_result(result) -> dict:

    if hasattr(result, "content") and result.content:
        text = getattr(result.content[0], "text", "")

        if not text:
            return {"error": "empty tool response"}

        try:
            return json.loads(text)
        except Exception:
            return {"raw": text}

    if isinstance(result, dict):
        return result

    return {"raw": str(result)}


@app.on_event("startup")
async def startup():
    await mcp.connect()


@app.get("/")
async def root():
    return {"ok": True}


@app.get("/health")
async def health():
    return {"ok": True}


@app.post("/chat")
async def chat(data: ChatRequest):
    user = data.message

    messages = [
        {
            "role": "system",
            "content": (
                "Ты AI-агент. "
                "Если вопрос про погоду, температуру, дождь, ветер или зонт — используй инструмент get_weather. "
                "Если инструмент не нужен — отвечай сам. "
                "Отвечай только на русском языке. "
                "Не используй китайский, английский или другие языки. "
                "Не придумывай данные инструмента."
            ),
        },
        {"role": "user", "content": user},
    ]

    tools = await mcp.tools()
    first = await ollama_chat(messages, tools)
    tool_calls = first.get("message", {}).get("tool_calls", [])

    if not tool_calls:
        return {"answer": first.get("message", {}).get("content", "")}

    call = tool_calls[0]
    name = call["function"]["name"]
    args = call["function"].get("arguments", {})

    result = await mcp.call(name, args)
    parsed = parse_tool_result(result)


    if "error" in parsed:
        return {
            "answer": f"Не удалось получить данные: {parsed['error']}"
        }

    if parsed.get("city") is None and parsed.get("temp") is None and parsed.get("desc") is None:
        return {
            "answer": "Не удалось получить корректные данные о погоде."
        }

    city = parsed.get("city", "неизвестный город")
    temp = parsed.get("temp", "нет данных")
    desc = parsed.get("desc", "нет данных")

    return {
        "answer": f"Сейчас в городе {city}: {desc}, температура {temp}°C."
    }
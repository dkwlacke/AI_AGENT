import os
import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("weather-server")

API_KEY = "fd1e16fcb82478078718e30bfdf05c31"


@mcp.tool()
async def get_weather(city: str) -> dict:
    if not API_KEY:
        return {"error": "no api key"}

    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": city,
        "appid": API_KEY,
        "units": "metric",
        "lang": "ru",
    }

    async with httpx.AsyncClient() as client:
        r = await client.get(url, params=params)
        data = r.json()

    return {
        "city": data.get("name"),
        "temp": data.get("main", {}).get("temp"),
        "desc": data.get("weather", [{}])[0].get("description"),
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
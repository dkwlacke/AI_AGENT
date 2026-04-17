import os
import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("weather-server")

API_KEY = os.getenv("OPENWEATHER_API_KEY")


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
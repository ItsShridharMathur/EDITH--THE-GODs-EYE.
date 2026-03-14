import asyncio
from typing import List, Dict
import requests
from duckduckgo_search import DDGS
import wikipedia


class WebSearch:
    def __init__(self, openweather_api_key: str = ""):
        self.openweather_api_key = openweather_api_key

    async def search(self, query: str, max_results: int = 5):
        q = query.lower().strip()

        # hard weather route first
        if q.startswith("weather ") or "weather in " in q or q.startswith("search weather"):
                weather = await asyncio.to_thread(self._weather_lookup, query)
        if weather:
            return [weather]
        return [] # don't fall through to DDG for weather

        ddg_results = await asyncio.to_thread(self._search_ddg, query, max_results)
        if ddg_results:
            return ddg_results

        return await asyncio.to_thread(self._search_wikipedia, query, max_results)

        # try DDG
        ddg_results = await asyncio.to_thread(self._search_ddg, query, max_results)
        if ddg_results:
            return ddg_results

        # fallback wiki
        wiki_results = await asyncio.to_thread(self._search_wikipedia, query, max_results)
        return wiki_results

    def _search_ddg(self, query: str, max_results: int) -> List[Dict]:
        try:
            with DDGS() as ddgs:
                raw = list(ddgs.text(query, region="wt-wt", safesearch="moderate", max_results=max_results))
            return [
                {
                    "title": r.get("title", "").strip(),
                    "url": r.get("href", "").strip(),
                    "snippet": r.get("body", "").strip(),
                }
                for r in raw
            ]
        except Exception:
            return []

    def _search_wikipedia(self, query: str, max_results: int) -> List[Dict]:
        try:
            titles = wikipedia.search(query, results=max_results)
            out = []
            for t in titles:
                try:
                    p = wikipedia.page(t, auto_suggest=False)
                    out.append(
                        {
                            "title": p.title,
                            "url": p.url,
                            "snippet": p.summary[:220] + ("..." if len(p.summary) > 220 else ""),
                        }
                    )
                except Exception:
                    continue
            return out
        except Exception:
            return []

    def _weather_lookup(self, query: str):
        if not self.openweather_api_key:
            return None

        q = query.lower()
        city = "delhi"
        if " in " in q:
            city = q.split(" in ", 1)[1].strip()

        try:
            url = "https://api.openweathermap.org/data/2.5/weather"
            params = {"q": city, "appid": self.openweather_api_key, "units": "metric"}
            r = requests.get(url, params=params, timeout=10)
            if r.status_code != 200:
                return None
            d = r.json()
            return {
                "title": f"Weather in {d['name']}",
                "url": "https://openweathermap.org/",
                "snippet": f"{d['weather'][0]['description']}, Temp {d['main']['temp']}°C, Humidity {d['main']['humidity']}%, Wind {d['wind']['speed']} m/s",
            }
        except Exception:
            return None
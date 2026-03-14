import os
import platform
import subprocess
import shlex
import re
from pathlib import Path
import psutil
import requests


class CommandRouter:
    def __init__(self, groq_client, openweather_api_key: str = ""):
        self.groq = groq_client
        self.openweather_api_key = openweather_api_key

    async def try_execute(self, text: str, web_search):
        t = text.lower().strip()

        if t in {"help", "commands"}:
            return self._help_text()

        # WEATHER
        city = self._extract_weather_city(text)
        if city:
            return self._get_live_weather(city)

        # SEARCH
        if t.startswith("search "):
            query = text[7:].strip()
            results = await web_search.search(query, max_results=5)
            if not results:
                return "Search is temporarily unavailable right now. Please try again."
            lines = []
            for i, r in enumerate(results[:5], 1):
                lines.append(f"{i}. {r.get('title','No title')}\n   {r.get('url','')}\n   {r.get('snippet','')}")
            return "\n".join(lines)

        # FILE OPS
        if t.startswith("create file "):
            payload = text[len("create file "):]
            if "|" not in payload:
                return "Use: create file <path> | <content>"
            path_str, content = [x.strip() for x in payload.split("|", 1)]
            path = Path(path_str)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            return f"Created file: {path}"

        if t.startswith("read file "):
            path = Path(text[len("read file "):].strip())
            if not path.exists():
                return "File not found."
            return path.read_text(encoding="utf-8")[:4000]

        if t.startswith("delete file "):
            target = text[len("delete file "):].strip()
            return {
                "requires_confirmation": True,
                "message": f"Are you sure you want to delete '{target}'? (yes/no)",
                "pending_action": {"type": "delete_file", "target": target},
            }

        if t.startswith("list files "):
            path = Path(text[len("list files "):].strip())
            if not path.exists() or not path.is_dir():
                return "Directory not found."
            files = [p.name for p in path.iterdir()]
            return "\n".join(files[:300]) or "No files."

        # SYSTEM
        if t == "system status":
            vm = psutil.virtual_memory()
            du = psutil.disk_usage("/")
            batt = psutil.sensors_battery()
            batt_text = f"{batt.percent}%" if batt else "N/A"
            return (
                f"OS: {platform.system()} {platform.release()}\n"
                f"CPU: {psutil.cpu_percent()}%\n"
                f"RAM: {vm.percent}%\n"
                f"Disk: {du.percent}%\n"
                f"Battery: {batt_text}"
            )

        if t.startswith("open "):
            target = text[5:].strip()
            try:
                if platform.system() == "Windows":
                    os.startfile(target)  # type: ignore[attr-defined]
                elif platform.system() == "Darwin":
                    subprocess.run(["open", target], check=False)
                else:
                    subprocess.run(["xdg-open", target], check=False)
                return f"Opened: {target}"
            except Exception as e:
                return f"Open failed: {e}"

        if t.startswith("run "):
            cmd = text[len("run "):].strip()
            return {
                "requires_confirmation": True,
                "message": f"Run system command '{cmd}' ? (yes/no)",
                "pending_action": {"type": "run_command", "target": cmd},
            }

        return None

    async def execute_pending(self, action: dict, web_search):
        atype = action.get("type")
        target = action.get("target", "")

        if atype == "delete_file":
            path = Path(target)
            if not path.exists():
                return "File not found."
            try:
                path.unlink()
                return f"Deleted: {path}"
            except Exception as e:
                return f"Delete failed: {e}"

        if atype == "run_command":
            try:
                try:
                    args = shlex.split(target)
                    result = subprocess.run(args, capture_output=True, text=True, timeout=20)
                except Exception:
                    result = subprocess.run(target, shell=True, capture_output=True, text=True, timeout=20)
                output = (result.stdout or result.stderr).strip()
                return f"Exit code: {result.returncode}\n{output[:3000]}"
            except Exception as e:
                return f"Command failed: {e}"

        return "Unknown pending action."

    def _extract_weather_city(self, text: str):
        t = text.lower().strip()
        t = re.sub(r"[?.,!]", "", t)

        patterns = [
            r"^weather in (.+)$",
            r"^search weather in (.+)$",
            r"^tell me weather of (.+)$",
            r"^tell me the weather of (.+)$",
            r"^what is the current weather in (.+)$",
            r"^what is the weather in (.+)$",
            r"^whats the weather in (.+)$",
            r"^current weather in (.+)$",
            r"^temperature in (.+)$",
            r"^(.+)\s+weather$",
            r"^(.+)\s+weather today$",
        ]

        for p in patterns:
            m = re.match(p, t)
            if m:
                city = m.group(1).strip()
                city = re.sub(r"\b(today|now|right now|please)\b", "", city).strip()
                return city

        if "weather" in t and " in " in t:
            city = t.split(" in ", 1)[1].strip()
            city = re.sub(r"\b(today|now|right now|please)\b", "", city).strip()
            return city

        return None

    def _get_live_weather(self, city: str) -> str:
        if not self.openweather_api_key:
            return "OPENWEATHER_API_KEY missing in .env"

        try:
            url = "https://api.openweathermap.org/data/2.5/weather"
            params = {"q": city, "appid": self.openweather_api_key, "units": "metric"}
            r = requests.get(url, params=params, timeout=10)

            if r.status_code == 404:
                return f"City '{city}' not found."
            if r.status_code != 200:
                return f"Weather API error ({r.status_code})."

            d = r.json()
            name = d.get("name", city.title())
            country = d.get("sys", {}).get("country", "")
            desc = d.get("weather", [{}])[0].get("description", "N/A")
            temp = d.get("main", {}).get("temp", "N/A")
            feels = d.get("main", {}).get("feels_like", "N/A")
            hum = d.get("main", {}).get("humidity", "N/A")
            wind = d.get("wind", {}).get("speed", "N/A")

            return (
                f"🌤 Weather in {name}, {country}\n"
                f"- Condition: {desc}\n"
                f"- Temperature: {temp}°C\n"
                f"- Feels like: {feels}°C\n"
                f"- Humidity: {hum}%\n"
                f"- Wind: {wind} m/s"
            )
        except Exception as e:
            return f"Weather fetch failed: {e}"

    def _help_text(self):
        return (
            "EDITH commands:\n"
            "- weather in <city>\n"
            "- tell me weather of <city>\n"
            "- search <query>\n"
            "- system status\n"
            "- create/read/delete/list files\n"
            "- run <command> (confirmation needed)\n"
            "- exit"
        )
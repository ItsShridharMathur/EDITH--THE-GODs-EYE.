from core.commands import CommandRouter
from core.memory import MemoryStore
from nlp.groq_client import GroqClient
from nlp.tts import TTS
from search.web import WebSearch


class Orchestrator:
    """
    Unified orchestrator for CLI + GUI.
    Supports:
    - command routing
    - confirmation flow
    - modes (chat / assistant)
    - remember/recall
    """

    def __init__(self, config):
        self.config = config
        self.groq = GroqClient(config)
        self.memory = MemoryStore(config.DB_PATH)
        self.search = WebSearch(openweather_api_key=getattr(config, "OPENWEATHER_API_KEY", "05dae85c1eeba9c43924fce31778ce9b"))
        self.commands = CommandRouter(
            groq_client=self.groq,
            openweather_api_key=getattr(config, "OPENWEATHER_API_KEY", "")
        )
        self.tts = TTS(enabled=config.ENABLE_TTS)

        self.pending_action = None
        self.mode = "assistant"  # assistant | chat

    async def handle(self, user_input: str) -> str:
        text = user_input.strip()
        self.memory.log("user", text)

        # --- built-in mode switches ---
        low = text.lower()
        if low == "mode chat":
            self.mode = "chat"
            reply = "Switched to chat mode."
            self._finalize(reply)
            return reply
        if low == "mode assistant":
            self.mode = "assistant"
            reply = "Switched to assistant mode."
            self._finalize(reply)
            return reply

        # --- lightweight memory commands ---
        if low.startswith("remember "):
            note = text[len("remember "):].strip()
            self.memory.set_note(note)
            reply = "Noted."
            self._finalize(reply)
            return reply

        if low == "recall":
            note = self.memory.get_note()
            reply = note if note else "I don't have any saved note yet."
            self._finalize(reply)
            return reply

        # --- pending confirmation flow ---
        if self.pending_action is not None:
            decision = low
            if decision in {"yes", "y", "confirm"}:
                result = await self.commands.execute_pending(self.pending_action, self.search)
                self.pending_action = None
                self._finalize(result)
                return result
            elif decision in {"no", "n", "cancel"}:
                self.pending_action = None
                result = "Cancelled."
                self._finalize(result)
                return result
            else:
                result = "Please reply with 'yes' or 'no'."
                self._finalize(result)
                return result

        # --- assistant mode: command-first ---
        if self.mode == "assistant":
            cmd_result = await self.commands.try_execute(text, self.search)

            if isinstance(cmd_result, dict) and cmd_result.get("requires_confirmation"):
                self.pending_action = cmd_result.get("pending_action")
                msg = cmd_result.get("message", "This action needs confirmation. Type yes/no.")
                self._finalize(msg)
                return msg

            if isinstance(cmd_result, str):
                self._finalize(cmd_result)
                return cmd_result

        # --- chat fallback / chat mode ---
        reply = await self.groq.chat(text)
        self._finalize(reply)
        return reply

    def _finalize(self, assistant_text: str):
        self.memory.log("assistant", assistant_text)
        self.tts.speak(assistant_text)
class TTS:
    def __init__(self, enabled: bool = False):
        self.enabled = enabled
        self.engine = None
        if enabled:
            try:
                import pyttsx3
                self.engine = pyttsx3.init()
            except Exception:
                self.enabled = False

    def speak(self, text: str):
        if not self.enabled or not self.engine:
            return
        self.engine.say(text)
        self.engine.runAndWait()
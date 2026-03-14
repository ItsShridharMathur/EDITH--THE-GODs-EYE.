import asyncio
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QPushButton, QLabel
)
from PyQt6.QtCore import QThread, pyqtSignal


class Worker(QThread):
    done = pyqtSignal(str)
    fail = pyqtSignal(str)

    def __init__(self, orchestrator, text: str):
        super().__init__()
        self.orchestrator = orchestrator
        self.text = text

    def run(self):
        try:
            result = asyncio.run(self.orchestrator.handle(self.text))
            self.done.emit(result)
        except Exception as e:
            self.fail.emit(str(e))


class EdithWindow(QMainWindow):
    def __init__(self, orchestrator):
        super().__init__()
        self.orchestrator = orchestrator
        self.worker = None

        self.setWindowTitle("EDITH - Step 3 GUI")
        self.resize(900, 600)

        root = QWidget()
        self.setCentralWidget(root)

        layout = QVBoxLayout(root)

        self.mode_label = QLabel("Mode: assistant")
        layout.addWidget(self.mode_label)

        self.chat = QTextEdit()
        self.chat.setReadOnly(True)
        layout.addWidget(self.chat)

        row = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("Type message... (try: help, mode chat, weather in delhi)")
        self.input.returnPressed.connect(self.send_message)
        row.addWidget(self.input)

        self.send_btn = QPushButton("Send")
        self.send_btn.clicked.connect(self.send_message)
        row.addWidget(self.send_btn)

        layout.addLayout(row)

        self.append("EDITH", "GUI started. Type 'help' to see commands.")

    def append(self, role: str, text: str):
        self.chat.append(f"<b>{role}:</b> {text}")

    def send_message(self):
        text = self.input.text().strip()
        if not text:
            return
        self.input.clear()
        self.append("You", text)

        self.send_btn.setEnabled(False)
        self.worker = Worker(self.orchestrator, text)
        self.worker.done.connect(self.on_done)
        self.worker.fail.connect(self.on_fail)
        self.worker.start()

    def on_done(self, response: str):
        self.append("EDITH", response)
        self.mode_label.setText(f"Mode: {self.orchestrator.mode}")
        self.send_btn.setEnabled(True)

    def on_fail(self, err: str):
        self.append("EDITH-ERROR", err)
        self.send_btn.setEnabled(True)
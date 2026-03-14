import asyncio
import argparse
import sys

from config import Config
from core.orchestrator import Orchestrator


def run_gui(config: Config):
    from PyQt6.QtWidgets import QApplication
    from gui.app import EdithWindow

    app = QApplication(sys.argv)
    orchestrator = Orchestrator(config)
    window = EdithWindow(orchestrator)
    window.show()
    sys.exit(app.exec())


async def run_cli(config: Config):
    orchestrator = Orchestrator(config)

    print("🤖 EDITH started (CLI). Type 'help' or 'exit'.\n")
    while True:
        user_input = input("You: ").strip()
        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit"}:
            print("EDITH: Goodbye!")
            break

        response = await orchestrator.handle(user_input)
        print(f"EDITH: {response}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--gui", action="store_true", help="Run with PyQt GUI")
    args = parser.parse_args()

    cfg = Config()
    cfg.validate()

    if args.gui:
        run_gui(cfg)
    else:
        asyncio.run(run_cli(cfg))
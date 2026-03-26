"""
ui/input.py
Player input handling and command parsing.
"""


def get_input(prompt: str = "> ") -> str:
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        return "quit"


def parse_command(raw: str) -> tuple[str, list[str]]:
    """Split raw input into command + args."""
    parts = raw.strip().lower().split()
    if not parts:
        return "", []
    cmd = parts[0]
    args = parts[1:]
    return cmd, args

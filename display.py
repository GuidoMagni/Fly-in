"""Colored terminal output."""
import sys
from typing import Dict, List

from models import Move, Network
from simulation import Stats

ANSI: Dict[str, str] = {
    "black": "30", "red": "31", "green": "32", "yellow": "33",
    "blue": "34", "magenta": "35", "purple": "35", "cyan": "36",
    "white": "37", "gray": "90", "grey": "90", "orange": "38;5;208",
    "brown": "38;5;94", "pink": "38;5;213", "gold": "38;5;220",
    "violet": "38;5;135", "maroon": "38;5;88", "darkred": "38;5;88",
    "lime": "38;5;118", "crimson": "38;5;161",
}


class Display:
    """Prints the simulation, one line per turn, colored by zone."""

    def __init__(self, network: Network) -> None:
        """Enable colors only on a terminal that is not opted out."""
        self.network = network
        self.colors = sys.stdout.isatty()

    def paint(self, text: str, color: str) -> str:
        """Wrap text in the ANSI code of a color name, if known."""
        code = ANSI.get(color.lower()) if color else None
        if not self.colors or code is None:
            return text
        return f"\033[{code}m{text}\033[0m"

    def line(self, batch: List[Move]) -> str:
        """Format one turn; each move takes its destination zone color."""
        tokens = []
        for move in batch:
            color = self.network.zones[move.zone].color or ""
            tokens.append(self.paint(f"D{move.drone}-{move.label}", color))
        return " ".join(tokens)

    def show(self, turns: List[List[Move]], stats: Stats) -> None:
        """Print every turn, then a summary on stderr."""
        for batch in turns:
            print(self.line(batch))
        print(f"Turns: {stats.turns} | Drones: {stats.drones} | "
              f"Moves: {stats.moves} | Avg arrival: {stats.avg_arrival:.2f} "
              f"| Moves/turn: {stats.moves_per_turn:.2f}", file=sys.stderr)

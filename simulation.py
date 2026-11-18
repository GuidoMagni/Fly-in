"""Turn-by-turn replay and validation of a schedule."""
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

from models import Move, Network, ZoneType


class SimulationError(Exception):
    """Raised when a schedule breaks a movement or capacity rule."""


@dataclass
class Stats:
    """Figures describing a finished simulation."""

    turns: int
    drones: int
    moves: int
    avg_arrival: float
    moves_per_turn: float


class Simulation:
    """Replays the moves and checks every rule on each turn."""

    def __init__(self, network: Network, moves: List[Move]) -> None:
        """Keep the network and the moves to replay."""
        self.network = network
        self.moves = moves
        self.arrival: Dict[int, int] = {}

    def run(self) -> List[List[Move]]:
        """Return the moves grouped per turn, or raise on a violation."""
        net = self.network
        last = max((m.turn for m in self.moves), default=0)
        by_turn: List[List[Move]] = [[] for _ in range(last)]
        for move in self.moves:
            by_turn[move.turn - 1].append(move)
        pos: Dict[int, Optional[str]] = {
            d: net.start.name for d in range(1, net.nb_drones + 1)}
        for turn, batch in enumerate(by_turn, 1):
            self._step(turn, batch, pos)
        if any(p != net.end.name for p in pos.values()):
            raise SimulationError("some drones did not reach the end")
        return by_turn

    def _step(self, turn: int, batch: List[Move],
              pos: Dict[int, Optional[str]]) -> None:
        net = self.network
        links: Dict[Tuple[str, str], int] = {}
        moved: Set[int] = set()
        for move in batch:
            if move.drone in moved:
                raise SimulationError(
                    f"turn {turn}: D{move.drone} moves twice")
            moved.add(move.drone)
            if move.origin is None:
                if pos[move.drone] is not None:
                    raise SimulationError(f"turn {turn}: bad flight state")
            elif (pos[move.drone] != move.origin
                  or move.conn.other(move.origin) != move.zone):
                raise SimulationError(f"turn {turn}: illegal D{move.drone}")
            if net.zones[move.zone].zone_type is ZoneType.BLOCKED:
                raise SimulationError(f"turn {turn}: blocked zone entered")
            links[move.conn.key] = links.get(move.conn.key, 0) + 1
            if links[move.conn.key] > move.conn.max_link_capacity:
                raise SimulationError(f"turn {turn}: {move.conn.name} full")
            arrived = move.label == move.zone
            pos[move.drone] = move.zone if arrived else None
            if arrived and move.zone == net.end.name:
                self.arrival[move.drone] = turn
        counts: Dict[str, int] = {}
        for place in pos.values():
            if place is not None:
                counts[place] = counts.get(place, 0) + 1
        for name, count in counts.items():
            if count > net.zones[name].capacity:
                raise SimulationError(f"turn {turn}: {name} over capacity")

    def stats(self, turns: int) -> Stats:
        """Return figures about the replayed simulation."""
        drones = self.network.nb_drones
        avg = sum(self.arrival.values()) / drones if drones else 0.0
        return Stats(turns, drones, len(self.moves), avg,
                     len(self.moves) / turns if turns else 0.0)

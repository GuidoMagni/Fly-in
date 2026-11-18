"""Data model of the Fly-in drone network."""
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple

UNLIMITED: int = 10 ** 9


class ZoneType(Enum):
    """Kinds of zones."""

    NORMAL = "normal"
    BLOCKED = "blocked"
    RESTRICTED = "restricted"
    PRIORITY = "priority"


@dataclass
class Zone:
    """A node of the network."""

    name: str
    x: int
    y: int
    zone_type: ZoneType = ZoneType.NORMAL
    color: Optional[str] = None
    max_drones: int = 1
    is_start: bool = False
    is_end: bool = False

    @property
    def capacity(self) -> int:
        """Return how many drones the zone can hold at once."""
        if self.is_start or self.is_end:
            return UNLIMITED
        return self.max_drones

    @property
    def move_cost(self) -> int:
        """Return the number of turns needed to enter the zone."""
        return 2 if self.zone_type is ZoneType.RESTRICTED else 1


@dataclass
class Connection:
    """A bidirectional edge between two zones."""

    first: str
    second: str
    max_link_capacity: int = 1

    @property
    def name(self) -> str:
        """Return the connection name as written in the map."""
        return f"{self.first}-{self.second}"

    @property
    def key(self) -> Tuple[str, str]:
        """Return an order-independent identifier."""
        return (min(self.first, self.second), max(self.first, self.second))

    def other(self, zone: str) -> str:
        """Return the endpoint opposite to the given zone."""
        return self.second if zone == self.first else self.first


@dataclass
class Move:
    """One drone movement displayed on a turn line.

    label is the zone name, or the connection name while in flight.
    origin is the zone left on this turn (None when continuing a flight).
    """

    drone: int
    turn: int
    label: str
    zone: str
    conn: Connection
    origin: Optional[str]


class Network:
    """The graph of zones and connections."""

    def __init__(self, nb_drones: int, zones: List[Zone],
                 connections: List[Connection]) -> None:
        """Build the network and its adjacency lists."""
        self.nb_drones: int = nb_drones
        self.zones: Dict[str, Zone] = {z.name: z for z in zones}
        self.connections: Dict[Tuple[str, str], Connection] = {
            c.key: c for c in connections}
        self.start: Zone = next(z for z in zones if z.is_start)
        self.end: Zone = next(z for z in zones if z.is_end)
        self._adjacency: Dict[str, List[Tuple[Zone, Connection]]] = {
            name: [] for name in self.zones}
        for conn in connections:
            first, second = self.zones[conn.first], self.zones[conn.second]
            if second.zone_type is not ZoneType.BLOCKED:
                self._adjacency[first.name].append((second, conn))
            if first.zone_type is not ZoneType.BLOCKED:
                self._adjacency[second.name].append((first, conn))

    def neighbors(self, name: str) -> List[Tuple[Zone, Connection]]:
        """Return the enterable zones adjacent to a zone."""
        return self._adjacency[name]

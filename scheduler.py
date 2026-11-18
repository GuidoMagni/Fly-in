"""Routing of the drones on a time-expanded graph."""
import heapq
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from models import Connection, Move, Network, Zone, ZoneType

Cost = Tuple[int, int]


class SchedulingError(Exception):
    """Raised when no valid schedule exists."""


@dataclass
class Node:
    """Best known way to be in a zone at a given turn."""

    cost: Cost
    prev: Optional[Tuple[str, int]]
    conn: Optional[Connection]


@dataclass
class Hop:
    """A wait (conn is None) or a move between two (zone, turn) states."""

    src: str
    t_src: int
    dst: str
    t_dst: int
    conn: Optional[Connection]


class Reservations:
    """Zone and link usage already committed, turn by turn."""

    def __init__(self) -> None:
        """Start with nothing reserved."""
        self._zones: Dict[Tuple[str, int], int] = {}
        self._links: Dict[Tuple[Tuple[str, str], int], int] = {}

    def zone_free(self, zone: Zone, turn: int) -> bool:
        """Tell whether the zone can take one more drone at turn."""
        return self._zones.get((zone.name, turn), 0) < zone.capacity

    def link_free(self, conn: Connection, turn: int) -> bool:
        """Tell whether the connection can take one more drone at turn."""
        return self._links.get((conn.key, turn), 0) < conn.max_link_capacity

    def hold_zone(self, name: str, turn: int) -> None:
        """Reserve one place in a zone at turn."""
        key = (name, turn)
        self._zones[key] = self._zones.get(key, 0) + 1

    def hold_link(self, conn: Connection, turn: int) -> None:
        """Reserve one place on a connection at turn."""
        key = (conn.key, turn)
        self._links[key] = self._links.get(key, 0) + 1


class Scheduler:
    """Plans every drone, one after the other, around earlier plans.

    Each drone gets the earliest-arrival path in the (zone, turn) graph.
    Ties are broken by fewer non-priority zones, then fewer waits spent
    outside the start zone.
    """

    def __init__(self, network: Network) -> None:
        """Keep the network to route on."""
        self.network = network
        self.horizon = 0

    def plan(self) -> List[Move]:
        """Return the moves of all drones, sorted by turn."""
        base = self._min_turns()
        self.horizon = (base + 2) * (self.network.nb_drones + 1)
        reservations = Reservations()
        moves: List[Move] = []
        for drone in range(1, self.network.nb_drones + 1):
            hops = self._search(reservations)
            if hops is None:
                raise SchedulingError(f"no schedule found for D{drone}")
            moves.extend(self._commit(drone, hops, reservations))
        moves.sort(key=lambda m: (m.turn, m.drone))
        return moves

    def _min_turns(self) -> int:
        """Dijkstra on turn costs, ignoring capacities."""
        start, end = self.network.start.name, self.network.end.name
        dist: Dict[str, int] = {start: 0}
        heap: List[Tuple[int, str]] = [(0, start)]
        while heap:
            d, name = heapq.heappop(heap)
            if d > dist[name]:
                continue
            if name == end:
                return d
            for zone, _ in self.network.neighbors(name):
                nd = d + zone.move_cost
                if nd < dist.get(zone.name, nd + 1):
                    dist[zone.name] = nd
                    heapq.heappush(heap, (nd, zone.name))
        raise SchedulingError("no path from start to end")

    def _search(self, res: Reservations) -> Optional[List[Hop]]:
        """Layer-by-layer search for the earliest arrival at the end."""
        start, end = self.network.start.name, self.network.end.name
        layers: Dict[int, Dict[str, Node]] = {
            0: {start: Node((0, 0), None, None)}}
        for turn in range(self.horizon + 1):
            layer = layers.get(turn, {})
            if end in layer:
                return self._rebuild(layers, turn)
            for name, node in layer.items():
                self._expand(name, turn, node, res, layers)
        return None

    def _expand(self, name: str, turn: int, node: Node, res: Reservations,
                layers: Dict[int, Dict[str, Node]]) -> None:
        zone = self.network.zones[name]
        if res.zone_free(zone, turn + 1):
            wait = 0 if zone.is_start else 1
            self._relax(layers, turn + 1, name,
                        Node((node.cost[0], node.cost[1] + wait),
                             (name, turn), None))
        for nxt, conn in self.network.neighbors(name):
            arrive = turn + nxt.move_cost
            if not all(res.link_free(conn, t)
                       for t in range(turn + 1, arrive + 1)):
                continue
            if not res.zone_free(nxt, arrive):
                continue
            penalty = 0 if nxt.zone_type is ZoneType.PRIORITY else 1
            self._relax(layers, arrive, nxt.name,
                        Node((node.cost[0] + penalty, node.cost[1]),
                             (name, turn), conn))

    def _relax(self, layers: Dict[int, Dict[str, Node]], turn: int,
               name: str, node: Node) -> None:
        layer = layers.setdefault(turn, {})
        if name not in layer or node.cost < layer[name].cost:
            layer[name] = node

    def _rebuild(self, layers: Dict[int, Dict[str, Node]],
                 turn: int) -> List[Hop]:
        hops: List[Hop] = []
        name = self.network.end.name
        node = layers[turn][name]
        while node.prev is not None:
            prev_name, prev_turn = node.prev
            hops.append(Hop(prev_name, prev_turn, name, turn, node.conn))
            name, turn = prev_name, prev_turn
            node = layers[turn][name]
        hops.reverse()
        return hops

    def _commit(self, drone: int, hops: List[Hop],
                res: Reservations) -> List[Move]:
        moves: List[Move] = []
        for hop in hops:
            res.hold_zone(hop.dst, hop.t_dst)
            if hop.conn is None:
                continue
            for turn in range(hop.t_src + 1, hop.t_dst + 1):
                res.hold_link(hop.conn, turn)
            if hop.t_dst - hop.t_src == 1:
                moves.append(Move(drone, hop.t_dst, hop.dst, hop.dst,
                                  hop.conn, hop.src))
            else:
                moves.append(Move(drone, hop.t_src + 1, hop.conn.name,
                                  hop.dst, hop.conn, hop.src))
                moves.append(Move(drone, hop.t_dst, hop.dst, hop.dst,
                                  hop.conn, None))
        return moves

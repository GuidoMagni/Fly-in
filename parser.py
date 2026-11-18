"""Parser for the Fly-in map format."""
import re
from typing import Dict, List, Optional, Set, Tuple

from models import Connection, Network, Zone, ZoneType


class ParseError(Exception):
    """Raised when the map file is invalid."""


ZONE_RE = re.compile(
    r"^(start_hub|end_hub|hub):\s*(\S+)\s+(\S+)\s+(\S+)\s*(?:\[(.*)\])?$")
CONN_RE = re.compile(r"^connection:\s*([^\s\[]+)\s*(?:\[(.*)\])?$")
DRONES_RE = re.compile(r"^nb_drones:\s*(\S+)$")


class MapParser:
    """Reads a map file and builds a Network."""

    def parse(self, path: str) -> Network:
        """Parse the file at path and return the network."""
        try:
            with open(path, "r", encoding="utf-8") as handle:
                lines = handle.read().splitlines()
        except (OSError, UnicodeDecodeError) as exc:
            raise ParseError(f"cannot read '{path}': {exc}") from exc

        nb_drones: Optional[int] = None
        zones: List[Zone] = []
        names: Set[str] = set()
        conns: List[Connection] = []
        seen: Set[Tuple[str, str]] = set()

        for lineno, raw in enumerate(lines, 1):
            line = raw.split("#", 1)[0].strip()
            if not line:
                continue
            if nb_drones is None:
                nb_drones = self._parse_drones(line, lineno)
            elif line.startswith("connection:"):
                conn = self._parse_connection(line, lineno, names)
                if conn.key in seen:
                    raise ParseError(
                        f"line {lineno}: duplicate connection '{conn.name}'")
                seen.add(conn.key)
                conns.append(conn)
            else:
                zone = self._parse_zone(line, lineno, names)
                names.add(zone.name)
                zones.append(zone)

        if nb_drones is None:
            raise ParseError("missing 'nb_drones' definition")
        if sum(z.is_start for z in zones) != 1:
            raise ParseError("exactly one start_hub is required")
        if sum(z.is_end for z in zones) != 1:
            raise ParseError("exactly one end_hub is required")
        return Network(nb_drones, zones, conns)

    def _parse_drones(self, line: str, lineno: int) -> int:
        match = DRONES_RE.match(line)
        if not match:
            raise ParseError(
                f"line {lineno}: first line must be 'nb_drones: <number>'")
        return self._positive(match.group(1), "nb_drones", lineno)

    def _parse_zone(self, line: str, lineno: int, names: Set[str]) -> Zone:
        match = ZONE_RE.match(line)
        if not match:
            raise ParseError(f"line {lineno}: invalid zone definition")
        kind, name, sx, sy, raw_meta = match.groups()
        if "-" in name:
            raise ParseError(f"line {lineno}: dash not allowed in '{name}'")
        if name in names:
            raise ParseError(f"line {lineno}: duplicate zone '{name}'")
        if not (re.fullmatch(r"-?\d+", sx) and re.fullmatch(r"-?\d+", sy)):
            raise ParseError(f"line {lineno}: coordinates must be integers")
        meta = self._metadata(raw_meta, {"zone", "color", "max_drones"},
                              lineno)
        zone = Zone(name, int(sx), int(sy), is_start=kind == "start_hub",
                    is_end=kind == "end_hub")
        if "zone" in meta:
            try:
                zone.zone_type = ZoneType(meta["zone"])
            except ValueError:
                raise ParseError(
                    f"line {lineno}: invalid zone type '{meta['zone']}'"
                ) from None
        if "color" in meta:
            zone.color = meta["color"]
        if "max_drones" in meta:
            zone.max_drones = self._positive(meta["max_drones"],
                                             "max_drones", lineno)
        return zone

    def _parse_connection(self, line: str, lineno: int,
                          names: Set[str]) -> Connection:
        match = CONN_RE.match(line)
        if not match:
            raise ParseError(f"line {lineno}: invalid connection definition")
        parts = match.group(1).split("-")
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise ParseError(
                f"line {lineno}: connection must be '<zone1>-<zone2>'")
        for part in parts:
            if part not in names:
                raise ParseError(f"line {lineno}: unknown zone '{part}'")
        if parts[0] == parts[1]:
            raise ParseError(f"line {lineno}: connection to itself")
        meta = self._metadata(match.group(2), {"max_link_capacity"}, lineno)
        conn = Connection(parts[0], parts[1])
        if "max_link_capacity" in meta:
            conn.max_link_capacity = self._positive(
                meta["max_link_capacity"], "max_link_capacity", lineno)
        return conn

    def _metadata(self, raw: Optional[str], allowed: Set[str],
                  lineno: int) -> Dict[str, str]:
        result: Dict[str, str] = {}
        if raw is None:
            return result
        for token in raw.split():
            key, sep, value = token.partition("=")
            if not sep or not value or key not in allowed:
                raise ParseError(
                    f"line {lineno}: invalid metadata '{token}'")
            if key in result:
                raise ParseError(f"line {lineno}: duplicate key '{key}'")
            result[key] = value
        return result

    def _positive(self, value: str, key: str, lineno: int) -> int:
        if not value.isdigit() or int(value) <= 0:
            raise ParseError(
                f"line {lineno}: {key} must be a positive integer")
        return int(value)

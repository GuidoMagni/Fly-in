*This project has been created as part of the 42 curriculum by gumagni.*

# Fly-in

## Description

Routes a fleet of drones from a start zone to an end zone through a graph
of zones, in as few simulation turns as possible, respecting zone types,
zone capacities (`max_drones`) and link capacities (`max_link_capacity`).

## Instructions

```
make install
make run MAP=maps/example.txt     # or: python3 main.py <map_file>
make lint                         # flake8 + mypy
```

Moves go to stdout (one line per turn); the summary goes to stderr.

## Algorithm

- `map_parser.py`: validates the format, reports `line N: cause` errors.
- `scheduler.py`: drones are planned one after the other on a
  time-expanded graph of `(zone, turn)` states. For each drone, a layered
  search finds the earliest arrival at the end zone, given the zone/link
  usage already reserved by previous drones. Waiting is a state transition;
  restricted zones take 2 turns and hold the link on both turns. Ties are
  broken by fewer non-priority zones, then fewer waits outside the start.
  Dijkstra (turn costs, no capacities) only gives the search horizon and
  detects unreachable ends.
- `simulation.py`: replays the schedule turn by turn and checks every rule
  (adjacency, blocked zones, zone and link capacities, flights completed).
- `display.py`: colors each move with the color of its destination zone
  (ANSI, only on a terminal) and prints turns, moves, average arrival time
  and moves per turn.

Complexity: roughly O(D * H * (Z + E)) for D drones, horizon H (turns)
and Z zones / E connections. Reservations are stored in dictionaries
(memory proportional to the occupied `(zone, turn)` and `(link, turn)`).
Paths are computed once per drone and never recomputed.

## Visual representation

Colored move tokens make it easy to follow which zones drones enter; the
stderr summary gives the metrics to compare runs.

## Example

Input: `maps/example.txt`. Output:

```
D1-corridorA D3-hub-roof1
D1-tunnelB D2-corridorA D3-roof1
D1-goal D2-tunnelB D3-roof2 D4-corridorA
D2-goal D3-goal D4-tunnelB D5-corridorA
D4-goal D5-tunnelB
D5-goal
```

## Resources

- Time-expanded networks / multi-agent path finding (Cooperative A*).
- Python docs: `heapq`, `dataclasses`, `typing`; flake8 and mypy docs.
- AI usage: <describe the tasks and parts where AI was used>.

"""Fly-in entry point: python3 main.py <map_file>."""
import sys
from typing import List

from display import Display
from parser import MapParser, ParseError
from scheduler import Scheduler, SchedulingError
from simulation import Simulation, SimulationError


def main(argv: List[str]) -> int:
    """Parse the map, plan, validate and display the simulation."""
    if len(argv) != 2:
        print("Usage: python3 main.py <map_file>", file=sys.stderr)
        return 1
    try:
        network = MapParser().parse(argv[1])
        moves = Scheduler(network).plan()
        simulation = Simulation(network, moves)
        turns = simulation.run()
        Display(network).show(turns, simulation.stats(len(turns)))
    except (ParseError, SchedulingError, SimulationError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Unexpected error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

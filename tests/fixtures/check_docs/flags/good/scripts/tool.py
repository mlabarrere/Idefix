import argparse

from src.cli import add_mission_arg


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("step", nargs="?", default="all")
    ap.add_argument("-n", "--count", type=int, default=1)
    ap.add_argument("--dry-run", action="store_true")
    add_mission_arg(ap)
    ap.parse_args()


if __name__ == "__main__":
    main()

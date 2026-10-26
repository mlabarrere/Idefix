import argparse


def add_mission_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--mission", default=None)

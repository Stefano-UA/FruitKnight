"""Entry point: ``python -m fruit_knight.main``."""

from __future__ import annotations

import argparse
import logging
import sys

from fruit_knight.config import ConfigError, load_config


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments.

    :param argv: argument list; ``sys.argv`` when omitted.
    :type argv: list[str] | None
    :return: parsed namespace.
    :rtype: argparse.Namespace
    """
    parser = argparse.ArgumentParser(prog="fruit_knight", description="Fruit Knight - webcam rehabilitation serious game")
    parser.add_argument("--config", help="path to an alternative settings.yaml")
    parser.add_argument("--no-camera", action="store_true", help="skip the webcam and play with the mouse")
    parser.add_argument("--verbose", action="store_true", help="enable debug logging")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Load configuration and run the application.

    :param argv: argument list; ``sys.argv`` when omitted.
    :type argv: list[str] | None
    :return: process exit code.
    :rtype: int
    """
    args = parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    try:
        cfg = load_config(args.config)
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2
    from fruit_knight.ui.app import App  # imported late so config errors do not need pygame

    App(cfg, use_camera=not args.no_camera).run()
    return 0


if __name__ == "__main__":
    sys.exit(main())

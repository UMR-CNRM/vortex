import argparse
import logging
import sys
from pathlib import Path
from typing import Any, Literal

import footprints
import yaml

import vortex
from vortex import toolbox

LOG = logging.getLogger()
LOG.addHandler(logging.StreamHandler())


def main() -> None:
    """
    Fetch/store a vortex resource from the command line.

    Files are fetched with the ``get`` subcommand and stored with the ``put``
    subcommand. The vortex resource description is provided via a yaml config
    file or via stdin.

    Example:

    ..code:: bash

        vtx get desc.yaml

    The config is a valid YAML document can contain the following keys:

    ..code:: yaml

        ---
        args: ... # the resource descrition
        addons: ... # a list of addons to load.

    Only ``args`` is required.
    ``addons`` is a list of addon arguments to pass to ``footprints.proxy.addon``.

    For example:

    ..code:: yaml

        ---
        args:
          remote: "path/to/my/file.txt"
          local: "file.txt"
          tube: "ftp"
          hostname: "hendrix.meteo.fr"
          unknown: true
        addons:
          - kind: grib

    :note: You can provide multiple yaml document separated via ``---``
    to execute multiple resources.
    """
    parser = argparse.ArgumentParser(
        description="Fetch and store resources using vortex."
    )
    parser.add_argument(
        "--addon",
        "-a",
        nargs="*",
        help="Addon to load. Multiple addons can be provided.",
    )
    parser.add_argument(
        "--log-level", type=str, default="INFO", help="Log level."
    )

    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    for name, help_text in [
        ("get", "Fetch data from data tree(s)"),
        ("put", "Store data from data tree(s)"),
    ]:
        sub = subparsers.add_parser(name, help=help_text)
        sub.add_argument(
            "path",
            type=str,
            nargs="?",
            default=None,
            help=(
                "Path to the config file to run. "
                "If not provided, will get the file from stdin."
            ),
        )

    args = parser.parse_args()

    LOG.setLevel(args.log_level)

    if args.path is not None:
        yaml_str = Path(args.path).read_text()
    else:
        yaml_str = sys.stdin.read()

    documents: list[dict[str, Any]] = []
    if yaml_str:
        documents = yaml.safe_load_all(yaml_str.strip())

    action = "input" if args.subcommand == "get" else "output"
    for document in documents:
        addons = document.get("addons", [])
        for addon in args.addon or []:
            addons.append({"kind": addon})
        vortex_cli(action, document.get("args", {}), addons)


def vortex_cli(
    action: Literal["input", "output"],
    args: dict[str, Any],
    addons: list[dict[str, Any]] | None = None,
) -> None:
    """
    Execute a vortex section and loads specified addons.

    :param section: The section to load.
    :param args: The section's arguments.
    :param addons: a list of addon arguments to pass to footprints.proxy.addon.
    """
    if addons is None:
        addons = []

    t = vortex.ticket()

    for addon in addons:
        LOG.info("Loading addon %s", addon)

        footprints.proxy.addon(**addon, shell=t.sh)

    if action == "input":
        toolbox.input(now=True, **args)
    elif action == "output":
        toolbox.output(now=True, **args)

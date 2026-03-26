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
    Run a vortex section via CLI.
    The argument of the section is provided via a yaml config file or via stdin.

    The config is a valid yaml document can contain the following keys:

    ..code:: yaml

        ---
        section: ...  # (input or output)
        args: ... # the section's arguments
        addons: ... # a list of addons to load.

    Only ``args`` is required. ``section`` will be ``input`` by default, or can be
    overriden using the ``--section`` argument to the script.

    ``addons`` is a list of addon arguments to pass to ``footprints.proxy.addon``.

    For example:

    ..code:: yaml

        ---
        section: input
        args:
          remote: "path/to/my/file.txt"
          local: "file.txt"
          tube: "ftp"
          hostname: "hendrix.meteo.fr"
          unknown: true
        addons:
          - kind: grib

    :note: You can provide multiple yaml document separated via ``---``
    to execute multiple sections.
    """
    parser = argparse.ArgumentParser(description="Save resource using vortex.")
    parser.add_argument(
        "path",
        type=str,
        nargs="?",
        default=None,
        help=(
            "Path to the config file to run. "
            "If not provided, will get the file from stdin."
        ),
    )
    parser.add_argument(
        "--section",
        "-s",
        type=str,
        default=None,
        choices=["input", "output"],
        help="Section to use (input or output).",
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
    args = parser.parse_args()

    LOG.setLevel(args.log_level)

    if args.path is not None:
        yaml_str = Path(args.path).read_text()
    else:
        yaml_str = sys.stdin.read()

    documents: list[dict[str, Any]] = []
    if yaml_str:
        documents = yaml.safe_load_all(yaml_str.strip())

    for document in documents:
        section = document.get("section", "input")
        addons = document.get("addons", [])
        if args.section is not None:
            section = args.section
        for addon in args.addon or []:
            addons.append({"kind": addon})
        vortex_cli(section, document.get("args", {}), addons)


def vortex_cli(
    section: Literal["input", "output"],
    args: dict[str, Any],
    addons: list[dict[str, Any]] | None = None,
) -> None:
    """
    Execute a section and loads specified addons.

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

    if section == "input":
        toolbox.input(now=True, **args)
    elif section == "output":
        toolbox.output(now=True, **args)

#!/usr/bin/env python3
"""Simple automation tool."""
import argparse
import asyncio
import itertools
import json
import logging
import os
import re
import sys
import time
import traceback
from typing import Tuple

import yaml

_LOGGER = logging.getLogger(__name__)

CHICKN_FILE = "chickn.yaml"


class InternalError(Exception):
    """Raised internally on error."""


async def _exec(cmd) -> Tuple[str, str]:
    _LOGGER.debug("Run command: %s", cmd)
    proc = await asyncio.create_subprocess_shell(
        cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )

    stdout, stderr = await proc.communicate()

    stdout = stdout.decode() if stdout else None
    stderr = stderr.decode() if stderr else None

    if proc.returncode != 0:
        raise InternalError(
            f"Command failed: {cmd}\n[STDOUT]\n{stdout}\n\n[STDERR]\n{stderr}"
        )

    return stdout, stderr


async def run_step(step, variables) -> None:
    """Run a step with given variables."""
    _LOGGER.info("Running step %s", step["name"])
    commands = [step["run"]] if isinstance(step["run"], str) else step["run"]

    for run_command in commands:
        command = run_command.format(**variables)
        retries = 1 + step.get("retries", 0)
        while retries > 0:
            retries -= 1
            try:
                await _exec(command)
                break
            except Exception:
                if retries == 0:
                    raise

                _LOGGER.warning(
                    "Command in step %s failed, trying again...", step["name"]
                )


async def run_pip(dependency_files, variables, force_reinstall=False) -> None:
    """Run pip and try to figure out if dependencies needs to be installed."""
    # Figure out which packages are installed
    stdout, _ = await _exec("pip list --format json")
    installed_packages = {
        package["name"]: package["version"] for package in json.loads(stdout)
    }
    _LOGGER.debug("Installed packages: %s", installed_packages)

    # Get all expected packages and if any of them mismatch, trigger installation
    expected_dependencies = {}
    for depfile in [filename.format(**variables) for filename in dependency_files]:
        _LOGGER.debug("Loading dependencies from %s", depfile)

        # NB: Sync code blocking event loop (fix at some point). Doesn't matter much
        # as nothing else runs in parallel.
        with open(depfile, "r", encoding="utf-8") as dep_handle:
            for line in dep_handle:
                match = re.match(r"(.*)==(.*)", line)
                if not match:
                    raise InternalError(f"Invalid dependency {line} in {depfile}")

                name, version = match.groups()
                expected_dependencies[name] = version.split(",")[0]

    _LOGGER.debug("Required versions: %s", expected_dependencies)

    # Compare what is installed to what is expected
    if not force_reinstall:
        for package in list(expected_dependencies.keys()):
            if installed_packages.get(package) == expected_dependencies[package]:
                del expected_dependencies[package]

    if expected_dependencies:
        _LOGGER.info(
            "Re-installing packages with mismatching versions: %s",
            ", ".join(
                [
                    f"{name}=={version} ({installed_packages.get(name)})"
                    for name, version in expected_dependencies.items()
                ]
            ),
        )

        await _exec(
            "pip install --upgrade "
            + ("--force-reinstall " if force_reinstall else "")
            + " ".join(
                [
                    name + "==" + version
                    for name, version in expected_dependencies.items()
                ]
            )
        )
    else:
        _LOGGER.info("All packages are up-to-date")


async def step_runner(name, coro) -> float:
    """Task function used to run a step."""
    start_time = time.time()
    await coro
    run_time = time.time() - start_time

    _LOGGER.info("Step %s finished in %.2fs", name, run_time)

    return run_time


# pylint: disable=too-few-public-methods
class TransformVariables(argparse.Action):
    """Transform variable overrides to internal representation."""

    def __call__(self, parser, namespace, values, option_string=None):
        """Parse variable definitions."""
        target = getattr(namespace, self.dest)
        for key, value in [value.split("=", maxsplit=1) for value in values]:
            target.setdefault(key, []).append(value)


async def appstart(  # pylint: disable=too-many-locals
    loop: asyncio.AbstractEventLoop,
) -> None:
    """Start function of script."""
    start_time = time.time()

    parser = argparse.ArgumentParser()
    parser.add_argument("steps", nargs="*", help="steps to run")
    parser.add_argument(
        "-v",
        "--variable",
        nargs="*",
        dest="variables",
        default={},
        help="set a variable",
        action=TransformVariables,
    )
    parser.add_argument(
        "-t",
        "--tags",
        nargs="*",
        default=[],
        action="append",
        help="tags for steps to run",
    )
    parser.add_argument(
        "-n", "--no-install", help="do not install dependencies", action="store_true"
    )
    parser.add_argument(
        "-f", "--force-pip", help="force install of dependencies", action="store_true"
    )
    parser.add_argument(
        "--no-venv", help="allow running without venv", action="store_true"
    )
    parser.add_argument(
        "-l", "--list", help="list available steps", action="store_true"
    )
    parser.add_argument("--debug", help="print debug information", action="store_true")

    args = parser.parse_args()

    # Do not run outside of venv unless check was disabled
    if not args.no_venv and "VIRTUAL_ENV" not in os.environ:
        _LOGGER.error("Not running in a virtual environment")
        return 1

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        stream=sys.stdout,
        datefmt="%Y-%m-%d %H:%M:%S",
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    with open(CHICKN_FILE, "r", encoding="utf-8") as _fh:
        chickn_file = yaml.safe_load(_fh)

    # Check if steps should be listed
    if args.list:
        all_steps = []
        for steps in chickn_file["pipeline"].values():
            for step in steps:
                all_steps.append(step["name"])
        print(", ".join(all_steps))
        return 0

    # Merge versions from chickn file with overrides from command line
    all_variables = chickn_file["variables"]
    all_variables.update(args.variables)
    variables = {
        name: " ".join(value) if isinstance(value, list) else value
        for name, value in chickn_file["variables"].items()
    }
    _LOGGER.debug("Variables: %s", variables)

    if not args.no_install:
        _LOGGER.info("Installing dependencies")
        await step_runner(
            "install_deps",
            run_pip(
                chickn_file["dependencies"]["files"],
                variables,
                force_reinstall=args.force_pip,
            ),
        )

    for stage in chickn_file["pipeline"]:
        tags = set(itertools.chain.from_iterable(args.tags))

        # Filter out steps specified by user
        steps = [
            step
            for step in chickn_file["pipeline"][stage]
            if (not args.steps or step["name"] in args.steps)
            and (not step.get("tags") or set(step["tags"]).intersection(tags))
        ]

        _LOGGER.info("Running %s with %d steps", stage, len(steps))
        tasks = [
            asyncio.ensure_future(step_runner(step["name"], run_step(step, variables)))
            for step in steps
        ]
        try:
            await asyncio.gather(*tasks)
        except Exception:
            failed_tasks = []

            _LOGGER.error("At least one task failed")
            for task in [
                task for task in tasks if task.done() and task.exception() is not None
            ]:
                ex = task.exception()
                task_name = steps[tasks.index(task)]["name"]

                _LOGGER.error(
                    "Task '%s' failed (%s): %s", task_name, type(ex).__name__, ex
                )
                if not isinstance(ex, InternalError):
                    traceback.print_tb(ex.__traceback__, file=sys.stderr)
                failed_tasks.append(task_name)

            for task in tasks:
                task.cancel()

            _LOGGER.error("Tasks failed: %s", ", ".join(failed_tasks))
            return 1

    _LOGGER.info("Finished in %.2f!", time.time() - start_time)

    return 0


def main() -> None:
    """Application start here."""
    if sys.platform == "win32":
        loop = asyncio.ProactorEventLoop()
        asyncio.set_event_loop(loop)
    else:
        loop = asyncio.get_event_loop()
    return loop.run_until_complete(appstart(loop))


if __name__ == "__main__":
    sys.exit(main())

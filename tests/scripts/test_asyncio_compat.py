"""Tests for Python 3.14+ asyncio compatibility.

Verifies that CLI entry points use asyncio.run() instead of
asyncio.get_event_loop(), which raises RuntimeError in Python 3.14
when no event loop exists.
"""

import subprocess
import sys

import pytest

SCRIPTS = ["atvremote", "atvscript", "atvlog", "atvproxy"]


@pytest.mark.parametrize("script", SCRIPTS)
def test_script_runs_without_preexisting_event_loop(script):
    """Verify scripts work via asyncio.run() without a pre-existing event loop.

    Running in a subprocess guarantees no event loop exists before the script
    starts, which is exactly the condition that breaks on Python 3.14 when
    asyncio.get_event_loop() is used instead of asyncio.run().

    The test passes --help so the script exits quickly without needing any
    network or device access. We assert that usage/help text appears in stdout,
    proving the script bootstrapped successfully rather than crashing with a
    RuntimeError from get_event_loop().

    Note: atvremote catches SystemExit (from argparse --help) and returns 1,
    so we do not assert on exit code -- only on successful output.
    """
    result = subprocess.run(
        [sys.executable, "-m", f"pyatv.scripts.{script}", "--help"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert "usage:" in result.stdout.lower(), (
        f"{script} --help produced no usage output.\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    # A RuntimeError from get_event_loop() would appear in stderr
    assert "RuntimeError" not in result.stderr, (
        f"{script} raised RuntimeError "
        f"(likely get_event_loop() without a running loop):\n"
        f"{result.stderr}"
    )

"""Unit tests for services.ephemeral.run_command."""

import importlib


def _run_command():
    return importlib.import_module("services.ephemeral").run_command


def test_run_command_success_strips_output():
    """A successful shell command returns True and stripped stdout."""
    success, stdout, stderr = _run_command()("echo '  hello  '")
    assert success is True
    assert stdout == "hello"
    assert stderr == ""


def test_run_command_failure_captures_stderr():
    """A failing shell command returns False and its stderr."""
    success, stdout, stderr = _run_command()("echo oops 1>&2; exit 3")
    assert success is False
    assert stdout == ""
    assert stderr == "oops"


def test_run_command_uses_shell_features():
    """Pipes work, confirming shell=True behaviour is preserved."""
    success, stdout, _ = _run_command()("printf 'a\\nb\\n' | wc -l")
    assert success is True
    assert stdout.strip() == "2"

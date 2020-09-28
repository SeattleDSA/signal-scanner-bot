import subprocess
from unittest import mock

import pytest


@pytest.fixture
def signal_module(env_module):
    from signal_scanner_bot import signal

    yield signal


@pytest.fixture
def subprocess_run_mock() -> subprocess.run:
    with mock.patch("subprocess.run") as run:
        yield run


@pytest.mark.parametrize(
    "recipient, group, expected",
    [
        ("333", False, ["333"]),
        (333, False, ["333"]),
        ("333", True, ["-g", "333"]),
    ],
)
def test_send_message(recipient, group, expected, signal_module, subprocess_run_mock):
    message = "sample message"
    signal_module.send_message(message, recipient, group=group)
    args = subprocess_run_mock.call_args.args[0]
    actual_message, *recipient_args = args[5:]
    assert actual_message == message
    expected_length = 2 if group else 1
    assert len(recipient_args) == expected_length
    assert recipient_args == expected


def test_panic(subprocess_run_mock, signal_module, env_module):
    error_text = "==sample error=="
    err = ValueError(error_text)
    signal_module.panic(err)
    args = subprocess_run_mock.call_args.args[0]
    assert args[6] == env_module.ADMIN_NUMBER
    assert error_text in args[5]

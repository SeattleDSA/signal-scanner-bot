import pytest


def test_env_success(monkeypatch, env_module):
    monkeypatch.setenv("TEST", "value")
    assert env_module._env("TEST") == "value"
    assert ("TEST", "value") in env_module._VARS


def test_env_fail(env_module):
    with pytest.raises(KeyError):
        env_module._env("MISSING")


def test_env_missing_pass(env_module):
    assert env_module._env("MISSING", fail=False) is None


def test_env_missing_default(env_module):
    assert env_module._env("MISSING", default=10) == 10


def test_env_fail_default(env_module):
    assert env_module._env("MISSING", fail=True, default=10) == 10

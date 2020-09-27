from datetime import datetime as dt

import pytest


@pytest.fixture
def filters_module(env_module):
    from signal_scanner_bot import filters

    yield filters


################################################################################
# Message timestamp
################################################################################
@pytest.mark.parametrize(
    "ts, convert, expected",
    [
        # TZ without convert
        (dt(2020, 1, 1, 1, 1, 1), False, dt(2020, 1, 1, 1, 1, 1)),
        # TZ with convert
        (dt(2020, 1, 1, 8, 1, 1), True, dt(2020, 1, 1, 1, 1, 1)),
    ],
)
def test_message_timestamp(ts, convert, expected, filters_module, env_module):
    env_module.TZ_UTC = convert
    data = {"timestamp": ts.timestamp() * 1000}
    actual = filters_module.message_timestamp(data, convert)
    assert actual == expected


def test_message_timestamp_failure(filters_module):
    data = {}
    with pytest.raises(KeyError):
        filters_module.message_timestamp(data)


################################################################################
# Signal filters
################################################################################
@pytest.mark.parametrize(
    "data, expected",
    [
        # Don't care
        ({}, True),
        ({"message": ""}, True),
        ({"message": False}, True),
        ({"message": 0}, True),
        # Do care
        ({"message": "actual message"}, False),
        ({"message": 1}, False),
    ],
)
def test_f_no_data(data, expected, filters_module):
    actual = filters_module._f_no_data(data)
    assert actual == expected


@pytest.mark.parametrize("data, listen_group, expected", [
    # Don't care
    ({}, False)
])
def test_f_no_group(data, listen_group, expected, filters_module, env_module):
    env_module.LISTEN_GROUP = listen_group
    actual = filters_module._f_no_group(data)
    assert actual == expected

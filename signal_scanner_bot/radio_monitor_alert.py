import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import aiohttp
import backoff
import pytz

from . import env


log = logging.getLogger(__name__)


def _convert_to_timestr(in_time: str) -> str:
    # Convert time string to datetime after converting it into proper ISO format
    # Add timezone awareness (source is in UTC) then output in specified TZ and
    # 12 hour format
    time_dt = datetime.fromisoformat(in_time.replace("Z", "+00:00"))
    time_dt_tz = time_dt.replace(tzinfo=pytz.utc)
    return time_dt_tz.astimezone(env.DEFAULT_TZ).strftime("%Y-%m-%d, %I:%M:%S %Z")


def _calculate_lookback_time() -> str:
    # Because time.timestamp() gives us time in the format 1633987202.136147 and
    # we want it in the format 1633987202136 we need to do some str manipulation.
    # First we get the current time in UTC, subtract a time delta equal to the
    # specified number of seconds defined in the RADIO_MONITOR_LOOKBACK, split
    # that timestamp on the decimal, then rejoin the str with the first three
    # numbers after the decimal.
    time = datetime.now(pytz.utc) - timedelta(seconds=(env.RADIO_MONITOR_LOOKBACK))
    time_stamp_array = str(time.timestamp()).split(".")
    return time_stamp_array[0] + time_stamp_array[1][:3]


async def get_openmhz_calls() -> Dict:
    lookback_time = _calculate_lookback_time()
    log.debug(f"Lookback is currently set to: {lookback_time}")
    async with aiohttp.ClientSession(raise_for_status=True) as session:
        async with session.get(
            env.OPENMHZ_URL, params={"time": lookback_time}
        ) as response:
            return (await response.json())["calls"]


async def get_pigs(calls: Dict) -> List[Tuple[Dict, str, str]]:
    interesting_pigs = []
    for call in calls:
        time = call["time"]
        # Due to requirements from aiohttp library it is required that the radios object be
        # of the forms:
        #  * {'key1': 'value1', 'key2': 'value2'}
        #  * {"key": ["value1", "value2"]}
        #  * [("key", "value1"), ("key", "value2")]
        #
        # more pointedly, it can not be
        #  * {"key": {"value1", "value2"}}
        #
        # because aiohttp will choke on it. See the following link for more details
        # https://docs.aiohttp.org/en/stable/client_quickstart.html#passing-parameters-in-urls
        radios = {"radio": list({f"7{radio['src']:0>5}" for radio in call["srcList"]})}
        if not len(radios["radio"]):
            continue
        async with aiohttp.ClientSession(raise_for_status=True) as session:
            async with session.get(env.RADIO_CHASER_URL, params=radios) as response:
                cops = await response.json()
        for cop in cops.values():
            if all(
                unit.lower() not in cop["unit_description"].lower()
                for unit in env.RADIO_MONITOR_UNITS
            ):
                log.debug(f"{cop}\nUnit not found in list of monitored units.")
                continue
            log.debug(f"{cop}\nUnit found in list of monitored units.")
            time_formatted_in_tz = _convert_to_timestr(time)
            interesting_pigs.append((cop, time_formatted_in_tz, call["url"]))
    return interesting_pigs


def format_pigs(pigs: List[Tuple[Dict, str, str]]) -> List[Tuple[str, str]]:
    formatted_pigs = []
    for cop, time, url in pigs:
        name, badge, unit_description, time = (
            cop["full_name"],
            cop["badge"],
            cop["unit_description"],
            time,
        )
        formatted_pigs.append((f"{name}\n{badge}\n{unit_description}\n{time}", url))
    return formatted_pigs


@backoff.on_exception(
    backoff.expo,
    aiohttp.ClientError,
    logger=log,
    max_time=env.RADIO_CHASER_BACKOFF,
)
async def check_radio_calls() -> Optional[List[Tuple[str, str]]]:
    calls = await get_openmhz_calls()
    pigs = await get_pigs(calls)
    if not pigs:
        return None
    log.debug(f"Interesting pigs found\n{pigs}")
    return format_pigs(pigs)

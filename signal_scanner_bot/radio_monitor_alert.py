import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import pytz
import requests

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


def get_openmhz_calls() -> Dict:
    lookback_time = _calculate_lookback_time()
    log.debug(f"Lookback is currently set to: {lookback_time}")
    response = requests.get(env.OPENMHZ_URL, params={"time": lookback_time})
    return response.json()["calls"]


def get_pigs(calls: Dict) -> List[Tuple[Dict, str, str]]:
    interesting_pigs = []
    for call in calls:
        time = call["time"]
        radios = radios = {f"7{radio['src']:0>5}" for radio in call["srcList"]}
        if not len(radios):
            continue
        cops = requests.get(env.RADIO_CHASER_URL, params={"radio": radios})
        log.debug(f"URL requested: {cops.url}")
        log.debug(f"List of cops returned by radio-chaser:\n{cops.json()}")
        for cop in cops.json().values():
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


def check_radio_calls() -> Optional[List[Tuple[str, str]]]:
    calls = get_openmhz_calls()
    log.debug(f"Calls from OpenMHz:\n{calls}")
    pigs = get_pigs(calls)
    if not pigs:
        return None
    log.debug(f"Interesting pigs found\n{pigs}")
    return format_pigs(pigs)

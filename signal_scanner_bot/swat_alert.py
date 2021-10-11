import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import pytz
import requests

from . import env


log = logging.getLogger(__name__)


def get_openmhz() -> Dict:
    time = datetime.now(pytz.utc) - timedelta(seconds=(env.RADIO_MONITOR_LOOKBACK))
    strArray = str(time.timestamp()).split(".")
    lookback_time = strArray[0] + strArray[1][:3]
    log.debug(f"Lookback is currently set to: {lookback_time}")
    response = requests.get(env.OPENMHZ_URL + f"&time={lookback_time}")
    return response.json()["calls"]


def get_pigs(calls: List[Dict]) -> Optional[List]:
    interesting_pigs = []
    for call in calls:
        time = call["time"]
        radios = {str(700000 + int(radio["src"])) for radio in call["srcList"]}
        if len(radios) > 0:
            api_radios = "radio=" + "&radio=".join(radios)
            cops = requests.get(env.RADIO_CHASER_URL + api_radios)
            for cop in cops.json().values():
                if [unit for unit in env.RADIO_MONITOR_UNITS if unit in cop["unit_description"]]:
                    # Convert time string to datetime after converting it into proper ISO format
                    # Add timezone awareness (sourc is in UTC) then output in specified TZ and
                    # 12 hour format
                    time_dt = datetime.fromisoformat(time.replace("Z", "+00:00"))
                    time_dt_tz = time_dt.replace(tzinfo=pytz.utc)
                    time_formatted_in_tz = time_dt_tz.astimezone(env.DEFAULT_TZ).strftime(
                        "%Y-%m-%d, %I:%M:%S %Z"
                    )
                    interesting_pigs.append((cop, time_formatted_in_tz, call["url"]))
    return interesting_pigs


def format_pigs(pigs: List) -> List[Tuple[str, str]]:
    return [
        (
            "{name}\n{badge}\n{unit_description}\n{time}".format(
                name=pig[0]["full_name"],
                badge=pig[0]["badge"],
                unit_description=pig[0]["unit_description"],
                time=pig[1],
            ),
            pig[2],
        )
        for pig in pigs
    ]


def check_swat_calls() -> Optional[List[Tuple[str, str]]]:
    calls = get_openmhz()
    pigs = get_pigs(calls)
    if pigs:
        log.debug("Too lazy to figure out typing just logging pigs out below.")
        log.debug(pigs)
        return format_pigs(pigs)
    return None

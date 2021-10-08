from typing import Dict, List, Optional

import requests

from . import env


def get_openmhz() -> Dict:
    response = requests.get(env.SWAT_OPENMHZ_URL)
    return response.json()["calls"]


def get_pigs(calls: Dict) -> Optional[List]:
    interesting_pigs = []
    for call in calls:
        time = call["time"]
        radios = {str(700000 + int(radio["src"])) for radio in call["srcList"]}
        if len(radios) > 0:
            api_radios = "radio=" + "&radio=".join(radios)
            cops = requests.get(env.SWAT_LOOKUP_URL + api_radios)
            for cop in cops.json().values():
                if [unit for unit in env.SWAT_UNITS if unit in cop["unit_description"]]:
                    interesting_pigs.append((cop, time))
    return interesting_pigs


def format_pigs(pigs: List) -> str:
    formatted_pigs = [
        "{name}\n{badge}\n{unit_description}\n{time}".format(
            name=pig[0]["full_name"],
            badge=pig[0]["badge"],
            unit_description=pig[0]["unit_description"],
            time=pig[1],
        )
        for pig in pigs
    ]
    return "\n".join(formatted_pigs)


def check_swat_calls() -> Optional[str]:
    calls = get_openmhz()
    pigs = get_pigs(calls)
    if pigs:
        return format_pigs(pigs)
    return None

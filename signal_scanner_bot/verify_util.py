import logging
import re
from . import signal
from typing import List
from typing import Tuple


def _find_unverified_numbers() -> List[Tuple[str, str]]:
    all_identities = signal.list_identities()
    if all_identities is None:
        return []
    all_identities = all_identities.split('\n')
    unverified_numbers = []
    for identity in all_identities:
        if ": UNTRUSTED " in identity:
            phone_number = re.search("\\+[1-9]\\d{10}:", identity).group(0)  # phone number
            safety_number = re.search("(?<=Safety Number: )[0-9 ]*", identity).group(0)  # safety number
            unverified_numbers.append((phone_number, safety_number))
    return unverified_numbers


def trust_everyone() -> None:
    to_verify = _find_unverified_numbers()
    for number in to_verify:
        logging.debug("trusting " + number[0])
        print("trust "+ number[0] + " safety '"+number[1]+"'")
        signal.trust_identity(number[0], number[1])


import logging
import re
from typing import List
from typing import Tuple

from . import signal


# Logging
log = logging.getLogger("verifier")
logging.basicConfig(
    format="[%(asctime)s - %(name)s - %(lineno)3d][%(levelname)s] %(message)s",
    level=logging.INFO,
)

# Constants
UNTRUSTED_REGEX = re.compile(
    r"""
^(?P<phone_number>\+[1-9]\d{10}): UNTRUSTED .* Safety Number: (?P<safety_number>[0-9 ]*)
""",
    flags=re.MULTILINE,
)


def _find_unverified_numbers() -> List[Tuple[str, str]]:
    all_identities = signal.list_identities()
    unverified_numbers = []
    for identity in all_identities:
        if match := re.search(UNTRUSTED_REGEX, identity):
            unverified_numbers.append(
                (match.group("phone_number"), match.group("safety_number"))
            )
    return unverified_numbers


def trust_everyone() -> None:
    to_verify = _find_unverified_numbers()
    for phone_number, safety_number in to_verify:
        logging.debug("trusting " + phone_number)
        signal.trust_identity(phone_number, safety_number)


if __name__ == "__main__":
    log.info("Running verification utility")
    trust_everyone()

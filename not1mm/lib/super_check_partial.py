"""Super Check Partial"""

import logging

import requests

MASTER_SCP_URL = "https://www.supercheckpartial.com/MASTER.SCP"

if __name__ == "__main__":
    print("I'm not the program you are looking for.")

logger = logging.getLogger("__main__")


class SCP:
    """Super check partial"""

    def __init__(self, working_path):
        """initialize dialog"""
        self.scp = []
        self.working_path = working_path
        self.read_scp()

    def update_masterscp(self) -> None:
        """Update the MASTER.SCP file.
        - Returns True if successful
        - Otherwise False
        """
        with requests.Session() as session:
            the_request = session.get(MASTER_SCP_URL)
            if the_request.status_code == 200:
                with open(self.working_path + "/data/MASTER.SCP", "wb+") as file:
                    file.write(the_request.content)
                return True
        return False

    def read_scp(self):
        """
        Reads in a list of known contesters into an internal dictionary
        """
        try:
            with open(
                self.working_path + "/data/MASTER.SCP", "r", encoding="utf-8"
            ) as file_descriptor:
                self.scp = file_descriptor.readlines()
                self.scp = list(map(lambda x: x.strip(), self.scp))
        except IOError as exception:
            logger.critical("read_scp: read error: %s", exception)

    def super_check(self, acall: str) -> list:
        """
        Performs a supercheck partial on the callsign entered in the field.
        """
        if len(acall) > 2:
            return list(filter(lambda x: x.startswith(acall), self.scp))
        return []

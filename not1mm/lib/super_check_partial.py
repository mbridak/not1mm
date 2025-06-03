"""Super Check Partial"""

# pylint: disable=unused-argument

import logging

from pathlib import Path
import requests

from rapidfuzz import fuzz
from rapidfuzz import process

from functools import lru_cache

MASTER_SCP_URL = "https://www.supercheckpartial.com/MASTER.SCP"

if __name__ == "__main__":
    print("I'm not the program you are looking for.")

logger = logging.getLogger("super_check_partial")


def prefer_prefix_score(query: str, candidate: str, **kwargs) -> int:
    """Return a score based on the quality of the match."""
    score = 0.5 * fuzz.ratio(query, candidate) + 0.5 * fuzz.partial_ratio(
        query, candidate
    )
    if not candidate.startswith(query):
        score = 0.8 * score
    return int(round(score))


@lru_cache(maxsize=1024)  # You can adjust this as needed
def prefix_bias_score(query: str, candidate: str, **kwargs) -> int:
    """Return a score based on the quality of the match."""
    score = fuzz.QRatio(query, candidate)

    if candidate[: len(query)] == query:
        return score
    return int(score * 0.8)


class SCP:
    """Super check partial"""

    def __init__(self, app_data_path):
        """initialize dialog"""
        self.scp = []
        self.app_data_path = app_data_path
        self.read_scp()

    def update_masterscp(self) -> None:
        """Update the MASTER.SCP file.
        - Returns True if successful
        - Otherwise False
        """
        try:
            with requests.Session() as session:
                the_request = session.get(MASTER_SCP_URL)
                if the_request.status_code == 200:
                    with open(Path(self.app_data_path) / "MASTER.SCP", "wb+") as file:
                        file.write(the_request.content)
                    return True
        except requests.exceptions.RequestException as exception:
            logger.critical("update_masterscp: %s", exception)
        return False

    def read_scp(self):
        """
        Reads in a list of known contesters into an internal dictionary
        """
        try:
            with open(
                Path(self.app_data_path) / "MASTER.SCP", "r", encoding="utf-8"
            ) as file_descriptor:
                self.scp = file_descriptor.readlines()
                self.scp = list(map(lambda x: x.strip(), self.scp))
        except IOError as exception:
            logger.critical("read_scp: read error: %s", exception)

    def super_check(self, acall: str) -> list:

        if len(acall) > 1:
            # Compute similarity scores between `acall` and all items in `self.scp`
            similarity_scores = process.cdist(
                [acall], self.scp, scorer=prefix_bias_score, workers=-1, score_cutoff=60
            )

            # Sort and retrieve the top 20 matches with their indices
            top_matches = sorted(enumerate(similarity_scores[0]), key=lambda x: -x[1])[
                :20
            ]

            # Extract the corresponding strings from `self.scp`
            matches = [self.scp[idx] for idx, score in top_matches if score > 0]

            return matches
        return []

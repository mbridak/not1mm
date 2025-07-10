"""check newer version"""

import xmltodict
import requests


class VersionTest:
    """Tests if version is current to PyPI packaged version."""

    def __init__(
        self,
        current_version: str,
        rss_feed="https://pypi.org/rss/project/not1mm/releases.xml",
    ):
        self.current_version = current_version
        self.rss_feed = rss_feed

    @staticmethod
    def versiontuple(version: str) -> tuple:
        """maps version number to a tuple"""
        return tuple(map(int, (version.split("."))))

    def test(self) -> bool:
        """
        Test version numbers.
        Returns True if Newer version exists.
        """
        try:
            request = requests.get(self.rss_feed, timeout=15.0)
        except requests.RequestException:
            return False

        if request.status_code == 200:
            newdict = xmltodict.parse(request.text)
            try:
                newest_release = (
                    newdict.get("rss").get("channel").get("item")[0].get("title")
                )
            except TypeError:
                return False
            except IndexError:
                return False
            return self.versiontuple(newest_release) > self.versiontuple(
                self.current_version
            )

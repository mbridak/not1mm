"""
callsign lookup classes for:
QRZ
HamDB
HamQTH
"""

import logging
import xmltodict
import requests
from functools import lru_cache

logger = logging.getLogger("lookup")


class HamDBlookup:
    """
    Class manages HamDB lookups.
    """

    def __init__(self) -> None:
        self.url = "https://api.hamdb.org/"
        self.error = False

    @lru_cache(maxsize=1000)
    def lookup(self, call: str) -> tuple:
        """
        Lookup a call on QRZ

        <?xml version="1.0" encoding="utf-8"?>
        <hamdb version="1.0">
        <callsign>
        <call>K6GTE</call>
        <class>G</class>
        <expires>11/07/2027</expires>
        <grid>DM13at</grid>
        <lat>33.8254731</lat>
        <lon>-117.9875229</lon>
        <status>A</status>
        <fname>Michael</fname>
        <mi>C</mi>
        <name>Bridak</name>
        <suffix/>
        <addr1>2854 W Bridgeport Ave</addr1>
        <addr2>Anaheim</addr2>
        <state>CA</state>
        <zip>92804</zip>
        <country>United States</country>
        </callsign>
        <messages>
        <status>OK</status>
        </messages>
        </hamdb>
        """

        logger.info("%s", call)
        grid = False
        name = False
        error_text = False
        nickname = False

        try:
            self.error = False
            query_result = requests.get(
                self.url + call + "/xml/wfd_logger", timeout=10.0
            )
        except requests.exceptions.Timeout as exception:
            self.error = True
            return grid, name, nickname, exception
        if query_result.status_code == 200:
            self.error = False
            rootdict = xmltodict.parse(query_result.text)
            root = rootdict.get("hamdb")
            if root:
                messages = root.get("messages")
                callsign = root.get("callsign")
            if messages:
                error_text = messages.get("status")
                logger.debug("HamDB: %s", error_text)
                if error_text != "OK":
                    self.error = False
            if callsign:
                logger.debug("HamDB: found callsign field")
                if callsign.get("grid"):
                    grid = callsign.get("grid")
                if callsign.get("fname"):
                    name = callsign.get("fname")
                if callsign.get("name"):
                    if not name:
                        name = callsign.get("name")
                    else:
                        name = f"{name} {callsign.get('name')}"
                if callsign.get("nickname"):
                    nickname = callsign.get("nickname")
        else:
            self.error = True
            error_text = str(query_result.status_code)
        logger.info("HamDB-lookup: %s %s %s %s", grid, name, nickname, error_text)
        return grid, name, nickname, error_text


class QRZlookup:
    """
    Class manages QRZ lookups. Pass in a username and password at instantiation.
    """

    def __init__(self, username: str, password: str) -> None:
        self.session = False
        self.expiration = False
        self.error = (
            False  # "password incorrect", "session timeout", and "callsign not found".
        )
        self.username = username
        self.password = password
        self.qrzurl = "https://xmldata.qrz.com/xml/134/"
        self.message = False
        self.lastresult = False
        self.getsession()

    def getsession(self) -> None:
        """
        Get QRZ session key.
        Stores key in class variable 'session'
        Error messages returned by QRZ will be in class variable 'error'
        Other messages returned will be in class variable 'message'

        <?xml version="1.0" ?>
        <QRZDatabase version="1.34">
        <Session>
            <Key>2331uf894c4bd29f3923f3bacf02c532d7bd9</Key>
            <Count>123</Count>
            <SubExp>Wed Jan 1 12:34:03 2013</SubExp>
            <GMTime>Sun Aug 16 03:51:47 2012</GMTime>
        </Session>
        </QRZDatabase>

        Session section fields
        Field	Description
        Key	a valid user session key
        Count	Number of lookups performed by this user in the current 24 hour period
        SubExp	time and date that the users subscription will expire - or - "non-subscriber"
        GMTime	Time stamp for this message
        Message	An informational message for the user
        Error	XML system error message
        """
        logger.info("QRZlookup-getsession:")
        self.error = False
        self.message = False
        self.session = False
        try:
            payload = {"username": self.username, "password": self.password}
            query_result = requests.get(self.qrzurl, params=payload, timeout=10.0)
            baseroot = xmltodict.parse(query_result.text)
            root = baseroot.get("QRZDatabase", {})
            self.session = (
                baseroot.get("QRZDatabase", {}).get("Session", {}).get("Key", "")
            )
            self.expiration = (
                baseroot.get("QRZDatabase", {}).get("Session", {}).get("SubExp", "")
            )
            self.error = (
                baseroot.get("QRZDatabase", {}).get("Session", {}).get("Error", "")
            )
            self.message = (
                baseroot.get("QRZDatabase", {}).get("Session", {}).get("Message", "")
            )

            logger.info("\n\n%s\n\n", root)
            logger.info(
                "key:%s error:%s message:%s",
                self.session,
                self.error,
                self.message,
            )
        except requests.exceptions.RequestException as exception:
            logger.info("%s", exception)
            self.session = False
            self.error = f"{exception}"

    @lru_cache(maxsize=1000)
    def lookup(self, call: str) -> dict:
        """
        Lookup a call on QRZ
        """
        logger.info("%s", call)
        root = {}
        if self.session:
            payload = {"s": self.session, "callsign": call}
            try:
                query_result = requests.get(self.qrzurl, params=payload, timeout=10.0)
            except (
                requests.exceptions.Timeout,
                requests.exceptions.ConnectionError,
            ) as exception:
                self.error = True
                return {"error": exception}
            baseroot = xmltodict.parse(query_result.text)
            logger.debug(f"xml lookup {baseroot}\n")
            root = baseroot.get("QRZDatabase", {})
            session = baseroot.get("QRZDatabase", {}).get("Session", {})
            logger.info("\n\n%s\n\n", root)
            if not session.get("Key"):  # key expired get a new one
                logger.info("no key, getting new one.")
                self.getsession()
                if self.session:
                    payload = {"s": self.session, "callsign": call}
                    query_result = requests.get(
                        self.qrzurl, params=payload, timeout=3.0
                    )
                    baseroot = xmltodict.parse(query_result.text)
                    root = baseroot.get("QRZDatabase", {})
        return root.get("Callsign")


class HamQTH:
    """HamQTH lookup"""

    def __init__(self, username: str, password: str) -> None:
        """initialize HamQTH lookup"""
        self.username = username
        self.password = password
        self.url = "https://www.hamqth.com/xml.php"
        self.session = False
        self.error = False
        self.getsession()

    def getsession(self) -> None:
        """get a session key"""
        logger.info("Getting session")
        self.error = False
        self.session = False
        payload = {"u": self.username, "p": self.password}
        try:
            query_result = requests.get(self.url, params=payload, timeout=2.0)
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
            self.error = True
            return
        logger.info("resultcode: %s", query_result.status_code)
        baseroot = xmltodict.parse(query_result.text)
        root = baseroot.get("HamQTH", {})
        session = root.get("session")
        if session:
            if session.get("session_id"):
                self.session = session.get("session_id")
            if session.get("error"):
                self.error = session.get("error")
        logger.info("session: %s", self.session)

    @lru_cache(maxsize=1000)
    def lookup(self, call: str) -> dict:
        """
        Lookup a call on HamQTH
        """
        the_result = {
            "grid": False,
            "name": False,
            "nickname": False,
            "error_text": False,
        }
        if self.session:
            payload = {"id": self.session, "callsign": call, "prg": "not1mm"}
            try:
                query_result = requests.get(self.url, params=payload, timeout=10.0)
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
                self.error = True
                return the_result
            logger.info("resultcode: %s", query_result.status_code)

            query_dict = xmltodict.parse(query_result.text)
            the_result["grid"] = (
                query_dict.get("HamQTH", {}).get("search", {}).get("grid", False)
            )
            the_result["name"] = (
                query_dict.get("HamQTH", {}).get("search", {}).get("adr_name", False)
            )
            the_result["nickname"] = (
                query_dict.get("HamQTH", {}).get("search", {}).get("nick", False)
            )
            the_result["error_text"] = (
                query_dict.get("HamQTH", {}).get("session", {}).get("error", False)
            )

            if the_result.get("error_text") == "Callsign not found":
                return the_result
            if the_result.get("error_text") == "Session does not exist or expired":
                self.getsession()
                query_result = requests.get(self.url, params=payload, timeout=10.0)
                the_result["grid"] = (
                    query_dict.get("HamQTH", {}).get("search", {}).get("grid", False)
                )
                the_result["name"] = (
                    query_dict.get("HamQTH", {})
                    .get("search", {})
                    .get("adr_name", False)
                )
                the_result["nickname"] = (
                    query_dict.get("HamQTH", {}).get("search", {}).get("nick", False)
                )
                the_result["error_text"] = (
                    query_dict.get("HamQTH", {}).get("session", {}).get("error", False)
                )

        return the_result


def main():
    """Just in case..."""
    print("I'm not a program.")


if __name__ == "__main__":
    main()

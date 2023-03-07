"""
callsign lookup classes for:
QRZ
HamDB
HamQTH
"""

import logging
import xmltodict
import requests

logger = logging.getLogger("__main__")


class HamDBlookup:
    """
    Class manages HamDB lookups.
    """

    def __init__(self) -> None:
        self.url = "https://api.hamdb.org/"
        self.error = False

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
            root = baseroot.get("QRZDatabase")
            if root:
                session = root.get("Session")
            logger.info("\n\n%s\n\n", root)
            if session.get("Key"):
                self.session = session.get("Key")
            if session.get("SubExp"):
                self.expiration = session.get("SubExp")
            if session.get("Error"):
                self.error = session.get("Error")
            if session.get("Message"):
                self.message = session.get("Message")
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

    def lookup(self, call: str) -> tuple:
        """
        Lookup a call on QRZ
        """
        logger.info("%s", call)
        _response = None
        if self.session:
            payload = {"s": self.session, "callsign": call}
            try:
                query_result = requests.get(self.qrzurl, params=payload, timeout=10.0)
            except requests.exceptions.Timeout as exception:
                self.error = True
                return {"error": exception}
            baseroot = xmltodict.parse(query_result.text)
            logger.debug(f"xml lookup {baseroot}\n")
            root = baseroot.get("QRZDatabase")
            logger.info("\n\n%s\n\n", root)
            session = root.get("Session")
            if not session.get("Key"):  # key expired get a new one
                logger.info("no key, getting new one.")
                self.getsession()
                if self.session:
                    payload = {"s": self.session, "callsign": call}
                    query_result = requests.get(
                        self.qrzurl, params=payload, timeout=3.0
                    )
                    baseroot = xmltodict.parse(query_result.text)
                    root = baseroot.get("QRZDatabase")
            # grid, name, nickname, error_text = self.parse_lookup(query_result)
        # logger.info("%s %s %s %s", grid, name, nickname, error_text)
        return root.get("Callsign")

    def parse_lookup(self, query_result):
        """
        Returns gridsquare and name for a callsign looked up by qrz or hamdb.
        Or False for both if none found or error.

        <?xml version="1.0" encoding="utf-8"?>
        <QRZDatabase version="1.34" xmlns="http://xmldata.qrz.com">
        <Callsign>
        <call>K6GTE</call>
        <aliases>KM6HQI</aliases>
        <dxcc>291</dxcc>
        <nickname>Mike</nickname>
        <fname>Michael C</fname>
        <name>Bridak</name>
        <addr1>2854 W Bridgeport Ave</addr1>
        <addr2>Anaheim</addr2>
        <state>CA</state>
        <zip>92804</zip>
        <country>United States</country>
        <lat>33.825460</lat>
        <lon>-117.987510</lon>
        <grid>DM13at</grid>
        <county>Orange</county>
        <ccode>271</ccode>
        <fips>06059</fips>
        <land>United States</land>
        <efdate>2021-01-13</efdate>
        <expdate>2027-11-07</expdate>
        <class>G</class>
        <codes>HVIE</codes>
        <email>michael.bridak@gmail.com</email>
        <u_views>1569</u_views>
        <bio>6399</bio>
        <biodate>2022-02-26 00:51:44</biodate>
        <image>https://cdn-xml.qrz.com/e/k6gte/qsl.png</image>
        <imageinfo>285:545:99376</imageinfo>
        <moddate>2021-04-08 21:41:07</moddate>
        <MSA>5945</MSA>
        <AreaCode>714</AreaCode>
        <TimeZone>Pacific</TimeZone>
        <GMTOffset>-8</GMTOffset>
        <DST>Y</DST>
        <eqsl>0</eqsl>
        <mqsl>1</mqsl>
        <cqzone>3</cqzone>
        <ituzone>6</ituzone>
        <born>1967</born>
        <lotw>1</lotw>
        <user>K6GTE</user>
        <geoloc>geocode</geoloc>
        <name_fmt>Michael C "Mike" Bridak</name_fmt>
        </Callsign>
        <Session>
        <Key>42d5c9736525b485e8edb782b101c74b</Key>
        <Count>4140</Count>
        <SubExp>Tue Feb 21 07:01:49 2023</SubExp>
        <GMTime>Sun May  1 20:00:36 2022</GMTime>
        <Remark>cpu: 0.022s</Remark>
        </Session>
        </QRZDatabase>

        """
        logger.info("QRZlookup-parse_lookup:")
        grid = False
        name = False
        error_text = False
        nickname = False
        if query_result.status_code == 200:
            baseroot = xmltodict.parse(query_result.text)
            root = baseroot.get("QRZDatabase")
            session = root.get("Session")
            callsign = root.get("Callsign")
            logger.info("\n\n%s\n\n", root)
            if session.get("Error"):
                error_text = session.get("Error")
                self.error = error_text
            if callsign:
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
        logger.info("%s %s %s %s", grid, name, nickname, error_text)
        return grid, name, nickname, error_text


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
            query_result = requests.get(self.url, params=payload, timeout=10.0)
        except requests.exceptions.Timeout:
            self.error = True
            return
        logger.info("resultcode: %s", query_result.status_code)
        baseroot = xmltodict.parse(query_result.text)
        root = baseroot.get("HamQTH")
        session = root.get("session")
        if session:
            if session.get("session_id"):
                self.session = session.get("session_id")
            if session.get("error"):
                self.error = session.get("error")
        logger.info("session: %s", self.session)

    def lookup(self, call: str) -> tuple:
        """
        Lookup a call on HamQTH
        """
        grid, name, nickname, error_text = False, False, False, False
        if self.session:
            payload = {"id": self.session, "callsign": call, "prg": "wfdlogger"}
            try:
                query_result = requests.get(self.url, params=payload, timeout=10.0)
            except requests.exceptions.Timeout as exception:
                self.error = True
                return grid, name, nickname, exception
            logger.info("resultcode: %s", query_result.status_code)
            baseroot = xmltodict.parse(query_result.text)
            root = baseroot.get("HamQTH")
            search = root.get("search")
            session = root.get("session")
            if not search:
                if session:
                    if session.get("error"):
                        if session.get("error") == "Callsign not found":
                            error_text = session.get("error")
                            return grid, name, nickname, error_text
                        if session.get("error") == "Session does not exist or expired":
                            self.getsession()
                            query_result = requests.get(
                                self.url, params=payload, timeout=10.0
                            )
            grid, name, nickname, error_text = self.parse_lookup(root)
        logger.info("%s %s %s %s", grid, name, nickname, error_text)
        return grid, name, nickname, error_text

    def parse_lookup(self, root) -> tuple:
        """
        Returns gridsquare and name for a callsign looked up by qrz or hamdb.
        Or False for both if none found or error.
        """
        grid, name, nickname, error_text = False, False, False, False
        session = root.get("session")
        search = root.get("search")
        if session:
            if session.get("error"):
                error_text = session.get("error")
        if search:
            if search.get("grid"):
                grid = search.get("grid")
            if search.get("nick"):
                nickname = search.get("nick")
            if search.get("adr_name"):
                name = search.get("adr_name")
        return grid, name, nickname, error_text


def main():
    """Just in case..."""
    print("I'm not a program.")


if __name__ == "__main__":
    main()

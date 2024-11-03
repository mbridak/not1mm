"""
K6GTE, Database class to store contacts
Email: michael.bridak@gmail.com
GPL V3
"""

# pylint: disable=line-too-long

# get Saturday plus 48 hours: select datetime('now', 'WEEKDAY 6','48 HOURS');
# DROP TABLE IF EXISTS t1;

import logging
import sqlite3

if __name__ == "__main__":
    print("I'm not the program you are looking for.")

logger = logging.getLogger("database")


class DataBase:
    """Database class for our database."""

    current_contest = 1

    def __init__(self, database: str, app_data_dir: str):
        """initializes DataBase instance"""
        logger.debug("Database: %s", database)
        self.app_data_dir = app_data_dir
        self.empty_contact = {
            "TS": "",
            "Call": "",
            "Freq": "",
            "QSXFreq": "",
            "Mode": "",
            "ContestName": "",
            "SNT": "",
            "RCV": "",
            "CountryPrefix": "",
            "StationPrefix": "",
            "QTH": "",
            "Name": "",
            "Comment": "",
            "NR": 0,
            "Sect": "",
            "Prec": "",
            "CK": 0,
            "ZN": 0,
            "SentNr": 0,
            "Points": 0,
            "IsMultiplier1": 0,
            "IsMultiplier2": 0,
            "Power": 0,
            "Band": 0.0,
            "WPXPrefix": "",
            "Exchange1": "",
            "RadioNR": "",
            "ContestNR": "",
            "isMultiplier3": 0,
            "MiscText": "",
            "IsRunQSO": "",
            "ContactType": "",
            "Run1Run2": "",
            "GridSquare": "",
            "Operator": "",
            "Continent": "",
            "RoverLocation": "",
            "RadioInterfaced": "",
            "NetworkedCompNr": 1,
            "NetBiosName": "",
            "IsOriginal": 1,
            "ID": "",
            "CLAIMEDQSO": 1,
        }
        self.database = database
        self.create_dxlog_table()
        self.update_dxlog_table()
        self.create_contest_table()
        self.create_contest_instance_table()
        self.create_station_table()
        self.create_callhistory_table()

    @staticmethod
    def row_factory(cursor, row):
        """
        cursor.description:
        (name, type_code, display_size,
        internal_size, precision, scale, null_ok)
        row: (value, value, ...)
        """
        return {
            col[0]: row[idx]
            for idx, col in enumerate(
                cursor.description,
            )
        }

    def create_dxlog_table(self) -> None:
        """creates the dxlog table"""
        logger.debug("Creating DXLOG Table")
        try:
            with sqlite3.connect(self.database) as conn:
                cursor = conn.cursor()
                sql_command = (
                    "CREATE TABLE IF NOT EXISTS DXLOG ("
                    "TS DATETIME NOT NULL, "
                    "Call VARCHAR(15) NOT NULL, "
                    "Freq DOUBLE NULL, "
                    "QSXFreq DOUBLE NULL DEFAULT 0, "
                    "Mode VARCHAR(6) DEFAULT '', "
                    "ContestName VARCHAR(10) DEFAULT 'NORMAL', "
                    "SNT VARCHAR(10) DEFAULT '', "
                    "RCV VARCHAR(15) DEFAULT '', "
                    "CountryPrefix VARCHAR(8) DEFAULT '', "
                    "StationPrefix VARCHAR(15) DEFAULT '', "
                    "QTH VARCHAR(25) DEFAULT '', "
                    "Name VARCHAR(20) DEFAULT '', "
                    "Comment VARCHAR(60) DEFAULT '', "
                    "NR INTEGER DEFAULT 0, "
                    "Sect VARCHAR(8) DEFAULT '', "
                    "Prec VARCHAR(1) DEFAULT '', "
                    "CK TINYINT DEFAULT 0, "
                    "ZN TINYINT DEFAULT 0, "
                    "SentNr INTEGER DEFAULT 0, "
                    "Points INTEGER DEFAULT 0, "
                    "IsMultiplier1 TINYINT DEFAULT 0, "
                    "IsMultiplier2 INTEGER DEFAULT 0, "
                    "Power VARCHAR(8) DEFAULT '', "
                    "Band FLOAT NULL DEFAULT 0, "
                    "WPXPrefix VARCHAR(8) DEFAULT '', "
                    "Exchange1 VARCHAR(20) DEFAULT '', "
                    "RadioNR TINYINT DEFAULT 1, "
                    "ContestNR INTEGER, "
                    "isMultiplier3 INTEGER DEFAULT 0, "
                    "MiscText VARCHAR(20) DEFAULT '', "
                    "IsRunQSO TINYINT(1) DEFAULT 0, "
                    "ContactType VARCHAR(1) DEFAULT '', "
                    "Run1Run2 TINYINT NOT NULL, "
                    "GridSquare VARCHAR(6) DEFAULT '', "
                    "Operator VARCHAR(20) DEFAULT '', "
                    "Continent VARCHAR(2) DEFAULT '', "
                    "RoverLocation VARCHAR(10) DEFAULT '', "
                    "RadioInterfaced INTEGER, "
                    "NetworkedCompNr INTEGER, NetBiosName varchar (255), "
                    "IsOriginal Boolean, "
                    "ID TEXT(32) NOT NULL DEFAULT '00000000000000000000000000000000', "
                    "CLAIMEDQSO INTEGER DEFAULT 1,"
                    "Dirty INTEGER DEFAULT 1,"
                    "PRIMARY KEY (`TS`, `Call`) );"
                )
                cursor.execute(sql_command)
                conn.commit()
        except sqlite3.OperationalError as exception:
            logger.debug("%s", exception)

    def create_callhistory_table(self) -> None:
        """creates the callhistory table"""
        logger.debug("Creating DXLOG Table")
        try:
            with sqlite3.connect(self.database) as conn:
                cursor = conn.cursor()
                sql_command = (
                    "CREATE TABLE IF NOT EXISTS CALLHISTORY ("
                    "Call VARCHAR(15) NOT NULL, "
                    "Name VARCHAR(20), "
                    "Loc1 VARCHAR(6) DEFAULT '', "
                    "Loc2 VARCHAR(6) DEFAULT '', "
                    "Sect VARCHAR(8) DEFAULT '', "
                    "State VARCHAR(8) DEFAULT '', "
                    "CK TINYINT DEFAULT 0, "
                    "BirthDate DATE, "
                    "Exch1 VARCHAR(12) DEFAULT '', "
                    "Misc VARCHAR(15) DEFAULT '', "
                    "Power VARCHAR(8) DEFAULT '', "
                    "CqZone TINYINT DEFAULT 0, "
                    "ITUZone TINYINT DEFAULT 0, "
                    "UserText VARCHAR(60) DEFAULT '', "
                    "LastUpdateNote VARCHAR(20) DEFAULT '' "
                    ");"
                )
                cursor.execute(sql_command)
                conn.commit()
        except sqlite3.OperationalError as exception:
            logger.debug("%s", exception)

    def update_dxlog_table(self) -> None:
        """update missing columns"""
        logger.debug("Updating DXLOG Table")
        try:
            with sqlite3.connect(self.database) as conn:
                cursor = conn.cursor()
                sql_command = "ALTER TABLE DXLOG ADD dirty INTEGER DEFAULT 1;"
                cursor.execute(sql_command)
                conn.commit()
        except sqlite3.OperationalError as exception:
            logger.debug("%s", exception)

    def create_contest_table(self) -> None:
        """Creates the Contest table"""
        logger.debug("Creating Contest Table")
        try:
            with sqlite3.connect(self.database) as conn:
                conn.row_factory = self.row_factory
                cursor = conn.cursor()
                sql_command = (
                    "CREATE TABLE IF NOT EXISTS [Contest] ("
                    "[Name] NVARCHAR(10)  NOT NULL PRIMARY KEY,"
                    "[DisplayName] NVARCHAR(50)  NULL,"
                    "[CabrilloName] NVARCHAR(15)  NOT NULL,"
                    "[Mode] NVARCHAR(6)  NOT NULL,"
                    "[DupeType] SMALLINT DEFAULT '''''''0''''''' NULL,"
                    "[Multiplier1Name] NVARCHAR(15) DEFAULT '''''''''''''''N/A''''''''''''''' NULL,"
                    "[Multiplier2Name] NVARCHAR(15) DEFAULT '''''''''''''''N/A''''''''''''''' NULL,"
                    "[Period] INT DEFAULT '''''''2''''''' NOT NULL,"
                    "[PointsPerContact] INT DEFAULT '''''''0''''''' NULL,"
                    "[Multiplier3Name] NVARCHAR(15)  NULL,"
                    "[MasterDTA] NVARCHAR(255)  NULL,"
                    "[CWMessages] NVARCHAR(255)  NULL,"
                    "[SSBMessages] NVARCHAR(255)  NULL,"
                    "[DigiMessages] NVARCHAR(255)  NULL,"
                    "[CabrilloVersion] NVARCHAR(20)  NULL"
                    ");"
                )
                cursor.execute(sql_command)
                conn.commit()

                sql_command = "select * from Contest;"
                cursor.execute(sql_command)
                result = cursor.fetchall()
                if len(result) == 0:
                    with open(
                        self.app_data_dir / "contests.sql", encoding="utf-8"
                    ) as data:
                        for line in data.readlines():
                            cursor.execute(line)
                    conn.commit()
        except sqlite3.OperationalError as exception:
            logger.debug("%s", exception)

    def create_contest_instance_table(self) -> None:
        """Creates the ContestInstance table"""
        logger.debug("Creating ContestInstance Table")
        try:
            with sqlite3.connect(self.database) as conn:
                cursor = conn.cursor()
                sql_command = (
                    "CREATE TABLE IF NOT EXISTS ContestInstance ("
                    "ContestID INTEGER PRIMARY KEY,"
                    "ContestName NVARCHAR(10),"
                    "StartDate DATETIME,"
                    "OperatorCategory NVARCHAR(20) DEFAULT "
                    "'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''',"
                    "BandCategory NVARCHAR(20) DEFAULT "
                    "'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''',"
                    "PowerCategory NVARCHAR(20) DEFAULT "
                    "'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''',"
                    "ModeCategory NVARCHAR(20) DEFAULT "
                    "'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''',"
                    "OverlayCategory NVARCHAR(20) DEFAULT "
                    "'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''',"
                    "ClaimedScore MONEY DEFAULT '''''''''''''''0''''''''''''''',"
                    "Operators NVARCHAR(255) DEFAULT "
                    "'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''',"
                    "Soapbox TEXT,"
                    "SentExchange NVARCHAR(50),"
                    "ContestNR INT,"
                    "SubType NVARCHAR(9),"
                    "StationCategory NVARCHAR(20),"
                    "AssistedCategory NVARCHAR(20),"
                    "TransmitterCategory NVARCHAR(20),"
                    "TimeCategory NVARCHAR(20));"
                )
                cursor.execute(sql_command)
                conn.commit()
        except sqlite3.OperationalError as exception:
            logger.debug("%s", exception)

    def create_station_table(self) -> None:
        """Creates the Station table"""
        logger.debug("Creating Station Table")
        try:
            with sqlite3.connect(self.database) as conn:
                cursor = conn.cursor()
                sql_command = (
                    "CREATE TABLE IF NOT EXISTS [Station] ("
                    "[Call] NVARCHAR(20) NOT NULL, "
                    "[Name] NVARCHAR(50), "
                    "[Email] NVARCHAR(50), "
                    "[Street1] NVARCHAR(50), "
                    "[Street2] NVARCHAR(50), "
                    "[City] NVARCHAR(30), "
                    "[State] NVARCHAR(8), "
                    "[Zip] NVARCHAR(25), "
                    "[Country] NVARCHAR(30), "
                    "[GridSquare] NVARCHAR(8) DEFAULT 'Unknown', "
                    "[LicenseClass] NVARCHAR(10) DEFAULT 'Unknown', "
                    "[Latitude] FLOAT DEFAULT 0, "
                    "[Longitude] FLOAT DEFAULT 0, "
                    "[PacketNode] NVARCHAR(10) DEFAULT 'N/A', "
                    "[ARRLSection] NVARCHAR(4), "
                    "[Club] NVARCHAR(50), "
                    "[IARUZone] SMALLINT DEFAULT 0, "
                    "[CQZone] SMALLINT NOT NULL, "
                    "[STXeq] NVARCHAR(50), "
                    "[SPowe] NVARCHAR(20), "
                    "[SAnte] NVARCHAR(30), "
                    "[SAntH1] NVARCHAR(15), "
                    "[SAntH2] NVARCHAR(15), "
                    "[RoverQTH] NVARCHAR(10), "
                    "PRIMARY KEY([Call]));"
                )
                cursor.execute(sql_command)
                conn.commit()
        except sqlite3.OperationalError as exception:
            logger.debug("%s", exception)

    def add_station(self, station: dict) -> None:
        """Add station information"""

        logger.info("%s", station)
        sql = "DELETE FROM Station;"
        try:
            with sqlite3.connect(self.database) as conn:
                logger.info("%s", sql)
                cur = conn.cursor()
                cur.execute(sql)
                conn.commit()
        except sqlite3.Error as exception:
            logger.info("DataBase add_station: %s", exception)

        pre = "INSERT INTO Station("
        values = []
        columns = ""
        placeholders = ""
        for key in station.keys():
            columns += f"{key},"
            values.append(station[key])
            placeholders += "?,"
        post = f") VALUES({placeholders[:-1]});"
        sql = f"{pre}{columns[:-1]}{post}"

        try:
            with sqlite3.connect(self.database) as conn:
                logger.info("%s", sql)
                cur = conn.cursor()
                cur.execute(sql, tuple(values))
                conn.commit()
        except sqlite3.Error as exception:
            logger.info("DataBase add_station: %s", exception)

    def fetch_station(self) -> dict:
        """returns a list of dicts with last contact in the database."""
        try:
            with sqlite3.connect(self.database) as conn:
                conn.row_factory = self.row_factory
                cursor = conn.cursor()
                cursor.execute("select * from Station;")
                return cursor.fetchone()
        except sqlite3.OperationalError as exception:
            logger.debug("%s", exception)
            return {}

    def get_next_contest_nr(self):
        """Returns the next ContestNR to use."""
        # select count(*) + 1 as count from ContestInstance;
        try:
            with sqlite3.connect(self.database) as conn:
                conn.row_factory = self.row_factory
                cursor = conn.cursor()
                cursor.execute("select count(*) + 1 as count from ContestInstance;")
                return cursor.fetchone()
        except sqlite3.OperationalError as exception:
            logger.debug("%s", exception)
            return {}

    def fetch_contest_by_id(self, contest_nr: str) -> dict:
        """returns a dict of ContestInstance"""
        try:
            with sqlite3.connect(self.database) as conn:
                conn.row_factory = self.row_factory
                cursor = conn.cursor()
                cursor.execute(
                    f"select * from ContestInstance where ContestNR='{contest_nr}';"
                )
                return cursor.fetchone()
        except sqlite3.OperationalError as exception:
            logger.debug("%s", exception)
            return {}

    def add_callhistory_item(self, history: dict) -> None:
        """Add an item to the call history db"""
        pre = "INSERT INTO CALLHISTORY("
        values = []
        columns = ""
        placeholders = ""
        for key in history.keys():
            columns += f"{key},"
            values.append(history[key])
            placeholders += "?,"
        post = f") VALUES({placeholders[:-1]});"
        sql = f"{pre}{columns[:-1]}{post}"

        try:
            with sqlite3.connect(self.database) as conn:
                cur = conn.cursor()
                cur.execute(sql, tuple(values))
                conn.commit()
        except sqlite3.Error as exception:
            logger.info("%s", exception)

    def add_callhistory_items(self, history_list: list) -> None:
        """Add a list of items to the call history db"""
        try:
            with sqlite3.connect(self.database) as conn:
                for history in history_list:
                    pre = "INSERT INTO CALLHISTORY("
                    values = []
                    columns = ""
                    placeholders = ""
                    for key in history.keys():
                        columns += f"{key},"
                        values.append(history[key])
                        placeholders += "?,"
                    post = f") VALUES({placeholders[:-1]});"
                    sql = f"{pre}{columns[:-1]}{post}"
                    cur = conn.cursor()
                    cur.execute(sql, tuple(values))
                conn.commit()
        except sqlite3.Error as exception:
            print(exception)
            logger.info("%s", exception)

    def add_contest(self, contest: dict) -> None:
        """Add Contest"""

        logger.info("%s", contest)
        pre = "INSERT INTO ContestInstance("
        values = []
        columns = ""
        placeholders = ""
        for key in contest.keys():
            columns += f"{key},"
            values.append(contest[key])
            placeholders += "?,"
        post = f") VALUES({placeholders[:-1]});"
        sql = f"{pre}{columns[:-1]}{post}"

        try:
            with sqlite3.connect(self.database) as conn:
                logger.info("%s", sql)
                cur = conn.cursor()
                cur.execute(sql, tuple(values))
                conn.commit()
        except sqlite3.Error as exception:
            logger.info("DataBase add_contest: %s", exception)

    def update_contest(self, contest: dict) -> None:
        """Update an existing contest"""
        pre = "UPDATE ContestInstance set "
        for key in contest.keys():
            pre += f"{key} = '{contest[key]}',"
        sql = f"{pre[:-1]} where ContestNR='{contest['ContestNR']}';"

        try:
            with sqlite3.connect(self.database) as conn:
                logger.info("%s\n%s", sql, contest)
                cur = conn.cursor()
                cur.execute(sql)
                conn.commit()
        except sqlite3.Error as exception:
            logger.info("DataBase update_contest: %s", exception)

    def fetch_all_contests(self) -> list:
        """returns a list of dicts with contests in the database."""
        try:
            with sqlite3.connect(self.database) as conn:
                conn.row_factory = self.row_factory
                cursor = conn.cursor()
                cursor.execute("select * from ContestInstance;")
                return cursor.fetchall()
        except sqlite3.OperationalError as exception:
            logger.debug("%s", exception)
            return ()

    def log_contact(self, contact: dict) -> None:
        """
        Inserts a contact into the db.
        pass in a dict object, see get_empty() for keys
        """

        logger.info("%s", contact)

        pre = "INSERT INTO DXLOG("
        values = []
        columns = ""
        placeholders = ""
        for key in contact.keys():
            columns += f"{key},"
            values.append(contact[key])
            placeholders += "?,"
        post = f") VALUES({placeholders[:-1]});"
        sql = f"{pre}{columns[:-1]}{post}"

        try:
            with sqlite3.connect(self.database) as conn:
                logger.info("%s", sql)
                cur = conn.cursor()
                cur.execute(sql, tuple(values))
                conn.commit()
        except sqlite3.Error as exception:
            logger.info("DataBase log_contact: %s", exception)

    def change_contact(self, qso: dict) -> None:
        """Update an existing contact."""

        pre = "UPDATE dxlog set "
        for key in qso.keys():
            pre += f"{key} = '{qso[key]}',"
        sql = f"{pre[:-1]} where ID='{qso['ID']}';"

        try:
            with sqlite3.connect(self.database) as conn:
                logger.debug("%s\n%s", sql, qso)
                cur = conn.cursor()
                cur.execute(sql)
                conn.commit()
        except sqlite3.Error as exception:
            logger.critical("DataBase change_contact: %s", exception)

    def delete_contact(self, unique_id: str) -> None:
        """Deletes a contact from the db."""
        if unique_id:
            try:
                with sqlite3.connect(self.database) as conn:
                    sql = f"delete from dxlog where ID='{unique_id}';"
                    cur = conn.cursor()
                    cur.execute(sql)
                    conn.commit()
            except sqlite3.Error as exception:
                logger.info("DataBase delete_contact: %s", exception)

    def delete_callhistory(self) -> None:
        """Deletes all info from callhistory table."""
        try:
            with sqlite3.connect(self.database) as conn:
                sql = "delete from CALLHISTORY;"
                cur = conn.cursor()
                cur.execute(sql)
                conn.commit()
        except sqlite3.Error as exception:
            logger.info("%s", exception)

    def fetch_call_history(self, call: str):
        """"""
        try:
            with sqlite3.connect(self.database) as conn:
                conn.row_factory = self.row_factory
                cursor = conn.cursor()
                cursor.execute(f"select * from CALLHISTORY where call='{call}';")
                return cursor.fetchone()
        except sqlite3.OperationalError as exception:
            logger.debug("%s", exception)
            return {}

    def fetch_all_contacts_asc(self) -> list:
        """returns a list of dicts with contacts in the database."""
        try:
            with sqlite3.connect(self.database) as conn:
                conn.row_factory = self.row_factory
                cursor = conn.cursor()
                cursor.execute(
                    f"select * from dxlog where ContestNR = {self.current_contest} order by TS ASC;"
                )
                return cursor.fetchall()
        except sqlite3.OperationalError as exception:
            logger.debug("%s", exception)
            return ()

    def fetch_all_contacts_desc(self) -> list:
        """returns a list of dicts with contacts in the database."""
        try:
            with sqlite3.connect(self.database) as conn:
                conn.row_factory = self.row_factory
                cursor = conn.cursor()
                cursor.execute(
                    f"select * from dxlog where ContestNR = {self.current_contest} order by ts desc;"
                )
                return cursor.fetchall()
        except sqlite3.OperationalError as exception:
            logger.debug("%s", exception)

    def fetch_last_contact(self) -> dict:
        """returns a list of dicts with last contact in the database."""
        try:
            with sqlite3.connect(self.database) as conn:
                conn.row_factory = self.row_factory
                cursor = conn.cursor()
                cursor.execute("select * from dxlog order by ts desc;")
                return cursor.fetchone()
        except sqlite3.OperationalError as exception:
            logger.debug("%s", exception)
            return {}

    def fetch_contact_by_uuid(self, uuid: str) -> dict:
        """returns a list of dicts with last contact in the database."""
        try:
            with sqlite3.connect(self.database) as conn:
                conn.row_factory = self.row_factory
                cursor = conn.cursor()
                cursor.execute(f"select * from dxlog where ID='{uuid}';")
                return cursor.fetchone()
        except sqlite3.OperationalError as exception:
            logger.debug("%s", exception)
            return {}

    def fetch_cqzn_exists(self, number) -> dict:
        """returns a dict key of nr_count"""
        try:
            with sqlite3.connect(self.database) as conn:
                conn.row_factory = self.row_factory
                cursor = conn.cursor()
                cursor.execute(
                    f"select count(*) as zn_count from dxlog where ZN = '{number}' and ContestNR = {self.current_contest};"
                )
                return cursor.fetchone()
        except sqlite3.OperationalError as exception:
            logger.debug("%s", exception)
            return {}

    def fetch_zn_band_count(self) -> dict:
        """
        returns dict with count of unique ZN and Band.
        {nr_count: count}
        """
        try:
            with sqlite3.connect(self.database) as conn:
                conn.row_factory = self.row_factory
                cursor = conn.cursor()
                cursor.execute(
                    f"select count(DISTINCT(ZN || ':' || Band)) as zb_count from dxlog where ContestNR = {self.current_contest};"
                )
                return cursor.fetchone()
        except sqlite3.OperationalError as exception:
            logger.debug("%s", exception)
            return {}

    def fetch_zn_band_mode_count(self) -> dict:
        """
        returns dict with count of unique ZN, Band and Mode.
        {nr_count: count}
        """
        try:
            with sqlite3.connect(self.database) as conn:
                conn.row_factory = self.row_factory
                cursor = conn.cursor()
                cursor.execute(
                    f"select count(DISTINCT(ZN || ':' || Band || ':' || Mode)) as zbm_count from dxlog where ContestNR = {self.current_contest};"
                )
                return cursor.fetchone()
        except sqlite3.OperationalError as exception:
            logger.debug("%s", exception)
            return {}

    def fetch_country_band_count(self) -> dict:
        """
        returns dict with count of unique NR.
        {cb_count: count}
        """
        try:
            with sqlite3.connect(self.database) as conn:
                conn.row_factory = self.row_factory
                cursor = conn.cursor()
                cursor.execute(
                    f"select count(DISTINCT(CountryPrefix || ':' || Band)) as cb_count from dxlog where ContestNR = {self.current_contest};"
                )
                return cursor.fetchone()
        except sqlite3.OperationalError as exception:
            logger.debug("%s", exception)
            return {}

    def fetch_country_count(self) -> dict:
        """
        Fetch count of unique countries
        {dxcc_count: count}
        """
        try:
            with sqlite3.connect(self.database) as conn:
                conn.row_factory = self.row_factory
                cursor = conn.cursor()
                cursor.execute(
                    f"select count(DISTINCT(CountryPrefix)) as dxcc_count from dxlog where ContestNR = {self.current_contest};"
                )
                return cursor.fetchone()
        except sqlite3.OperationalError as exception:
            logger.debug("%s", exception)
            return {}

    def fetch_arrldx_country_band_count(self) -> dict:
        """
        returns dict with count of unique NR.
        {nr_count: count}
        """
        try:
            with sqlite3.connect(self.database) as conn:
                conn.row_factory = self.row_factory
                cursor = conn.cursor()
                cursor.execute(
                    f"select count(DISTINCT(CountryPrefix || ':' || Band)) as cb_count from dxlog where ContestNR = {self.current_contest} and points = 3;"
                )
                return cursor.fetchone()
        except sqlite3.OperationalError as exception:
            logger.debug("%s", exception)
            return {}

    def fetch_arrldx_state_prov_count(self) -> dict:
        """
        returns dict with count of unique NR.
        {nr_count: count}
        """
        try:
            with sqlite3.connect(self.database) as conn:
                conn.row_factory = self.row_factory
                cursor = conn.cursor()
                cursor.execute(
                    f"select count(DISTINCT(NR || ':' || Band)) as cb_count from dxlog where ContestNR = {self.current_contest} and points = 3;"
                )
                return cursor.fetchone()
        except sqlite3.OperationalError as exception:
            logger.debug("%s", exception)
            return {}

    def fetch_nr_count(self) -> dict:
        """
        returns dict with count of unique NR.
        {nr_count: count}
        """
        try:
            with sqlite3.connect(self.database) as conn:
                conn.row_factory = self.row_factory
                cursor = conn.cursor()
                cursor.execute(
                    f"select count(DISTINCT NR) as nr_count from dxlog where ContestNR = {self.current_contest};"
                )
                return cursor.fetchone()
        except sqlite3.OperationalError as exception:
            logger.debug("%s", exception)
            return {}

    def fetch_nr_exists(self, number) -> dict:
        """returns a dict key of nr_count"""
        try:
            with sqlite3.connect(self.database) as conn:
                conn.row_factory = self.row_factory
                cursor = conn.cursor()
                cursor.execute(
                    f"select count(*) as nr_count from dxlog where NR = '{number}' and ContestNR = {self.current_contest};"
                )
                return cursor.fetchone()
        except sqlite3.OperationalError as exception:
            logger.debug("%s", exception)
            return {}

    def fetch_call_exists(self, call: str) -> dict:
        """returns a dict key of call_count"""
        try:
            with sqlite3.connect(self.database) as conn:
                conn.row_factory = self.row_factory
                cursor = conn.cursor()
                cursor.execute(
                    f"select count(*) as call_count from dxlog where Call = '{call}' and ContestNR = {self.current_contest};"
                )
                return cursor.fetchone()
        except sqlite3.OperationalError as exception:
            logger.debug("%s", exception)
            return {}

    def fetch_nr_exists_before_me(self, number, time_stamp) -> dict:
        """returns a dict key of nr_count"""
        try:
            with sqlite3.connect(self.database) as conn:
                conn.row_factory = self.row_factory
                cursor = conn.cursor()
                cursor.execute(
                    f"select count(*) as nr_count from dxlog where  TS < '{time_stamp}' and NR = '{number}' and ContestNR = {self.current_contest};"
                )
                return cursor.fetchone()
        except sqlite3.OperationalError as exception:
            logger.debug("%s", exception)
            return {}

    def fetch_call_count(self) -> dict:
        """
        returns dict with count of unique calls.
        {call_count: count}
        """
        try:
            with sqlite3.connect(self.database) as conn:
                conn.row_factory = self.row_factory
                cursor = conn.cursor()
                cursor.execute(
                    f"select count(DISTINCT Call) as call_count from dxlog where ContestNR = {self.current_contest};"
                )
                return cursor.fetchone()
        except sqlite3.OperationalError as exception:
            logger.debug("%s", exception)
            return {}

    def fetch_wpx_count(self) -> dict:
        """
        returns dict with count of unique WPXPrefix.
        {wpx_count: count}
        """
        try:
            with sqlite3.connect(self.database) as conn:
                conn.row_factory = self.row_factory
                cursor = conn.cursor()
                cursor.execute(
                    f"select count(DISTINCT WPXPrefix) as wpx_count from dxlog where ContestNR = {self.current_contest};"
                )
                return cursor.fetchone()
        except sqlite3.OperationalError as exception:
            logger.debug("%s", exception)
            return {}

    def fetch_dxcc_exists(self, dxcc) -> dict:
        """returns the dict dxcc_count of dxcc existing in current contest."""
        try:
            with sqlite3.connect(self.database) as conn:
                conn.row_factory = self.row_factory
                cursor = conn.cursor()
                cursor.execute(
                    f"select count(*) as dxcc_count from dxlog where CountryPrefix = '{dxcc}' and ContestNR = {self.current_contest};"
                )
                return cursor.fetchone()
        except sqlite3.OperationalError as exception:
            logger.debug("%s", exception)
            return {}

    def fetch_dxcc_exists_before_me(self, dxcc, time_stamp) -> dict:
        """returns the dict dxcc_count of dxcc existing in current contest."""
        try:
            with sqlite3.connect(self.database) as conn:
                conn.row_factory = self.row_factory
                cursor = conn.cursor()
                cursor.execute(
                    f"select count(*) as dxcc_count from dxlog where TS < '{time_stamp}' and CountryPrefix = '{dxcc}' and ContestNR = {self.current_contest};"
                )
                return cursor.fetchone()
        except sqlite3.OperationalError as exception:
            logger.debug("%s", exception)
            return {}

    def fetch_wpx_exists(self, wpx) -> dict:
        """returns a dict key of wpx_count"""
        try:
            with sqlite3.connect(self.database) as conn:
                conn.row_factory = self.row_factory
                cursor = conn.cursor()
                cursor.execute(
                    f"select count(*) as wpx_count from dxlog where WPXPrefix = '{wpx}' and ContestNR = {self.current_contest};"
                )
                return cursor.fetchone()
        except sqlite3.OperationalError as exception:
            logger.debug("%s", exception)
            return {}

    def fetch_wpx_exists_before_me(self, wpx, time_stamp) -> dict:
        """returns a dict key of wpx_count"""
        try:
            with sqlite3.connect(self.database) as conn:
                conn.row_factory = self.row_factory
                cursor = conn.cursor()
                cursor.execute(
                    f"select count(*) as wpx_count from dxlog where  TS < '{time_stamp}' and WPXPrefix = '{wpx}' and ContestNR = {self.current_contest};"
                )
                return cursor.fetchone()
        except sqlite3.OperationalError as exception:
            logger.debug("%s", exception)
            return {}

    def fetch_sect_band_exists(self, sect, band) -> dict:
        """returns a dict key of sect_count"""
        try:
            with sqlite3.connect(self.database) as conn:
                conn.row_factory = self.row_factory
                cursor = conn.cursor()
                cursor.execute(
                    f"select count(*) as sect_count from dxlog where Sect = '{sect}' and Band = '{band}' and ContestNR = {self.current_contest};"
                )
                return cursor.fetchone()
        except sqlite3.OperationalError as exception:
            logger.debug("%s", exception)
            return {}

    def fetch_sect_exists(self, sect) -> dict:
        """returns a dict key of sect_count"""
        try:
            with sqlite3.connect(self.database) as conn:
                conn.row_factory = self.row_factory
                cursor = conn.cursor()
                cursor.execute(
                    f"select count(*) as sect_count from dxlog where Sect = '{sect}' and ContestNR = {self.current_contest};"
                )
                return cursor.fetchone()
        except sqlite3.OperationalError as exception:
            logger.debug("%s", exception)
            return {}

    def fetch_sect_exists_before_me(self, sec, time_stamp) -> dict:
        """returns a dict key of sect_count"""
        try:
            with sqlite3.connect(self.database) as conn:
                conn.row_factory = self.row_factory
                cursor = conn.cursor()
                cursor.execute(
                    f"select count(*) as sect_count from dxlog where  TS < '{time_stamp}' and Sect = '{sec}' and ContestNR = {self.current_contest};"
                )
                return cursor.fetchone()
        except sqlite3.OperationalError as exception:
            logger.debug("%s", exception)
            return {}

    def fetch_section_band_count(self) -> dict:
        """
        returns dict with count of unique Section/Band.
        {sb_count: count}
        """
        try:
            with sqlite3.connect(self.database) as conn:
                conn.row_factory = self.row_factory
                cursor = conn.cursor()
                cursor.execute(
                    f"select count(DISTINCT(Sect || ':' || Band)) as sb_count from dxlog where ContestNR = {self.current_contest};"
                )
                return cursor.fetchone()
        except sqlite3.OperationalError as exception:
            logger.debug("%s", exception)
            return {}

    def fetch_section_band_count_nodx(self) -> dict:
        """
        returns dict with count of unique Section/Band.
        {sb_count: count}
        """
        try:
            with sqlite3.connect(self.database) as conn:
                conn.row_factory = self.row_factory
                cursor = conn.cursor()
                cursor.execute(
                    "select count(DISTINCT(Sect || ':' || Band)) as sb_count from dxlog "
                    f"where ContestNR = {self.current_contest} and Sect != 'DX';"
                )
                return cursor.fetchone()
        except sqlite3.OperationalError as exception:
            logger.debug("%s", exception)
            return {}

    def check_dupe_on_band_mode(self, call, band, mode) -> dict:
        """Checks if a call is dupe on band/mode"""
        try:
            with sqlite3.connect(self.database) as conn:
                conn.row_factory = self.row_factory
                cursor = conn.cursor()
                cursor.execute(
                    f"select count(*) as isdupe from dxlog where Call = '{call}' and Mode = '{mode}' and Band = '{band}' and ContestNR = {self.current_contest};"
                )
                return cursor.fetchone()
        except sqlite3.OperationalError as exception:
            logger.debug("%s", exception)
            return {}

    def check_dupe_on_band(self, call, band) -> dict:
        """Checks if a call is dupe on band/mode"""
        try:
            with sqlite3.connect(self.database) as conn:
                conn.row_factory = self.row_factory
                cursor = conn.cursor()
                cursor.execute(
                    f"select count(*) as isdupe from dxlog where Call = '{call}' and Band = '{band}' and ContestNR = {self.current_contest};"
                )
                return cursor.fetchone()
        except sqlite3.OperationalError as exception:
            logger.debug("%s", exception)
            return {}

    def check_dupe(self, call) -> dict:
        """Checks if a call is dupe on band/mode"""
        try:
            with sqlite3.connect(self.database) as conn:
                conn.row_factory = self.row_factory
                cursor = conn.cursor()
                cursor.execute(
                    f"select count(*) as isdupe from dxlog where Call = '{call}' and ContestNR = {self.current_contest};"
                )
                return cursor.fetchone()
        except sqlite3.OperationalError as exception:
            logger.debug("%s", exception)
            return {}

    def fetch_points(self) -> dict:
        """return points"""
        try:
            with sqlite3.connect(self.database) as conn:
                conn.row_factory = self.row_factory
                cursor = conn.cursor()
                cursor.execute(
                    f"select sum(Points) as Points from dxlog where ContestNR = {self.current_contest};"
                )
                return cursor.fetchone()
        except sqlite3.OperationalError as exception:
            logger.debug("%s", exception)
            return {}

    def fetch_mult_count(self, mult: int) -> dict:
        """return QSO count"""
        try:
            with sqlite3.connect(self.database) as conn:
                conn.row_factory = self.row_factory
                cursor = conn.cursor()
                cursor.execute(
                    f"select count(*) as count from dxlog where IsMultiplier{mult} = 1 and ContestNR = {self.current_contest};"
                )
                return cursor.fetchone()
        except sqlite3.OperationalError as exception:
            logger.debug("%s", exception)
            return {}

    def fetch_qso_count(self) -> dict:
        """return QSO count"""
        try:
            with sqlite3.connect(self.database) as conn:
                conn.row_factory = self.row_factory
                cursor = conn.cursor()
                cursor.execute(
                    f"select count(*) as qsos from dxlog where ContestNR = {self.current_contest};"
                )
                return cursor.fetchone()
        except sqlite3.OperationalError as exception:
            logger.debug("%s", exception)
            return {}

    def fetch_like_calls(self, call: str) -> list:
        """returns a list of dicts with contacts in the database."""
        try:
            with sqlite3.connect(self.database) as conn:
                conn.row_factory = self.row_factory
                cursor = conn.cursor()
                cursor.execute(
                    f"select * from dxlog where call like '%{call}%' and ContestNR = {self.current_contest} order by TS ASC;"
                )
                return cursor.fetchall()
        except sqlite3.OperationalError as exception:
            logger.debug("%s", exception)
            return ()

    def get_serial(self) -> dict:
        """Return next serial number"""
        try:
            with sqlite3.connect(self.database) as conn:
                conn.row_factory = self.row_factory
                cursor = conn.cursor()
                cursor.execute(
                    f"select max(SentNR) + 1 as serial_nr from DXLOG where ContestNR = {self.current_contest};"
                )
                return cursor.fetchone()
        except sqlite3.OperationalError as exception:
            logger.debug("%s", exception)
            return {}

    def get_empty(self) -> dict:
        """Return a dictionary object with keys and no values."""
        return self.empty_contact

    def get_calls_and_bands(self) -> dict:
        """
        Returns a dict like:
        {'K5TUX': [14.0, 21.0], 'N2CQR': [14.0], 'NE4RD': [14.0]}
        """
        try:
            with sqlite3.connect(self.database) as conn:
                conn.row_factory = self.row_factory
                cursor = conn.cursor()
                cursor.execute(
                    f"select call, band from DXLOG where ContestNR = {self.current_contest};"
                )
                result = cursor.fetchall()
                worked_list = {}
                # This converts a list of dicts like:
                # [
                #     {"Call": "K5TUX", "Band": 14.0},
                #     {"Call": "K5TUX", "Band": 21.0},
                #     {"Call": "N2CQR", "Band": 14.0},
                #     {"Call": "NE4RD", "Band": 14.0},
                # ]
                #
                # To:
                # {'K5TUX': [14.0, 21.0], 'N2CQR': [14.0], 'NE4RD': [14.0]}
                for worked_dict in result:
                    call = worked_dict.get("Call")
                    if call in worked_list:
                        bandlist = worked_list[call]
                        bandlist.append(worked_dict["Band"])
                        worked_list[call] = bandlist
                        continue
                    worked_list[call] = [worked_dict["Band"]]
                return worked_list
        except sqlite3.OperationalError as exception:
            logger.debug("%s", exception)
            return {}

    def get_like_calls_and_bands(self, call: str) -> dict:
        """
        Returns a dict like:
        {'K5TUX': [14.0, 21.0], 'N2CQR': [14.0], 'NE4RD': [14.0]}
        """
        try:
            with sqlite3.connect(self.database) as conn:
                conn.row_factory = self.row_factory
                cursor = conn.cursor()
                cursor.execute(
                    f"select call, band from DXLOG where call like '%{call}%' and ContestNR = {self.current_contest};"
                )
                result = cursor.fetchall()
                worked_list = {}
                # This converts a list of dicts like:
                # [
                #     {"Call": "K5TUX", "Band": 14.0},
                #     {"Call": "K5TUX", "Band": 21.0},
                #     {"Call": "N2CQR", "Band": 14.0},
                #     {"Call": "NE4RD", "Band": 14.0},
                # ]
                #
                # To:
                # {'K5TUX': [14.0, 21.0], 'N2CQR': [14.0], 'NE4RD': [14.0]}
                for worked_dict in result:
                    call = worked_dict.get("Call")
                    if call in worked_list:
                        bandlist = worked_list[call]
                        bandlist.append(worked_dict["Band"])
                        worked_list[call] = bandlist
                        continue
                    worked_list[call] = [worked_dict["Band"]]
                return worked_list
        except sqlite3.OperationalError as exception:
            logger.debug("%s", exception)
            return {}

    def get_ops(self) -> list:
        """get dict of unique station operators for contest"""
        try:
            with sqlite3.connect(self.database) as conn:
                conn.row_factory = self.row_factory
                cursor = conn.cursor()
                cursor.execute(
                    f"select DISTINCT(Operator) from DXLOG where ContestNR = {self.current_contest};"
                )
                return cursor.fetchall()
        except sqlite3.OperationalError as exception:
            logger.debug("%s", exception)
            return {}

    def get_unique_band_and_mode(self) -> dict:
        """get count of unique band and mode as {mult: x}"""
        try:
            with sqlite3.connect(self.database) as conn:
                conn.row_factory = self.row_factory
                cursor = conn.cursor()
                cursor.execute(
                    f"select count(DISTINCT(band || ':' || mode)) as mult from dxlog where ContestNR = {self.current_contest};"
                )
                return cursor.fetchone()
        except sqlite3.OperationalError as exception:
            logger.debug("%s", exception)
            return {}

    def exec_sql(self, query: str) -> dict:
        """Exec one off queries returning one dict"""
        try:
            with sqlite3.connect(self.database) as conn:
                conn.row_factory = self.row_factory
                cursor = conn.cursor()
                cursor.execute(query)
                return cursor.fetchone()
        except sqlite3.OperationalError as exception:
            logger.debug("%s", exception)
            return {}

    def exec_sql_mult(self, query: str) -> list:
        """Exec one off queries returning list of dicts"""
        try:
            with sqlite3.connect(self.database) as conn:
                conn.row_factory = self.row_factory
                cursor = conn.cursor()
                cursor.execute(query)
                return cursor.fetchall()
        except sqlite3.OperationalError as exception:
            logger.debug("%s", exception)
            return ()

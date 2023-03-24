"""
K6GTE, Database class to store contacts
Email: michael.bridak@gmail.com
GPL V3
"""
# pylint: disable=line-too-long

import logging
import sqlite3

if __name__ == "__main__":
    print("I'm not the program you are looking for.")

logger = logging.getLogger("__main__")


class DataBase:
    """Database class for our database."""

    def __init__(self, database: str, working_path: str):
        """initializes DataBase instance"""
        logger.debug("Database: %s", database)
        self.working_path = working_path
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
            "isMultiplier3": "",
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
        self.create_contest_table()
        self.create_contest_instance_table()
        self.create_station_table()

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
        with sqlite3.connect(self.database) as conn:
            cursor = conn.cursor()
            sql_command = (
                "CREATE TABLE IF NOT EXISTS DXLOG ("
                "TS DATETIME NOT NULL, "
                "Call VARCHAR(15) NOT NULL, "
                "Freq DOUBLE NULL, "
                "QSXFreq DOUBLE NULL DEFAULT 0, "
                "Mode VARCHAR(6), "
                "ContestName VARCHAR(10) DEFAULT 'NORMAL', "
                "SNT VARCHAR(10), "
                "RCV VARCHAR(15), "
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
                "Power VARCHAR(8), "
                "Band FLOAT NULL DEFAULT 0, "
                "WPXPrefix VARCHAR(8), "
                "Exchange1 VARCHAR(20), "
                "RadioNR TINYINT DEFAULT 1, "
                "ContestNR INTEGER, "
                "isMultiplier3 INTEGER, "
                "MiscText VARCHAR(20), "
                "IsRunQSO TINYINT(1) DEFAULT 0, "
                "ContactType VARCHAR(1), "
                "Run1Run2 TINYINT NOT NULL, "
                "GridSquare VARCHAR(6), "
                "Operator VARCHAR(20), "
                "Continent VARCHAR(2), "
                "RoverLocation VARCHAR(10), "
                "RadioInterfaced INTEGER, "
                "NetworkedCompNr INTEGER, NetBiosName varchar (255), "
                "IsOriginal Boolean, "
                "ID TEXT(16) NOT NULL DEFAULT '0000000000000000', "
                "CLAIMEDQSO INTEGER DEFAULT 1,"
                "PRIMARY KEY (`TS`, `Call`) );"
            )
            cursor.execute(sql_command)
            conn.commit()

    def create_contest_table(self) -> None:
        """Creates the Contest table"""
        logger.debug("Creating Contest Table")
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
                    self.working_path + "/data/contests.sql", encoding="utf-8"
                ) as data:
                    for line in data.readlines():
                        cursor.execute(line)
                conn.commit()

    def create_contest_instance_table(self) -> None:
        """Creates the ContestInstance table"""
        logger.debug("Creating ContestInstance Table")
        with sqlite3.connect(self.database) as conn:
            cursor = conn.cursor()
            sql_command = (
                "CREATE TABLE IF NOT EXISTS [ContestInstance] ("
                "[ContestID] INT NOT NULL,"
                "[ContestName] NVARCHAR(10),"
                "[StartDate] DATETIME,"
                "[OperatorCategory] NVARCHAR(20) DEFAULT "
                "'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''',"
                "[BandCategory] NVARCHAR(20) DEFAULT "
                "'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''',"
                "[PowerCategory] NVARCHAR(20) DEFAULT "
                "'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''',"
                "[ModeCategory] NVARCHAR(20) DEFAULT "
                "'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''',"
                "[OverlayCategory] NVARCHAR(20) DEFAULT "
                "'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''',"
                "[ClaimedScore] MONEY DEFAULT '''''''''''''''0''''''''''''''',"
                "[Operators] NVARCHAR(255) DEFAULT "
                "'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''',"
                "[Soapbox] TEXT,"
                "[SentExchange] NVARCHAR(50),"
                "[ContestNR] INT,"
                "[SubType] NVARCHAR(9),"
                "[StationCategory] NVARCHAR(20),"
                "[AssistedCategory] NVARCHAR(20),"
                "[TransmitterCategory] NVARCHAR(20),"
                "[TimeCategory] NVARCHAR(20),"
                "CONSTRAINT [sqlite_autoindex_ContestInstance_1] PRIMARY KEY ([ContestID]));"
            )
            cursor.execute(sql_command)
            conn.commit()

    def create_station_table(self) -> None:
        """Creates the Station table"""
        logger.debug("Creating Station Table")
        with sqlite3.connect(self.database) as conn:
            cursor = conn.cursor()
            sql_command = (
                "CREATE TABLE IF NOT EXISTS [Station] ("
                "[Call] NVARCHAR(20) NOT NULL, "
                "[Name] NVARCHAR(50), "
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
                logger.info("%s\n%s", sql, qso)
                cur = conn.cursor()
                cur.execute(sql)
                conn.commit()
        except sqlite3.Error as exception:
            logger.info("DataBase change_contact: %s", exception)

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

    def fetch_all_contacts_asc(self) -> list:
        """returns a list of dicts with contacts in the database."""
        with sqlite3.connect(self.database) as conn:
            conn.row_factory = self.row_factory
            cursor = conn.cursor()
            cursor.execute("select * from dxlog order by TS ASC;")
            return cursor.fetchall()

    def fetch_all_contacts_desc(self) -> list:
        """returns a list of dicts with contacts in the database."""
        with sqlite3.connect(self.database) as conn:
            conn.row_factory = self.row_factory
            cursor = conn.cursor()
            cursor.execute("select * from dxlog order by ts desc;")
            return cursor.fetchall()

    def fetch_last_contact(self) -> dict:
        """returns a list of dicts with last contact in the database."""
        with sqlite3.connect(self.database) as conn:
            conn.row_factory = self.row_factory
            cursor = conn.cursor()
            cursor.execute("select * from dxlog order by ts desc;")
            return cursor.fetchone()

    def fetch_contact_by_uuid(self, uuid: str) -> dict:
        """returns a list of dicts with last contact in the database."""
        with sqlite3.connect(self.database) as conn:
            conn.row_factory = self.row_factory
            cursor = conn.cursor()
            cursor.execute(f"select * from dxlog where ID='{uuid}';")
            return cursor.fetchone()

    def fetch_wpx_count(self) -> dict:
        """returns a list of dicts with last contact in the database."""
        with sqlite3.connect(self.database) as conn:
            conn.row_factory = self.row_factory
            cursor = conn.cursor()
            cursor.execute("select count(DISTINCT WPXPrefix) as wpx_count from dxlog;")
            return cursor.fetchone()

    def fetch_wpx_exists(self, wpx) -> dict:
        """returns a dict key of wpx_count"""
        with sqlite3.connect(self.database) as conn:
            conn.row_factory = self.row_factory
            cursor = conn.cursor()
            cursor.execute(
                f"select count(*) as wpx_count from dxlog where WPXPrefix = '{wpx}';"
            )
            return cursor.fetchone()

    def check_dupe_on_band_mode(self, call, band, mode) -> dict:
        """Checks if a call is dupe on band/mode"""
        with sqlite3.connect(self.database) as conn:
            conn.row_factory = self.row_factory
            cursor = conn.cursor()
            print(
                f"select count(*) as isdupe from dxlog where Call = '{call}' and Mode = '{mode}' and Band = '{band}';"
            )
            cursor.execute(
                f"select count(*) as isdupe from dxlog where Call = '{call}' and Mode = '{mode}' and Band = '{band}';"
            )
            return cursor.fetchone()

    def fetch_points(self) -> dict:
        """return points"""
        with sqlite3.connect(self.database) as conn:
            conn.row_factory = self.row_factory
            cursor = conn.cursor()
            cursor.execute("select sum(Points) as Points from dxlog;")
            return cursor.fetchone()

    def fetch_qso_count(self) -> dict:
        """return QSO count"""
        with sqlite3.connect(self.database) as conn:
            conn.row_factory = self.row_factory
            cursor = conn.cursor()
            cursor.execute("select count(*) as qsos from dxlog;")
            return cursor.fetchone()

    def fetch_like_calls(self, call: str) -> list:
        """returns a list of dicts with contacts in the database."""
        with sqlite3.connect(self.database) as conn:
            conn.row_factory = self.row_factory
            cursor = conn.cursor()
            cursor.execute(
                f"select * from dxlog where call like '%{call}%' order by TS ASC;"
            )
            return cursor.fetchall()

    def get_serial(self) -> dict:
        """Return serial number"""
        with sqlite3.connect(self.database) as conn:
            conn.row_factory = self.row_factory
            cursor = conn.cursor()
            cursor.execute("select max(SentNR) + 1 as serial_nr from DXLOG;")
            return cursor.fetchone()

    def get_empty(self) -> dict:
        """Return a dictionary object with keys and no values."""
        return self.empty_contact

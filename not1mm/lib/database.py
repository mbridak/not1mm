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
        self.connect(database)
        self.create_dxlog_table()
        self.update_dxlog_table()
        self.create_contest_table()
        self.create_contest_instance_table()
        self.create_station_table()
        self.create_callhistory_table()

    @staticmethod
    def row_factory(cursor, row):
        """
        Converts a row (value, value, ...) into a dict {colname: value, ...}

        cursor.description:
        (name, type_code, display_size,
        internal_size, precision, scale, null_ok)
        """
        return {
            col[0]: row[idx]
            for idx, col in enumerate(
                cursor.description,
            )
        }

    def connect(self, database):
        self.database = database
        try:
            self.conn = sqlite3.connect(database)
            self.conn.row_factory = self.row_factory
            cursor = self.conn.cursor()
            cursor.execute("PRAGMA journal_mode=DELETE")
            self.conn.commit()
        except sqlite3.OperationalError as exception:
            logger.error("%s", exception)

    def exec_sql(self, query: str, params=()) -> dict:
        """Exec read query returning one dict"""
        try:
            logger.debug("%s", query)
            if params:
                logger.debug("Parameters: %s", params)
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchone()
        except sqlite3.OperationalError as exception:
            logger.error("%s", exception)
            return {}

    def exec_sql_mult(self, query: str, params=()) -> list:
        """Exec read query returning list of dicts"""
        try:
            logger.debug("%s", query)
            if params:
                logger.debug("Parameters: %s", params)
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()
        except sqlite3.OperationalError as exception:
            logger.error("%s", exception)
            return ()

    def exec_sql_commit(self, query: str, params=(), error_logger=logger.error) -> None:
        """Exec write query with database changes and commit"""
        try:
            logger.debug("%s", query)
            if params:
                logger.debug("Parameters: %s", params)
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            self.conn.commit()
        except sqlite3.OperationalError as exception:
            error_logger("%s", exception)

    def exec_sql_insert(self, table: str, row: dict) -> None:
        """Insert a dict into table columns"""
        if row == {}:
            return

        fields, values, placeholders = [], [], []
        for field in row.keys():
            fields.append(field)
            values.append(row[field])
            placeholders.append("?")

        self.exec_sql_commit(
            f"insert into {table} ({', '.join(fields)}) values ({', '.join(placeholders)});",
            values,
        )

    def exec_sql_update(self, table: str, row: dict, key: str) -> None:
        """Update a row with dict values (identified by key, part of the dict)"""
        if len(row) <= 1 or key not in row:
            return

        fields, values = [], []
        for field in row.keys():
            if field == key:
                continue
            fields.append(f"{field} = ?")
            values.append(row[field])

        self.exec_sql_commit(
            f"update {table} set {', '.join(fields)} where {key} = ?;",
            values + [row[key]],
        )

    def create_dxlog_table(self) -> None:
        """creates the dxlog table"""
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
        self.exec_sql_commit(sql_command)

    def create_callhistory_table(self) -> None:
        """creates the callhistory table"""
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
        self.exec_sql_commit(sql_command)

    def update_dxlog_table(self) -> None:
        """update missing columns"""
        logger.debug("Updating DXLOG Table")
        sql_command = "ALTER TABLE DXLOG ADD dirty INTEGER DEFAULT 1;"
        self.exec_sql_commit(sql_command, error_logger=logger.debug)

    def create_contest_table(self) -> None:
        """Creates the Contest table"""
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
        self.exec_sql_commit(sql_command)

        result = self.exec_sql("select count(*) as count from Contest;")
        if result.get("count") == 0:
            with open(self.app_data_dir / "contests.sql", encoding="utf-8") as data:
                logger.debug("Populating contests table")
                cursor = self.conn.cursor()
                cursor.executescript(data.read())
                self.conn.commit()

    def create_contest_instance_table(self) -> None:
        """Creates the ContestInstance table"""
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
        self.exec_sql_commit(sql_command)

    def create_station_table(self) -> None:
        """Creates the Station table"""
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
        self.exec_sql_commit(sql_command)

    def add_station(self, station: dict) -> None:
        """Add station information"""
        logger.info("%s", station)
        self.exec_sql_commit("DELETE FROM Station;")
        self.exec_sql_insert("Station", station)

    def fetch_station(self) -> dict:
        """returns a list of dicts with last contact in the database."""
        return self.exec_sql("select * from Station;")

    def get_next_contest_nr(self):
        """Returns the next ContestNR to use."""
        return self.exec_sql("select count(*) + 1 as count from ContestInstance;")

    def fetch_contest_by_id(self, contest_nr: str) -> dict:
        """returns a dict of ContestInstance"""
        return self.exec_sql(
            "select * from ContestInstance where ContestNR = ?;", (contest_nr,)
        )

    def add_callhistory_item(self, history: dict) -> None:
        """Add an item to the call history db"""
        self.exec_sql_insert("CALLHISTORY", history)

    def add_callhistory_items(self, history_list: list) -> None:
        """Add a list of items to the call history db"""
        for history in history_list:
            self.exec_sql_insert("CALLHISTORY", history)

    def get_contest_profile(self, contest: str):
        """get the contest profile"""
        return self.exec_sql("select * from Contest where Name = ?;", (contest,))

    def get_contest_list(self):
        """get the list of contests"""
        return self.exec_sql_mult(
            "select Name, DisplayName from Contest order by DisplayName;"
        )

    def add_contest(self, contest: dict) -> None:
        """Add Contest"""
        logger.info("%s", contest)
        self.exec_sql_insert("ContestInstance", contest)

    def update_contest(self, contest: dict) -> None:
        """Update an existing contest"""
        self.exec_sql_update("ContestInstance", contest, "ContestNR")

    def fetch_all_contests(self) -> list:
        """returns a list of dicts with contests in the database."""
        return self.exec_sql_mult("select * from ContestInstance;")

    def log_contact(self, contact: dict) -> None:
        """
        Inserts a contact into the db.
        pass in a dict object, see get_empty() for keys
        """
        logger.info("%s", contact)
        self.exec_sql_insert("DXLOG", contact)

    def change_contact(self, qso: dict) -> None:
        """Update an existing contact."""
        self.exec_sql_update("DXLOG", qso, "ID")

    def delete_contact(self, unique_id: str) -> None:
        """Deletes a contact from the db."""
        if unique_id:
            self.exec_sql_commit("delete from dxlog where ID = ?;", (unique_id,))

    def clear_dirty_flag(self, unique_id: str) -> None:
        """Clears the dirty flag."""
        if unique_id:
            self.exec_sql_commit("update dxlog set dirty=0 where ID = ?;", (unique_id,))

    def make_all_dirty(self) -> None:
        """Set the dirty flag."""
        self.exec_sql_commit(
            "update dxlog set dirty=1 where ContestNR = ?;", (self.current_contest,)
        )

    def delete_callhistory(self) -> None:
        """Deletes all info from callhistory table."""
        self.exec_sql_commit("delete from CALLHISTORY;")

    def fetch_call_history(self, call: str):
        """"""
        return self.exec_sql("select * from CALLHISTORY where call = ?;", (call,))

    def fetch_all_contacts_asc(self) -> list:
        """returns a list of dicts with contacts in the database."""
        return self.exec_sql_mult(
            "select * from dxlog where ContestNR = ? order by TS ASC;",
            (self.current_contest,),
        )

    def fetch_all_dirty_contacts(self) -> list:
        """returns a list of dicts of contacts with dirty flag set in the database."""
        return self.exec_sql_mult(
            "select * from dxlog where ContestNR = ? and dirty = 1;",
            (self.current_contest,),
        )

    def fetch_all_contacts_desc(self) -> list:
        """returns a list of dicts with contacts in the database."""
        return self.exec_sql_mult(
            "select * from dxlog where ContestNR = ? order by ts desc;",
            (self.current_contest,),
        )

    def fetch_last_contact(self) -> dict:
        """returns a list of dicts with last contact in the database."""
        return self.exec_sql("select * from dxlog order by ts desc;")

    def fetch_contact_by_uuid(self, uuid: str) -> dict:
        """returns a list of dicts with last contact in the database."""
        return self.exec_sql(f"select * from dxlog where ID = ?;", (uuid,))

    def fetch_cqzn_exists(self, number) -> dict:
        """returns a dict key of nr_count"""
        return self.exec_sql(
            "select count(*) as zn_count from dxlog where ZN = ? and ContestNR = ?;",
            (number, self.current_contest),
        )

    def fetch_zn_band_count(self) -> dict:
        """
        returns dict with count of unique ZN and Band.
        {nr_count: count}
        """
        return self.exec_sql(
            "select count(DISTINCT(ZN || ':' || Band)) as zb_count from dxlog where ContestNR = ?;",
            (self.current_contest,),
        )

    def fetch_zn_band_mode_count(self) -> dict:
        """
        returns dict with count of unique ZN, Band and Mode.
        {nr_count: count}
        """
        return self.exec_sql(
            "select count(DISTINCT(ZN || ':' || Band || ':' || Mode)) as zbm_count from dxlog where ContestNR = ?;",
            (self.current_contest,),
        )

    def fetch_country_band_count(self) -> dict:
        """
        returns dict with count of unique NR.
        {cb_count: count}
        """
        return self.exec_sql(
            "select count(DISTINCT(CountryPrefix || ':' || Band)) as cb_count from dxlog where ContestNR = ?;",
            (self.current_contest,),
        )

    def fetch_country_count(self) -> dict:
        """
        Fetch count of unique countries
        {dxcc_count: count}
        """
        return self.exec_sql(
            "select count(DISTINCT(CountryPrefix)) as dxcc_count from dxlog where ContestNR = ?;",
            (self.current_contest,),
        )

    def fetch_dxcc_by_band_count(self) -> list:
        """
        Fetch list containing count of unique countries by band

        """
        query = f"""
                    SELECT CountryPrefix,
                        SUM(CASE WHEN Band = 1.8 THEN 1 ELSE 0 END) AS '160m',
                        SUM(CASE WHEN Band = 3.5 THEN 1 ELSE 0 END) AS '80m',
                        SUM(CASE WHEN Band = 7.0 THEN 1 ELSE 0 END) AS '40m',
                        SUM(CASE WHEN Band = 14.0 THEN 1 ELSE 0 END) AS '20m',
                        SUM(CASE WHEN Band = 21.0 THEN 1 ELSE 0 END) AS '15m',
                        SUM(CASE WHEN Band = 28.0 THEN 1 ELSE 0 END) AS '10m',
                        COUNT(*) AS Total
                    FROM DXLOG where ContestNR = {self.current_contest}
                    GROUP BY CountryPrefix
                """
        #                            ORDER BY Total DESC
        return self.exec_sql_mult(query)

    def fetch_zone_by_band_count(self) -> list:
        """
        Fetch list containing count of unique zones by band

        """
        query = f"""
                    SELECT ZN,
                        SUM(CASE WHEN Band = 1.8 THEN 1 ELSE 0 END) AS '160m',
                        SUM(CASE WHEN Band = 3.5 THEN 1 ELSE 0 END) AS '80m',
                        SUM(CASE WHEN Band = 7.0 THEN 1 ELSE 0 END) AS '40m',
                        SUM(CASE WHEN Band = 14.0 THEN 1 ELSE 0 END) AS '20m',
                        SUM(CASE WHEN Band = 21.0 THEN 1 ELSE 0 END) AS '15m',
                        SUM(CASE WHEN Band = 28.0 THEN 1 ELSE 0 END) AS '10m',
                        COUNT(*) AS Total
                    FROM DXLOG where ContestNR = {self.current_contest}
                    GROUP BY ZN
                """
        #                            ORDER BY Total DESC
        return self.exec_sql_mult(query)

    def fetch_exchange1_unique_count(self) -> dict:
        """
        Fetch count of unique countries
        {exch1_count: count}
        """
        return self.exec_sql(
            "select count(DISTINCT(Exchange1)) as exch1_count from dxlog where Exchange1 != '' and ContestNR = ?;",
            (self.current_contest,),
        )

    def fetch_arrldx_country_band_count(self) -> dict:
        """
        returns dict with count of unique NR.
        {nr_count: count}
        """
        return self.exec_sql(
            "select count(DISTINCT(CountryPrefix || ':' || Band)) as cb_count from dxlog where ContestNR = ? and points = 3;",
            (self.current_contest,),
        )

    def fetch_arrldx_state_prov_count(self) -> dict:
        """
        returns dict with count of unique NR.
        {nr_count: count}
        """
        return self.exec_sql(
            "select count(DISTINCT(NR || ':' || Band)) as cb_count from dxlog where ContestNR = ? and points = 3;",
            (self.current_contest,),
        )

    def fetch_nr_count(self) -> dict:
        """
        returns dict with count of unique NR.
        {nr_count: count}
        """
        return self.exec_sql(
            "select count(DISTINCT NR) as nr_count from dxlog where ContestNR = ?;",
            (self.current_contest,),
        )

    def fetch_nr_exists(self, number) -> dict:
        """returns a dict key of nr_count"""
        return self.exec_sql(
            "select count(*) as nr_count from dxlog where NR = ? and ContestNR = ?;",
            (number, self.current_contest),
        )

    def fetch_call_exists(self, call: str) -> dict:
        """returns a dict key of call_count"""
        return self.exec_sql(
            "select count(*) as call_count from dxlog where Call = ? and ContestNR = ?;",
            (call, self.current_contest),
        )

    def fetch_nr_exists_before_me(self, number, time_stamp) -> dict:
        """returns a dict key of nr_count"""
        return self.exec_sql(
            "select count(*) as nr_count from dxlog where  TS < ? and NR = ? and ContestNR = ?;",
            (time_stamp, number, self.current_contest),
        )

    def fetch_call_count(self) -> dict:
        """
        returns dict with count of unique calls.
        {call_count: count}
        """
        return self.exec_sql(
            "select count(DISTINCT Call) as call_count from dxlog where ContestNR = ?;",
            (self.current_contest,),
        )

    def fetch_wpx_count(self) -> dict:
        """
        returns dict with count of unique WPXPrefix.
        {wpx_count: count}
        """
        return self.exec_sql(
            "select count(DISTINCT WPXPrefix) as wpx_count from dxlog where ContestNR = ?;",
            (self.current_contest,),
        )

    def fetch_dxcc_exists(self, dxcc) -> dict:
        """returns the dict dxcc_count of dxcc existing in current contest."""
        return self.exec_sql(
            "select count(*) as dxcc_count from dxlog where CountryPrefix = ? and ContestNR = ?;",
            (dxcc, self.current_contest),
        )

    def fetch_dxcc_exists_before_me(self, dxcc, time_stamp) -> dict:
        """returns the dict dxcc_count of dxcc existing in current contest."""
        return self.exec_sql(
            "select count(*) as dxcc_count from dxlog where TS < ? and CountryPrefix = ? and ContestNR = ?;",
            (time_stamp, dxcc, self.current_contest),
        )

    def fetch_wpx_exists(self, wpx) -> dict:
        """returns a dict key of wpx_count"""
        return self.exec_sql(
            "select count(*) as wpx_count from dxlog where WPXPrefix = ? and ContestNR = ?;",
            (wpx, self.current_contest),
        )

    def fetch_wpx_exists_before_me(self, wpx, time_stamp) -> dict:
        """returns a dict key of wpx_count"""
        return self.exec_sql(
            "select count(*) as wpx_count from dxlog where TS < ? and WPXPrefix = ? and ContestNR = ?;",
            (time_stamp, wpx, self.current_contest),
        )

    def fetch_sect_band_exists(self, sect, band) -> dict:
        """returns a dict key of sect_count"""
        return self.exec_sql(
            "select count(*) as sect_count from dxlog where Sect = ? and Band = ? and ContestNR = ?;",
            (sect, band, self.current_contest),
        )

    def fetch_sect_exists(self, sect) -> dict:
        """returns a dict key of sect_count"""
        return self.exec_sql(
            "select count(*) as sect_count from dxlog where Sect = ? and ContestNR = ?;",
            (sect, self.current_contest),
        )

    def fetch_sect_exists_before_me(self, sect, time_stamp) -> dict:
        """returns a dict key of sect_count"""
        return self.exec_sql(
            "select count(*) as sect_count from dxlog where  TS < ? and Sect = ? and ContestNR = ?;",
            (time_stamp, sect, self.current_contest),
        )

    def fetch_section_band_count(self) -> dict:
        """
        returns dict with count of unique Section/Band.
        {sb_count: count}
        """
        return self.exec_sql(
            "select count(DISTINCT(Sect || ':' || Band)) as sb_count from dxlog where ContestNR = ?;",
            (self.current_contest,),
        )

    def fetch_section_band_count_nodx(self) -> dict:
        """
        returns dict with count of unique Section/Band.
        {sb_count: count}
        """
        return self.exec_sql(
            "select count(DISTINCT(Sect || ':' || Band)) as sb_count from dxlog where ContestNR = ? and Sect != 'DX';",
            (self.current_contest,),
        )

    def check_dupe_on_band_mode(self, call, band, mode) -> dict:
        """Checks if a call is dupe on band/mode"""
        match mode:
            case "LSB" | "USB" | "SSB" | "FM" | "AM":
                mode_test = "PH"
            case "CW" | "CW-U" | "CW-L" | "CWR" | "CW-R":
                mode_test = "CW"
            case (
                "FT8"
                | "FT4"
                | "RTTY"
                | "PSK31"
                | "FSK441"
                | "MSK144"
                | "JT65"
                | "JT9"
                | "Q65"
                | "PKTUSB"
                | "PKTLSB"
            ):
                mode_test = "DI"
            case _:
                mode_test = "OTHER"
        # end match

        query = f"""
                    select 
                    count(*) as isdupe
                    from (
                            select
                                CASE 
                                    WHEN Mode IN ('LSB','USB','SSB','FM','AM') THEN 'PH' 
                                    WHEN Mode like 'CW%' THEN 'CW' 
                                    WHEN Mode In ('FT8','FT4','RTTY','PSK31','FSK441','MSK144','JT65','JT9','Q65', 'PKTUSB', 'PKTLSB') THEN 'DI' 
                                    ELSE 'OTHER' 
                                END mode,
                                *
                            from DXLOG
                            ) as sortedmode

                    where sortedmode.Call = ? and sortedmode.mode = ? and sortedmode.Band = ? and sortedmode.ContestNR = ?;
                    """
        return self.exec_sql(query, (call, mode_test, band, self.current_contest))

    def check_dupe_on_band(self, call, band) -> dict:
        """Checks if a call is dupe on band/mode"""
        return self.exec_sql(
            "select count(*) as isdupe from dxlog where Call = ? and Band = ? and ContestNR = ?;",
            (call, band, self.current_contest),
        )

    def check_dupe(self, call) -> dict:
        """Checks if a call is dupe on band/mode"""
        return self.exec_sql(
            "select count(*) as isdupe from dxlog where Call = ? and ContestNR = ?;",
            (call, self.current_contest),
        )

    def fetch_points(self) -> dict:
        """return points"""
        return self.exec_sql(
            "select sum(Points) as Points from dxlog where ContestNR = ?;",
            (self.current_contest,),
        )

    def fetch_mult_count(self, mult: int) -> dict:
        """return QSO count"""
        return self.exec_sql(
            f"select count(*) as count from dxlog where IsMultiplier{mult} = 1 and ContestNR = ?;",
            (self.current_contest,),
        )

    def fetch_qso_count(self) -> dict:
        """return QSO count"""
        return self.exec_sql(
            "select count(*) as qsos from dxlog where ContestNR = ?;",
            (self.current_contest,),
        )

    def fetch_like_calls(self, call: str) -> list:
        """returns a list of dicts with contacts in the database."""
        return self.exec_sql_mult(
            "select * from dxlog where call like ? and ContestNR = ? order by TS ASC;",
            (f"%{call}%", self.current_contest),
        )

    def get_serial(self) -> dict:
        """Return next serial number"""
        return self.exec_sql(
            "select max(SentNR) + 1 as serial_nr from DXLOG where ContestNR = ?;",
            (self.current_contest,),
        )

    def get_last_serial(self) -> dict:
        """Return next serial number"""
        return self.exec_sql(
            "select max(SentNR) as serial_nr from DXLOG where ContestNR = ?;",
            (self.current_contest,),
        )

    def get_empty(self) -> dict:
        """Return a dictionary object with keys and no values."""
        return self.empty_contact

    def get_calls_and_bands(self) -> dict:
        """
        Returns a dict like:
        {'K5TUX': [14.0, 21.0], 'N2CQR': [14.0], 'NE4RD': [14.0]}
        """
        result = self.exec_sql_mult(
            "select call, band from DXLOG where ContestNR = ?;", (self.current_contest,)
        )
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

    def get_like_calls_and_bands(self, call: str) -> dict:
        """
        Returns a dict like:
        {'K5TUX': [14.0, 21.0], 'N2CQR': [14.0], 'NE4RD': [14.0]}
        """
        result = self.exec_sql_mult(
            "select call, band from DXLOG where call like ? and ContestNR = ?;",
            (f"%{call}%", self.current_contest),
        )
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

    def get_ops(self) -> list:
        """get dict of unique station operators for contest"""
        return self.exec_sql_mult(
            "select DISTINCT(Operator) from DXLOG where ContestNR = ?;",
            (self.current_contest,),
        )

    def get_unique_band_and_mode(self) -> dict:
        """get count of unique band and mode as {mult: x}"""
        return self.exec_sql(
            "select count(DISTINCT(band || ':' || mode)) as mult from dxlog where ContestNR = ?;",
            (self.current_contest,),
        )

    def check_dupe_on_period_mode(self, call, band, mode, period_1, period_2) -> dict:
        """Checks if a call is dupe on band/mode"""
        return self.exec_sql(
            "select count(*) as isdupe from dxlog where Call = ? and Mode = ? and Band = ? and ContestNR = ? AND TS >= ? AND TS <= ?;",
            (call, mode, band, self.current_contest, period_1, period_2),
        )

    def fetch_band_lastletter_exists(self, band, call) -> dict:
        return self.exec_sql(
            "select count(*) as count from dxlog where band = ? and substr(call, -1) = substr(?, -1) and ContestNR = ?;",
            (band, call, self.current_contest),
        )

    def fetch_band_lastletter_exists_before_me(self, band, call, time_stamp) -> dict:
        return self.exec_sql(
            "select count(*) as count from dxlog where band = ? and substr(call, -1) = substr(?, -1) and TS < ? and ContestNR = ?;",
            (band, call, time_stamp, self.current_contest),
        )

    def fetch_band_lastletter_count(self) -> dict:
        return self.exec_sql(
            "select count(DISTINCT substr(call, -1) || ':' || band) as count from dxlog where ContestNR = ?;",
            (self.current_contest,),
        )

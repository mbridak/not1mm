"""
K6GTE, Database class to store contacts
Email: michael.bridak@gmail.com
GPL V3
"""
import logging
import sqlite3

if __name__ == "__main__":
    print("I'm not the program you are looking for.")


class DataBase:
    """Database class for our database."""

    def __init__(self, database: str):
        """initializes DataBase instance"""
        self.logger = logging.getLogger("__name__")
        self.empty_contact = {
            "primarykey": 1,
            "app": "",
            "contestname": "",
            "contestnr": "",
            "timestamp": "",
            "mycall": "",
            "band": "",
            "rxfreq": "",
            "txfreq": "",
            "operator": "",
            "mode": "",
            "call": "",
            "countryprefix": "",
            "wpxprefix": "",
            "stationprefix": "",
            "continent": "",
            "snt": "",
            "sntnr": "",
            "rcv": "",
            "rcvnr": "",
            "gridsquare": "",
            "exchangel": "",
            "section": "",
            "comment": "",
            "qth": "",
            "name": "",
            "power": "",
            "misctext": "",
            "zone": "",
            "prec": "",
            "ck": "",
            "ismultiplierl": "",
            "ismultiplier2": "",
            "ismultiplier3": "",
            "points": "",
            "radionr": "",
            "run1run2": "",
            "RoverLocation": "",
            "RadioInterfaced": "",
            "NetworkedCompNr": "",
            "IsOriginal": "",
            "NetBiosName": "",
            "IsRunQSO": "",
            "StationName": "",
            "ID": "",
            "IsClaimedQso": 1,
        }
        self.database = database
        self.create_db()

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

    def create_db(self) -> None:
        """create a database and table if it does not exist"""
        self.logger.info("Creating Database: %s", self.database)
        with sqlite3.connect(self.database) as conn:
            cursor = conn.cursor()
            sql_table = (
                "CREATE TABLE IF NOT EXISTS contactinfo "
                "(primarykey INTEGER PRIMARY KEY, "
                "app TEXT DEFAULT K6GTELOGGER,"
                "contestname TEXT,"
                "contestnr TEXT,"
                "timestamp TEXT,"
                "mycall TEXT,"
                "band TEXT,"
                "rxfreq TEXT,"
                "txfreq TEXT,"
                "operator TEXT,"
                "mode TEXT,"
                "call TEXT,"
                "countryprefix TEXT,"
                "wpxprefix TEXT,"
                "stationprefix TEXT,"
                "continent TEXT,"
                "snt TEXT,"
                "sntnr TEXT,"
                "rcv TEXT,"
                "rcvnr TEXT,"
                "gridsquare TEXT,"
                "exchangel TEXT,"
                "section TEXT,"
                "comment TEXT,"
                "qth TEXT,"
                "name TEXT,"
                "power TEXT,"
                "misctext TEXT,"
                "zone TEXT,"
                "prec TEXT,"
                "ck TEXT,"
                "ismultiplierl TEXT,"
                "ismultiplier2 TEXT,"
                "ismultiplier3 TEXT,"
                "points TEXT,"
                "radionr TEXT,"
                "run1run2 TEXT,"
                "RoverLocation TEXT,"
                "RadioInterfaced TEXT,"
                "NetworkedCompNr TEXT,"
                "IsOriginal TEXT,"
                "NetBiosName TEXT,"
                "IsRunQSO TEXT,"
                "StationName TEXT,"
                "ID TEXT UNIQUE,"
                "IsClaimedQso TEXT,"
                "dirty INTEGER DEFAULT 1);"
            )
            cursor.execute(sql_table)
            conn.commit()

    def log_contact(self, contact: dict) -> None:
        """
        Inserts a contact into the db.
        pass in a dict object, see get_empty() for keys
        """
        self.logger.info("%s", contact)

        pre = "INSERT INTO contactinfo("
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
                self.logger.info("%s", sql)
                cur = conn.cursor()
                cur.execute(sql, tuple(values))
                conn.commit()
        except sqlite3.Error as exception:
            self.logger.info("DataBase log_contact: %s", exception)

    def change_contact(self, qso: dict) -> None:
        """Update an existing contact."""

        pre = "UPDATE contactinfo set "
        for key in qso.keys():
            pre += f"{key} = '{qso[key]}',"
        sql = f"{pre[:-1]} where primarykey='{qso['primarykey']}';"

        try:
            with sqlite3.connect(self.database) as conn:
                self.logger.info("%s\n%s", sql, qso)
                cur = conn.cursor()
                cur.execute(sql)
                conn.commit()
        except sqlite3.Error as exception:
            self.logger.info("DataBase change_contact: %s", exception)

    def get_unique_id(self, contact) -> str:
        """get unique id"""
        unique_id = ""
        if contact:
            try:
                with sqlite3.connect(self.database) as conn:
                    sql = f"select ID from contactinfo where primarykey={int(contact)}"
                    cursor = conn.cursor()
                    cursor.execute(sql)
                    unique_id = str(cursor.fetchone()[0])
            except sqlite3.Error as exception:
                self.logger.debug("%s", exception)
        return unique_id

    def delete_contact(self, contact) -> None:
        """Deletes a contact from the db."""
        if contact:
            try:
                with sqlite3.connect(self.database) as conn:
                    sql = f"delete from contactinfo where primarykey={int(contact)};"
                    cur = conn.cursor()
                    cur.execute(sql)
                    conn.commit()
            except sqlite3.Error as exception:
                self.logger.info("DataBase delete_contact: %s", exception)

    def fetch_all_contacts_asc(self) -> list:
        """returns a list of dicts with contacts in the database."""
        with sqlite3.connect(self.database) as conn:
            conn.row_factory = self.row_factory
            cursor = conn.cursor()
            cursor.execute("select * from contactinfo order by timestamp ASC;")
            return cursor.fetchall()

    def fetch_all_contacts_desc(self) -> list:
        """returns a list of dicts with contacts in the database."""
        with sqlite3.connect(self.database) as conn:
            conn.row_factory = self.row_factory
            cursor = conn.cursor()
            cursor.execute("select * from contactinfo order by timestamp desc;")
            return cursor.fetchall()

    def fetch_last_contact(self) -> dict:
        """returns a list of dicts with last contact in the database."""
        with sqlite3.connect(self.database) as conn:
            conn.row_factory = self.row_factory
            cursor = conn.cursor()
            cursor.execute("select * from contactinfo order by timestamp desc;")
            return cursor.fetchone()

    def fetch_all_dirty_contacts(self) -> list:
        """
        Return a list of dict, containing all contacts still flagged as dirty.\n
        """
        with sqlite3.connect(self.database) as conn:
            conn.row_factory = self.row_factory
            cursor = conn.cursor()
            cursor.execute("select * from contactinfo where dirty=1 order by id")
            return cursor.fetchall()

    def get_empty(self) -> dict:
        """Return a dictionary object with keys and no values."""
        return self.empty_contact

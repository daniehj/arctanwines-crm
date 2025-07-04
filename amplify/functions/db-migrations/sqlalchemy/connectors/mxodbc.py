# connectors/mxodbc.py
# Copyright (C) 2005-2023 the SQLAlchemy authors and contributors
# <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: https://www.opensource.org/licenses/mit-license.php

"""
Provide a SQLALchemy connector for the eGenix mxODBC commercial
Python adapter for ODBC. This is not a free product, but eGenix
provides SQLAlchemy with a license for use in continuous integration
testing.

This has been tested for use with mxODBC 3.1.2 on SQL Server 2005
and 2008, using the SQL Server Native driver. However, it is
possible for this to be used on other database platforms.

For more info on mxODBC, see https://www.egenix.com/

.. deprecated:: 1.4 The mxODBC DBAPI is deprecated and will be removed
   in a future version. Please use one of the supported DBAPIs to
   connect to mssql.

"""

import re
import sys
import warnings

from . import Connector
from ..util import warn_deprecated


class MxODBCConnector(Connector):
    driver = "mxodbc"

    supports_sane_multi_rowcount = False
    supports_unicode_statements = True
    supports_unicode_binds = True

    supports_native_decimal = True

    @classmethod
    def dbapi(cls):
        # this classmethod will normally be replaced by an instance
        # attribute of the same name, so this is normally only called once.
        cls._load_mx_exceptions()
        platform = sys.platform
        if platform == "win32":
            from mx.ODBC import Windows as Module
        # this can be the string "linux2", and possibly others
        elif "linux" in platform:
            from mx.ODBC import unixODBC as Module
        elif platform == "darwin":
            from mx.ODBC import iODBC as Module
        else:
            raise ImportError("Unrecognized platform for mxODBC import")

        warn_deprecated(
            "The mxODBC DBAPI is deprecated and will be removed"
            "in a future version. Please use one of the supported DBAPIs to"
            "connect to mssql.",
            version="1.4",
        )
        return Module

    @classmethod
    def _load_mx_exceptions(cls):
        """Import mxODBC exception classes into the module namespace,
        as if they had been imported normally. This is done here
        to avoid requiring all SQLAlchemy users to install mxODBC.
        """
        global InterfaceError, ProgrammingError
        from mx.ODBC import InterfaceError
        from mx.ODBC import ProgrammingError

    def on_connect(self):
        def connect(conn):
            conn.stringformat = self.dbapi.MIXED_STRINGFORMAT
            conn.datetimeformat = self.dbapi.PYDATETIME_DATETIMEFORMAT
            conn.decimalformat = self.dbapi.DECIMAL_DECIMALFORMAT
            conn.errorhandler = self._error_handler()

        return connect

    def _error_handler(self):
        """Return a handler that adjusts mxODBC's raised Warnings to
        emit Python standard warnings.
        """
        from mx.ODBC.Error import Warning as MxOdbcWarning

        def error_handler(connection, cursor, errorclass, errorvalue):
            if issubclass(errorclass, MxOdbcWarning):
                errorclass.__bases__ = (Warning,)
                warnings.warn(
                    message=str(errorvalue), category=errorclass, stacklevel=2
                )
            else:
                raise errorclass(errorvalue)

        return error_handler

    def create_connect_args(self, url):
        r"""Return a tuple of \*args, \**kwargs for creating a connection.

        The mxODBC 3.x connection constructor looks like this:

            connect(dsn, user='', password='',
                    clear_auto_commit=1, errorhandler=None)

        This method translates the values in the provided URI
        into args and kwargs needed to instantiate an mxODBC Connection.

        The arg 'errorhandler' is not used by SQLAlchemy and will
        not be populated.

        """
        opts = url.translate_connect_args(username="user")
        opts.update(url.query)
        args = opts.pop("host")
        opts.pop("port", None)
        opts.pop("database", None)
        return (args,), opts

    def is_disconnect(self, e, connection, cursor):
        # TODO: eGenix recommends checking connection.closed here
        # Does that detect dropped connections ?
        if isinstance(e, self.dbapi.ProgrammingError):
            return "connection already closed" in str(e)
        elif isinstance(e, self.dbapi.Error):
            return "[08S01]" in str(e)
        else:
            return False

    def _get_server_version_info(self, connection):
        # eGenix suggests using conn.dbms_version instead
        # of what we're doing here
        dbapi_con = connection.connection
        version = []
        r = re.compile(r"[.\-]")
        # 18 == pyodbc.SQL_DBMS_VER
        for n in r.split(dbapi_con.getinfo(18)[1]):
            try:
                version.append(int(n))
            except ValueError:
                version.append(n)
        return tuple(version)

    def _get_direct(self, context):
        if context:
            native_odbc_execute = context.execution_options.get(
                "native_odbc_execute", "auto"
            )
            # default to direct=True in all cases, is more generally
            # compatible especially with SQL Server
            return False if native_odbc_execute is True else True
        else:
            return True

    def do_executemany(self, cursor, statement, parameters, context=None):
        cursor.executemany(statement, parameters, direct=self._get_direct(context))

    def do_execute(self, cursor, statement, parameters, context=None):
        cursor.execute(statement, parameters, direct=self._get_direct(context))

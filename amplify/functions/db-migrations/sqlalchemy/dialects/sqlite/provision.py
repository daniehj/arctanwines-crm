import os
import re

from ... import exc
from ...engine import url as sa_url
from ...testing.provision import create_db
from ...testing.provision import drop_db
from ...testing.provision import follower_url_from_main
from ...testing.provision import generate_driver_url
from ...testing.provision import log
from ...testing.provision import post_configure_engine
from ...testing.provision import run_reap_dbs
from ...testing.provision import stop_test_class_outside_fixtures
from ...testing.provision import temp_table_keyword_args


# TODO: I can't get this to build dynamically with pytest-xdist procs
_drivernames = {"pysqlite", "aiosqlite", "pysqlcipher"}


@generate_driver_url.for_db("sqlite")
def generate_driver_url(url, driver, query_str):
    if driver == "pysqlcipher" and url.get_driver_name() != "pysqlcipher":
        if url.database:
            url = url.set(database=url.database + ".enc")
        url = url.set(password="test")
    url = url.set(drivername="sqlite+%s" % (driver,))
    try:
        url.get_dialect()
    except exc.NoSuchModuleError:
        return None
    else:
        return url


@follower_url_from_main.for_db("sqlite")
def _sqlite_follower_url_from_main(url, ident):
    url = sa_url.make_url(url)

    if not url.database or url.database == ":memory:":
        return url
    else:
        m = re.match(r"(.+?)\.(.+)$", url.database)
        name, ext = m.group(1, 2)
        drivername = url.get_driver_name()
        return sa_url.make_url(
            "sqlite+%s:///%s_%s.%s" % (drivername, drivername, ident, ext)
        )


@post_configure_engine.for_db("sqlite")
def _sqlite_post_configure_engine(url, engine, follower_ident):
    from sqlalchemy import event

    @event.listens_for(engine, "connect")
    def connect(dbapi_connection, connection_record):
        # use file DBs in all cases, memory acts kind of strangely
        # as an attached
        if not follower_ident:
            # note this test_schema.db gets created for all test runs.
            # there's not any dedicated cleanup step for it.  it in some
            # ways corresponds to the "test.test_schema" schema that's
            # expected to be already present, so for now it just stays
            # in a given checkout directory.
            dbapi_connection.execute(
                'ATTACH DATABASE "%s_test_schema.db" AS test_schema' % (engine.driver,)
            )
        else:
            dbapi_connection.execute(
                'ATTACH DATABASE "%s_%s_test_schema.db" AS test_schema'
                % (follower_ident, engine.driver)
            )


@create_db.for_db("sqlite")
def _sqlite_create_db(cfg, eng, ident):
    pass


@drop_db.for_db("sqlite")
def _sqlite_drop_db(cfg, eng, ident):
    for path in [
        "%s.db" % ident,
        "%s_%s_test_schema.db" % (ident, eng.driver),
    ]:
        if os.path.exists(path):
            log.info("deleting SQLite database file: %s" % path)
            os.remove(path)


@stop_test_class_outside_fixtures.for_db("sqlite")
def stop_test_class_outside_fixtures(config, db, cls):
    with db.connect() as conn:
        files = [
            row.file for row in conn.exec_driver_sql("PRAGMA database_list") if row.file
        ]

    if files:
        db.dispose()
        # some sqlite file tests are not cleaning up well yet, so do this
        # just to make things simple for now
        for file_ in files:
            if file_ and os.path.exists(file_):
                os.remove(file_)


@temp_table_keyword_args.for_db("sqlite")
def _sqlite_temp_table_keyword_args(cfg, eng):
    return {"prefixes": ["TEMPORARY"]}


@run_reap_dbs.for_db("sqlite")
def _reap_sqlite_dbs(url, idents):
    log.info("db reaper connecting to %r", url)

    log.info("identifiers in file: %s", ", ".join(idents))
    for ident in idents:
        # we don't have a config so we can't call _sqlite_drop_db due to the
        # decorator
        for ext in ("db", "db.enc"):
            for path in (
                ["%s.%s" % (ident, ext)]
                + ["%s_%s.%s" % (drivername, ident, ext) for drivername in _drivernames]
                + [
                    "%s_test_schema.%s" % (drivername, ext)
                    for drivername in _drivernames
                ]
                + [
                    "%s_%s_test_schema.%s" % (ident, drivername, ext)
                    for drivername in _drivernames
                ]
            ):
                if os.path.exists(path):
                    log.info("deleting SQLite database file: %s" % path)
                    os.remove(path)

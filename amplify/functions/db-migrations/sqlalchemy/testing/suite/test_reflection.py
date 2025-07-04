import operator
import re

import sqlalchemy as sa
from .. import config
from .. import engines
from .. import eq_
from .. import expect_warnings
from .. import fixtures
from .. import is_
from ..provision import get_temp_table_name
from ..provision import temp_table_keyword_args
from ..schema import Column
from ..schema import Table
from ... import event
from ... import ForeignKey
from ... import func
from ... import Identity
from ... import inspect
from ... import Integer
from ... import MetaData
from ... import String
from ... import testing
from ... import types as sql_types
from ...schema import DDL
from ...schema import Index
from ...sql.elements import quoted_name
from ...sql.schema import BLANK_SCHEMA
from ...testing import is_false
from ...testing import is_true


metadata, users = None, None


class OneConnectionTablesTest(fixtures.TablesTest):
    @classmethod
    def setup_bind(cls):
        # TODO: when temp tables are subject to server reset,
        # this will also have to disable that server reset from
        # happening
        if config.requirements.independent_connections.enabled:
            from sqlalchemy import pool

            return engines.testing_engine(
                options=dict(poolclass=pool.StaticPool, scope="class"),
            )
        else:
            return config.db


class HasTableTest(OneConnectionTablesTest):
    __backend__ = True

    @classmethod
    def define_tables(cls, metadata):
        Table(
            "test_table",
            metadata,
            Column("id", Integer, primary_key=True),
            Column("data", String(50)),
        )
        if testing.requires.schemas.enabled:
            Table(
                "test_table_s",
                metadata,
                Column("id", Integer, primary_key=True),
                Column("data", String(50)),
                schema=config.test_schema,
            )

        if testing.requires.view_reflection:
            cls.define_views(metadata)
        if testing.requires.has_temp_table.enabled:
            cls.define_temp_tables(metadata)

    @classmethod
    def define_views(cls, metadata):
        query = "CREATE VIEW vv AS SELECT id, data FROM test_table"

        event.listen(metadata, "after_create", DDL(query))
        event.listen(metadata, "before_drop", DDL("DROP VIEW vv"))

        if testing.requires.schemas.enabled:
            query = "CREATE VIEW %s.vv AS SELECT id, data FROM %s.test_table_s" % (
                config.test_schema,
                config.test_schema,
            )
            event.listen(metadata, "after_create", DDL(query))
            event.listen(
                metadata,
                "before_drop",
                DDL("DROP VIEW %s.vv" % (config.test_schema)),
            )

    @classmethod
    def temp_table_name(cls):
        return get_temp_table_name(config, config.db, "user_tmp_%s" % (config.ident,))

    @classmethod
    def define_temp_tables(cls, metadata):
        kw = temp_table_keyword_args(config, config.db)
        table_name = cls.temp_table_name()
        user_tmp = Table(
            table_name,
            metadata,
            Column("id", sa.INT, primary_key=True),
            Column("name", sa.VARCHAR(50)),
            **kw
        )
        if (
            testing.requires.view_reflection.enabled
            and testing.requires.temporary_views.enabled
        ):
            event.listen(
                user_tmp,
                "after_create",
                DDL(
                    "create temporary view user_tmp_v as "
                    "select * from user_tmp_%s" % config.ident
                ),
            )
            event.listen(user_tmp, "before_drop", DDL("drop view user_tmp_v"))

    def test_has_table(self):
        with config.db.begin() as conn:
            is_true(config.db.dialect.has_table(conn, "test_table"))
            is_false(config.db.dialect.has_table(conn, "test_table_s"))
            is_false(config.db.dialect.has_table(conn, "nonexistent_table"))

    @testing.requires.schemas
    def test_has_table_schema(self):
        with config.db.begin() as conn:
            is_false(
                config.db.dialect.has_table(
                    conn, "test_table", schema=config.test_schema
                )
            )
            is_true(
                config.db.dialect.has_table(
                    conn, "test_table_s", schema=config.test_schema
                )
            )
            is_false(
                config.db.dialect.has_table(
                    conn, "nonexistent_table", schema=config.test_schema
                )
            )

    @testing.fails_on(
        "oracle",
        "per #8700 this remains at its previous behavior of not " "working within 1.4.",
    )
    @testing.requires.views
    def test_has_table_view(self, connection):
        insp = inspect(connection)
        is_true(insp.has_table("vv"))

    @testing.requires.has_temp_table
    def test_has_table_temp_table(self, connection):
        insp = inspect(connection)
        temp_table_name = self.temp_table_name()
        is_true(insp.has_table(temp_table_name))

    @testing.requires.has_temp_table
    @testing.requires.view_reflection
    @testing.requires.temporary_views
    def test_has_table_temp_view(self, connection):
        insp = inspect(connection)
        is_true(insp.has_table("user_tmp_v"))

    @testing.fails_on(
        "oracle",
        "per #8700 this remains at its previous behavior of not " "working within 1.4",
    )
    @testing.requires.views
    @testing.requires.schemas
    def test_has_table_view_schema(self, connection):
        insp = inspect(connection)
        is_true(insp.has_table("vv", config.test_schema))


class HasIndexTest(fixtures.TablesTest):
    __backend__ = True

    @classmethod
    def define_tables(cls, metadata):
        tt = Table(
            "test_table",
            metadata,
            Column("id", Integer, primary_key=True),
            Column("data", String(50)),
        )
        Index("my_idx", tt.c.data)

        if testing.requires.schemas.enabled:
            tt = Table(
                "test_table",
                metadata,
                Column("id", Integer, primary_key=True),
                Column("data", String(50)),
                schema=config.test_schema,
            )
            Index("my_idx_s", tt.c.data)

    def test_has_index(self):
        with config.db.begin() as conn:
            assert config.db.dialect.has_index(conn, "test_table", "my_idx")
            assert not config.db.dialect.has_index(conn, "test_table", "my_idx_s")
            assert not config.db.dialect.has_index(conn, "nonexistent_table", "my_idx")
            assert not config.db.dialect.has_index(
                conn, "test_table", "nonexistent_idx"
            )

    @testing.requires.schemas
    def test_has_index_schema(self):
        with config.db.begin() as conn:
            assert config.db.dialect.has_index(
                conn, "test_table", "my_idx_s", schema=config.test_schema
            )
            assert not config.db.dialect.has_index(
                conn, "test_table", "my_idx", schema=config.test_schema
            )
            assert not config.db.dialect.has_index(
                conn,
                "nonexistent_table",
                "my_idx_s",
                schema=config.test_schema,
            )
            assert not config.db.dialect.has_index(
                conn,
                "test_table",
                "nonexistent_idx_s",
                schema=config.test_schema,
            )


class QuotedNameArgumentTest(fixtures.TablesTest):
    run_create_tables = "once"
    __backend__ = True

    @classmethod
    def define_tables(cls, metadata):
        Table(
            "quote ' one",
            metadata,
            Column("id", Integer),
            Column("name", String(50)),
            Column("data", String(50)),
            Column("related_id", Integer),
            sa.PrimaryKeyConstraint("id", name="pk quote ' one"),
            sa.Index("ix quote ' one", "name"),
            sa.UniqueConstraint(
                "data",
                name="uq quote' one",
            ),
            sa.ForeignKeyConstraint(["id"], ["related.id"], name="fk quote ' one"),
            sa.CheckConstraint("name != 'foo'", name="ck quote ' one"),
            comment=r"""quote ' one comment""",
            test_needs_fk=True,
        )

        if testing.requires.symbol_names_w_double_quote.enabled:
            Table(
                'quote " two',
                metadata,
                Column("id", Integer),
                Column("name", String(50)),
                Column("data", String(50)),
                Column("related_id", Integer),
                sa.PrimaryKeyConstraint("id", name='pk quote " two'),
                sa.Index('ix quote " two', "name"),
                sa.UniqueConstraint(
                    "data",
                    name='uq quote" two',
                ),
                sa.ForeignKeyConstraint(["id"], ["related.id"], name='fk quote " two'),
                sa.CheckConstraint("name != 'foo'", name='ck quote " two '),
                comment=r"""quote " two comment""",
                test_needs_fk=True,
            )

        Table(
            "related",
            metadata,
            Column("id", Integer, primary_key=True),
            Column("related", Integer),
            test_needs_fk=True,
        )

        if testing.requires.view_column_reflection.enabled:
            if testing.requires.symbol_names_w_double_quote.enabled:
                names = [
                    "quote ' one",
                    'quote " two',
                ]
            else:
                names = [
                    "quote ' one",
                ]
            for name in names:
                query = "CREATE VIEW %s AS SELECT * FROM %s" % (
                    config.db.dialect.identifier_preparer.quote("view %s" % name),
                    config.db.dialect.identifier_preparer.quote(name),
                )

                event.listen(metadata, "after_create", DDL(query))
                event.listen(
                    metadata,
                    "before_drop",
                    DDL(
                        "DROP VIEW %s"
                        % config.db.dialect.identifier_preparer.quote("view %s" % name)
                    ),
                )

    def quote_fixtures(fn):
        return testing.combinations(
            ("quote ' one",),
            ('quote " two', testing.requires.symbol_names_w_double_quote),
        )(fn)

    @quote_fixtures
    def test_get_table_options(self, name):
        insp = inspect(config.db)

        insp.get_table_options(name)

    @quote_fixtures
    @testing.requires.view_column_reflection
    def test_get_view_definition(self, name):
        insp = inspect(config.db)
        assert insp.get_view_definition("view %s" % name)

    @quote_fixtures
    def test_get_columns(self, name):
        insp = inspect(config.db)
        assert insp.get_columns(name)

    @quote_fixtures
    def test_get_pk_constraint(self, name):
        insp = inspect(config.db)
        assert insp.get_pk_constraint(name)

    @quote_fixtures
    def test_get_foreign_keys(self, name):
        insp = inspect(config.db)
        assert insp.get_foreign_keys(name)

    @quote_fixtures
    def test_get_indexes(self, name):
        insp = inspect(config.db)
        assert insp.get_indexes(name)

    @quote_fixtures
    @testing.requires.unique_constraint_reflection
    def test_get_unique_constraints(self, name):
        insp = inspect(config.db)
        assert insp.get_unique_constraints(name)

    @quote_fixtures
    @testing.requires.comment_reflection
    def test_get_table_comment(self, name):
        insp = inspect(config.db)
        assert insp.get_table_comment(name)

    @quote_fixtures
    @testing.requires.check_constraint_reflection
    def test_get_check_constraints(self, name):
        insp = inspect(config.db)
        assert insp.get_check_constraints(name)


class ComponentReflectionTest(OneConnectionTablesTest):
    run_inserts = run_deletes = None

    __backend__ = True

    @classmethod
    def define_tables(cls, metadata):
        cls.define_reflected_tables(metadata, None)
        if testing.requires.schemas.enabled:
            cls.define_reflected_tables(metadata, testing.config.test_schema)

    @classmethod
    def define_reflected_tables(cls, metadata, schema):
        if schema:
            schema_prefix = schema + "."
        else:
            schema_prefix = ""

        if testing.requires.self_referential_foreign_keys.enabled:
            users = Table(
                "users",
                metadata,
                Column("user_id", sa.INT, primary_key=True),
                Column("test1", sa.CHAR(5), nullable=False),
                Column("test2", sa.Float(5), nullable=False),
                Column(
                    "parent_user_id",
                    sa.Integer,
                    sa.ForeignKey("%susers.user_id" % schema_prefix, name="user_id_fk"),
                ),
                schema=schema,
                test_needs_fk=True,
            )
        else:
            users = Table(
                "users",
                metadata,
                Column("user_id", sa.INT, primary_key=True),
                Column("test1", sa.CHAR(5), nullable=False),
                Column("test2", sa.Float(5), nullable=False),
                schema=schema,
                test_needs_fk=True,
            )

        Table(
            "dingalings",
            metadata,
            Column("dingaling_id", sa.Integer, primary_key=True),
            Column(
                "address_id",
                sa.Integer,
                sa.ForeignKey("%semail_addresses.address_id" % schema_prefix),
            ),
            Column("data", sa.String(30)),
            schema=schema,
            test_needs_fk=True,
        )
        Table(
            "email_addresses",
            metadata,
            Column("address_id", sa.Integer),
            Column("remote_user_id", sa.Integer, sa.ForeignKey(users.c.user_id)),
            Column("email_address", sa.String(20)),
            sa.PrimaryKeyConstraint("address_id", name="email_ad_pk"),
            schema=schema,
            test_needs_fk=True,
        )
        Table(
            "comment_test",
            metadata,
            Column("id", sa.Integer, primary_key=True, comment="id comment"),
            Column("data", sa.String(20), comment="data % comment"),
            Column(
                "d2",
                sa.String(20),
                comment=r"""Comment types type speedily ' " \ '' Fun!""",
            ),
            schema=schema,
            comment=r"""the test % ' " \ table comment""",
        )

        if testing.requires.cross_schema_fk_reflection.enabled:
            if schema is None:
                Table(
                    "local_table",
                    metadata,
                    Column("id", sa.Integer, primary_key=True),
                    Column("data", sa.String(20)),
                    Column(
                        "remote_id",
                        ForeignKey("%s.remote_table_2.id" % testing.config.test_schema),
                    ),
                    test_needs_fk=True,
                    schema=config.db.dialect.default_schema_name,
                )
            else:
                Table(
                    "remote_table",
                    metadata,
                    Column("id", sa.Integer, primary_key=True),
                    Column(
                        "local_id",
                        ForeignKey(
                            "%s.local_table.id" % config.db.dialect.default_schema_name
                        ),
                    ),
                    Column("data", sa.String(20)),
                    schema=schema,
                    test_needs_fk=True,
                )
                Table(
                    "remote_table_2",
                    metadata,
                    Column("id", sa.Integer, primary_key=True),
                    Column("data", sa.String(20)),
                    schema=schema,
                    test_needs_fk=True,
                )

        if testing.requires.index_reflection.enabled:
            cls.define_index(metadata, users)

            if not schema:
                # test_needs_fk is at the moment to force MySQL InnoDB
                noncol_idx_test_nopk = Table(
                    "noncol_idx_test_nopk",
                    metadata,
                    Column("q", sa.String(5)),
                    test_needs_fk=True,
                )

                noncol_idx_test_pk = Table(
                    "noncol_idx_test_pk",
                    metadata,
                    Column("id", sa.Integer, primary_key=True),
                    Column("q", sa.String(5)),
                    test_needs_fk=True,
                )

                if testing.requires.indexes_with_ascdesc.enabled:
                    Index("noncol_idx_nopk", noncol_idx_test_nopk.c.q.desc())
                    Index("noncol_idx_pk", noncol_idx_test_pk.c.q.desc())

        if testing.requires.view_column_reflection.enabled:
            cls.define_views(metadata, schema)
        if not schema and testing.requires.temp_table_reflection.enabled:
            cls.define_temp_tables(metadata)

    @classmethod
    def define_temp_tables(cls, metadata):
        kw = temp_table_keyword_args(config, config.db)
        table_name = get_temp_table_name(
            config, config.db, "user_tmp_%s" % config.ident
        )
        user_tmp = Table(
            table_name,
            metadata,
            Column("id", sa.INT, primary_key=True),
            Column("name", sa.VARCHAR(50)),
            Column("foo", sa.INT),
            # disambiguate temp table unique constraint names.  this is
            # pretty arbitrary for a generic dialect however we are doing
            # it to suit SQL Server which will produce name conflicts for
            # unique constraints created against temp tables in different
            # databases.
            # https://www.arbinada.com/en/node/1645
            sa.UniqueConstraint("name", name="user_tmp_uq_%s" % config.ident),
            sa.Index("user_tmp_ix", "foo"),
            **kw
        )
        if (
            testing.requires.view_reflection.enabled
            and testing.requires.temporary_views.enabled
        ):
            event.listen(
                user_tmp,
                "after_create",
                DDL(
                    "create temporary view user_tmp_v as "
                    "select * from user_tmp_%s" % config.ident
                ),
            )
            event.listen(user_tmp, "before_drop", DDL("drop view user_tmp_v"))

    @classmethod
    def define_index(cls, metadata, users):
        Index("users_t_idx", users.c.test1, users.c.test2)
        Index("users_all_idx", users.c.user_id, users.c.test2, users.c.test1)

    @classmethod
    def define_views(cls, metadata, schema):
        for table_name in ("users", "email_addresses"):
            fullname = table_name
            if schema:
                fullname = "%s.%s" % (schema, table_name)
            view_name = fullname + "_v"
            query = "CREATE VIEW %s AS SELECT * FROM %s" % (
                view_name,
                fullname,
            )

            event.listen(metadata, "after_create", DDL(query))
            event.listen(metadata, "before_drop", DDL("DROP VIEW %s" % view_name))

    @testing.requires.schema_reflection
    def test_get_schema_names(self):
        insp = inspect(self.bind)

        self.assert_(testing.config.test_schema in insp.get_schema_names())

    @testing.requires.schema_reflection
    def test_get_schema_names_w_translate_map(self, connection):
        """test #7300"""

        connection = connection.execution_options(
            schema_translate_map={
                "foo": "bar",
                BLANK_SCHEMA: testing.config.test_schema,
            }
        )
        insp = inspect(connection)

        self.assert_(testing.config.test_schema in insp.get_schema_names())

    @testing.requires.schema_reflection
    def test_dialect_initialize(self):
        engine = engines.testing_engine()
        inspect(engine)
        assert hasattr(engine.dialect, "default_schema_name")

    @testing.requires.schema_reflection
    def test_get_default_schema_name(self):
        insp = inspect(self.bind)
        eq_(insp.default_schema_name, self.bind.dialect.default_schema_name)

    @testing.requires.foreign_key_constraint_reflection
    @testing.combinations(
        (None, True, False, False),
        (None, True, False, True, testing.requires.schemas),
        ("foreign_key", True, False, False),
        (None, False, True, False),
        (None, False, True, True, testing.requires.schemas),
        (None, True, True, False),
        (None, True, True, True, testing.requires.schemas),
        argnames="order_by,include_plain,include_views,use_schema",
    )
    def test_get_table_names(
        self, connection, order_by, include_plain, include_views, use_schema
    ):
        if use_schema:
            schema = config.test_schema
        else:
            schema = None

        _ignore_tables = [
            "comment_test",
            "noncol_idx_test_pk",
            "noncol_idx_test_nopk",
            "local_table",
            "remote_table",
            "remote_table_2",
        ]

        insp = inspect(connection)

        if include_views:
            table_names = insp.get_view_names(schema)
            table_names.sort()
            answer = ["email_addresses_v", "users_v"]
            eq_(sorted(table_names), answer)

        if include_plain:
            if order_by:
                tables = [
                    rec[0]
                    for rec in insp.get_sorted_table_and_fkc_names(schema)
                    if rec[0]
                ]
            else:
                tables = insp.get_table_names(schema)
            table_names = [t for t in tables if t not in _ignore_tables]

            if order_by == "foreign_key":
                answer = ["users", "email_addresses", "dingalings"]
                eq_(table_names, answer)
            else:
                answer = ["dingalings", "email_addresses", "users"]
                eq_(sorted(table_names), answer)

    @testing.requires.temp_table_names
    def test_get_temp_table_names(self):
        insp = inspect(self.bind)
        temp_table_names = insp.get_temp_table_names()
        eq_(sorted(temp_table_names), ["user_tmp_%s" % config.ident])

    @testing.requires.view_reflection
    @testing.requires.temp_table_names
    @testing.requires.temporary_views
    def test_get_temp_view_names(self):
        insp = inspect(self.bind)
        temp_table_names = insp.get_temp_view_names()
        eq_(sorted(temp_table_names), ["user_tmp_v"])

    @testing.requires.comment_reflection
    def test_get_comments(self):
        self._test_get_comments()

    @testing.requires.comment_reflection
    @testing.requires.schemas
    def test_get_comments_with_schema(self):
        self._test_get_comments(testing.config.test_schema)

    def _test_get_comments(self, schema=None):
        insp = inspect(self.bind)

        eq_(
            insp.get_table_comment("comment_test", schema=schema),
            {"text": r"""the test % ' " \ table comment"""},
        )

        eq_(insp.get_table_comment("users", schema=schema), {"text": None})

        eq_(
            [
                {"name": rec["name"], "comment": rec["comment"]}
                for rec in insp.get_columns("comment_test", schema=schema)
            ],
            [
                {"comment": "id comment", "name": "id"},
                {"comment": "data % comment", "name": "data"},
                {
                    "comment": (r"""Comment types type speedily ' " \ '' Fun!"""),
                    "name": "d2",
                },
            ],
        )

    @testing.combinations(
        (False, False),
        (False, True, testing.requires.schemas),
        (True, False, testing.requires.view_reflection),
        (
            True,
            True,
            testing.requires.schemas + testing.requires.view_reflection,
        ),
        argnames="use_views,use_schema",
    )
    def test_get_columns(self, connection, use_views, use_schema):
        if use_schema:
            schema = config.test_schema
        else:
            schema = None

        users, addresses = (self.tables.users, self.tables.email_addresses)
        if use_views:
            table_names = ["users_v", "email_addresses_v"]
        else:
            table_names = ["users", "email_addresses"]

        insp = inspect(connection)
        for table_name, table in zip(table_names, (users, addresses)):
            schema_name = schema
            cols = insp.get_columns(table_name, schema=schema_name)
            self.assert_(len(cols) > 0, len(cols))

            # should be in order

            for i, col in enumerate(table.columns):
                eq_(col.name, cols[i]["name"])
                ctype = cols[i]["type"].__class__
                ctype_def = col.type
                if isinstance(ctype_def, sa.types.TypeEngine):
                    ctype_def = ctype_def.__class__

                # Oracle returns Date for DateTime.

                if testing.against("oracle") and ctype_def in (
                    sql_types.Date,
                    sql_types.DateTime,
                ):
                    ctype_def = sql_types.Date

                # assert that the desired type and return type share
                # a base within one of the generic types.

                self.assert_(
                    len(
                        set(ctype.__mro__)
                        .intersection(ctype_def.__mro__)
                        .intersection(
                            [
                                sql_types.Integer,
                                sql_types.Numeric,
                                sql_types.DateTime,
                                sql_types.Date,
                                sql_types.Time,
                                sql_types.String,
                                sql_types._Binary,
                            ]
                        )
                    )
                    > 0,
                    "%s(%s), %s(%s)" % (col.name, col.type, cols[i]["name"], ctype),
                )

                if not col.primary_key:
                    assert cols[i]["default"] is None

    @testing.requires.temp_table_reflection
    def test_get_temp_table_columns(self):
        table_name = get_temp_table_name(
            config, self.bind, "user_tmp_%s" % config.ident
        )
        user_tmp = self.tables[table_name]
        insp = inspect(self.bind)
        cols = insp.get_columns(table_name)
        self.assert_(len(cols) > 0, len(cols))

        for i, col in enumerate(user_tmp.columns):
            eq_(col.name, cols[i]["name"])

    @testing.requires.temp_table_reflection
    @testing.requires.view_column_reflection
    @testing.requires.temporary_views
    def test_get_temp_view_columns(self):
        insp = inspect(self.bind)
        cols = insp.get_columns("user_tmp_v")
        eq_([col["name"] for col in cols], ["id", "name", "foo"])

    @testing.combinations(
        (False,), (True, testing.requires.schemas), argnames="use_schema"
    )
    @testing.requires.primary_key_constraint_reflection
    def test_get_pk_constraint(self, connection, use_schema):
        if use_schema:
            schema = testing.config.test_schema
        else:
            schema = None

        users, addresses = self.tables.users, self.tables.email_addresses
        insp = inspect(connection)

        users_cons = insp.get_pk_constraint(users.name, schema=schema)
        users_pkeys = users_cons["constrained_columns"]
        eq_(users_pkeys, ["user_id"])

        addr_cons = insp.get_pk_constraint(addresses.name, schema=schema)
        addr_pkeys = addr_cons["constrained_columns"]
        eq_(addr_pkeys, ["address_id"])

        with testing.requires.reflects_pk_names.fail_if():
            eq_(addr_cons["name"], "email_ad_pk")

    @testing.combinations(
        (False,), (True, testing.requires.schemas), argnames="use_schema"
    )
    @testing.requires.foreign_key_constraint_reflection
    def test_get_foreign_keys(self, connection, use_schema):
        if use_schema:
            schema = config.test_schema
        else:
            schema = None

        users, addresses = (self.tables.users, self.tables.email_addresses)
        insp = inspect(connection)
        expected_schema = schema
        # users

        if testing.requires.self_referential_foreign_keys.enabled:
            users_fkeys = insp.get_foreign_keys(users.name, schema=schema)
            fkey1 = users_fkeys[0]

            with testing.requires.named_constraints.fail_if():
                eq_(fkey1["name"], "user_id_fk")

            eq_(fkey1["referred_schema"], expected_schema)
            eq_(fkey1["referred_table"], users.name)
            eq_(fkey1["referred_columns"], ["user_id"])
            if testing.requires.self_referential_foreign_keys.enabled:
                eq_(fkey1["constrained_columns"], ["parent_user_id"])

        # addresses
        addr_fkeys = insp.get_foreign_keys(addresses.name, schema=schema)
        fkey1 = addr_fkeys[0]

        with testing.requires.implicitly_named_constraints.fail_if():
            self.assert_(fkey1["name"] is not None)

        eq_(fkey1["referred_schema"], expected_schema)
        eq_(fkey1["referred_table"], users.name)
        eq_(fkey1["referred_columns"], ["user_id"])
        eq_(fkey1["constrained_columns"], ["remote_user_id"])

    @testing.requires.cross_schema_fk_reflection
    @testing.requires.schemas
    def test_get_inter_schema_foreign_keys(self):
        local_table, remote_table, remote_table_2 = self.tables(
            "%s.local_table" % self.bind.dialect.default_schema_name,
            "%s.remote_table" % testing.config.test_schema,
            "%s.remote_table_2" % testing.config.test_schema,
        )

        insp = inspect(self.bind)

        local_fkeys = insp.get_foreign_keys(local_table.name)
        eq_(len(local_fkeys), 1)

        fkey1 = local_fkeys[0]
        eq_(fkey1["referred_schema"], testing.config.test_schema)
        eq_(fkey1["referred_table"], remote_table_2.name)
        eq_(fkey1["referred_columns"], ["id"])
        eq_(fkey1["constrained_columns"], ["remote_id"])

        remote_fkeys = insp.get_foreign_keys(
            remote_table.name, schema=testing.config.test_schema
        )
        eq_(len(remote_fkeys), 1)

        fkey2 = remote_fkeys[0]

        assert fkey2["referred_schema"] in (
            None,
            self.bind.dialect.default_schema_name,
        )
        eq_(fkey2["referred_table"], local_table.name)
        eq_(fkey2["referred_columns"], ["id"])
        eq_(fkey2["constrained_columns"], ["local_id"])

    def _assert_insp_indexes(self, indexes, expected_indexes):
        index_names = [d["name"] for d in indexes]
        for e_index in expected_indexes:
            assert e_index["name"] in index_names
            index = indexes[index_names.index(e_index["name"])]
            for key in e_index:
                eq_(e_index[key], index[key])

    @testing.combinations(
        (False,), (True, testing.requires.schemas), argnames="use_schema"
    )
    def test_get_indexes(self, connection, use_schema):
        if use_schema:
            schema = config.test_schema
        else:
            schema = None

        # The database may decide to create indexes for foreign keys, etc.
        # so there may be more indexes than expected.
        insp = inspect(self.bind)
        indexes = insp.get_indexes("users", schema=schema)
        expected_indexes = [
            {
                "unique": False,
                "column_names": ["test1", "test2"],
                "name": "users_t_idx",
            },
            {
                "unique": False,
                "column_names": ["user_id", "test2", "test1"],
                "name": "users_all_idx",
            },
        ]
        self._assert_insp_indexes(indexes, expected_indexes)

    @testing.combinations(
        ("noncol_idx_test_nopk", "noncol_idx_nopk"),
        ("noncol_idx_test_pk", "noncol_idx_pk"),
        argnames="tname,ixname",
    )
    @testing.requires.index_reflection
    @testing.requires.indexes_with_ascdesc
    def test_get_noncol_index(self, connection, tname, ixname):
        insp = inspect(connection)
        indexes = insp.get_indexes(tname)

        # reflecting an index that has "x DESC" in it as the column.
        # the DB may or may not give us "x", but make sure we get the index
        # back, it has a name, it's connected to the table.
        expected_indexes = [{"unique": False, "name": ixname}]
        self._assert_insp_indexes(indexes, expected_indexes)

        t = Table(tname, MetaData(), autoload_with=connection)
        eq_(len(t.indexes), 1)
        is_(list(t.indexes)[0].table, t)
        eq_(list(t.indexes)[0].name, ixname)

    @testing.requires.temp_table_reflection
    @testing.requires.unique_constraint_reflection
    def test_get_temp_table_unique_constraints(self):
        insp = inspect(self.bind)
        reflected = insp.get_unique_constraints("user_tmp_%s" % config.ident)
        for refl in reflected:
            # Different dialects handle duplicate index and constraints
            # differently, so ignore this flag
            refl.pop("duplicates_index", None)
        eq_(
            reflected,
            [
                {
                    "column_names": ["name"],
                    "name": "user_tmp_uq_%s" % config.ident,
                }
            ],
        )

    @testing.requires.temp_table_reflect_indexes
    def test_get_temp_table_indexes(self):
        insp = inspect(self.bind)
        table_name = get_temp_table_name(
            config, config.db, "user_tmp_%s" % config.ident
        )
        indexes = insp.get_indexes(table_name)
        for ind in indexes:
            ind.pop("dialect_options", None)
        expected = [{"unique": False, "column_names": ["foo"], "name": "user_tmp_ix"}]
        if testing.requires.index_reflects_included_columns.enabled:
            expected[0]["include_columns"] = []
        eq_(
            [idx for idx in indexes if idx["name"] == "user_tmp_ix"],
            expected,
        )

    @testing.combinations(
        (True, testing.requires.schemas), (False,), argnames="use_schema"
    )
    @testing.requires.unique_constraint_reflection
    def test_get_unique_constraints(self, metadata, connection, use_schema):
        # SQLite dialect needs to parse the names of the constraints
        # separately from what it gets from PRAGMA index_list(), and
        # then matches them up.  so same set of column_names in two
        # constraints will confuse it.    Perhaps we should no longer
        # bother with index_list() here since we have the whole
        # CREATE TABLE?

        if use_schema:
            schema = config.test_schema
        else:
            schema = None
        uniques = sorted(
            [
                {"name": "unique_a", "column_names": ["a"]},
                {"name": "unique_a_b_c", "column_names": ["a", "b", "c"]},
                {"name": "unique_c_a_b", "column_names": ["c", "a", "b"]},
                {"name": "unique_asc_key", "column_names": ["asc", "key"]},
                {"name": "i.have.dots", "column_names": ["b"]},
                {"name": "i have spaces", "column_names": ["c"]},
            ],
            key=operator.itemgetter("name"),
        )
        table = Table(
            "testtbl",
            metadata,
            Column("a", sa.String(20)),
            Column("b", sa.String(30)),
            Column("c", sa.Integer),
            # reserved identifiers
            Column("asc", sa.String(30)),
            Column("key", sa.String(30)),
            schema=schema,
        )
        for uc in uniques:
            table.append_constraint(
                sa.UniqueConstraint(*uc["column_names"], name=uc["name"])
            )
        table.create(connection)

        inspector = inspect(connection)
        reflected = sorted(
            inspector.get_unique_constraints("testtbl", schema=schema),
            key=operator.itemgetter("name"),
        )

        names_that_duplicate_index = set()

        eq_(len(uniques), len(reflected))

        for orig, refl in zip(uniques, reflected):
            # Different dialects handle duplicate index and constraints
            # differently, so ignore this flag
            dupe = refl.pop("duplicates_index", None)
            if dupe:
                names_that_duplicate_index.add(dupe)
            eq_(orig, refl)

        reflected_metadata = MetaData()
        reflected = Table(
            "testtbl",
            reflected_metadata,
            autoload_with=connection,
            schema=schema,
        )

        # test "deduplicates for index" logic.   MySQL and Oracle
        # "unique constraints" are actually unique indexes (with possible
        # exception of a unique that is a dupe of another one in the case
        # of Oracle).  make sure # they aren't duplicated.
        idx_names = set([idx.name for idx in reflected.indexes])
        uq_names = set(
            [
                uq.name
                for uq in reflected.constraints
                if isinstance(uq, sa.UniqueConstraint)
            ]
        ).difference(["unique_c_a_b"])

        assert not idx_names.intersection(uq_names)
        if names_that_duplicate_index:
            eq_(names_that_duplicate_index, idx_names)
            eq_(uq_names, set())

    @testing.requires.view_reflection
    @testing.combinations(
        (False,), (True, testing.requires.schemas), argnames="use_schema"
    )
    def test_get_view_definition(self, connection, use_schema):
        if use_schema:
            schema = config.test_schema
        else:
            schema = None
        view_name1 = "users_v"
        view_name2 = "email_addresses_v"
        insp = inspect(connection)
        v1 = insp.get_view_definition(view_name1, schema=schema)
        self.assert_(v1)
        v2 = insp.get_view_definition(view_name2, schema=schema)
        self.assert_(v2)

    # why is this here if it's PG specific ?
    @testing.combinations(
        ("users", False),
        ("users", True, testing.requires.schemas),
        argnames="table_name,use_schema",
    )
    @testing.only_on("postgresql", "PG specific feature")
    def test_get_table_oid(self, connection, table_name, use_schema):
        if use_schema:
            schema = config.test_schema
        else:
            schema = None
        insp = inspect(connection)
        oid = insp.get_table_oid(table_name, schema)
        self.assert_(isinstance(oid, int))

    @testing.requires.table_reflection
    def test_autoincrement_col(self):
        """test that 'autoincrement' is reflected according to sqla's policy.

        Don't mark this test as unsupported for any backend !

        (technically it fails with MySQL InnoDB since "id" comes before "id2")

        A backend is better off not returning "autoincrement" at all,
        instead of potentially returning "False" for an auto-incrementing
        primary key column.

        """

        insp = inspect(self.bind)

        for tname, cname in [
            ("users", "user_id"),
            ("email_addresses", "address_id"),
            ("dingalings", "dingaling_id"),
        ]:
            cols = insp.get_columns(tname)
            id_ = {c["name"]: c for c in cols}[cname]
            assert id_.get("autoincrement", True)


class TableNoColumnsTest(fixtures.TestBase):
    __requires__ = ("reflect_tables_no_columns",)
    __backend__ = True

    @testing.fixture
    def table_no_columns(self, connection, metadata):
        Table("empty", metadata)
        metadata.create_all(connection)

    @testing.fixture
    def view_no_columns(self, connection, metadata):
        Table("empty", metadata)
        metadata.create_all(connection)

        Table("empty", metadata)
        event.listen(
            metadata,
            "after_create",
            DDL("CREATE VIEW empty_v AS SELECT * FROM empty"),
        )

        # for transactional DDL the transaction is rolled back before this
        # drop statement is invoked
        event.listen(metadata, "before_drop", DDL("DROP VIEW IF EXISTS empty_v"))
        metadata.create_all(connection)

    @testing.requires.reflect_tables_no_columns
    def test_reflect_table_no_columns(self, connection, table_no_columns):
        t2 = Table("empty", MetaData(), autoload_with=connection)
        eq_(list(t2.c), [])

    @testing.requires.reflect_tables_no_columns
    def test_get_columns_table_no_columns(self, connection, table_no_columns):
        eq_(inspect(connection).get_columns("empty"), [])

    @testing.requires.reflect_tables_no_columns
    def test_reflect_incl_table_no_columns(self, connection, table_no_columns):
        m = MetaData()
        m.reflect(connection)
        assert set(m.tables).intersection(["empty"])

    @testing.requires.views
    @testing.requires.reflect_tables_no_columns
    def test_reflect_view_no_columns(self, connection, view_no_columns):
        t2 = Table("empty_v", MetaData(), autoload_with=connection)
        eq_(list(t2.c), [])

    @testing.requires.views
    @testing.requires.reflect_tables_no_columns
    def test_get_columns_view_no_columns(self, connection, view_no_columns):
        eq_(inspect(connection).get_columns("empty_v"), [])


class ComponentReflectionTestExtra(fixtures.TestBase):
    __backend__ = True

    @testing.combinations(
        (True, testing.requires.schemas), (False,), argnames="use_schema"
    )
    @testing.requires.check_constraint_reflection
    def test_get_check_constraints(self, metadata, connection, use_schema):
        if use_schema:
            schema = config.test_schema
        else:
            schema = None

        Table(
            "sa_cc",
            metadata,
            Column("a", Integer()),
            sa.CheckConstraint("a > 1 AND a < 5", name="cc1"),
            sa.CheckConstraint("a = 1 OR (a > 2 AND a < 5)", name="UsesCasing"),
            schema=schema,
        )

        metadata.create_all(connection)

        inspector = inspect(connection)
        reflected = sorted(
            inspector.get_check_constraints("sa_cc", schema=schema),
            key=operator.itemgetter("name"),
        )

        # trying to minimize effect of quoting, parenthesis, etc.
        # may need to add more to this as new dialects get CHECK
        # constraint reflection support
        def normalize(sqltext):
            return " ".join(re.findall(r"and|\d|=|a|or|<|>", sqltext.lower(), re.I))

        reflected = [
            {"name": item["name"], "sqltext": normalize(item["sqltext"])}
            for item in reflected
        ]
        eq_(
            reflected,
            [
                {"name": "UsesCasing", "sqltext": "a = 1 or a > 2 and a < 5"},
                {"name": "cc1", "sqltext": "a > 1 and a < 5"},
            ],
        )

    @testing.requires.indexes_with_expressions
    def test_reflect_expression_based_indexes(self, metadata, connection):
        t = Table(
            "t",
            metadata,
            Column("x", String(30)),
            Column("y", String(30)),
        )

        Index("t_idx", func.lower(t.c.x), func.lower(t.c.y))

        Index("t_idx_2", t.c.x)

        metadata.create_all(connection)

        insp = inspect(connection)

        expected = [
            {
                "name": "t_idx_2",
                "column_names": ["x"],
                "unique": False,
                "dialect_options": {},
            }
        ]

        if testing.requires.index_reflects_included_columns.enabled:
            expected[0]["include_columns"] = []
            expected[0]["dialect_options"] = {"%s_include" % connection.engine.name: []}

        with expect_warnings(
            "Skipped unsupported reflection of expression-based index t_idx"
        ):
            eq_(insp.get_indexes("t"), expected)

    @testing.requires.index_reflects_included_columns
    def test_reflect_covering_index(self, metadata, connection):
        t = Table(
            "t",
            metadata,
            Column("x", String(30)),
            Column("y", String(30)),
        )
        idx = Index("t_idx", t.c.x)
        idx.dialect_options[connection.engine.name]["include"] = ["y"]

        metadata.create_all(connection)

        insp = inspect(connection)

        eq_(
            insp.get_indexes("t"),
            [
                {
                    "name": "t_idx",
                    "column_names": ["x"],
                    "include_columns": ["y"],
                    "unique": False,
                    "dialect_options": {"%s_include" % connection.engine.name: ["y"]},
                }
            ],
        )

        t2 = Table("t", MetaData(), autoload_with=connection)
        eq_(
            list(t2.indexes)[0].dialect_options[connection.engine.name]["include"],
            ["y"],
        )

    def _type_round_trip(self, connection, metadata, *types):
        t = Table(
            "t", metadata, *[Column("t%d" % i, type_) for i, type_ in enumerate(types)]
        )
        t.create(connection)

        return [c["type"] for c in inspect(connection).get_columns("t")]

    @testing.requires.table_reflection
    def test_numeric_reflection(self, connection, metadata):
        for typ in self._type_round_trip(
            connection, metadata, sql_types.Numeric(18, 5)
        ):
            assert isinstance(typ, sql_types.Numeric)
            eq_(typ.precision, 18)
            eq_(typ.scale, 5)

    @testing.requires.table_reflection
    def test_varchar_reflection(self, connection, metadata):
        typ = self._type_round_trip(connection, metadata, sql_types.String(52))[0]
        assert isinstance(typ, sql_types.String)
        eq_(typ.length, 52)

    @testing.requires.table_reflection
    def test_nullable_reflection(self, connection, metadata):
        t = Table(
            "t",
            metadata,
            Column("a", Integer, nullable=True),
            Column("b", Integer, nullable=False),
        )
        t.create(connection)
        eq_(
            dict(
                (col["name"], col["nullable"])
                for col in inspect(connection).get_columns("t")
            ),
            {"a": True, "b": False},
        )

    @testing.combinations(
        (
            None,
            "CASCADE",
            None,
            testing.requires.foreign_key_constraint_option_reflection_ondelete,
        ),
        (
            None,
            None,
            "SET NULL",
            testing.requires.foreign_key_constraint_option_reflection_onupdate,
        ),
        (
            {},
            None,
            "NO ACTION",
            testing.requires.foreign_key_constraint_option_reflection_onupdate,
        ),
        (
            {},
            "NO ACTION",
            None,
            testing.requires.fk_constraint_option_reflection_ondelete_noaction,
        ),
        (
            None,
            None,
            "RESTRICT",
            testing.requires.fk_constraint_option_reflection_onupdate_restrict,
        ),
        (
            None,
            "RESTRICT",
            None,
            testing.requires.fk_constraint_option_reflection_ondelete_restrict,
        ),
        argnames="expected,ondelete,onupdate",
    )
    def test_get_foreign_key_options(
        self, connection, metadata, expected, ondelete, onupdate
    ):
        options = {}
        if ondelete:
            options["ondelete"] = ondelete
        if onupdate:
            options["onupdate"] = onupdate

        if expected is None:
            expected = options

        Table(
            "x",
            metadata,
            Column("id", Integer, primary_key=True),
            test_needs_fk=True,
        )

        Table(
            "table",
            metadata,
            Column("id", Integer, primary_key=True),
            Column("x_id", Integer, sa.ForeignKey("x.id", name="xid")),
            Column("test", String(10)),
            test_needs_fk=True,
        )

        Table(
            "user",
            metadata,
            Column("id", Integer, primary_key=True),
            Column("name", String(50), nullable=False),
            Column("tid", Integer),
            sa.ForeignKeyConstraint(["tid"], ["table.id"], name="myfk", **options),
            test_needs_fk=True,
        )

        metadata.create_all(connection)

        insp = inspect(connection)

        # test 'options' is always present for a backend
        # that can reflect these, since alembic looks for this
        opts = insp.get_foreign_keys("table")[0]["options"]

        eq_(dict((k, opts[k]) for k in opts if opts[k]), {})

        opts = insp.get_foreign_keys("user")[0]["options"]
        eq_(opts, expected)
        # eq_(dict((k, opts[k]) for k in opts if opts[k]), expected)


class NormalizedNameTest(fixtures.TablesTest):
    __requires__ = ("denormalized_names",)
    __backend__ = True

    @classmethod
    def define_tables(cls, metadata):
        Table(
            quoted_name("t1", quote=True),
            metadata,
            Column("id", Integer, primary_key=True),
        )
        Table(
            quoted_name("t2", quote=True),
            metadata,
            Column("id", Integer, primary_key=True),
            Column("t1id", ForeignKey("t1.id")),
        )

    def test_reflect_lowercase_forced_tables(self):
        m2 = MetaData()
        t2_ref = Table(quoted_name("t2", quote=True), m2, autoload_with=config.db)
        t1_ref = m2.tables["t1"]
        assert t2_ref.c.t1id.references(t1_ref.c.id)

        m3 = MetaData()
        m3.reflect(config.db, only=lambda name, m: name.lower() in ("t1", "t2"))
        assert m3.tables["t2"].c.t1id.references(m3.tables["t1"].c.id)

    def test_get_table_names(self):
        tablenames = [
            t for t in inspect(config.db).get_table_names() if t.lower() in ("t1", "t2")
        ]

        eq_(tablenames[0].upper(), tablenames[0].lower())
        eq_(tablenames[1].upper(), tablenames[1].lower())


class ComputedReflectionTest(fixtures.ComputedReflectionFixtureTest):
    def test_computed_col_default_not_set(self):
        insp = inspect(config.db)

        cols = insp.get_columns("computed_default_table")
        col_data = {c["name"]: c for c in cols}
        is_true("42" in col_data["with_default"]["default"])
        is_(col_data["normal"]["default"], None)
        is_(col_data["computed_col"]["default"], None)

    def test_get_column_returns_computed(self):
        insp = inspect(config.db)

        cols = insp.get_columns("computed_default_table")
        data = {c["name"]: c for c in cols}
        for key in ("id", "normal", "with_default"):
            is_true("computed" not in data[key])
        compData = data["computed_col"]
        is_true("computed" in compData)
        is_true("sqltext" in compData["computed"])
        eq_(self.normalize(compData["computed"]["sqltext"]), "normal+42")
        eq_(
            "persisted" in compData["computed"],
            testing.requires.computed_columns_reflect_persisted.enabled,
        )
        if testing.requires.computed_columns_reflect_persisted.enabled:
            eq_(
                compData["computed"]["persisted"],
                testing.requires.computed_columns_default_persisted.enabled,
            )

    def check_column(self, data, column, sqltext, persisted):
        is_true("computed" in data[column])
        compData = data[column]["computed"]
        eq_(self.normalize(compData["sqltext"]), sqltext)
        if testing.requires.computed_columns_reflect_persisted.enabled:
            is_true("persisted" in compData)
            is_(compData["persisted"], persisted)

    def test_get_column_returns_persisted(self):
        insp = inspect(config.db)

        cols = insp.get_columns("computed_column_table")
        data = {c["name"]: c for c in cols}

        self.check_column(
            data,
            "computed_no_flag",
            "normal+42",
            testing.requires.computed_columns_default_persisted.enabled,
        )
        if testing.requires.computed_columns_virtual.enabled:
            self.check_column(
                data,
                "computed_virtual",
                "normal+2",
                False,
            )
        if testing.requires.computed_columns_stored.enabled:
            self.check_column(
                data,
                "computed_stored",
                "normal-42",
                True,
            )

    @testing.requires.schemas
    def test_get_column_returns_persisted_with_schema(self):
        insp = inspect(config.db)

        cols = insp.get_columns("computed_column_table", schema=config.test_schema)
        data = {c["name"]: c for c in cols}

        self.check_column(
            data,
            "computed_no_flag",
            "normal/42",
            testing.requires.computed_columns_default_persisted.enabled,
        )
        if testing.requires.computed_columns_virtual.enabled:
            self.check_column(
                data,
                "computed_virtual",
                "normal/2",
                False,
            )
        if testing.requires.computed_columns_stored.enabled:
            self.check_column(
                data,
                "computed_stored",
                "normal*42",
                True,
            )


class IdentityReflectionTest(fixtures.TablesTest):
    run_inserts = run_deletes = None

    __backend__ = True
    __requires__ = ("identity_columns", "table_reflection")

    @classmethod
    def define_tables(cls, metadata):
        Table(
            "t1",
            metadata,
            Column("normal", Integer),
            Column("id1", Integer, Identity()),
        )
        Table(
            "t2",
            metadata,
            Column(
                "id2",
                Integer,
                Identity(
                    always=True,
                    start=2,
                    increment=3,
                    minvalue=-2,
                    maxvalue=42,
                    cycle=True,
                    cache=4,
                ),
            ),
        )
        if testing.requires.schemas.enabled:
            Table(
                "t1",
                metadata,
                Column("normal", Integer),
                Column("id1", Integer, Identity(always=True, start=20)),
                schema=config.test_schema,
            )

    def check(self, value, exp, approx):
        if testing.requires.identity_columns_standard.enabled:
            common_keys = (
                "always",
                "start",
                "increment",
                "minvalue",
                "maxvalue",
                "cycle",
                "cache",
            )
            for k in list(value):
                if k not in common_keys:
                    value.pop(k)
            if approx:
                eq_(len(value), len(exp))
                for k in value:
                    if k == "minvalue":
                        is_true(value[k] <= exp[k])
                    elif k in {"maxvalue", "cache"}:
                        is_true(value[k] >= exp[k])
                    else:
                        eq_(value[k], exp[k], k)
            else:
                eq_(value, exp)
        else:
            eq_(value["start"], exp["start"])
            eq_(value["increment"], exp["increment"])

    def test_reflect_identity(self):
        insp = inspect(config.db)

        cols = insp.get_columns("t1") + insp.get_columns("t2")
        for col in cols:
            if col["name"] == "normal":
                is_false("identity" in col)
            elif col["name"] == "id1":
                is_true(col["autoincrement"] in (True, "auto"))
                eq_(col["default"], None)
                is_true("identity" in col)
                self.check(
                    col["identity"],
                    dict(
                        always=False,
                        start=1,
                        increment=1,
                        minvalue=1,
                        maxvalue=2147483647,
                        cycle=False,
                        cache=1,
                    ),
                    approx=True,
                )
            elif col["name"] == "id2":
                is_true(col["autoincrement"] in (True, "auto"))
                eq_(col["default"], None)
                is_true("identity" in col)
                self.check(
                    col["identity"],
                    dict(
                        always=True,
                        start=2,
                        increment=3,
                        minvalue=-2,
                        maxvalue=42,
                        cycle=True,
                        cache=4,
                    ),
                    approx=False,
                )

    @testing.requires.schemas
    def test_reflect_identity_schema(self):
        insp = inspect(config.db)

        cols = insp.get_columns("t1", schema=config.test_schema)
        for col in cols:
            if col["name"] == "normal":
                is_false("identity" in col)
            elif col["name"] == "id1":
                is_true(col["autoincrement"] in (True, "auto"))
                eq_(col["default"], None)
                is_true("identity" in col)
                self.check(
                    col["identity"],
                    dict(
                        always=True,
                        start=20,
                        increment=1,
                        minvalue=1,
                        maxvalue=2147483647,
                        cycle=False,
                        cache=1,
                    ),
                    approx=True,
                )


class CompositeKeyReflectionTest(fixtures.TablesTest):
    __backend__ = True

    @classmethod
    def define_tables(cls, metadata):
        tb1 = Table(
            "tb1",
            metadata,
            Column("id", Integer),
            Column("attr", Integer),
            Column("name", sql_types.VARCHAR(20)),
            sa.PrimaryKeyConstraint("name", "id", "attr", name="pk_tb1"),
            schema=None,
            test_needs_fk=True,
        )
        Table(
            "tb2",
            metadata,
            Column("id", Integer, primary_key=True),
            Column("pid", Integer),
            Column("pattr", Integer),
            Column("pname", sql_types.VARCHAR(20)),
            sa.ForeignKeyConstraint(
                ["pname", "pid", "pattr"],
                [tb1.c.name, tb1.c.id, tb1.c.attr],
                name="fk_tb1_name_id_attr",
            ),
            schema=None,
            test_needs_fk=True,
        )

    @testing.requires.primary_key_constraint_reflection
    def test_pk_column_order(self):
        # test for issue #5661
        insp = inspect(self.bind)
        primary_key = insp.get_pk_constraint(self.tables.tb1.name)
        eq_(primary_key.get("constrained_columns"), ["name", "id", "attr"])

    @testing.requires.foreign_key_constraint_reflection
    def test_fk_column_order(self):
        # test for issue #5661
        insp = inspect(self.bind)
        foreign_keys = insp.get_foreign_keys(self.tables.tb2.name)
        eq_(len(foreign_keys), 1)
        fkey1 = foreign_keys[0]
        eq_(fkey1.get("referred_columns"), ["name", "id", "attr"])
        eq_(fkey1.get("constrained_columns"), ["pname", "pid", "pattr"])


__all__ = (
    "ComponentReflectionTest",
    "ComponentReflectionTestExtra",
    "TableNoColumnsTest",
    "QuotedNameArgumentTest",
    "HasTableTest",
    "HasIndexTest",
    "NormalizedNameTest",
    "ComputedReflectionTest",
    "IdentityReflectionTest",
    "CompositeKeyReflectionTest",
)

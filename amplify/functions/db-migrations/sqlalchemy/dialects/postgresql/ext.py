# postgresql/ext.py
# Copyright (C) 2005-2023 the SQLAlchemy authors and contributors
# <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: https://www.opensource.org/licenses/mit-license.php

from .array import ARRAY
from ... import util
from ...sql import coercions
from ...sql import elements
from ...sql import expression
from ...sql import functions
from ...sql import roles
from ...sql import schema
from ...sql.schema import ColumnCollectionConstraint
from ...sql.visitors import InternalTraversal


class aggregate_order_by(expression.ColumnElement):
    """Represent a PostgreSQL aggregate order by expression.

    E.g.::

        from sqlalchemy.dialects.postgresql import aggregate_order_by
        expr = func.array_agg(aggregate_order_by(table.c.a, table.c.b.desc()))
        stmt = select(expr)

    would represent the expression::

        SELECT array_agg(a ORDER BY b DESC) FROM table;

    Similarly::

        expr = func.string_agg(
            table.c.a,
            aggregate_order_by(literal_column("','"), table.c.a)
        )
        stmt = select(expr)

    Would represent::

        SELECT string_agg(a, ',' ORDER BY a) FROM table;

    .. versionadded:: 1.1

    .. versionchanged:: 1.2.13 - the ORDER BY argument may be multiple terms

    .. seealso::

        :class:`_functions.array_agg`

    """

    __visit_name__ = "aggregate_order_by"

    stringify_dialect = "postgresql"
    _traverse_internals = [
        ("target", InternalTraversal.dp_clauseelement),
        ("type", InternalTraversal.dp_type),
        ("order_by", InternalTraversal.dp_clauseelement),
    ]

    def __init__(self, target, *order_by):
        self.target = coercions.expect(roles.ExpressionElementRole, target)
        self.type = self.target.type

        _lob = len(order_by)
        if _lob == 0:
            raise TypeError("at least one ORDER BY element is required")
        elif _lob == 1:
            self.order_by = coercions.expect(roles.ExpressionElementRole, order_by[0])
        else:
            self.order_by = elements.ClauseList(
                *order_by, _literal_as_text_role=roles.ExpressionElementRole
            )

    def self_group(self, against=None):
        return self

    def get_children(self, **kwargs):
        return self.target, self.order_by

    def _copy_internals(self, clone=elements._clone, **kw):
        self.target = clone(self.target, **kw)
        self.order_by = clone(self.order_by, **kw)

    @property
    def _from_objects(self):
        return self.target._from_objects + self.order_by._from_objects


class ExcludeConstraint(ColumnCollectionConstraint):
    """A table-level EXCLUDE constraint.

    Defines an EXCLUDE constraint as described in the `PostgreSQL
    documentation`__.

    __ https://www.postgresql.org/docs/current/static/sql-createtable.html#SQL-CREATETABLE-EXCLUDE

    """  # noqa

    __visit_name__ = "exclude_constraint"

    where = None
    inherit_cache = False

    create_drop_stringify_dialect = "postgresql"

    @elements._document_text_coercion(
        "where",
        ":class:`.ExcludeConstraint`",
        ":paramref:`.ExcludeConstraint.where`",
    )
    def __init__(self, *elements, **kw):
        r"""
        Create an :class:`.ExcludeConstraint` object.

        E.g.::

            const = ExcludeConstraint(
                (Column('period'), '&&'),
                (Column('group'), '='),
                where=(Column('group') != 'some group'),
                ops={'group': 'my_operator_class'}
            )

        The constraint is normally embedded into the :class:`_schema.Table`
        construct
        directly, or added later using :meth:`.append_constraint`::

            some_table = Table(
                'some_table', metadata,
                Column('id', Integer, primary_key=True),
                Column('period', TSRANGE()),
                Column('group', String)
            )

            some_table.append_constraint(
                ExcludeConstraint(
                    (some_table.c.period, '&&'),
                    (some_table.c.group, '='),
                    where=some_table.c.group != 'some group',
                    name='some_table_excl_const',
                    ops={'group': 'my_operator_class'}
                )
            )

        :param \*elements:

          A sequence of two tuples of the form ``(column, operator)`` where
          "column" is a SQL expression element or a raw SQL string, most
          typically a :class:`_schema.Column` object,
          and "operator" is a string
          containing the operator to use.   In order to specify a column name
          when a  :class:`_schema.Column` object is not available,
          while ensuring
          that any necessary quoting rules take effect, an ad-hoc
          :class:`_schema.Column` or :func:`_expression.column`
          object should be
          used.

        :param name:
          Optional, the in-database name of this constraint.

        :param deferrable:
          Optional bool.  If set, emit DEFERRABLE or NOT DEFERRABLE when
          issuing DDL for this constraint.

        :param initially:
          Optional string.  If set, emit INITIALLY <value> when issuing DDL
          for this constraint.

        :param using:
          Optional string.  If set, emit USING <index_method> when issuing DDL
          for this constraint. Defaults to 'gist'.

        :param where:
          Optional SQL expression construct or literal SQL string.
          If set, emit WHERE <predicate> when issuing DDL
          for this constraint.

        :param ops:
          Optional dictionary.  Used to define operator classes for the
          elements; works the same way as that of the
          :ref:`postgresql_ops <postgresql_operator_classes>`
          parameter specified to the :class:`_schema.Index` construct.

          .. versionadded:: 1.3.21

          .. seealso::

            :ref:`postgresql_operator_classes` - general description of how
            PostgreSQL operator classes are specified.

        """
        columns = []
        render_exprs = []
        self.operators = {}

        expressions, operators = zip(*elements)

        for (expr, column, strname, add_element), operator in zip(
            coercions.expect_col_expression_collection(
                roles.DDLConstraintColumnRole, expressions
            ),
            operators,
        ):
            if add_element is not None:
                columns.append(add_element)

            name = column.name if column is not None else strname

            if name is not None:
                # backwards compat
                self.operators[name] = operator

            render_exprs.append((expr, name, operator))

        self._render_exprs = render_exprs

        ColumnCollectionConstraint.__init__(
            self,
            *columns,
            name=kw.get("name"),
            deferrable=kw.get("deferrable"),
            initially=kw.get("initially")
        )
        self.using = kw.get("using", "gist")
        where = kw.get("where")
        if where is not None:
            self.where = coercions.expect(roles.StatementOptionRole, where)

        self.ops = kw.get("ops", {})

    def _set_parent(self, table, **kw):
        super(ExcludeConstraint, self)._set_parent(table)

        self._render_exprs = [
            (
                expr if isinstance(expr, elements.ClauseElement) else colexpr,
                name,
                operator,
            )
            for (expr, name, operator), colexpr in util.zip_longest(
                self._render_exprs, self.columns
            )
        ]

    def _copy(self, target_table=None, **kw):
        elements = [
            (
                schema._copy_expression(expr, self.parent, target_table),
                self.operators[expr.name],
            )
            for expr in self.columns
        ]
        c = self.__class__(
            *elements,
            name=self.name,
            deferrable=self.deferrable,
            initially=self.initially,
            where=self.where,
            using=self.using
        )
        c.dispatch._update(self.dispatch)
        return c


def array_agg(*arg, **kw):
    """PostgreSQL-specific form of :class:`_functions.array_agg`, ensures
    return type is :class:`_postgresql.ARRAY` and not
    the plain :class:`_types.ARRAY`, unless an explicit ``type_``
    is passed.

    .. versionadded:: 1.1

    """
    kw["_default_array_type"] = ARRAY
    return functions.func.array_agg(*arg, **kw)

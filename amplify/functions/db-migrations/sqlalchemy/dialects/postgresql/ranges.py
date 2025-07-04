# Copyright (C) 2013-2023 the SQLAlchemy authors and contributors
# <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: https://www.opensource.org/licenses/mit-license.php

from ... import types as sqltypes


__all__ = ("INT4RANGE", "INT8RANGE", "NUMRANGE")


class RangeOperators(object):
    """
    This mixin provides functionality for the Range Operators
    listed in the Range Operators table of the `PostgreSQL documentation`__
    for Range Functions and Operators. It is used by all the range types
    provided in the ``postgres`` dialect and can likely be used for
    any range types you create yourself.

    __ https://www.postgresql.org/docs/current/static/functions-range.html

    No extra support is provided for the Range Functions listed in the Range
    Functions table of the PostgreSQL documentation. For these, the normal
    :func:`~sqlalchemy.sql.expression.func` object should be used.

    """

    class comparator_factory(sqltypes.Concatenable.Comparator):
        """Define comparison operations for range types."""

        def __ne__(self, other):
            "Boolean expression. Returns true if two ranges are not equal"
            if other is None:
                return super(RangeOperators.comparator_factory, self).__ne__(other)
            else:
                return self.expr.op("<>", is_comparison=True)(other)

        def contains(self, other, **kw):
            """Boolean expression. Returns true if the right hand operand,
            which can be an element or a range, is contained within the
            column.

            kwargs may be ignored by this operator but are required for API
            conformance.
            """
            return self.expr.op("@>", is_comparison=True)(other)

        def contained_by(self, other):
            """Boolean expression. Returns true if the column is contained
            within the right hand operand.
            """
            return self.expr.op("<@", is_comparison=True)(other)

        def overlaps(self, other):
            """Boolean expression. Returns true if the column overlaps
            (has points in common with) the right hand operand.
            """
            return self.expr.op("&&", is_comparison=True)(other)

        def strictly_left_of(self, other):
            """Boolean expression. Returns true if the column is strictly
            left of the right hand operand.
            """
            return self.expr.op("<<", is_comparison=True)(other)

        __lshift__ = strictly_left_of

        def strictly_right_of(self, other):
            """Boolean expression. Returns true if the column is strictly
            right of the right hand operand.
            """
            return self.expr.op(">>", is_comparison=True)(other)

        __rshift__ = strictly_right_of

        def not_extend_right_of(self, other):
            """Boolean expression. Returns true if the range in the column
            does not extend right of the range in the operand.
            """
            return self.expr.op("&<", is_comparison=True)(other)

        def not_extend_left_of(self, other):
            """Boolean expression. Returns true if the range in the column
            does not extend left of the range in the operand.
            """
            return self.expr.op("&>", is_comparison=True)(other)

        def adjacent_to(self, other):
            """Boolean expression. Returns true if the range in the column
            is adjacent to the range in the operand.
            """
            return self.expr.op("-|-", is_comparison=True)(other)

        def __add__(self, other):
            """Range expression. Returns the union of the two ranges.
            Will raise an exception if the resulting range is not
            contiguous.
            """
            return self.expr.op("+")(other)


class INT4RANGE(RangeOperators, sqltypes.TypeEngine):
    """Represent the PostgreSQL INT4RANGE type."""

    __visit_name__ = "INT4RANGE"


class INT8RANGE(RangeOperators, sqltypes.TypeEngine):
    """Represent the PostgreSQL INT8RANGE type."""

    __visit_name__ = "INT8RANGE"


class NUMRANGE(RangeOperators, sqltypes.TypeEngine):
    """Represent the PostgreSQL NUMRANGE type."""

    __visit_name__ = "NUMRANGE"


class DATERANGE(RangeOperators, sqltypes.TypeEngine):
    """Represent the PostgreSQL DATERANGE type."""

    __visit_name__ = "DATERANGE"


class TSRANGE(RangeOperators, sqltypes.TypeEngine):
    """Represent the PostgreSQL TSRANGE type."""

    __visit_name__ = "TSRANGE"


class TSTZRANGE(RangeOperators, sqltypes.TypeEngine):
    """Represent the PostgreSQL TSTZRANGE type."""

    __visit_name__ = "TSTZRANGE"

# orm/base.py
# Copyright (C) 2005-2023 the SQLAlchemy authors and contributors
# <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: https://www.opensource.org/licenses/mit-license.php

"""Constants and rudimental functions used throughout the ORM.

"""

import operator

from . import exc
from .. import exc as sa_exc
from .. import inspection
from .. import util


PASSIVE_NO_RESULT = util.symbol(
    "PASSIVE_NO_RESULT",
    """Symbol returned by a loader callable or other attribute/history
    retrieval operation when a value could not be determined, based
    on loader callable flags.
    """,
)

PASSIVE_CLASS_MISMATCH = util.symbol(
    "PASSIVE_CLASS_MISMATCH",
    """Symbol indicating that an object is locally present for a given
    primary key identity but it is not of the requested class.  The
    return value is therefore None and no SQL should be emitted.""",
)

ATTR_WAS_SET = util.symbol(
    "ATTR_WAS_SET",
    """Symbol returned by a loader callable to indicate the
    retrieved value, or values, were assigned to their attributes
    on the target object.
    """,
)

ATTR_EMPTY = util.symbol(
    "ATTR_EMPTY",
    """Symbol used internally to indicate an attribute had no callable.""",
)

NO_VALUE = util.symbol(
    "NO_VALUE",
    """Symbol which may be placed as the 'previous' value of an attribute,
    indicating no value was loaded for an attribute when it was modified,
    and flags indicated we were not to load it.
    """,
)
NEVER_SET = NO_VALUE
"""
Synonymous with NO_VALUE

.. versionchanged:: 1.4   NEVER_SET was merged with NO_VALUE
"""

NO_CHANGE = util.symbol(
    "NO_CHANGE",
    """No callables or SQL should be emitted on attribute access
    and no state should change
    """,
    canonical=0,
)

CALLABLES_OK = util.symbol(
    "CALLABLES_OK",
    """Loader callables can be fired off if a value
    is not present.
    """,
    canonical=1,
)

SQL_OK = util.symbol(
    "SQL_OK",
    """Loader callables can emit SQL at least on scalar value attributes.""",
    canonical=2,
)

RELATED_OBJECT_OK = util.symbol(
    "RELATED_OBJECT_OK",
    """Callables can use SQL to load related objects as well
    as scalar value attributes.
    """,
    canonical=4,
)

INIT_OK = util.symbol(
    "INIT_OK",
    """Attributes should be initialized with a blank
    value (None or an empty collection) upon get, if no other
    value can be obtained.
    """,
    canonical=8,
)

NON_PERSISTENT_OK = util.symbol(
    "NON_PERSISTENT_OK",
    """Callables can be emitted if the parent is not persistent.""",
    canonical=16,
)

LOAD_AGAINST_COMMITTED = util.symbol(
    "LOAD_AGAINST_COMMITTED",
    """Callables should use committed values as primary/foreign keys during a
    load.
    """,
    canonical=32,
)

NO_AUTOFLUSH = util.symbol(
    "NO_AUTOFLUSH",
    """Loader callables should disable autoflush.""",
    canonical=64,
)

NO_RAISE = util.symbol(
    "NO_RAISE",
    """Loader callables should not raise any assertions""",
    canonical=128,
)

DEFERRED_HISTORY_LOAD = util.symbol(
    "DEFERRED_HISTORY_LOAD",
    """indicates special load of the previous value of an attribute""",
    canonical=256,
)

# pre-packaged sets of flags used as inputs
PASSIVE_OFF = util.symbol(
    "PASSIVE_OFF",
    "Callables can be emitted in all cases.",
    canonical=(RELATED_OBJECT_OK | NON_PERSISTENT_OK | INIT_OK | CALLABLES_OK | SQL_OK),
)
PASSIVE_RETURN_NO_VALUE = util.symbol(
    "PASSIVE_RETURN_NO_VALUE",
    """PASSIVE_OFF ^ INIT_OK""",
    canonical=PASSIVE_OFF ^ INIT_OK,
)
PASSIVE_NO_INITIALIZE = util.symbol(
    "PASSIVE_NO_INITIALIZE",
    "PASSIVE_RETURN_NO_VALUE ^ CALLABLES_OK",
    canonical=PASSIVE_RETURN_NO_VALUE ^ CALLABLES_OK,
)
PASSIVE_NO_FETCH = util.symbol(
    "PASSIVE_NO_FETCH", "PASSIVE_OFF ^ SQL_OK", canonical=PASSIVE_OFF ^ SQL_OK
)
PASSIVE_NO_FETCH_RELATED = util.symbol(
    "PASSIVE_NO_FETCH_RELATED",
    "PASSIVE_OFF ^ RELATED_OBJECT_OK",
    canonical=PASSIVE_OFF ^ RELATED_OBJECT_OK,
)
PASSIVE_ONLY_PERSISTENT = util.symbol(
    "PASSIVE_ONLY_PERSISTENT",
    "PASSIVE_OFF ^ NON_PERSISTENT_OK",
    canonical=PASSIVE_OFF ^ NON_PERSISTENT_OK,
)

PASSIVE_MERGE = util.symbol(
    "PASSIVE_OFF | NO_RAISE",
    "Symbol used specifically for session.merge() and similar cases",
    canonical=PASSIVE_OFF | NO_RAISE,
)

DEFAULT_MANAGER_ATTR = "_sa_class_manager"
DEFAULT_STATE_ATTR = "_sa_instance_state"

EXT_CONTINUE = util.symbol("EXT_CONTINUE")
EXT_STOP = util.symbol("EXT_STOP")
EXT_SKIP = util.symbol("EXT_SKIP")

ONETOMANY = util.symbol(
    "ONETOMANY",
    """Indicates the one-to-many direction for a :func:`_orm.relationship`.

    This symbol is typically used by the internals but may be exposed within
    certain API features.

    """,
)

MANYTOONE = util.symbol(
    "MANYTOONE",
    """Indicates the many-to-one direction for a :func:`_orm.relationship`.

    This symbol is typically used by the internals but may be exposed within
    certain API features.

    """,
)

MANYTOMANY = util.symbol(
    "MANYTOMANY",
    """Indicates the many-to-many direction for a :func:`_orm.relationship`.

    This symbol is typically used by the internals but may be exposed within
    certain API features.

    """,
)

NOT_EXTENSION = util.symbol(
    "NOT_EXTENSION",
    """Symbol indicating an :class:`InspectionAttr` that's
    not part of sqlalchemy.ext.

    Is assigned to the :attr:`.InspectionAttr.extension_type`
    attribute.

    """,
)

_never_set = frozenset([NEVER_SET])

_none_set = frozenset([None, NEVER_SET, PASSIVE_NO_RESULT])

_SET_DEFERRED_EXPIRED = util.symbol("SET_DEFERRED_EXPIRED")

_DEFER_FOR_STATE = util.symbol("DEFER_FOR_STATE")

_RAISE_FOR_STATE = util.symbol("RAISE_FOR_STATE")


def _assertions(*assertions):
    @util.decorator
    def generate(fn, *args, **kw):
        self = args[0]
        for assertion in assertions:
            assertion(self, fn.__name__)
        fn(self, *args[1:], **kw)

    return generate


# these can be replaced by sqlalchemy.ext.instrumentation
# if augmented class instrumentation is enabled.
def manager_of_class(cls):
    return cls.__dict__.get(DEFAULT_MANAGER_ATTR, None)


instance_state = operator.attrgetter(DEFAULT_STATE_ATTR)

instance_dict = operator.attrgetter("__dict__")


def instance_str(instance):
    """Return a string describing an instance."""

    return state_str(instance_state(instance))


def state_str(state):
    """Return a string describing an instance via its InstanceState."""

    if state is None:
        return "None"
    else:
        return "<%s at 0x%x>" % (state.class_.__name__, id(state.obj()))


def state_class_str(state):
    """Return a string describing an instance's class via its
    InstanceState.
    """

    if state is None:
        return "None"
    else:
        return "<%s>" % (state.class_.__name__,)


def attribute_str(instance, attribute):
    return instance_str(instance) + "." + attribute


def state_attribute_str(state, attribute):
    return state_str(state) + "." + attribute


def object_mapper(instance):
    """Given an object, return the primary Mapper associated with the object
    instance.

    Raises :class:`sqlalchemy.orm.exc.UnmappedInstanceError`
    if no mapping is configured.

    This function is available via the inspection system as::

        inspect(instance).mapper

    Using the inspection system will raise
    :class:`sqlalchemy.exc.NoInspectionAvailable` if the instance is
    not part of a mapping.

    """
    return object_state(instance).mapper


def object_state(instance):
    """Given an object, return the :class:`.InstanceState`
    associated with the object.

    Raises :class:`sqlalchemy.orm.exc.UnmappedInstanceError`
    if no mapping is configured.

    Equivalent functionality is available via the :func:`_sa.inspect`
    function as::

        inspect(instance)

    Using the inspection system will raise
    :class:`sqlalchemy.exc.NoInspectionAvailable` if the instance is
    not part of a mapping.

    """
    state = _inspect_mapped_object(instance)
    if state is None:
        raise exc.UnmappedInstanceError(instance)
    else:
        return state


@inspection._inspects(object)
def _inspect_mapped_object(instance):
    try:
        return instance_state(instance)
    except (exc.UnmappedClassError,) + exc.NO_STATE:
        return None


def _class_to_mapper(class_or_mapper):
    insp = inspection.inspect(class_or_mapper, False)
    if insp is not None:
        return insp.mapper
    else:
        raise exc.UnmappedClassError(class_or_mapper)


def _mapper_or_none(entity):
    """Return the :class:`_orm.Mapper` for the given class or None if the
    class is not mapped.
    """

    insp = inspection.inspect(entity, False)
    if insp is not None:
        return insp.mapper
    else:
        return None


def _is_mapped_class(entity):
    """Return True if the given object is a mapped class,
    :class:`_orm.Mapper`, or :class:`.AliasedClass`.
    """

    insp = inspection.inspect(entity, False)
    return (
        insp is not None
        and not insp.is_clause_element
        and (insp.is_mapper or insp.is_aliased_class)
    )


def _orm_columns(entity):
    insp = inspection.inspect(entity, False)
    if hasattr(insp, "selectable") and hasattr(insp.selectable, "c"):
        return [c for c in insp.selectable.c]
    else:
        return [entity]


def _is_aliased_class(entity):
    insp = inspection.inspect(entity, False)
    return insp is not None and getattr(insp, "is_aliased_class", False)


def _entity_descriptor(entity, key):
    """Return a class attribute given an entity and string name.

    May return :class:`.InstrumentedAttribute` or user-defined
    attribute.

    """
    insp = inspection.inspect(entity)
    if insp.is_selectable:
        description = entity
        entity = insp.c
    elif insp.is_aliased_class:
        entity = insp.entity
        description = entity
    elif hasattr(insp, "mapper"):
        description = entity = insp.mapper.class_
    else:
        description = entity

    try:
        return getattr(entity, key)
    except AttributeError as err:
        util.raise_(
            sa_exc.InvalidRequestError(
                "Entity '%s' has no property '%s'" % (description, key)
            ),
            replace_context=err,
        )


_state_mapper = util.dottedgetter("manager.mapper")


@inspection._inspects(type)
def _inspect_mapped_class(class_, configure=False):
    try:
        class_manager = manager_of_class(class_)
        if not class_manager.is_mapped:
            return None
        mapper = class_manager.mapper
    except exc.NO_STATE:
        return None
    else:
        if configure:
            mapper._check_configure()
        return mapper


def class_mapper(class_, configure=True):
    """Given a class, return the primary :class:`_orm.Mapper` associated
    with the key.

    Raises :exc:`.UnmappedClassError` if no mapping is configured
    on the given class, or :exc:`.ArgumentError` if a non-class
    object is passed.

    Equivalent functionality is available via the :func:`_sa.inspect`
    function as::

        inspect(some_mapped_class)

    Using the inspection system will raise
    :class:`sqlalchemy.exc.NoInspectionAvailable` if the class is not mapped.

    """
    mapper = _inspect_mapped_class(class_, configure=configure)
    if mapper is None:
        if not isinstance(class_, type):
            raise sa_exc.ArgumentError("Class object expected, got '%r'." % (class_,))
        raise exc.UnmappedClassError(class_)
    else:
        return mapper


class InspectionAttr(object):
    """A base class applied to all ORM objects that can be returned
    by the :func:`_sa.inspect` function.

    The attributes defined here allow the usage of simple boolean
    checks to test basic facts about the object returned.

    While the boolean checks here are basically the same as using
    the Python isinstance() function, the flags here can be used without
    the need to import all of these classes, and also such that
    the SQLAlchemy class system can change while leaving the flags
    here intact for forwards-compatibility.

    """

    __slots__ = ()

    is_selectable = False
    """Return True if this object is an instance of
    :class:`_expression.Selectable`."""

    is_aliased_class = False
    """True if this object is an instance of :class:`.AliasedClass`."""

    is_instance = False
    """True if this object is an instance of :class:`.InstanceState`."""

    is_mapper = False
    """True if this object is an instance of :class:`_orm.Mapper`."""

    is_bundle = False
    """True if this object is an instance of :class:`.Bundle`."""

    is_property = False
    """True if this object is an instance of :class:`.MapperProperty`."""

    is_attribute = False
    """True if this object is a Python :term:`descriptor`.

    This can refer to one of many types.   Usually a
    :class:`.QueryableAttribute` which handles attributes events on behalf
    of a :class:`.MapperProperty`.   But can also be an extension type
    such as :class:`.AssociationProxy` or :class:`.hybrid_property`.
    The :attr:`.InspectionAttr.extension_type` will refer to a constant
    identifying the specific subtype.

    .. seealso::

        :attr:`_orm.Mapper.all_orm_descriptors`

    """

    _is_internal_proxy = False
    """True if this object is an internal proxy object.

    .. versionadded:: 1.2.12

    """

    is_clause_element = False
    """True if this object is an instance of
    :class:`_expression.ClauseElement`."""

    extension_type = NOT_EXTENSION
    """The extension type, if any.
    Defaults to :data:`.interfaces.NOT_EXTENSION`

    .. seealso::

        :data:`.HYBRID_METHOD`

        :data:`.HYBRID_PROPERTY`

        :data:`.ASSOCIATION_PROXY`

    """


class InspectionAttrInfo(InspectionAttr):
    """Adds the ``.info`` attribute to :class:`.InspectionAttr`.

    The rationale for :class:`.InspectionAttr` vs. :class:`.InspectionAttrInfo`
    is that the former is compatible as a mixin for classes that specify
    ``__slots__``; this is essentially an implementation artifact.

    """

    @util.memoized_property
    def info(self):
        """Info dictionary associated with the object, allowing user-defined
        data to be associated with this :class:`.InspectionAttr`.

        The dictionary is generated when first accessed.  Alternatively,
        it can be specified as a constructor argument to the
        :func:`.column_property`, :func:`_orm.relationship`, or
        :func:`.composite`
        functions.

        .. versionchanged:: 1.0.0 :attr:`.MapperProperty.info` is also
           available on extension types via the
           :attr:`.InspectionAttrInfo.info` attribute, so that it can apply
           to a wider variety of ORM and extension constructs.

        .. seealso::

            :attr:`.QueryableAttribute.info`

            :attr:`.SchemaItem.info`

        """
        return {}


class _MappedAttribute(object):
    """Mixin for attributes which should be replaced by mapper-assigned
    attributes.

    """

    __slots__ = ()

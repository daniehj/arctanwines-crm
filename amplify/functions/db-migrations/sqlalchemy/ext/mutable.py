# ext/mutable.py
# Copyright (C) 2005-2023 the SQLAlchemy authors and contributors
# <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: https://www.opensource.org/licenses/mit-license.php

r"""Provide support for tracking of in-place changes to scalar values,
which are propagated into ORM change events on owning parent objects.

.. _mutable_scalars:

Establishing Mutability on Scalar Column Values
===============================================

A typical example of a "mutable" structure is a Python dictionary.
Following the example introduced in :ref:`types_toplevel`, we
begin with a custom type that marshals Python dictionaries into
JSON strings before being persisted::

    from sqlalchemy.types import TypeDecorator, VARCHAR
    import json

    class JSONEncodedDict(TypeDecorator):
        "Represents an immutable structure as a json-encoded string."

        impl = VARCHAR

        def process_bind_param(self, value, dialect):
            if value is not None:
                value = json.dumps(value)
            return value

        def process_result_value(self, value, dialect):
            if value is not None:
                value = json.loads(value)
            return value

The usage of ``json`` is only for the purposes of example. The
:mod:`sqlalchemy.ext.mutable` extension can be used
with any type whose target Python type may be mutable, including
:class:`.PickleType`, :class:`_postgresql.ARRAY`, etc.

When using the :mod:`sqlalchemy.ext.mutable` extension, the value itself
tracks all parents which reference it.  Below, we illustrate a simple
version of the :class:`.MutableDict` dictionary object, which applies
the :class:`.Mutable` mixin to a plain Python dictionary::

    from sqlalchemy.ext.mutable import Mutable

    class MutableDict(Mutable, dict):
        @classmethod
        def coerce(cls, key, value):
            "Convert plain dictionaries to MutableDict."

            if not isinstance(value, MutableDict):
                if isinstance(value, dict):
                    return MutableDict(value)

                # this call will raise ValueError
                return Mutable.coerce(key, value)
            else:
                return value

        def __setitem__(self, key, value):
            "Detect dictionary set events and emit change events."

            dict.__setitem__(self, key, value)
            self.changed()

        def __delitem__(self, key):
            "Detect dictionary del events and emit change events."

            dict.__delitem__(self, key)
            self.changed()

The above dictionary class takes the approach of subclassing the Python
built-in ``dict`` to produce a dict
subclass which routes all mutation events through ``__setitem__``.  There are
variants on this approach, such as subclassing ``UserDict.UserDict`` or
``collections.MutableMapping``; the part that's important to this example is
that the :meth:`.Mutable.changed` method is called whenever an in-place
change to the datastructure takes place.

We also redefine the :meth:`.Mutable.coerce` method which will be used to
convert any values that are not instances of ``MutableDict``, such
as the plain dictionaries returned by the ``json`` module, into the
appropriate type.  Defining this method is optional; we could just as well
created our ``JSONEncodedDict`` such that it always returns an instance
of ``MutableDict``, and additionally ensured that all calling code
uses ``MutableDict`` explicitly.  When :meth:`.Mutable.coerce` is not
overridden, any values applied to a parent object which are not instances
of the mutable type will raise a ``ValueError``.

Our new ``MutableDict`` type offers a class method
:meth:`~.Mutable.as_mutable` which we can use within column metadata
to associate with types. This method grabs the given type object or
class and associates a listener that will detect all future mappings
of this type, applying event listening instrumentation to the mapped
attribute. Such as, with classical table metadata::

    from sqlalchemy import Table, Column, Integer

    my_data = Table('my_data', metadata,
        Column('id', Integer, primary_key=True),
        Column('data', MutableDict.as_mutable(JSONEncodedDict))
    )

Above, :meth:`~.Mutable.as_mutable` returns an instance of ``JSONEncodedDict``
(if the type object was not an instance already), which will intercept any
attributes which are mapped against this type.  Below we establish a simple
mapping against the ``my_data`` table::

    from sqlalchemy import mapper

    class MyDataClass(object):
        pass

    # associates mutation listeners with MyDataClass.data
    mapper(MyDataClass, my_data)

The ``MyDataClass.data`` member will now be notified of in place changes
to its value.

There's no difference in usage when using declarative::

    from sqlalchemy.ext.declarative import declarative_base

    Base = declarative_base()

    class MyDataClass(Base):
        __tablename__ = 'my_data'
        id = Column(Integer, primary_key=True)
        data = Column(MutableDict.as_mutable(JSONEncodedDict))

Any in-place changes to the ``MyDataClass.data`` member
will flag the attribute as "dirty" on the parent object::

    >>> from sqlalchemy.orm import Session

    >>> sess = Session()
    >>> m1 = MyDataClass(data={'value1':'foo'})
    >>> sess.add(m1)
    >>> sess.commit()

    >>> m1.data['value1'] = 'bar'
    >>> assert m1 in sess.dirty
    True

The ``MutableDict`` can be associated with all future instances
of ``JSONEncodedDict`` in one step, using
:meth:`~.Mutable.associate_with`.  This is similar to
:meth:`~.Mutable.as_mutable` except it will intercept all occurrences
of ``MutableDict`` in all mappings unconditionally, without
the need to declare it individually::

    MutableDict.associate_with(JSONEncodedDict)

    class MyDataClass(Base):
        __tablename__ = 'my_data'
        id = Column(Integer, primary_key=True)
        data = Column(JSONEncodedDict)


Supporting Pickling
--------------------

The key to the :mod:`sqlalchemy.ext.mutable` extension relies upon the
placement of a ``weakref.WeakKeyDictionary`` upon the value object, which
stores a mapping of parent mapped objects keyed to the attribute name under
which they are associated with this value. ``WeakKeyDictionary`` objects are
not picklable, due to the fact that they contain weakrefs and function
callbacks. In our case, this is a good thing, since if this dictionary were
picklable, it could lead to an excessively large pickle size for our value
objects that are pickled by themselves outside of the context of the parent.
The developer responsibility here is only to provide a ``__getstate__`` method
that excludes the :meth:`~MutableBase._parents` collection from the pickle
stream::

    class MyMutableType(Mutable):
        def __getstate__(self):
            d = self.__dict__.copy()
            d.pop('_parents', None)
            return d

With our dictionary example, we need to return the contents of the dict itself
(and also restore them on __setstate__)::

    class MutableDict(Mutable, dict):
        # ....

        def __getstate__(self):
            return dict(self)

        def __setstate__(self, state):
            self.update(state)

In the case that our mutable value object is pickled as it is attached to one
or more parent objects that are also part of the pickle, the :class:`.Mutable`
mixin will re-establish the :attr:`.Mutable._parents` collection on each value
object as the owning parents themselves are unpickled.

Receiving Events
----------------

The :meth:`.AttributeEvents.modified` event handler may be used to receive
an event when a mutable scalar emits a change event.  This event handler
is called when the :func:`.attributes.flag_modified` function is called
from within the mutable extension::

    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy import event

    Base = declarative_base()

    class MyDataClass(Base):
        __tablename__ = 'my_data'
        id = Column(Integer, primary_key=True)
        data = Column(MutableDict.as_mutable(JSONEncodedDict))

    @event.listens_for(MyDataClass.data, "modified")
    def modified_json(instance):
        print("json value modified:", instance.data)

.. _mutable_composites:

Establishing Mutability on Composites
=====================================

Composites are a special ORM feature which allow a single scalar attribute to
be assigned an object value which represents information "composed" from one
or more columns from the underlying mapped table. The usual example is that of
a geometric "point", and is introduced in :ref:`mapper_composite`.

As is the case with :class:`.Mutable`, the user-defined composite class
subclasses :class:`.MutableComposite` as a mixin, and detects and delivers
change events to its parents via the :meth:`.MutableComposite.changed` method.
In the case of a composite class, the detection is usually via the usage of
Python descriptors (i.e. ``@property``), or alternatively via the special
Python method ``__setattr__()``. Below we expand upon the ``Point`` class
introduced in :ref:`mapper_composite` to subclass :class:`.MutableComposite`
and to also route attribute set events via ``__setattr__`` to the
:meth:`.MutableComposite.changed` method::

    from sqlalchemy.ext.mutable import MutableComposite

    class Point(MutableComposite):
        def __init__(self, x, y):
            self.x = x
            self.y = y

        def __setattr__(self, key, value):
            "Intercept set events"

            # set the attribute
            object.__setattr__(self, key, value)

            # alert all parents to the change
            self.changed()

        def __composite_values__(self):
            return self.x, self.y

        def __eq__(self, other):
            return isinstance(other, Point) and \
                other.x == self.x and \
                other.y == self.y

        def __ne__(self, other):
            return not self.__eq__(other)

The :class:`.MutableComposite` class uses a Python metaclass to automatically
establish listeners for any usage of :func:`_orm.composite` that specifies our
``Point`` type. Below, when ``Point`` is mapped to the ``Vertex`` class,
listeners are established which will route change events from ``Point``
objects to each of the ``Vertex.start`` and ``Vertex.end`` attributes::

    from sqlalchemy.orm import composite, mapper
    from sqlalchemy import Table, Column

    vertices = Table('vertices', metadata,
        Column('id', Integer, primary_key=True),
        Column('x1', Integer),
        Column('y1', Integer),
        Column('x2', Integer),
        Column('y2', Integer),
        )

    class Vertex(object):
        pass

    mapper(Vertex, vertices, properties={
        'start': composite(Point, vertices.c.x1, vertices.c.y1),
        'end': composite(Point, vertices.c.x2, vertices.c.y2)
    })

Any in-place changes to the ``Vertex.start`` or ``Vertex.end`` members
will flag the attribute as "dirty" on the parent object::

    >>> from sqlalchemy.orm import Session

    >>> sess = Session()
    >>> v1 = Vertex(start=Point(3, 4), end=Point(12, 15))
    >>> sess.add(v1)
    >>> sess.commit()

    >>> v1.end.x = 8
    >>> assert v1 in sess.dirty
    True

Coercing Mutable Composites
---------------------------

The :meth:`.MutableBase.coerce` method is also supported on composite types.
In the case of :class:`.MutableComposite`, the :meth:`.MutableBase.coerce`
method is only called for attribute set operations, not load operations.
Overriding the :meth:`.MutableBase.coerce` method is essentially equivalent
to using a :func:`.validates` validation routine for all attributes which
make use of the custom composite type::

    class Point(MutableComposite):
        # other Point methods
        # ...

        def coerce(cls, key, value):
            if isinstance(value, tuple):
                value = Point(*value)
            elif not isinstance(value, Point):
                raise ValueError("tuple or Point expected")
            return value

Supporting Pickling
--------------------

As is the case with :class:`.Mutable`, the :class:`.MutableComposite` helper
class uses a ``weakref.WeakKeyDictionary`` available via the
:meth:`MutableBase._parents` attribute which isn't picklable. If we need to
pickle instances of ``Point`` or its owning class ``Vertex``, we at least need
to define a ``__getstate__`` that doesn't include the ``_parents`` dictionary.
Below we define both a ``__getstate__`` and a ``__setstate__`` that package up
the minimal form of our ``Point`` class::

    class Point(MutableComposite):
        # ...

        def __getstate__(self):
            return self.x, self.y

        def __setstate__(self, state):
            self.x, self.y = state

As with :class:`.Mutable`, the :class:`.MutableComposite` augments the
pickling process of the parent's object-relational state so that the
:meth:`MutableBase._parents` collection is restored to all ``Point`` objects.

"""
from collections import defaultdict
import weakref

from .. import event
from .. import inspect
from .. import types
from ..orm import Mapper
from ..orm import mapper
from ..orm.attributes import flag_modified
from ..sql.base import SchemaEventTarget
from ..util import memoized_property


class MutableBase(object):
    """Common base class to :class:`.Mutable`
    and :class:`.MutableComposite`.

    """

    @memoized_property
    def _parents(self):
        """Dictionary of parent object's :class:`.InstanceState`->attribute
        name on the parent.

        This attribute is a so-called "memoized" property.  It initializes
        itself with a new ``weakref.WeakKeyDictionary`` the first time
        it is accessed, returning the same object upon subsequent access.

        .. versionchanged:: 1.4 the :class:`.InstanceState` is now used
           as the key in the weak dictionary rather than the instance
           itself.

        """

        return weakref.WeakKeyDictionary()

    @classmethod
    def coerce(cls, key, value):
        """Given a value, coerce it into the target type.

        Can be overridden by custom subclasses to coerce incoming
        data into a particular type.

        By default, raises ``ValueError``.

        This method is called in different scenarios depending on if
        the parent class is of type :class:`.Mutable` or of type
        :class:`.MutableComposite`.  In the case of the former, it is called
        for both attribute-set operations as well as during ORM loading
        operations.  For the latter, it is only called during attribute-set
        operations; the mechanics of the :func:`.composite` construct
        handle coercion during load operations.


        :param key: string name of the ORM-mapped attribute being set.
        :param value: the incoming value.
        :return: the method should return the coerced value, or raise
         ``ValueError`` if the coercion cannot be completed.

        """
        if value is None:
            return None
        msg = "Attribute '%s' does not accept objects of type %s"
        raise ValueError(msg % (key, type(value)))

    @classmethod
    def _get_listen_keys(cls, attribute):
        """Given a descriptor attribute, return a ``set()`` of the attribute
        keys which indicate a change in the state of this attribute.

        This is normally just ``set([attribute.key])``, but can be overridden
        to provide for additional keys.  E.g. a :class:`.MutableComposite`
        augments this set with the attribute keys associated with the columns
        that comprise the composite value.

        This collection is consulted in the case of intercepting the
        :meth:`.InstanceEvents.refresh` and
        :meth:`.InstanceEvents.refresh_flush` events, which pass along a list
        of attribute names that have been refreshed; the list is compared
        against this set to determine if action needs to be taken.

        .. versionadded:: 1.0.5

        """
        return {attribute.key}

    @classmethod
    def _listen_on_attribute(cls, attribute, coerce, parent_cls):
        """Establish this type as a mutation listener for the given
        mapped descriptor.

        """
        key = attribute.key
        if parent_cls is not attribute.class_:
            return

        # rely on "propagate" here
        parent_cls = attribute.class_

        listen_keys = cls._get_listen_keys(attribute)

        def load(state, *args):
            """Listen for objects loaded or refreshed.

            Wrap the target data member's value with
            ``Mutable``.

            """
            val = state.dict.get(key, None)
            if val is not None:
                if coerce:
                    val = cls.coerce(key, val)
                    state.dict[key] = val
                val._parents[state] = key

        def load_attrs(state, ctx, attrs):
            if not attrs or listen_keys.intersection(attrs):
                load(state)

        def set_(target, value, oldvalue, initiator):
            """Listen for set/replace events on the target
            data member.

            Establish a weak reference to the parent object
            on the incoming value, remove it for the one
            outgoing.

            """
            if value is oldvalue:
                return value

            if not isinstance(value, cls):
                value = cls.coerce(key, value)
            if value is not None:
                value._parents[target] = key
            if isinstance(oldvalue, cls):
                oldvalue._parents.pop(inspect(target), None)
            return value

        def pickle(state, state_dict):
            val = state.dict.get(key, None)
            if val is not None:
                if "ext.mutable.values" not in state_dict:
                    state_dict["ext.mutable.values"] = defaultdict(list)
                state_dict["ext.mutable.values"][key].append(val)

        def unpickle(state, state_dict):
            if "ext.mutable.values" in state_dict:
                collection = state_dict["ext.mutable.values"]
                if isinstance(collection, list):
                    # legacy format
                    for val in collection:
                        val._parents[state] = key
                else:
                    for val in state_dict["ext.mutable.values"][key]:
                        val._parents[state] = key

        event.listen(
            parent_cls,
            "_sa_event_merge_wo_load",
            load,
            raw=True,
            propagate=True,
        )

        event.listen(parent_cls, "load", load, raw=True, propagate=True)
        event.listen(parent_cls, "refresh", load_attrs, raw=True, propagate=True)
        event.listen(parent_cls, "refresh_flush", load_attrs, raw=True, propagate=True)
        event.listen(attribute, "set", set_, raw=True, retval=True, propagate=True)
        event.listen(parent_cls, "pickle", pickle, raw=True, propagate=True)
        event.listen(parent_cls, "unpickle", unpickle, raw=True, propagate=True)


class Mutable(MutableBase):
    """Mixin that defines transparent propagation of change
    events to a parent object.

    See the example in :ref:`mutable_scalars` for usage information.

    """

    def changed(self):
        """Subclasses should call this method whenever change events occur."""

        for parent, key in self._parents.items():
            flag_modified(parent.obj(), key)

    @classmethod
    def associate_with_attribute(cls, attribute):
        """Establish this type as a mutation listener for the given
        mapped descriptor.

        """
        cls._listen_on_attribute(attribute, True, attribute.class_)

    @classmethod
    def associate_with(cls, sqltype):
        """Associate this wrapper with all future mapped columns
        of the given type.

        This is a convenience method that calls
        ``associate_with_attribute`` automatically.

        .. warning::

           The listeners established by this method are *global*
           to all mappers, and are *not* garbage collected.   Only use
           :meth:`.associate_with` for types that are permanent to an
           application, not with ad-hoc types else this will cause unbounded
           growth in memory usage.

        """

        def listen_for_type(mapper, class_):
            if mapper.non_primary:
                return
            for prop in mapper.column_attrs:
                if isinstance(prop.columns[0].type, sqltype):
                    cls.associate_with_attribute(getattr(class_, prop.key))

        event.listen(mapper, "mapper_configured", listen_for_type)

    @classmethod
    def as_mutable(cls, sqltype):
        """Associate a SQL type with this mutable Python type.

        This establishes listeners that will detect ORM mappings against
        the given type, adding mutation event trackers to those mappings.

        The type is returned, unconditionally as an instance, so that
        :meth:`.as_mutable` can be used inline::

            Table('mytable', metadata,
                Column('id', Integer, primary_key=True),
                Column('data', MyMutableType.as_mutable(PickleType))
            )

        Note that the returned type is always an instance, even if a class
        is given, and that only columns which are declared specifically with
        that type instance receive additional instrumentation.

        To associate a particular mutable type with all occurrences of a
        particular type, use the :meth:`.Mutable.associate_with` classmethod
        of the particular :class:`.Mutable` subclass to establish a global
        association.

        .. warning::

           The listeners established by this method are *global*
           to all mappers, and are *not* garbage collected.   Only use
           :meth:`.as_mutable` for types that are permanent to an application,
           not with ad-hoc types else this will cause unbounded growth
           in memory usage.

        """
        sqltype = types.to_instance(sqltype)

        # a SchemaType will be copied when the Column is copied,
        # and we'll lose our ability to link that type back to the original.
        # so track our original type w/ columns
        if isinstance(sqltype, SchemaEventTarget):

            @event.listens_for(sqltype, "before_parent_attach")
            def _add_column_memo(sqltyp, parent):
                parent.info["_ext_mutable_orig_type"] = sqltyp

            schema_event_check = True
        else:
            schema_event_check = False

        def listen_for_type(mapper, class_):
            if mapper.non_primary:
                return
            for prop in mapper.column_attrs:
                if (
                    schema_event_check
                    and hasattr(prop.expression, "info")
                    and prop.expression.info.get("_ext_mutable_orig_type") is sqltype
                ) or (prop.columns[0].type is sqltype):
                    cls.associate_with_attribute(getattr(class_, prop.key))

        event.listen(mapper, "mapper_configured", listen_for_type)

        return sqltype


class MutableComposite(MutableBase):
    """Mixin that defines transparent propagation of change
    events on a SQLAlchemy "composite" object to its
    owning parent or parents.

    See the example in :ref:`mutable_composites` for usage information.

    """

    @classmethod
    def _get_listen_keys(cls, attribute):
        return {attribute.key}.union(attribute.property._attribute_keys)

    def changed(self):
        """Subclasses should call this method whenever change events occur."""

        for parent, key in self._parents.items():
            prop = parent.mapper.get_property(key)
            for value, attr_name in zip(
                self.__composite_values__(), prop._attribute_keys
            ):
                setattr(parent.obj(), attr_name, value)


def _setup_composite_listener():
    def _listen_for_type(mapper, class_):
        for prop in mapper.iterate_properties:
            if (
                hasattr(prop, "composite_class")
                and isinstance(prop.composite_class, type)
                and issubclass(prop.composite_class, MutableComposite)
            ):
                prop.composite_class._listen_on_attribute(
                    getattr(class_, prop.key), False, class_
                )

    if not event.contains(Mapper, "mapper_configured", _listen_for_type):
        event.listen(Mapper, "mapper_configured", _listen_for_type)


_setup_composite_listener()


class MutableDict(Mutable, dict):
    """A dictionary type that implements :class:`.Mutable`.

    The :class:`.MutableDict` object implements a dictionary that will
    emit change events to the underlying mapping when the contents of
    the dictionary are altered, including when values are added or removed.

    Note that :class:`.MutableDict` does **not** apply mutable tracking to  the
    *values themselves* inside the dictionary. Therefore it is not a sufficient
    solution for the use case of tracking deep changes to a *recursive*
    dictionary structure, such as a JSON structure.  To support this use case,
    build a subclass of  :class:`.MutableDict` that provides appropriate
    coercion to the values placed in the dictionary so that they too are
    "mutable", and emit events up to their parent structure.

    .. seealso::

        :class:`.MutableList`

        :class:`.MutableSet`

    """

    def __setitem__(self, key, value):
        """Detect dictionary set events and emit change events."""
        dict.__setitem__(self, key, value)
        self.changed()

    def setdefault(self, key, value):
        result = dict.setdefault(self, key, value)
        self.changed()
        return result

    def __delitem__(self, key):
        """Detect dictionary del events and emit change events."""
        dict.__delitem__(self, key)
        self.changed()

    def update(self, *a, **kw):
        dict.update(self, *a, **kw)
        self.changed()

    def pop(self, *arg):
        result = dict.pop(self, *arg)
        self.changed()
        return result

    def popitem(self):
        result = dict.popitem(self)
        self.changed()
        return result

    def clear(self):
        dict.clear(self)
        self.changed()

    @classmethod
    def coerce(cls, key, value):
        """Convert plain dictionary to instance of this class."""
        if not isinstance(value, cls):
            if isinstance(value, dict):
                return cls(value)
            return Mutable.coerce(key, value)
        else:
            return value

    def __getstate__(self):
        return dict(self)

    def __setstate__(self, state):
        self.update(state)


class MutableList(Mutable, list):
    """A list type that implements :class:`.Mutable`.

    The :class:`.MutableList` object implements a list that will
    emit change events to the underlying mapping when the contents of
    the list are altered, including when values are added or removed.

    Note that :class:`.MutableList` does **not** apply mutable tracking to  the
    *values themselves* inside the list. Therefore it is not a sufficient
    solution for the use case of tracking deep changes to a *recursive*
    mutable structure, such as a JSON structure.  To support this use case,
    build a subclass of  :class:`.MutableList` that provides appropriate
    coercion to the values placed in the dictionary so that they too are
    "mutable", and emit events up to their parent structure.

    .. versionadded:: 1.1

    .. seealso::

        :class:`.MutableDict`

        :class:`.MutableSet`

    """

    def __reduce_ex__(self, proto):
        return (self.__class__, (list(self),))

    # needed for backwards compatibility with
    # older pickles
    def __setstate__(self, state):
        self[:] = state

    def __setitem__(self, index, value):
        """Detect list set events and emit change events."""
        list.__setitem__(self, index, value)
        self.changed()

    def __setslice__(self, start, end, value):
        """Detect list set events and emit change events."""
        list.__setslice__(self, start, end, value)
        self.changed()

    def __delitem__(self, index):
        """Detect list del events and emit change events."""
        list.__delitem__(self, index)
        self.changed()

    def __delslice__(self, start, end):
        """Detect list del events and emit change events."""
        list.__delslice__(self, start, end)
        self.changed()

    def pop(self, *arg):
        result = list.pop(self, *arg)
        self.changed()
        return result

    def append(self, x):
        list.append(self, x)
        self.changed()

    def extend(self, x):
        list.extend(self, x)
        self.changed()

    def __iadd__(self, x):
        self.extend(x)
        return self

    def insert(self, i, x):
        list.insert(self, i, x)
        self.changed()

    def remove(self, i):
        list.remove(self, i)
        self.changed()

    def clear(self):
        list.clear(self)
        self.changed()

    def sort(self, **kw):
        list.sort(self, **kw)
        self.changed()

    def reverse(self):
        list.reverse(self)
        self.changed()

    @classmethod
    def coerce(cls, index, value):
        """Convert plain list to instance of this class."""
        if not isinstance(value, cls):
            if isinstance(value, list):
                return cls(value)
            return Mutable.coerce(index, value)
        else:
            return value


class MutableSet(Mutable, set):
    """A set type that implements :class:`.Mutable`.

    The :class:`.MutableSet` object implements a set that will
    emit change events to the underlying mapping when the contents of
    the set are altered, including when values are added or removed.

    Note that :class:`.MutableSet` does **not** apply mutable tracking to  the
    *values themselves* inside the set. Therefore it is not a sufficient
    solution for the use case of tracking deep changes to a *recursive*
    mutable structure.  To support this use case,
    build a subclass of  :class:`.MutableSet` that provides appropriate
    coercion to the values placed in the dictionary so that they too are
    "mutable", and emit events up to their parent structure.

    .. versionadded:: 1.1

    .. seealso::

        :class:`.MutableDict`

        :class:`.MutableList`


    """

    def update(self, *arg):
        set.update(self, *arg)
        self.changed()

    def intersection_update(self, *arg):
        set.intersection_update(self, *arg)
        self.changed()

    def difference_update(self, *arg):
        set.difference_update(self, *arg)
        self.changed()

    def symmetric_difference_update(self, *arg):
        set.symmetric_difference_update(self, *arg)
        self.changed()

    def __ior__(self, other):
        self.update(other)
        return self

    def __iand__(self, other):
        self.intersection_update(other)
        return self

    def __ixor__(self, other):
        self.symmetric_difference_update(other)
        return self

    def __isub__(self, other):
        self.difference_update(other)
        return self

    def add(self, elem):
        set.add(self, elem)
        self.changed()

    def remove(self, elem):
        set.remove(self, elem)
        self.changed()

    def discard(self, elem):
        set.discard(self, elem)
        self.changed()

    def pop(self, *arg):
        result = set.pop(self, *arg)
        self.changed()
        return result

    def clear(self):
        set.clear(self)
        self.changed()

    @classmethod
    def coerce(cls, index, value):
        """Convert plain set to instance of this class."""
        if not isinstance(value, cls):
            if isinstance(value, set):
                return cls(value)
            return Mutable.coerce(index, value)
        else:
            return value

    def __getstate__(self):
        return set(self)

    def __setstate__(self, state):
        self.update(state)

    def __reduce_ex__(self, proto):
        return (self.__class__, (list(self),))

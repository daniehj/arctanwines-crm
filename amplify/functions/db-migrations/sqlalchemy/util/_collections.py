# util/_collections.py
# Copyright (C) 2005-2023 the SQLAlchemy authors and contributors
# <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: https://www.opensource.org/licenses/mit-license.php

"""Collection classes and helpers."""

from __future__ import absolute_import

import operator
import types
import weakref

from .compat import binary_types
from .compat import collections_abc
from .compat import itertools_filterfalse
from .compat import py2k
from .compat import py37
from .compat import string_types
from .compat import threading


EMPTY_SET = frozenset()


class ImmutableContainer(object):
    def _immutable(self, *arg, **kw):
        raise TypeError("%s object is immutable" % self.__class__.__name__)

    __delitem__ = __setitem__ = __setattr__ = _immutable


def _immutabledict_py_fallback():
    class immutabledict(ImmutableContainer, dict):
        clear = pop = popitem = setdefault = update = ImmutableContainer._immutable

        def __new__(cls, *args):
            new = dict.__new__(cls)
            dict.__init__(new, *args)
            return new

        def __init__(self, *args):
            pass

        def __reduce__(self):
            return _immutabledict_reconstructor, (dict(self),)

        def union(self, __d=None):
            if not __d:
                return self

            new = dict.__new__(self.__class__)
            dict.__init__(new, self)
            dict.update(new, __d)
            return new

        def _union_w_kw(self, __d=None, **kw):
            # not sure if C version works correctly w/ this yet
            if not __d and not kw:
                return self

            new = dict.__new__(self.__class__)
            dict.__init__(new, self)
            if __d:
                dict.update(new, __d)
            dict.update(new, kw)
            return new

        def merge_with(self, *dicts):
            new = None
            for d in dicts:
                if d:
                    if new is None:
                        new = dict.__new__(self.__class__)
                        dict.__init__(new, self)
                    dict.update(new, d)
            if new is None:
                return self

            return new

        def __repr__(self):
            return "immutabledict(%s)" % dict.__repr__(self)

    return immutabledict


try:
    from sqlalchemy.cimmutabledict import immutabledict

    collections_abc.Mapping.register(immutabledict)

except ImportError:
    immutabledict = _immutabledict_py_fallback()

    def _immutabledict_reconstructor(*arg):
        """do the pickle dance"""
        return immutabledict(*arg)


def coerce_to_immutabledict(d):
    if not d:
        return EMPTY_DICT
    elif isinstance(d, immutabledict):
        return d
    else:
        return immutabledict(d)


EMPTY_DICT = immutabledict()


class FacadeDict(ImmutableContainer, dict):
    """A dictionary that is not publicly mutable."""

    clear = pop = popitem = setdefault = update = ImmutableContainer._immutable

    def __new__(cls, *args):
        new = dict.__new__(cls)
        return new

    def copy(self):
        raise NotImplementedError(
            "an immutabledict shouldn't need to be copied.  use dict(d) "
            "if you need a mutable dictionary."
        )

    def __reduce__(self):
        return FacadeDict, (dict(self),)

    def _insert_item(self, key, value):
        """insert an item into the dictionary directly."""
        dict.__setitem__(self, key, value)

    def __repr__(self):
        return "FacadeDict(%s)" % dict.__repr__(self)


class Properties(object):
    """Provide a __getattr__/__setattr__ interface over a dict."""

    __slots__ = ("_data",)

    def __init__(self, data):
        object.__setattr__(self, "_data", data)

    def __len__(self):
        return len(self._data)

    def __iter__(self):
        return iter(list(self._data.values()))

    def __dir__(self):
        return dir(super(Properties, self)) + [str(k) for k in self._data.keys()]

    def __add__(self, other):
        return list(self) + list(other)

    def __setitem__(self, key, obj):
        self._data[key] = obj

    def __getitem__(self, key):
        return self._data[key]

    def __delitem__(self, key):
        del self._data[key]

    def __setattr__(self, key, obj):
        self._data[key] = obj

    def __getstate__(self):
        return {"_data": self._data}

    def __setstate__(self, state):
        object.__setattr__(self, "_data", state["_data"])

    def __getattr__(self, key):
        try:
            return self._data[key]
        except KeyError:
            raise AttributeError(key)

    def __contains__(self, key):
        return key in self._data

    def as_immutable(self):
        """Return an immutable proxy for this :class:`.Properties`."""

        return ImmutableProperties(self._data)

    def update(self, value):
        self._data.update(value)

    def get(self, key, default=None):
        if key in self:
            return self[key]
        else:
            return default

    def keys(self):
        return list(self._data)

    def values(self):
        return list(self._data.values())

    def items(self):
        return list(self._data.items())

    def has_key(self, key):
        return key in self._data

    def clear(self):
        self._data.clear()


class OrderedProperties(Properties):
    """Provide a __getattr__/__setattr__ interface with an OrderedDict
    as backing store."""

    __slots__ = ()

    def __init__(self):
        Properties.__init__(self, OrderedDict())


class ImmutableProperties(ImmutableContainer, Properties):
    """Provide immutable dict/object attribute to an underlying dictionary."""

    __slots__ = ()


def _ordered_dictionary_sort(d, key=None):
    """Sort an OrderedDict in-place."""

    items = [(k, d[k]) for k in sorted(d, key=key)]

    d.clear()

    d.update(items)


if py37:
    OrderedDict = dict
    sort_dictionary = _ordered_dictionary_sort

else:
    # prevent sort_dictionary from being used against a plain dictionary
    # for Python < 3.7

    def sort_dictionary(d, key=None):
        """Sort an OrderedDict in place."""

        d._ordered_dictionary_sort(key=key)

    class OrderedDict(dict):
        """Dictionary that maintains insertion order.

        Superseded by Python dict as of Python 3.7

        """

        __slots__ = ("_list",)

        def _ordered_dictionary_sort(self, key=None):
            _ordered_dictionary_sort(self, key=key)

        def __reduce__(self):
            return OrderedDict, (self.items(),)

        def __init__(self, ____sequence=None, **kwargs):
            self._list = []
            if ____sequence is None:
                if kwargs:
                    self.update(**kwargs)
            else:
                self.update(____sequence, **kwargs)

        def clear(self):
            self._list = []
            dict.clear(self)

        def copy(self):
            return self.__copy__()

        def __copy__(self):
            return OrderedDict(self)

        def update(self, ____sequence=None, **kwargs):
            if ____sequence is not None:
                if hasattr(____sequence, "keys"):
                    for key in ____sequence.keys():
                        self.__setitem__(key, ____sequence[key])
                else:
                    for key, value in ____sequence:
                        self[key] = value
            if kwargs:
                self.update(kwargs)

        def setdefault(self, key, value):
            if key not in self:
                self.__setitem__(key, value)
                return value
            else:
                return self.__getitem__(key)

        def __iter__(self):
            return iter(self._list)

        def keys(self):
            return list(self)

        def values(self):
            return [self[key] for key in self._list]

        def items(self):
            return [(key, self[key]) for key in self._list]

        if py2k:

            def itervalues(self):
                return iter(self.values())

            def iterkeys(self):
                return iter(self)

            def iteritems(self):
                return iter(self.items())

        def __setitem__(self, key, obj):
            if key not in self:
                try:
                    self._list.append(key)
                except AttributeError:
                    # work around Python pickle loads() with
                    # dict subclass (seems to ignore __setstate__?)
                    self._list = [key]
            dict.__setitem__(self, key, obj)

        def __delitem__(self, key):
            dict.__delitem__(self, key)
            self._list.remove(key)

        def pop(self, key, *default):
            present = key in self
            value = dict.pop(self, key, *default)
            if present:
                self._list.remove(key)
            return value

        def popitem(self):
            item = dict.popitem(self)
            self._list.remove(item[0])
            return item


class OrderedSet(set):
    def __init__(self, d=None):
        set.__init__(self)
        if d is not None:
            self._list = unique_list(d)
            set.update(self, self._list)
        else:
            self._list = []

    def add(self, element):
        if element not in self:
            self._list.append(element)
        set.add(self, element)

    def remove(self, element):
        set.remove(self, element)
        self._list.remove(element)

    def insert(self, pos, element):
        if element not in self:
            self._list.insert(pos, element)
        set.add(self, element)

    def discard(self, element):
        if element in self:
            self._list.remove(element)
            set.remove(self, element)

    def clear(self):
        set.clear(self)
        self._list = []

    def __getitem__(self, key):
        return self._list[key]

    def __iter__(self):
        return iter(self._list)

    def __add__(self, other):
        return self.union(other)

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self._list)

    __str__ = __repr__

    def update(self, iterable):
        for e in iterable:
            if e not in self:
                self._list.append(e)
                set.add(self, e)
        return self

    __ior__ = update

    def union(self, other):
        result = self.__class__(self)
        result.update(other)
        return result

    __or__ = union

    def intersection(self, other):
        other = set(other)
        return self.__class__(a for a in self if a in other)

    __and__ = intersection

    def symmetric_difference(self, other):
        other = set(other)
        result = self.__class__(a for a in self if a not in other)
        result.update(a for a in other if a not in self)
        return result

    __xor__ = symmetric_difference

    def difference(self, other):
        other = set(other)
        return self.__class__(a for a in self if a not in other)

    __sub__ = difference

    def intersection_update(self, other):
        other = set(other)
        set.intersection_update(self, other)
        self._list = [a for a in self._list if a in other]
        return self

    __iand__ = intersection_update

    def symmetric_difference_update(self, other):
        set.symmetric_difference_update(self, other)
        self._list = [a for a in self._list if a in self]
        self._list += [a for a in other._list if a in self]
        return self

    __ixor__ = symmetric_difference_update

    def difference_update(self, other):
        set.difference_update(self, other)
        self._list = [a for a in self._list if a in self]
        return self

    __isub__ = difference_update


class IdentitySet(object):
    """A set that considers only object id() for uniqueness.

    This strategy has edge cases for builtin types- it's possible to have
    two 'foo' strings in one of these sets, for example.  Use sparingly.

    """

    def __init__(self, iterable=None):
        self._members = dict()
        if iterable:
            self.update(iterable)

    def add(self, value):
        self._members[id(value)] = value

    def __contains__(self, value):
        return id(value) in self._members

    def remove(self, value):
        del self._members[id(value)]

    def discard(self, value):
        try:
            self.remove(value)
        except KeyError:
            pass

    def pop(self):
        try:
            pair = self._members.popitem()
            return pair[1]
        except KeyError:
            raise KeyError("pop from an empty set")

    def clear(self):
        self._members.clear()

    def __cmp__(self, other):
        raise TypeError("cannot compare sets using cmp()")

    def __eq__(self, other):
        if isinstance(other, IdentitySet):
            return self._members == other._members
        else:
            return False

    def __ne__(self, other):
        if isinstance(other, IdentitySet):
            return self._members != other._members
        else:
            return True

    def issubset(self, iterable):
        if isinstance(iterable, self.__class__):
            other = iterable
        else:
            other = self.__class__(iterable)

        if len(self) > len(other):
            return False
        for m in itertools_filterfalse(
            other._members.__contains__, iter(self._members.keys())
        ):
            return False
        return True

    def __le__(self, other):
        if not isinstance(other, IdentitySet):
            return NotImplemented
        return self.issubset(other)

    def __lt__(self, other):
        if not isinstance(other, IdentitySet):
            return NotImplemented
        return len(self) < len(other) and self.issubset(other)

    def issuperset(self, iterable):
        if isinstance(iterable, self.__class__):
            other = iterable
        else:
            other = self.__class__(iterable)

        if len(self) < len(other):
            return False

        for m in itertools_filterfalse(
            self._members.__contains__, iter(other._members.keys())
        ):
            return False
        return True

    def __ge__(self, other):
        if not isinstance(other, IdentitySet):
            return NotImplemented
        return self.issuperset(other)

    def __gt__(self, other):
        if not isinstance(other, IdentitySet):
            return NotImplemented
        return len(self) > len(other) and self.issuperset(other)

    def union(self, iterable):
        result = self.__class__()
        members = self._members
        result._members.update(members)
        result._members.update((id(obj), obj) for obj in iterable)
        return result

    def __or__(self, other):
        if not isinstance(other, IdentitySet):
            return NotImplemented
        return self.union(other)

    def update(self, iterable):
        self._members.update((id(obj), obj) for obj in iterable)

    def __ior__(self, other):
        if not isinstance(other, IdentitySet):
            return NotImplemented
        self.update(other)
        return self

    def difference(self, iterable):
        result = self.__class__()
        members = self._members
        if isinstance(iterable, self.__class__):
            other = set(iterable._members.keys())
        else:
            other = {id(obj) for obj in iterable}
        result._members.update(((k, v) for k, v in members.items() if k not in other))
        return result

    def __sub__(self, other):
        if not isinstance(other, IdentitySet):
            return NotImplemented
        return self.difference(other)

    def difference_update(self, iterable):
        self._members = self.difference(iterable)._members

    def __isub__(self, other):
        if not isinstance(other, IdentitySet):
            return NotImplemented
        self.difference_update(other)
        return self

    def intersection(self, iterable):
        result = self.__class__()
        members = self._members
        if isinstance(iterable, self.__class__):
            other = set(iterable._members.keys())
        else:
            other = {id(obj) for obj in iterable}
        result._members.update((k, v) for k, v in members.items() if k in other)
        return result

    def __and__(self, other):
        if not isinstance(other, IdentitySet):
            return NotImplemented
        return self.intersection(other)

    def intersection_update(self, iterable):
        self._members = self.intersection(iterable)._members

    def __iand__(self, other):
        if not isinstance(other, IdentitySet):
            return NotImplemented
        self.intersection_update(other)
        return self

    def symmetric_difference(self, iterable):
        result = self.__class__()
        members = self._members
        if isinstance(iterable, self.__class__):
            other = iterable._members
        else:
            other = {id(obj): obj for obj in iterable}
        result._members.update(((k, v) for k, v in members.items() if k not in other))
        result._members.update(((k, v) for k, v in other.items() if k not in members))
        return result

    def __xor__(self, other):
        if not isinstance(other, IdentitySet):
            return NotImplemented
        return self.symmetric_difference(other)

    def symmetric_difference_update(self, iterable):
        self._members = self.symmetric_difference(iterable)._members

    def __ixor__(self, other):
        if not isinstance(other, IdentitySet):
            return NotImplemented
        self.symmetric_difference(other)
        return self

    def copy(self):
        return type(self)(iter(self._members.values()))

    __copy__ = copy

    def __len__(self):
        return len(self._members)

    def __iter__(self):
        return iter(self._members.values())

    def __hash__(self):
        raise TypeError("set objects are unhashable")

    def __repr__(self):
        return "%s(%r)" % (type(self).__name__, list(self._members.values()))


class WeakSequence(object):
    def __init__(self, __elements=()):
        # adapted from weakref.WeakKeyDictionary, prevent reference
        # cycles in the collection itself
        def _remove(item, selfref=weakref.ref(self)):
            self = selfref()
            if self is not None:
                self._storage.remove(item)

        self._remove = _remove
        self._storage = [weakref.ref(element, _remove) for element in __elements]

    def append(self, item):
        self._storage.append(weakref.ref(item, self._remove))

    def __len__(self):
        return len(self._storage)

    def __iter__(self):
        return (obj for obj in (ref() for ref in self._storage) if obj is not None)

    def __getitem__(self, index):
        try:
            obj = self._storage[index]
        except KeyError:
            raise IndexError("Index %s out of range" % index)
        else:
            return obj()


class OrderedIdentitySet(IdentitySet):
    def __init__(self, iterable=None):
        IdentitySet.__init__(self)
        self._members = OrderedDict()
        if iterable:
            for o in iterable:
                self.add(o)


class PopulateDict(dict):
    """A dict which populates missing values via a creation function.

    Note the creation function takes a key, unlike
    collections.defaultdict.

    """

    def __init__(self, creator):
        self.creator = creator

    def __missing__(self, key):
        self[key] = val = self.creator(key)
        return val


class WeakPopulateDict(dict):
    """Like PopulateDict, but assumes a self + a method and does not create
    a reference cycle.

    """

    def __init__(self, creator_method):
        self.creator = creator_method.__func__
        weakself = creator_method.__self__
        self.weakself = weakref.ref(weakself)

    def __missing__(self, key):
        self[key] = val = self.creator(self.weakself(), key)
        return val


# Define collections that are capable of storing
# ColumnElement objects as hashable keys/elements.
# At this point, these are mostly historical, things
# used to be more complicated.
column_set = set
column_dict = dict
ordered_column_set = OrderedSet


_getters = PopulateDict(operator.itemgetter)

_property_getters = PopulateDict(lambda idx: property(operator.itemgetter(idx)))


def unique_list(seq, hashfunc=None):
    seen = set()
    seen_add = seen.add
    if not hashfunc:
        return [x for x in seq if x not in seen and not seen_add(x)]
    else:
        return [x for x in seq if hashfunc(x) not in seen and not seen_add(hashfunc(x))]


class UniqueAppender(object):
    """Appends items to a collection ensuring uniqueness.

    Additional appends() of the same object are ignored.  Membership is
    determined by identity (``is a``) not equality (``==``).
    """

    def __init__(self, data, via=None):
        self.data = data
        self._unique = {}
        if via:
            self._data_appender = getattr(data, via)
        elif hasattr(data, "append"):
            self._data_appender = data.append
        elif hasattr(data, "add"):
            self._data_appender = data.add

    def append(self, item):
        id_ = id(item)
        if id_ not in self._unique:
            self._data_appender(item)
            self._unique[id_] = True

    def __iter__(self):
        return iter(self.data)


def coerce_generator_arg(arg):
    if len(arg) == 1 and isinstance(arg[0], types.GeneratorType):
        return list(arg[0])
    else:
        return arg


def to_list(x, default=None):
    if x is None:
        return default
    if not isinstance(x, collections_abc.Iterable) or isinstance(
        x, string_types + binary_types
    ):
        return [x]
    elif isinstance(x, list):
        return x
    else:
        return list(x)


def has_intersection(set_, iterable):
    r"""return True if any items of set\_ are present in iterable.

    Goes through special effort to ensure __hash__ is not called
    on items in iterable that don't support it.

    """
    # TODO: optimize, write in C, etc.
    return bool(set_.intersection([i for i in iterable if i.__hash__]))


def to_set(x):
    if x is None:
        return set()
    if not isinstance(x, set):
        return set(to_list(x))
    else:
        return x


def to_column_set(x):
    if x is None:
        return column_set()
    if not isinstance(x, column_set):
        return column_set(to_list(x))
    else:
        return x


def update_copy(d, _new=None, **kw):
    """Copy the given dict and update with the given values."""

    d = d.copy()
    if _new:
        d.update(_new)
    d.update(**kw)
    return d


def flatten_iterator(x):
    """Given an iterator of which further sub-elements may also be
    iterators, flatten the sub-elements into a single iterator.

    """
    for elem in x:
        if not isinstance(elem, str) and hasattr(elem, "__iter__"):
            for y in flatten_iterator(elem):
                yield y
        else:
            yield elem


class LRUCache(dict):
    """Dictionary with 'squishy' removal of least
    recently used items.

    Note that either get() or [] should be used here, but
    generally its not safe to do an "in" check first as the dictionary
    can change subsequent to that call.

    """

    __slots__ = "capacity", "threshold", "size_alert", "_counter", "_mutex"

    def __init__(self, capacity=100, threshold=0.5, size_alert=None):
        self.capacity = capacity
        self.threshold = threshold
        self.size_alert = size_alert
        self._counter = 0
        self._mutex = threading.Lock()

    def _inc_counter(self):
        self._counter += 1
        return self._counter

    def get(self, key, default=None):
        item = dict.get(self, key, default)
        if item is not default:
            item[2] = self._inc_counter()
            return item[1]
        else:
            return default

    def __getitem__(self, key):
        item = dict.__getitem__(self, key)
        item[2] = self._inc_counter()
        return item[1]

    def values(self):
        return [i[1] for i in dict.values(self)]

    def setdefault(self, key, value):
        if key in self:
            return self[key]
        else:
            self[key] = value
            return value

    def __setitem__(self, key, value):
        item = dict.get(self, key)
        if item is None:
            item = [key, value, self._inc_counter()]
            dict.__setitem__(self, key, item)
        else:
            item[1] = value
        self._manage_size()

    @property
    def size_threshold(self):
        return self.capacity + self.capacity * self.threshold

    def _manage_size(self):
        if not self._mutex.acquire(False):
            return
        try:
            size_alert = bool(self.size_alert)
            while len(self) > self.capacity + self.capacity * self.threshold:
                if size_alert:
                    size_alert = False
                    self.size_alert(self)
                by_counter = sorted(
                    dict.values(self), key=operator.itemgetter(2), reverse=True
                )
                for item in by_counter[self.capacity :]:
                    try:
                        del self[item[0]]
                    except KeyError:
                        # deleted elsewhere; skip
                        continue
        finally:
            self._mutex.release()


class ScopedRegistry(object):
    """A Registry that can store one or multiple instances of a single
    class on the basis of a "scope" function.

    The object implements ``__call__`` as the "getter", so by
    calling ``myregistry()`` the contained object is returned
    for the current scope.

    :param createfunc:
      a callable that returns a new object to be placed in the registry

    :param scopefunc:
      a callable that will return a key to store/retrieve an object.
    """

    def __init__(self, createfunc, scopefunc):
        """Construct a new :class:`.ScopedRegistry`.

        :param createfunc:  A creation function that will generate
          a new value for the current scope, if none is present.

        :param scopefunc:  A function that returns a hashable
          token representing the current scope (such as, current
          thread identifier).

        """
        self.createfunc = createfunc
        self.scopefunc = scopefunc
        self.registry = {}

    def __call__(self):
        key = self.scopefunc()
        try:
            return self.registry[key]
        except KeyError:
            return self.registry.setdefault(key, self.createfunc())

    def has(self):
        """Return True if an object is present in the current scope."""

        return self.scopefunc() in self.registry

    def set(self, obj):
        """Set the value for the current scope."""

        self.registry[self.scopefunc()] = obj

    def clear(self):
        """Clear the current scope, if any."""

        try:
            del self.registry[self.scopefunc()]
        except KeyError:
            pass


class ThreadLocalRegistry(ScopedRegistry):
    """A :class:`.ScopedRegistry` that uses a ``threading.local()``
    variable for storage.

    """

    def __init__(self, createfunc):
        self.createfunc = createfunc
        self.registry = threading.local()

    def __call__(self):
        try:
            return self.registry.value
        except AttributeError:
            val = self.registry.value = self.createfunc()
            return val

    def has(self):
        return hasattr(self.registry, "value")

    def set(self, obj):
        self.registry.value = obj

    def clear(self):
        try:
            del self.registry.value
        except AttributeError:
            pass


def has_dupes(sequence, target):
    """Given a sequence and search object, return True if there's more
    than one, False if zero or one of them.


    """
    # compare to .index version below, this version introduces less function
    # overhead and is usually the same speed.  At 15000 items (way bigger than
    # a relationship-bound collection in memory usually is) it begins to
    # fall behind the other version only by microseconds.
    c = 0
    for item in sequence:
        if item is target:
            c += 1
            if c > 1:
                return True
    return False


# .index version.  the two __contains__ calls as well
# as .index() and isinstance() slow this down.
# def has_dupes(sequence, target):
#    if target not in sequence:
#        return False
#    elif not isinstance(sequence, collections_abc.Sequence):
#        return False
#
#    idx = sequence.index(target)
#    return target in sequence[idx + 1:]

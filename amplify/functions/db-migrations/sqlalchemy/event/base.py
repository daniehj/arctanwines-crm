# event/base.py
# Copyright (C) 2005-2023 the SQLAlchemy authors and contributors
# <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: https://www.opensource.org/licenses/mit-license.php

"""Base implementation classes.

The public-facing ``Events`` serves as the base class for an event interface;
its public attributes represent different kinds of events.   These attributes
are mirrored onto a ``_Dispatch`` class, which serves as a container for
collections of listener functions.   These collections are represented both
at the class level of a particular ``_Dispatch`` class as well as within
instances of ``_Dispatch``.

"""
from __future__ import absolute_import

import weakref

from .attr import _ClsLevelDispatch
from .attr import _EmptyListener
from .attr import _JoinedListener
from .. import util


_registrars = util.defaultdict(list)


def _is_event_name(name):
    # _sa_event prefix is special to support internal-only event names.
    # most event names are just plain method names that aren't
    # underscored.

    return (not name.startswith("_") and name != "dispatch") or name.startswith(
        "_sa_event"
    )


class _UnpickleDispatch(object):
    """Serializable callable that re-generates an instance of
    :class:`_Dispatch` given a particular :class:`.Events` subclass.

    """

    def __call__(self, _instance_cls):
        for cls in _instance_cls.__mro__:
            if "dispatch" in cls.__dict__:
                return cls.__dict__["dispatch"].dispatch._for_class(_instance_cls)
        else:
            raise AttributeError("No class with a 'dispatch' member present.")


class _Dispatch(object):
    """Mirror the event listening definitions of an Events class with
    listener collections.

    Classes which define a "dispatch" member will return a
    non-instantiated :class:`._Dispatch` subclass when the member
    is accessed at the class level.  When the "dispatch" member is
    accessed at the instance level of its owner, an instance
    of the :class:`._Dispatch` class is returned.

    A :class:`._Dispatch` class is generated for each :class:`.Events`
    class defined, by the :func:`._create_dispatcher_class` function.
    The original :class:`.Events` classes remain untouched.
    This decouples the construction of :class:`.Events` subclasses from
    the implementation used by the event internals, and allows
    inspecting tools like Sphinx to work in an unsurprising
    way against the public API.

    """

    # In one ORM edge case, an attribute is added to _Dispatch,
    # so __dict__ is used in just that case and potentially others.
    __slots__ = "_parent", "_instance_cls", "__dict__", "_empty_listeners"

    _empty_listener_reg = weakref.WeakKeyDictionary()

    def __init__(self, parent, instance_cls=None):
        self._parent = parent
        self._instance_cls = instance_cls

        if instance_cls:
            try:
                self._empty_listeners = self._empty_listener_reg[instance_cls]
            except KeyError:
                self._empty_listeners = self._empty_listener_reg[instance_cls] = {
                    ls.name: _EmptyListener(ls, instance_cls)
                    for ls in parent._event_descriptors
                }
        else:
            self._empty_listeners = {}

    def __getattr__(self, name):
        # Assign EmptyListeners as attributes on demand
        # to reduce startup time for new dispatch objects.
        try:
            ls = self._empty_listeners[name]
        except KeyError:
            raise AttributeError(name)
        else:
            setattr(self, ls.name, ls)
            return ls

    @property
    def _event_descriptors(self):
        for k in self._event_names:
            # Yield _ClsLevelDispatch related
            # to relevant event name.
            yield getattr(self, k)

    @property
    def _listen(self):
        return self._events._listen

    def _for_class(self, instance_cls):
        return self.__class__(self, instance_cls)

    def _for_instance(self, instance):
        instance_cls = instance.__class__
        return self._for_class(instance_cls)

    def _join(self, other):
        """Create a 'join' of this :class:`._Dispatch` and another.

        This new dispatcher will dispatch events to both
        :class:`._Dispatch` objects.

        """
        if "_joined_dispatch_cls" not in self.__class__.__dict__:
            cls = type(
                "Joined%s" % self.__class__.__name__,
                (_JoinedDispatcher,),
                {"__slots__": self._event_names},
            )

            self.__class__._joined_dispatch_cls = cls
        return self._joined_dispatch_cls(self, other)

    def __reduce__(self):
        return _UnpickleDispatch(), (self._instance_cls,)

    def _update(self, other, only_propagate=True):
        """Populate from the listeners in another :class:`_Dispatch`
        object."""
        for ls in other._event_descriptors:
            if isinstance(ls, _EmptyListener):
                continue
            getattr(self, ls.name).for_modify(self)._update(
                ls, only_propagate=only_propagate
            )

    def _clear(self):
        for ls in self._event_descriptors:
            ls.for_modify(self).clear()


class _EventMeta(type):
    """Intercept new Event subclasses and create
    associated _Dispatch classes."""

    def __init__(cls, classname, bases, dict_):
        _create_dispatcher_class(cls, classname, bases, dict_)
        type.__init__(cls, classname, bases, dict_)


def _create_dispatcher_class(cls, classname, bases, dict_):
    """Create a :class:`._Dispatch` class corresponding to an
    :class:`.Events` class."""

    # there's all kinds of ways to do this,
    # i.e. make a Dispatch class that shares the '_listen' method
    # of the Event class, this is the straight monkeypatch.
    if hasattr(cls, "dispatch"):
        dispatch_base = cls.dispatch.__class__
    else:
        dispatch_base = _Dispatch

    event_names = [k for k in dict_ if _is_event_name(k)]
    dispatch_cls = type(
        "%sDispatch" % classname, (dispatch_base,), {"__slots__": event_names}
    )

    dispatch_cls._event_names = event_names

    dispatch_inst = cls._set_dispatch(cls, dispatch_cls)
    for k in dispatch_cls._event_names:
        setattr(dispatch_inst, k, _ClsLevelDispatch(cls, dict_[k]))
        _registrars[k].append(cls)

    for super_ in dispatch_cls.__bases__:
        if issubclass(super_, _Dispatch) and super_ is not _Dispatch:
            for ls in super_._events.dispatch._event_descriptors:
                setattr(dispatch_inst, ls.name, ls)
                dispatch_cls._event_names.append(ls.name)

    if getattr(cls, "_dispatch_target", None):
        the_cls = cls._dispatch_target
        if hasattr(the_cls, "__slots__") and "_slots_dispatch" in the_cls.__slots__:
            cls._dispatch_target.dispatch = slots_dispatcher(cls)
        else:
            cls._dispatch_target.dispatch = dispatcher(cls)


def _remove_dispatcher(cls):
    for k in cls.dispatch._event_names:
        _registrars[k].remove(cls)
        if not _registrars[k]:
            del _registrars[k]


class Events(util.with_metaclass(_EventMeta, object)):
    """Define event listening functions for a particular target type."""

    @staticmethod
    def _set_dispatch(cls, dispatch_cls):
        # This allows an Events subclass to define additional utility
        # methods made available to the target via
        # "self.dispatch._events.<utilitymethod>"
        # @staticmethod to allow easy "super" calls while in a metaclass
        # constructor.
        cls.dispatch = dispatch_cls(None)
        dispatch_cls._events = cls
        return cls.dispatch

    @classmethod
    def _accept_with(cls, target):
        def dispatch_is(*types):
            return all(isinstance(target.dispatch, t) for t in types)

        def dispatch_parent_is(t):
            return isinstance(target.dispatch.parent, t)

        # Mapper, ClassManager, Session override this to
        # also accept classes, scoped_sessions, sessionmakers, etc.
        if hasattr(target, "dispatch"):
            if (
                dispatch_is(cls.dispatch.__class__)
                or dispatch_is(type, cls.dispatch.__class__)
                or (
                    dispatch_is(_JoinedDispatcher)
                    and dispatch_parent_is(cls.dispatch.__class__)
                )
            ):
                return target

    @classmethod
    def _listen(
        cls,
        event_key,
        propagate=False,
        insert=False,
        named=False,
        asyncio=False,
    ):
        event_key.base_listen(
            propagate=propagate, insert=insert, named=named, asyncio=asyncio
        )

    @classmethod
    def _remove(cls, event_key):
        event_key.remove()

    @classmethod
    def _clear(cls):
        cls.dispatch._clear()


class _JoinedDispatcher(object):
    """Represent a connection between two _Dispatch objects."""

    __slots__ = "local", "parent", "_instance_cls"

    def __init__(self, local, parent):
        self.local = local
        self.parent = parent
        self._instance_cls = self.local._instance_cls

    def __getattr__(self, name):
        # Assign _JoinedListeners as attributes on demand
        # to reduce startup time for new dispatch objects.
        ls = getattr(self.local, name)
        jl = _JoinedListener(self.parent, ls.name, ls)
        setattr(self, ls.name, jl)
        return jl

    @property
    def _listen(self):
        return self.parent._listen

    @property
    def _events(self):
        return self.parent._events


class dispatcher(object):
    """Descriptor used by target classes to
    deliver the _Dispatch class at the class level
    and produce new _Dispatch instances for target
    instances.

    """

    def __init__(self, events):
        self.dispatch = events.dispatch
        self.events = events

    def __get__(self, obj, cls):
        if obj is None:
            return self.dispatch

        disp = self.dispatch._for_instance(obj)
        try:
            obj.__dict__["dispatch"] = disp
        except AttributeError as ae:
            util.raise_(
                TypeError(
                    "target %r doesn't have __dict__, should it be "
                    "defining _slots_dispatch?" % (obj,)
                ),
                replace_context=ae,
            )
        return disp


class slots_dispatcher(dispatcher):
    def __get__(self, obj, cls):
        if obj is None:
            return self.dispatch

        if hasattr(obj, "_slots_dispatch"):
            return obj._slots_dispatch

        disp = self.dispatch._for_instance(obj)
        obj._slots_dispatch = disp
        return disp

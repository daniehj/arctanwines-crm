# ext/declarative/clsregistry.py
# Copyright (C) 2005-2023 the SQLAlchemy authors and contributors
# <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: https://www.opensource.org/licenses/mit-license.php
"""Routines to handle the string class registry used by declarative.

This system allows specification of classes and expressions used in
:func:`_orm.relationship` using strings.

"""
import weakref

from . import attributes
from . import interfaces
from .descriptor_props import SynonymProperty
from .properties import ColumnProperty
from .util import class_mapper
from .. import exc
from .. import inspection
from .. import util
from ..sql.schema import _get_table_key

# strong references to registries which we place in
# the _decl_class_registry, which is usually weak referencing.
# the internal registries here link to classes with weakrefs and remove
# themselves when all references to contained classes are removed.
_registries = set()


def add_class(classname, cls, decl_class_registry):
    """Add a class to the _decl_class_registry associated with the
    given declarative class.

    """
    if classname in decl_class_registry:
        # class already exists.
        existing = decl_class_registry[classname]
        if not isinstance(existing, _MultipleClassMarker):
            existing = decl_class_registry[classname] = _MultipleClassMarker(
                [cls, existing]
            )
    else:
        decl_class_registry[classname] = cls

    try:
        root_module = decl_class_registry["_sa_module_registry"]
    except KeyError:
        decl_class_registry["_sa_module_registry"] = root_module = _ModuleMarker(
            "_sa_module_registry", None
        )

    tokens = cls.__module__.split(".")

    # build up a tree like this:
    # modulename:  myapp.snacks.nuts
    #
    # myapp->snack->nuts->(classes)
    # snack->nuts->(classes)
    # nuts->(classes)
    #
    # this allows partial token paths to be used.
    while tokens:
        token = tokens.pop(0)
        module = root_module.get_module(token)
        for token in tokens:
            module = module.get_module(token)
        module.add_class(classname, cls)


def remove_class(classname, cls, decl_class_registry):
    if classname in decl_class_registry:
        existing = decl_class_registry[classname]
        if isinstance(existing, _MultipleClassMarker):
            existing.remove_item(cls)
        else:
            del decl_class_registry[classname]

    try:
        root_module = decl_class_registry["_sa_module_registry"]
    except KeyError:
        return

    tokens = cls.__module__.split(".")

    while tokens:
        token = tokens.pop(0)
        module = root_module.get_module(token)
        for token in tokens:
            module = module.get_module(token)
        module.remove_class(classname, cls)


def _key_is_empty(key, decl_class_registry, test):
    """test if a key is empty of a certain object.

    used for unit tests against the registry to see if garbage collection
    is working.

    "test" is a callable that will be passed an object should return True
    if the given object is the one we were looking for.

    We can't pass the actual object itself b.c. this is for testing garbage
    collection; the caller will have to have removed references to the
    object itself.

    """
    if key not in decl_class_registry:
        return True

    thing = decl_class_registry[key]
    if isinstance(thing, _MultipleClassMarker):
        for sub_thing in thing.contents:
            if test(sub_thing):
                return False
    else:
        return not test(thing)


class _MultipleClassMarker(object):
    """refers to multiple classes of the same name
    within _decl_class_registry.

    """

    __slots__ = "on_remove", "contents", "__weakref__"

    def __init__(self, classes, on_remove=None):
        self.on_remove = on_remove
        self.contents = set([weakref.ref(item, self._remove_item) for item in classes])
        _registries.add(self)

    def remove_item(self, cls):
        self._remove_item(weakref.ref(cls))

    def __iter__(self):
        return (ref() for ref in self.contents)

    def attempt_get(self, path, key):
        if len(self.contents) > 1:
            raise exc.InvalidRequestError(
                'Multiple classes found for path "%s" '
                "in the registry of this declarative "
                "base. Please use a fully module-qualified path."
                % (".".join(path + [key]))
            )
        else:
            ref = list(self.contents)[0]
            cls = ref()
            if cls is None:
                raise NameError(key)
            return cls

    def _remove_item(self, ref):
        self.contents.discard(ref)
        if not self.contents:
            _registries.discard(self)
            if self.on_remove:
                self.on_remove()

    def add_item(self, item):
        # protect against class registration race condition against
        # asynchronous garbage collection calling _remove_item,
        # [ticket:3208]
        modules = set(
            [
                cls.__module__
                for cls in [ref() for ref in self.contents]
                if cls is not None
            ]
        )
        if item.__module__ in modules:
            util.warn(
                "This declarative base already contains a class with the "
                "same class name and module name as %s.%s, and will "
                "be replaced in the string-lookup table."
                % (item.__module__, item.__name__)
            )
        self.contents.add(weakref.ref(item, self._remove_item))


class _ModuleMarker(object):
    """Refers to a module name within
    _decl_class_registry.

    """

    __slots__ = "parent", "name", "contents", "mod_ns", "path", "__weakref__"

    def __init__(self, name, parent):
        self.parent = parent
        self.name = name
        self.contents = {}
        self.mod_ns = _ModNS(self)
        if self.parent:
            self.path = self.parent.path + [self.name]
        else:
            self.path = []
        _registries.add(self)

    def __contains__(self, name):
        return name in self.contents

    def __getitem__(self, name):
        return self.contents[name]

    def _remove_item(self, name):
        self.contents.pop(name, None)
        if not self.contents and self.parent is not None:
            self.parent._remove_item(self.name)
            _registries.discard(self)

    def resolve_attr(self, key):
        return getattr(self.mod_ns, key)

    def get_module(self, name):
        if name not in self.contents:
            marker = _ModuleMarker(name, self)
            self.contents[name] = marker
        else:
            marker = self.contents[name]
        return marker

    def add_class(self, name, cls):
        if name in self.contents:
            existing = self.contents[name]
            existing.add_item(cls)
        else:
            existing = self.contents[name] = _MultipleClassMarker(
                [cls], on_remove=lambda: self._remove_item(name)
            )

    def remove_class(self, name, cls):
        if name in self.contents:
            existing = self.contents[name]
            existing.remove_item(cls)


class _ModNS(object):
    __slots__ = ("__parent",)

    def __init__(self, parent):
        self.__parent = parent

    def __getattr__(self, key):
        try:
            value = self.__parent.contents[key]
        except KeyError:
            pass
        else:
            if value is not None:
                if isinstance(value, _ModuleMarker):
                    return value.mod_ns
                else:
                    assert isinstance(value, _MultipleClassMarker)
                    return value.attempt_get(self.__parent.path, key)
        raise NameError(
            "Module %r has no mapped classes "
            "registered under the name %r" % (self.__parent.name, key)
        )


class _GetColumns(object):
    __slots__ = ("cls",)

    def __init__(self, cls):
        self.cls = cls

    def __getattr__(self, key):
        mp = class_mapper(self.cls, configure=False)
        if mp:
            if key not in mp.all_orm_descriptors:
                raise AttributeError(
                    "Class %r does not have a mapped column named %r" % (self.cls, key)
                )

            desc = mp.all_orm_descriptors[key]
            if desc.extension_type is interfaces.NOT_EXTENSION:
                prop = desc.property
                if isinstance(prop, SynonymProperty):
                    key = prop.name
                elif not isinstance(prop, ColumnProperty):
                    raise exc.InvalidRequestError(
                        "Property %r is not an instance of"
                        " ColumnProperty (i.e. does not correspond"
                        " directly to a Column)." % key
                    )
        return getattr(self.cls, key)


inspection._inspects(_GetColumns)(lambda target: inspection.inspect(target.cls))


class _GetTable(object):
    __slots__ = "key", "metadata"

    def __init__(self, key, metadata):
        self.key = key
        self.metadata = metadata

    def __getattr__(self, key):
        return self.metadata.tables[_get_table_key(key, self.key)]


def _determine_container(key, value):
    if isinstance(value, _MultipleClassMarker):
        value = value.attempt_get([], key)
    return _GetColumns(value)


class _class_resolver(object):
    __slots__ = (
        "cls",
        "prop",
        "arg",
        "fallback",
        "_dict",
        "_resolvers",
        "favor_tables",
    )

    def __init__(self, cls, prop, fallback, arg, favor_tables=False):
        self.cls = cls
        self.prop = prop
        self.arg = arg
        self.fallback = fallback
        self._dict = util.PopulateDict(self._access_cls)
        self._resolvers = ()
        self.favor_tables = favor_tables

    def _access_cls(self, key):
        cls = self.cls

        manager = attributes.manager_of_class(cls)
        decl_base = manager.registry
        decl_class_registry = decl_base._class_registry
        metadata = decl_base.metadata

        if self.favor_tables:
            if key in metadata.tables:
                return metadata.tables[key]
            elif key in metadata._schemas:
                return _GetTable(key, cls.metadata)

        if key in decl_class_registry:
            return _determine_container(key, decl_class_registry[key])

        if not self.favor_tables:
            if key in metadata.tables:
                return metadata.tables[key]
            elif key in metadata._schemas:
                return _GetTable(key, cls.metadata)

        if (
            "_sa_module_registry" in decl_class_registry
            and key in decl_class_registry["_sa_module_registry"]
        ):
            registry = decl_class_registry["_sa_module_registry"]
            return registry.resolve_attr(key)
        elif self._resolvers:
            for resolv in self._resolvers:
                value = resolv(key)
                if value is not None:
                    return value

        return self.fallback[key]

    def _raise_for_name(self, name, err):
        util.raise_(
            exc.InvalidRequestError(
                "When initializing mapper %s, expression %r failed to "
                "locate a name (%r). If this is a class name, consider "
                "adding this relationship() to the %r class after "
                "both dependent classes have been defined."
                % (self.prop.parent, self.arg, name, self.cls)
            ),
            from_=err,
        )

    def _resolve_name(self):
        name = self.arg
        d = self._dict
        rval = None
        try:
            for token in name.split("."):
                if rval is None:
                    rval = d[token]
                else:
                    rval = getattr(rval, token)
        except KeyError as err:
            self._raise_for_name(name, err)
        except NameError as n:
            self._raise_for_name(n.args[0], n)
        else:
            if isinstance(rval, _GetColumns):
                return rval.cls
            else:
                return rval

    def __call__(self):
        try:
            x = eval(self.arg, globals(), self._dict)

            if isinstance(x, _GetColumns):
                return x.cls
            else:
                return x
        except NameError as n:
            self._raise_for_name(n.args[0], n)


_fallback_dict = None


def _resolver(cls, prop):
    global _fallback_dict

    if _fallback_dict is None:
        import sqlalchemy
        from sqlalchemy.orm import foreign, remote

        _fallback_dict = util.immutabledict(sqlalchemy.__dict__).union(
            {"foreign": foreign, "remote": remote}
        )

    def resolve_arg(arg, favor_tables=False):
        return _class_resolver(
            cls, prop, _fallback_dict, arg, favor_tables=favor_tables
        )

    def resolve_name(arg):
        return _class_resolver(cls, prop, _fallback_dict, arg)._resolve_name

    return resolve_name, resolve_arg

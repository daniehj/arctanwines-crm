# ext/associationproxy.py
# Copyright (C) 2005-2023 the SQLAlchemy authors and contributors
# <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: https://www.opensource.org/licenses/mit-license.php

"""Contain the ``AssociationProxy`` class.

The ``AssociationProxy`` is a Python property object which provides
transparent proxied access to the endpoint of an association object.

See the example ``examples/association/proxied_association.py``.

"""
import operator

from .. import exc
from .. import inspect
from .. import orm
from .. import util
from ..orm import collections
from ..orm import interfaces
from ..sql import or_
from ..sql.operators import ColumnOperators


def association_proxy(target_collection, attr, **kw):
    r"""Return a Python property implementing a view of a target
    attribute which references an attribute on members of the
    target.

    The returned value is an instance of :class:`.AssociationProxy`.

    Implements a Python property representing a relationship as a collection
    of simpler values, or a scalar value.  The proxied property will mimic
    the collection type of the target (list, dict or set), or, in the case of
    a one to one relationship, a simple scalar value.

    :param target_collection: Name of the attribute we'll proxy to.
      This attribute is typically mapped by
      :func:`~sqlalchemy.orm.relationship` to link to a target collection, but
      can also be a many-to-one or non-scalar relationship.

    :param attr: Attribute on the associated instance or instances we'll
      proxy for.

      For example, given a target collection of [obj1, obj2], a list created
      by this proxy property would look like [getattr(obj1, *attr*),
      getattr(obj2, *attr*)]

      If the relationship is one-to-one or otherwise uselist=False, then
      simply: getattr(obj, *attr*)

    :param creator: optional.

      When new items are added to this proxied collection, new instances of
      the class collected by the target collection will be created.  For list
      and set collections, the target class constructor will be called with
      the 'value' for the new instance.  For dict types, two arguments are
      passed: key and value.

      If you want to construct instances differently, supply a *creator*
      function that takes arguments as above and returns instances.

      For scalar relationships, creator() will be called if the target is None.
      If the target is present, set operations are proxied to setattr() on the
      associated object.

      If you have an associated object with multiple attributes, you may set
      up multiple association proxies mapping to different attributes.  See
      the unit tests for examples, and for examples of how creator() functions
      can be used to construct the scalar relationship on-demand in this
      situation.

    :param \*\*kw: Passes along any other keyword arguments to
      :class:`.AssociationProxy`.

    """
    return AssociationProxy(target_collection, attr, **kw)


ASSOCIATION_PROXY = util.symbol("ASSOCIATION_PROXY")
"""Symbol indicating an :class:`.InspectionAttr` that's
    of type :class:`.AssociationProxy`.

   Is assigned to the :attr:`.InspectionAttr.extension_type`
   attribute.

"""


class AssociationProxy(interfaces.InspectionAttrInfo):
    """A descriptor that presents a read/write view of an object attribute."""

    is_attribute = True
    extension_type = ASSOCIATION_PROXY

    def __init__(
        self,
        target_collection,
        attr,
        creator=None,
        getset_factory=None,
        proxy_factory=None,
        proxy_bulk_set=None,
        info=None,
        cascade_scalar_deletes=False,
    ):
        """Construct a new :class:`.AssociationProxy`.

        The :func:`.association_proxy` function is provided as the usual
        entrypoint here, though :class:`.AssociationProxy` can be instantiated
        and/or subclassed directly.

        :param target_collection: Name of the collection we'll proxy to,
          usually created with :func:`_orm.relationship`.

        :param attr: Attribute on the collected instances we'll proxy
          for.  For example, given a target collection of [obj1, obj2], a
          list created by this proxy property would look like
          [getattr(obj1, attr), getattr(obj2, attr)]

        :param creator: Optional. When new items are added to this proxied
          collection, new instances of the class collected by the target
          collection will be created.  For list and set collections, the
          target class constructor will be called with the 'value' for the
          new instance.  For dict types, two arguments are passed:
          key and value.

          If you want to construct instances differently, supply a 'creator'
          function that takes arguments as above and returns instances.

        :param cascade_scalar_deletes: when True, indicates that setting
         the proxied value to ``None``, or deleting it via ``del``, should
         also remove the source object.  Only applies to scalar attributes.
         Normally, removing the proxied target will not remove the proxy
         source, as this object may have other state that is still to be
         kept.

         .. versionadded:: 1.3

         .. seealso::

            :ref:`cascade_scalar_deletes` - complete usage example

        :param getset_factory: Optional.  Proxied attribute access is
          automatically handled by routines that get and set values based on
          the `attr` argument for this proxy.

          If you would like to customize this behavior, you may supply a
          `getset_factory` callable that produces a tuple of `getter` and
          `setter` functions.  The factory is called with two arguments, the
          abstract type of the underlying collection and this proxy instance.

        :param proxy_factory: Optional.  The type of collection to emulate is
          determined by sniffing the target collection.  If your collection
          type can't be determined by duck typing or you'd like to use a
          different collection implementation, you may supply a factory
          function to produce those collections.  Only applicable to
          non-scalar relationships.

        :param proxy_bulk_set: Optional, use with proxy_factory.  See
          the _set() method for details.

        :param info: optional, will be assigned to
         :attr:`.AssociationProxy.info` if present.

         .. versionadded:: 1.0.9

        """
        self.target_collection = target_collection
        self.value_attr = attr
        self.creator = creator
        self.getset_factory = getset_factory
        self.proxy_factory = proxy_factory
        self.proxy_bulk_set = proxy_bulk_set
        self.cascade_scalar_deletes = cascade_scalar_deletes

        self.key = "_%s_%s_%s" % (
            type(self).__name__,
            target_collection,
            id(self),
        )
        if info:
            self.info = info

    def __get__(self, obj, class_):
        if class_ is None:
            return self
        inst = self._as_instance(class_, obj)
        if inst:
            return inst.get(obj)

        # obj has to be None here
        # assert obj is None

        return self

    def __set__(self, obj, values):
        class_ = type(obj)
        return self._as_instance(class_, obj).set(obj, values)

    def __delete__(self, obj):
        class_ = type(obj)
        return self._as_instance(class_, obj).delete(obj)

    def for_class(self, class_, obj=None):
        r"""Return the internal state local to a specific mapped class.

        E.g., given a class ``User``::

            class User(Base):
                # ...

                keywords = association_proxy('kws', 'keyword')

        If we access this :class:`.AssociationProxy` from
        :attr:`_orm.Mapper.all_orm_descriptors`, and we want to view the
        target class for this proxy as mapped by ``User``::

            inspect(User).all_orm_descriptors["keywords"].for_class(User).target_class

        This returns an instance of :class:`.AssociationProxyInstance` that
        is specific to the ``User`` class.   The :class:`.AssociationProxy`
        object remains agnostic of its parent class.

        :param class\_: the class that we are returning state for.

        :param obj: optional, an instance of the class that is required
         if the attribute refers to a polymorphic target, e.g. where we have
         to look at the type of the actual destination object to get the
         complete path.

        .. versionadded:: 1.3 - :class:`.AssociationProxy` no longer stores
           any state specific to a particular parent class; the state is now
           stored in per-class :class:`.AssociationProxyInstance` objects.


        """
        return self._as_instance(class_, obj)

    def _as_instance(self, class_, obj):
        try:
            inst = class_.__dict__[self.key + "_inst"]
        except KeyError:
            inst = None

        # avoid exception context
        if inst is None:
            owner = self._calc_owner(class_)
            if owner is not None:
                inst = AssociationProxyInstance.for_proxy(self, owner, obj)
                setattr(class_, self.key + "_inst", inst)
            else:
                inst = None

        if inst is not None and not inst._is_canonical:
            # the AssociationProxyInstance can't be generalized
            # since the proxied attribute is not on the targeted
            # class, only on subclasses of it, which might be
            # different.  only return for the specific
            # object's current value
            return inst._non_canonical_get_for_object(obj)
        else:
            return inst

    def _calc_owner(self, target_cls):
        # we might be getting invoked for a subclass
        # that is not mapped yet, in some declarative situations.
        # save until we are mapped
        try:
            insp = inspect(target_cls)
        except exc.NoInspectionAvailable:
            # can't find a mapper, don't set owner. if we are a not-yet-mapped
            # subclass, we can also scan through __mro__ to find a mapped
            # class, but instead just wait for us to be called again against a
            # mapped class normally.
            return None
        else:
            return insp.mapper.class_manager.class_

    def _default_getset(self, collection_class):
        attr = self.value_attr
        _getter = operator.attrgetter(attr)

        def getter(target):
            return _getter(target) if target is not None else None

        if collection_class is dict:

            def setter(o, k, v):
                setattr(o, attr, v)

        else:

            def setter(o, v):
                setattr(o, attr, v)

        return getter, setter

    def __repr__(self):
        return "AssociationProxy(%r, %r)" % (
            self.target_collection,
            self.value_attr,
        )


class AssociationProxyInstance(object):
    """A per-class object that serves class- and object-specific results.

    This is used by :class:`.AssociationProxy` when it is invoked
    in terms of a specific class or instance of a class, i.e. when it is
    used as a regular Python descriptor.

    When referring to the :class:`.AssociationProxy` as a normal Python
    descriptor, the :class:`.AssociationProxyInstance` is the object that
    actually serves the information.   Under normal circumstances, its presence
    is transparent::

        >>> User.keywords.scalar
        False

    In the special case that the :class:`.AssociationProxy` object is being
    accessed directly, in order to get an explicit handle to the
    :class:`.AssociationProxyInstance`, use the
    :meth:`.AssociationProxy.for_class` method::

        proxy_state = inspect(User).all_orm_descriptors["keywords"].for_class(User)

        # view if proxy object is scalar or not
        >>> proxy_state.scalar
        False

    .. versionadded:: 1.3

    """  # noqa

    def __init__(self, parent, owning_class, target_class, value_attr):
        self.parent = parent
        self.key = parent.key
        self.owning_class = owning_class
        self.target_collection = parent.target_collection
        self.collection_class = None
        self.target_class = target_class
        self.value_attr = value_attr

    target_class = None
    """The intermediary class handled by this
    :class:`.AssociationProxyInstance`.

    Intercepted append/set/assignment events will result
    in the generation of new instances of this class.

    """

    @classmethod
    def for_proxy(cls, parent, owning_class, parent_instance):
        target_collection = parent.target_collection
        value_attr = parent.value_attr
        prop = orm.class_mapper(owning_class).get_property(target_collection)

        # this was never asserted before but this should be made clear.
        if not isinstance(prop, orm.RelationshipProperty):
            util.raise_(
                NotImplementedError(
                    "association proxy to a non-relationship "
                    "intermediary is not supported"
                ),
                replace_context=None,
            )

        target_class = prop.mapper.class_

        try:
            target_assoc = cls._cls_unwrap_target_assoc_proxy(target_class, value_attr)
        except AttributeError:
            # the proxied attribute doesn't exist on the target class;
            # return an "ambiguous" instance that will work on a per-object
            # basis
            return AmbiguousAssociationProxyInstance(
                parent, owning_class, target_class, value_attr
            )
        except Exception as err:
            util.raise_(
                exc.InvalidRequestError(
                    "Association proxy received an unexpected error when "
                    "trying to retreive attribute "
                    '"%s.%s" from '
                    'class "%s": %s'
                    % (
                        target_class.__name__,
                        parent.value_attr,
                        target_class.__name__,
                        err,
                    )
                ),
                from_=err,
            )
        else:
            return cls._construct_for_assoc(
                target_assoc, parent, owning_class, target_class, value_attr
            )

    @classmethod
    def _construct_for_assoc(
        cls, target_assoc, parent, owning_class, target_class, value_attr
    ):
        if target_assoc is not None:
            return ObjectAssociationProxyInstance(
                parent, owning_class, target_class, value_attr
            )

        attr = getattr(target_class, value_attr)
        if not hasattr(attr, "_is_internal_proxy"):
            return AmbiguousAssociationProxyInstance(
                parent, owning_class, target_class, value_attr
            )
        is_object = attr._impl_uses_objects
        if is_object:
            return ObjectAssociationProxyInstance(
                parent, owning_class, target_class, value_attr
            )
        else:
            return ColumnAssociationProxyInstance(
                parent, owning_class, target_class, value_attr
            )

    def _get_property(self):
        return orm.class_mapper(self.owning_class).get_property(self.target_collection)

    @property
    def _comparator(self):
        return self._get_property().comparator

    def __clause_element__(self):
        raise NotImplementedError(
            "The association proxy can't be used as a plain column "
            "expression; it only works inside of a comparison expression"
        )

    @classmethod
    def _cls_unwrap_target_assoc_proxy(cls, target_class, value_attr):
        attr = getattr(target_class, value_attr)
        if isinstance(attr, (AssociationProxy, AssociationProxyInstance)):
            return attr
        return None

    @util.memoized_property
    def _unwrap_target_assoc_proxy(self):
        return self._cls_unwrap_target_assoc_proxy(self.target_class, self.value_attr)

    @property
    def remote_attr(self):
        """The 'remote' class attribute referenced by this
        :class:`.AssociationProxyInstance`.

        .. seealso::

            :attr:`.AssociationProxyInstance.attr`

            :attr:`.AssociationProxyInstance.local_attr`

        """
        return getattr(self.target_class, self.value_attr)

    @property
    def local_attr(self):
        """The 'local' class attribute referenced by this
        :class:`.AssociationProxyInstance`.

        .. seealso::

            :attr:`.AssociationProxyInstance.attr`

            :attr:`.AssociationProxyInstance.remote_attr`

        """
        return getattr(self.owning_class, self.target_collection)

    @property
    def attr(self):
        """Return a tuple of ``(local_attr, remote_attr)``.

        This attribute was originally intended to facilitate using the
        :meth:`_query.Query.join` method to join across the two relationships
        at once, however this makes use of a deprecated calling style.

        To use :meth:`_sql.select.join` or :meth:`_orm.Query.join` with
        an association proxy, the current method is to make use of the
        :attr:`.AssociationProxyInstance.local_attr` and
        :attr:`.AssociationProxyInstance.remote_attr` attributes separately::

            stmt = (
                select(Parent).
                join(Parent.proxied.local_attr).
                join(Parent.proxied.remote_attr)
            )

        A future release may seek to provide a more succinct join pattern
        for association proxy attributes.

        .. seealso::

            :attr:`.AssociationProxyInstance.local_attr`

            :attr:`.AssociationProxyInstance.remote_attr`

        """
        return (self.local_attr, self.remote_attr)

    @util.memoized_property
    def scalar(self):
        """Return ``True`` if this :class:`.AssociationProxyInstance`
        proxies a scalar relationship on the local side."""

        scalar = not self._get_property().uselist
        if scalar:
            self._initialize_scalar_accessors()
        return scalar

    @util.memoized_property
    def _value_is_scalar(self):
        return not self._get_property().mapper.get_property(self.value_attr).uselist

    @property
    def _target_is_object(self):
        raise NotImplementedError()

    def _initialize_scalar_accessors(self):
        if self.parent.getset_factory:
            get, set_ = self.parent.getset_factory(None, self)
        else:
            get, set_ = self.parent._default_getset(None)
        self._scalar_get, self._scalar_set = get, set_

    def _default_getset(self, collection_class):
        attr = self.value_attr
        _getter = operator.attrgetter(attr)

        def getter(target):
            return _getter(target) if target is not None else None

        if collection_class is dict:

            def setter(o, k, v):
                return setattr(o, attr, v)

        else:

            def setter(o, v):
                return setattr(o, attr, v)

        return getter, setter

    @property
    def info(self):
        return self.parent.info

    def get(self, obj):
        if obj is None:
            return self

        if self.scalar:
            target = getattr(obj, self.target_collection)
            return self._scalar_get(target)
        else:
            try:
                # If the owning instance is reborn (orm session resurrect,
                # etc.), refresh the proxy cache.
                creator_id, self_id, proxy = getattr(obj, self.key)
            except AttributeError:
                pass
            else:
                if id(obj) == creator_id and id(self) == self_id:
                    assert self.collection_class is not None
                    return proxy

            self.collection_class, proxy = self._new(
                _lazy_collection(obj, self.target_collection)
            )
            setattr(obj, self.key, (id(obj), id(self), proxy))
            return proxy

    def set(self, obj, values):
        if self.scalar:
            creator = self.parent.creator if self.parent.creator else self.target_class
            target = getattr(obj, self.target_collection)
            if target is None:
                if values is None:
                    return
                setattr(obj, self.target_collection, creator(values))
            else:
                self._scalar_set(target, values)
                if values is None and self.parent.cascade_scalar_deletes:
                    setattr(obj, self.target_collection, None)
        else:
            proxy = self.get(obj)
            assert self.collection_class is not None
            if proxy is not values:
                proxy._bulk_replace(self, values)

    def delete(self, obj):
        if self.owning_class is None:
            self._calc_owner(obj, None)

        if self.scalar:
            target = getattr(obj, self.target_collection)
            if target is not None:
                delattr(target, self.value_attr)
        delattr(obj, self.target_collection)

    def _new(self, lazy_collection):
        creator = self.parent.creator if self.parent.creator else self.target_class
        collection_class = util.duck_type_collection(lazy_collection())

        if self.parent.proxy_factory:
            return (
                collection_class,
                self.parent.proxy_factory(
                    lazy_collection, creator, self.value_attr, self
                ),
            )

        if self.parent.getset_factory:
            getter, setter = self.parent.getset_factory(collection_class, self)
        else:
            getter, setter = self.parent._default_getset(collection_class)

        if collection_class is list:
            return (
                collection_class,
                _AssociationList(lazy_collection, creator, getter, setter, self),
            )
        elif collection_class is dict:
            return (
                collection_class,
                _AssociationDict(lazy_collection, creator, getter, setter, self),
            )
        elif collection_class is set:
            return (
                collection_class,
                _AssociationSet(lazy_collection, creator, getter, setter, self),
            )
        else:
            raise exc.ArgumentError(
                "could not guess which interface to use for "
                'collection_class "%s" backing "%s"; specify a '
                "proxy_factory and proxy_bulk_set manually"
                % (self.collection_class.__name__, self.target_collection)
            )

    def _set(self, proxy, values):
        if self.parent.proxy_bulk_set:
            self.parent.proxy_bulk_set(proxy, values)
        elif self.collection_class is list:
            proxy.extend(values)
        elif self.collection_class is dict:
            proxy.update(values)
        elif self.collection_class is set:
            proxy.update(values)
        else:
            raise exc.ArgumentError(
                "no proxy_bulk_set supplied for custom "
                "collection_class implementation"
            )

    def _inflate(self, proxy):
        creator = self.parent.creator and self.parent.creator or self.target_class

        if self.parent.getset_factory:
            getter, setter = self.parent.getset_factory(self.collection_class, self)
        else:
            getter, setter = self.parent._default_getset(self.collection_class)

        proxy.creator = creator
        proxy.getter = getter
        proxy.setter = setter

    def _criterion_exists(self, criterion=None, **kwargs):
        is_has = kwargs.pop("is_has", None)

        target_assoc = self._unwrap_target_assoc_proxy
        if target_assoc is not None:
            inner = target_assoc._criterion_exists(criterion=criterion, **kwargs)
            return self._comparator._criterion_exists(inner)

        if self._target_is_object:
            prop = getattr(self.target_class, self.value_attr)
            value_expr = prop._criterion_exists(criterion, **kwargs)
        else:
            if kwargs:
                raise exc.ArgumentError(
                    "Can't apply keyword arguments to column-targeted "
                    "association proxy; use =="
                )
            elif is_has and criterion is not None:
                raise exc.ArgumentError(
                    "Non-empty has() not allowed for "
                    "column-targeted association proxy; use =="
                )

            value_expr = criterion

        return self._comparator._criterion_exists(value_expr)

    def any(self, criterion=None, **kwargs):
        """Produce a proxied 'any' expression using EXISTS.

        This expression will be a composed product
        using the :meth:`.RelationshipProperty.Comparator.any`
        and/or :meth:`.RelationshipProperty.Comparator.has`
        operators of the underlying proxied attributes.

        """
        if self._unwrap_target_assoc_proxy is None and (
            self.scalar and (not self._target_is_object or self._value_is_scalar)
        ):
            raise exc.InvalidRequestError(
                "'any()' not implemented for scalar " "attributes. Use has()."
            )
        return self._criterion_exists(criterion=criterion, is_has=False, **kwargs)

    def has(self, criterion=None, **kwargs):
        """Produce a proxied 'has' expression using EXISTS.

        This expression will be a composed product
        using the :meth:`.RelationshipProperty.Comparator.any`
        and/or :meth:`.RelationshipProperty.Comparator.has`
        operators of the underlying proxied attributes.

        """
        if self._unwrap_target_assoc_proxy is None and (
            not self.scalar or (self._target_is_object and not self._value_is_scalar)
        ):
            raise exc.InvalidRequestError(
                "'has()' not implemented for collections.  " "Use any()."
            )
        return self._criterion_exists(criterion=criterion, is_has=True, **kwargs)

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self.parent)


class AmbiguousAssociationProxyInstance(AssociationProxyInstance):
    """an :class:`.AssociationProxyInstance` where we cannot determine
    the type of target object.
    """

    _is_canonical = False

    def _ambiguous(self):
        raise AttributeError(
            "Association proxy %s.%s refers to an attribute '%s' that is not "
            "directly mapped on class %s; therefore this operation cannot "
            "proceed since we don't know what type of object is referred "
            "towards"
            % (
                self.owning_class.__name__,
                self.target_collection,
                self.value_attr,
                self.target_class,
            )
        )

    def get(self, obj):
        if obj is None:
            return self
        else:
            return super(AmbiguousAssociationProxyInstance, self).get(obj)

    def __eq__(self, obj):
        self._ambiguous()

    def __ne__(self, obj):
        self._ambiguous()

    def any(self, criterion=None, **kwargs):
        self._ambiguous()

    def has(self, criterion=None, **kwargs):
        self._ambiguous()

    @util.memoized_property
    def _lookup_cache(self):
        # mapping of <subclass>->AssociationProxyInstance.
        # e.g. proxy is A-> A.b -> B -> B.b_attr, but B.b_attr doesn't exist;
        # only B1(B) and B2(B) have "b_attr", keys in here would be B1, B2
        return {}

    def _non_canonical_get_for_object(self, parent_instance):
        if parent_instance is not None:
            actual_obj = getattr(parent_instance, self.target_collection)
            if actual_obj is not None:
                try:
                    insp = inspect(actual_obj)
                except exc.NoInspectionAvailable:
                    pass
                else:
                    mapper = insp.mapper
                    instance_class = mapper.class_
                    if instance_class not in self._lookup_cache:
                        self._populate_cache(instance_class, mapper)

                    try:
                        return self._lookup_cache[instance_class]
                    except KeyError:
                        pass

        # no object or ambiguous object given, so return "self", which
        # is a proxy with generally only instance-level functionality
        return self

    def _populate_cache(self, instance_class, mapper):
        prop = orm.class_mapper(self.owning_class).get_property(self.target_collection)

        if mapper.isa(prop.mapper):
            target_class = instance_class
            try:
                target_assoc = self._cls_unwrap_target_assoc_proxy(
                    target_class, self.value_attr
                )
            except AttributeError:
                pass
            else:
                self._lookup_cache[instance_class] = self._construct_for_assoc(
                    target_assoc,
                    self.parent,
                    self.owning_class,
                    target_class,
                    self.value_attr,
                )


class ObjectAssociationProxyInstance(AssociationProxyInstance):
    """an :class:`.AssociationProxyInstance` that has an object as a target."""

    _target_is_object = True
    _is_canonical = True

    def contains(self, obj):
        """Produce a proxied 'contains' expression using EXISTS.

        This expression will be a composed product
        using the :meth:`.RelationshipProperty.Comparator.any`,
        :meth:`.RelationshipProperty.Comparator.has`,
        and/or :meth:`.RelationshipProperty.Comparator.contains`
        operators of the underlying proxied attributes.
        """

        target_assoc = self._unwrap_target_assoc_proxy
        if target_assoc is not None:
            return self._comparator._criterion_exists(
                target_assoc.contains(obj)
                if not target_assoc.scalar
                else target_assoc == obj
            )
        elif self._target_is_object and self.scalar and not self._value_is_scalar:
            return self._comparator.has(
                getattr(self.target_class, self.value_attr).contains(obj)
            )
        elif self._target_is_object and self.scalar and self._value_is_scalar:
            raise exc.InvalidRequestError(
                "contains() doesn't apply to a scalar object endpoint; use =="
            )
        else:
            return self._comparator._criterion_exists(**{self.value_attr: obj})

    def __eq__(self, obj):
        # note the has() here will fail for collections; eq_()
        # is only allowed with a scalar.
        if obj is None:
            return or_(
                self._comparator.has(**{self.value_attr: obj}),
                self._comparator == None,
            )
        else:
            return self._comparator.has(**{self.value_attr: obj})

    def __ne__(self, obj):
        # note the has() here will fail for collections; eq_()
        # is only allowed with a scalar.
        return self._comparator.has(getattr(self.target_class, self.value_attr) != obj)


class ColumnAssociationProxyInstance(ColumnOperators, AssociationProxyInstance):
    """an :class:`.AssociationProxyInstance` that has a database column as a
    target.
    """

    _target_is_object = False
    _is_canonical = True

    def __eq__(self, other):
        # special case "is None" to check for no related row as well
        expr = self._criterion_exists(self.remote_attr.operate(operator.eq, other))
        if other is None:
            return or_(expr, self._comparator == None)
        else:
            return expr

    def operate(self, op, *other, **kwargs):
        return self._criterion_exists(self.remote_attr.operate(op, *other, **kwargs))


class _lazy_collection(object):
    def __init__(self, obj, target):
        self.parent = obj
        self.target = target

    def __call__(self):
        return getattr(self.parent, self.target)

    def __getstate__(self):
        return {"obj": self.parent, "target": self.target}

    def __setstate__(self, state):
        self.parent = state["obj"]
        self.target = state["target"]


class _AssociationCollection(object):
    def __init__(self, lazy_collection, creator, getter, setter, parent):
        """Constructs an _AssociationCollection.

        This will always be a subclass of either _AssociationList,
        _AssociationSet, or _AssociationDict.

        lazy_collection
          A callable returning a list-based collection of entities (usually an
          object attribute managed by a SQLAlchemy relationship())

        creator
          A function that creates new target entities.  Given one parameter:
          value.  This assertion is assumed::

            obj = creator(somevalue)
            assert getter(obj) == somevalue

        getter
          A function.  Given an associated object, return the 'value'.

        setter
          A function.  Given an associated object and a value, store that
          value on the object.

        """
        self.lazy_collection = lazy_collection
        self.creator = creator
        self.getter = getter
        self.setter = setter
        self.parent = parent

    col = property(lambda self: self.lazy_collection())

    def __len__(self):
        return len(self.col)

    def __bool__(self):
        return bool(self.col)

    __nonzero__ = __bool__

    def __getstate__(self):
        return {"parent": self.parent, "lazy_collection": self.lazy_collection}

    def __setstate__(self, state):
        self.parent = state["parent"]
        self.lazy_collection = state["lazy_collection"]
        self.parent._inflate(self)

    def _bulk_replace(self, assoc_proxy, values):
        self.clear()
        assoc_proxy._set(self, values)


class _AssociationList(_AssociationCollection):
    """Generic, converting, list-to-list proxy."""

    def _create(self, value):
        return self.creator(value)

    def _get(self, object_):
        return self.getter(object_)

    def _set(self, object_, value):
        return self.setter(object_, value)

    def __getitem__(self, index):
        if not isinstance(index, slice):
            return self._get(self.col[index])
        else:
            return [self._get(member) for member in self.col[index]]

    def __setitem__(self, index, value):
        if not isinstance(index, slice):
            self._set(self.col[index], value)
        else:
            if index.stop is None:
                stop = len(self)
            elif index.stop < 0:
                stop = len(self) + index.stop
            else:
                stop = index.stop
            step = index.step or 1

            start = index.start or 0
            rng = list(range(index.start or 0, stop, step))
            if step == 1:
                for i in rng:
                    del self[start]
                i = start
                for item in value:
                    self.insert(i, item)
                    i += 1
            else:
                if len(value) != len(rng):
                    raise ValueError(
                        "attempt to assign sequence of size %s to "
                        "extended slice of size %s" % (len(value), len(rng))
                    )
                for i, item in zip(rng, value):
                    self._set(self.col[i], item)

    def __delitem__(self, index):
        del self.col[index]

    def __contains__(self, value):
        for member in self.col:
            # testlib.pragma exempt:__eq__
            if self._get(member) == value:
                return True
        return False

    def __getslice__(self, start, end):
        return [self._get(member) for member in self.col[start:end]]

    def __setslice__(self, start, end, values):
        members = [self._create(v) for v in values]
        self.col[start:end] = members

    def __delslice__(self, start, end):
        del self.col[start:end]

    def __iter__(self):
        """Iterate over proxied values.

        For the actual domain objects, iterate over .col instead or
        just use the underlying collection directly from its property
        on the parent.
        """

        for member in self.col:
            yield self._get(member)
        return

    def append(self, value):
        col = self.col
        item = self._create(value)
        col.append(item)

    def count(self, value):
        return sum([1 for _ in util.itertools_filter(lambda v: v == value, iter(self))])

    def extend(self, values):
        for v in values:
            self.append(v)

    def insert(self, index, value):
        self.col[index:index] = [self._create(value)]

    def pop(self, index=-1):
        return self.getter(self.col.pop(index))

    def remove(self, value):
        for i, val in enumerate(self):
            if val == value:
                del self.col[i]
                return
        raise ValueError("value not in list")

    def reverse(self):
        """Not supported, use reversed(mylist)"""

        raise NotImplementedError

    def sort(self):
        """Not supported, use sorted(mylist)"""

        raise NotImplementedError

    def clear(self):
        del self.col[0 : len(self.col)]

    def __eq__(self, other):
        return list(self) == other

    def __ne__(self, other):
        return list(self) != other

    def __lt__(self, other):
        return list(self) < other

    def __le__(self, other):
        return list(self) <= other

    def __gt__(self, other):
        return list(self) > other

    def __ge__(self, other):
        return list(self) >= other

    def __cmp__(self, other):
        return util.cmp(list(self), other)

    def __add__(self, iterable):
        try:
            other = list(iterable)
        except TypeError:
            return NotImplemented
        return list(self) + other

    def __radd__(self, iterable):
        try:
            other = list(iterable)
        except TypeError:
            return NotImplemented
        return other + list(self)

    def __mul__(self, n):
        if not isinstance(n, int):
            return NotImplemented
        return list(self) * n

    __rmul__ = __mul__

    def __iadd__(self, iterable):
        self.extend(iterable)
        return self

    def __imul__(self, n):
        # unlike a regular list *=, proxied __imul__ will generate unique
        # backing objects for each copy.  *= on proxied lists is a bit of
        # a stretch anyhow, and this interpretation of the __imul__ contract
        # is more plausibly useful than copying the backing objects.
        if not isinstance(n, int):
            return NotImplemented
        if n == 0:
            self.clear()
        elif n > 1:
            self.extend(list(self) * (n - 1))
        return self

    def index(self, item, *args):
        return list(self).index(item, *args)

    def copy(self):
        return list(self)

    def __repr__(self):
        return repr(list(self))

    def __hash__(self):
        raise TypeError("%s objects are unhashable" % type(self).__name__)

    for func_name, func in list(locals().items()):
        if (
            callable(func)
            and func.__name__ == func_name
            and not func.__doc__
            and hasattr(list, func_name)
        ):
            func.__doc__ = getattr(list, func_name).__doc__
    del func_name, func


_NotProvided = util.symbol("_NotProvided")


class _AssociationDict(_AssociationCollection):
    """Generic, converting, dict-to-dict proxy."""

    def _create(self, key, value):
        return self.creator(key, value)

    def _get(self, object_):
        return self.getter(object_)

    def _set(self, object_, key, value):
        return self.setter(object_, key, value)

    def __getitem__(self, key):
        return self._get(self.col[key])

    def __setitem__(self, key, value):
        if key in self.col:
            self._set(self.col[key], key, value)
        else:
            self.col[key] = self._create(key, value)

    def __delitem__(self, key):
        del self.col[key]

    def __contains__(self, key):
        # testlib.pragma exempt:__hash__
        return key in self.col

    def has_key(self, key):
        # testlib.pragma exempt:__hash__
        return key in self.col

    def __iter__(self):
        return iter(self.col.keys())

    def clear(self):
        self.col.clear()

    def __eq__(self, other):
        return dict(self) == other

    def __ne__(self, other):
        return dict(self) != other

    def __lt__(self, other):
        return dict(self) < other

    def __le__(self, other):
        return dict(self) <= other

    def __gt__(self, other):
        return dict(self) > other

    def __ge__(self, other):
        return dict(self) >= other

    def __cmp__(self, other):
        return util.cmp(dict(self), other)

    def __repr__(self):
        return repr(dict(self.items()))

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def setdefault(self, key, default=None):
        if key not in self.col:
            self.col[key] = self._create(key, default)
            return default
        else:
            return self[key]

    def keys(self):
        return self.col.keys()

    if util.py2k:

        def iteritems(self):
            return ((key, self._get(self.col[key])) for key in self.col)

        def itervalues(self):
            return (self._get(self.col[key]) for key in self.col)

        def iterkeys(self):
            return self.col.iterkeys()

        def values(self):
            return [self._get(member) for member in self.col.values()]

        def items(self):
            return [(k, self._get(self.col[k])) for k in self]

    else:

        def items(self):
            return ((key, self._get(self.col[key])) for key in self.col)

        def values(self):
            return (self._get(self.col[key]) for key in self.col)

    def pop(self, key, default=_NotProvided):
        if default is _NotProvided:
            member = self.col.pop(key)
        else:
            member = self.col.pop(key, default)
        return self._get(member)

    def popitem(self):
        item = self.col.popitem()
        return (item[0], self._get(item[1]))

    def update(self, *a, **kw):
        if len(a) > 1:
            raise TypeError("update expected at most 1 arguments, got %i" % len(a))
        elif len(a) == 1:
            seq_or_map = a[0]
            # discern dict from sequence - took the advice from
            # https://www.voidspace.org.uk/python/articles/duck_typing.shtml
            # still not perfect :(
            if hasattr(seq_or_map, "keys"):
                for item in seq_or_map:
                    self[item] = seq_or_map[item]
            else:
                try:
                    for k, v in seq_or_map:
                        self[k] = v
                except ValueError as err:
                    util.raise_(
                        ValueError(
                            "dictionary update sequence " "requires 2-element tuples"
                        ),
                        replace_context=err,
                    )

        for key, value in kw:
            self[key] = value

    def _bulk_replace(self, assoc_proxy, values):
        existing = set(self)
        constants = existing.intersection(values or ())
        additions = set(values or ()).difference(constants)
        removals = existing.difference(constants)

        for key, member in values.items() or ():
            if key in additions:
                self[key] = member
            elif key in constants:
                self[key] = member

        for key in removals:
            del self[key]

    def copy(self):
        return dict(self.items())

    def __hash__(self):
        raise TypeError("%s objects are unhashable" % type(self).__name__)

    for func_name, func in list(locals().items()):
        if (
            callable(func)
            and func.__name__ == func_name
            and not func.__doc__
            and hasattr(dict, func_name)
        ):
            func.__doc__ = getattr(dict, func_name).__doc__
    del func_name, func


class _AssociationSet(_AssociationCollection):
    """Generic, converting, set-to-set proxy."""

    def _create(self, value):
        return self.creator(value)

    def _get(self, object_):
        return self.getter(object_)

    def __len__(self):
        return len(self.col)

    def __bool__(self):
        if self.col:
            return True
        else:
            return False

    __nonzero__ = __bool__

    def __contains__(self, value):
        for member in self.col:
            # testlib.pragma exempt:__eq__
            if self._get(member) == value:
                return True
        return False

    def __iter__(self):
        """Iterate over proxied values.

        For the actual domain objects, iterate over .col instead or just use
        the underlying collection directly from its property on the parent.

        """
        for member in self.col:
            yield self._get(member)
        return

    def add(self, value):
        if value not in self:
            self.col.add(self._create(value))

    # for discard and remove, choosing a more expensive check strategy rather
    # than call self.creator()
    def discard(self, value):
        for member in self.col:
            if self._get(member) == value:
                self.col.discard(member)
                break

    def remove(self, value):
        for member in self.col:
            if self._get(member) == value:
                self.col.discard(member)
                return
        raise KeyError(value)

    def pop(self):
        if not self.col:
            raise KeyError("pop from an empty set")
        member = self.col.pop()
        return self._get(member)

    def update(self, other):
        for value in other:
            self.add(value)

    def _bulk_replace(self, assoc_proxy, values):
        existing = set(self)
        constants = existing.intersection(values or ())
        additions = set(values or ()).difference(constants)
        removals = existing.difference(constants)

        appender = self.add
        remover = self.remove

        for member in values or ():
            if member in additions:
                appender(member)
            elif member in constants:
                appender(member)

        for member in removals:
            remover(member)

    def __ior__(self, other):
        if not collections._set_binops_check_strict(self, other):
            return NotImplemented
        for value in other:
            self.add(value)
        return self

    def _set(self):
        return set(iter(self))

    def union(self, other):
        return set(self).union(other)

    __or__ = union

    def difference(self, other):
        return set(self).difference(other)

    __sub__ = difference

    def difference_update(self, other):
        for value in other:
            self.discard(value)

    def __isub__(self, other):
        if not collections._set_binops_check_strict(self, other):
            return NotImplemented
        for value in other:
            self.discard(value)
        return self

    def intersection(self, other):
        return set(self).intersection(other)

    __and__ = intersection

    def intersection_update(self, other):
        want, have = self.intersection(other), set(self)

        remove, add = have - want, want - have

        for value in remove:
            self.remove(value)
        for value in add:
            self.add(value)

    def __iand__(self, other):
        if not collections._set_binops_check_strict(self, other):
            return NotImplemented
        want, have = self.intersection(other), set(self)

        remove, add = have - want, want - have

        for value in remove:
            self.remove(value)
        for value in add:
            self.add(value)
        return self

    def symmetric_difference(self, other):
        return set(self).symmetric_difference(other)

    __xor__ = symmetric_difference

    def symmetric_difference_update(self, other):
        want, have = self.symmetric_difference(other), set(self)

        remove, add = have - want, want - have

        for value in remove:
            self.remove(value)
        for value in add:
            self.add(value)

    def __ixor__(self, other):
        if not collections._set_binops_check_strict(self, other):
            return NotImplemented
        want, have = self.symmetric_difference(other), set(self)

        remove, add = have - want, want - have

        for value in remove:
            self.remove(value)
        for value in add:
            self.add(value)
        return self

    def issubset(self, other):
        return set(self).issubset(other)

    def issuperset(self, other):
        return set(self).issuperset(other)

    def clear(self):
        self.col.clear()

    def copy(self):
        return set(self)

    def __eq__(self, other):
        return set(self) == other

    def __ne__(self, other):
        return set(self) != other

    def __lt__(self, other):
        return set(self) < other

    def __le__(self, other):
        return set(self) <= other

    def __gt__(self, other):
        return set(self) > other

    def __ge__(self, other):
        return set(self) >= other

    def __repr__(self):
        return repr(set(self))

    def __hash__(self):
        raise TypeError("%s objects are unhashable" % type(self).__name__)

    for func_name, func in list(locals().items()):
        if (
            callable(func)
            and func.__name__ == func_name
            and not func.__doc__
            and hasattr(set, func_name)
        ):
            func.__doc__ = getattr(set, func_name).__doc__
    del func_name, func

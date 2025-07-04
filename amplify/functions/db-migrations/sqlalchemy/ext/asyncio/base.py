# ext/asyncio/base.py
# Copyright (C) 2020-2023 the SQLAlchemy authors and contributors
# <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: https://www.opensource.org/licenses/mit-license.php
import abc
import functools
import weakref

from . import exc as async_exc


class ReversibleProxy:
    # weakref.ref(async proxy object) -> weakref.ref(sync proxied object)
    _proxy_objects = {}
    __slots__ = ("__weakref__",)

    def _assign_proxied(self, target):
        if target is not None:
            target_ref = weakref.ref(target, ReversibleProxy._target_gced)
            proxy_ref = weakref.ref(
                self,
                functools.partial(ReversibleProxy._target_gced, target_ref),
            )
            ReversibleProxy._proxy_objects[target_ref] = proxy_ref

        return target

    @classmethod
    def _target_gced(cls, ref, proxy_ref=None):
        cls._proxy_objects.pop(ref, None)

    @classmethod
    def _regenerate_proxy_for_target(cls, target):
        raise NotImplementedError()

    @classmethod
    def _retrieve_proxy_for_target(cls, target, regenerate=True):
        try:
            proxy_ref = cls._proxy_objects[weakref.ref(target)]
        except KeyError:
            pass
        else:
            proxy = proxy_ref()
            if proxy is not None:
                return proxy

        if regenerate:
            return cls._regenerate_proxy_for_target(target)
        else:
            return None


class StartableContext(abc.ABC):
    __slots__ = ()

    @abc.abstractmethod
    async def start(self, is_ctxmanager=False):
        pass

    def __await__(self):
        return self.start().__await__()

    async def __aenter__(self):
        return await self.start(is_ctxmanager=True)

    @abc.abstractmethod
    async def __aexit__(self, type_, value, traceback):
        pass

    def _raise_for_not_started(self):
        raise async_exc.AsyncContextNotStarted(
            "%s context has not been started and object has not been awaited."
            % (self.__class__.__name__)
        )


class ProxyComparable(ReversibleProxy):
    __slots__ = ()

    def __hash__(self):
        return id(self)

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self._proxied == other._proxied

    def __ne__(self, other):
        return not isinstance(other, self.__class__) or self._proxied != other._proxied

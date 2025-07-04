# util/queue.py
# Copyright (C) 2005-2023 the SQLAlchemy authors and contributors
# <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: https://www.opensource.org/licenses/mit-license.php

"""An adaptation of Py2.3/2.4's Queue module which supports reentrant
behavior, using RLock instead of Lock for its mutex object.  The
Queue object is used exclusively by the sqlalchemy.pool.QueuePool
class.

This is to support the connection pool's usage of weakref callbacks to return
connections to the underlying Queue, which can in extremely
rare cases be invoked within the ``get()`` method of the Queue itself,
producing a ``put()`` inside the ``get()`` and therefore a reentrant
condition.

"""

from collections import deque
from time import time as _time

from . import compat
from .compat import threading
from .concurrency import asyncio
from .concurrency import await_fallback
from .concurrency import await_only
from .langhelpers import memoized_property


__all__ = ["Empty", "Full", "Queue"]


class Empty(Exception):
    "Exception raised by Queue.get(block=0)/get_nowait()."

    pass


class Full(Exception):
    "Exception raised by Queue.put(block=0)/put_nowait()."

    pass


class Queue:
    def __init__(self, maxsize=0, use_lifo=False):
        """Initialize a queue object with a given maximum size.

        If `maxsize` is <= 0, the queue size is infinite.

        If `use_lifo` is True, this Queue acts like a Stack (LIFO).
        """

        self._init(maxsize)
        # mutex must be held whenever the queue is mutating.  All methods
        # that acquire mutex must release it before returning.  mutex
        # is shared between the two conditions, so acquiring and
        # releasing the conditions also acquires and releases mutex.
        self.mutex = threading.RLock()
        # Notify not_empty whenever an item is added to the queue; a
        # thread waiting to get is notified then.
        self.not_empty = threading.Condition(self.mutex)
        # Notify not_full whenever an item is removed from the queue;
        # a thread waiting to put is notified then.
        self.not_full = threading.Condition(self.mutex)
        # If this queue uses LIFO or FIFO
        self.use_lifo = use_lifo

    def qsize(self):
        """Return the approximate size of the queue (not reliable!)."""

        with self.mutex:
            return self._qsize()

    def empty(self):
        """Return True if the queue is empty, False otherwise (not
        reliable!)."""

        with self.mutex:
            return self._empty()

    def full(self):
        """Return True if the queue is full, False otherwise (not
        reliable!)."""

        with self.mutex:
            return self._full()

    def put(self, item, block=True, timeout=None):
        """Put an item into the queue.

        If optional args `block` is True and `timeout` is None (the
        default), block if necessary until a free slot is
        available. If `timeout` is a positive number, it blocks at
        most `timeout` seconds and raises the ``Full`` exception if no
        free slot was available within that time.  Otherwise (`block`
        is false), put an item on the queue if a free slot is
        immediately available, else raise the ``Full`` exception
        (`timeout` is ignored in that case).
        """

        with self.not_full:
            if not block:
                if self._full():
                    raise Full
            elif timeout is None:
                while self._full():
                    self.not_full.wait()
            else:
                if timeout < 0:
                    raise ValueError("'timeout' must be a positive number")
                endtime = _time() + timeout
                while self._full():
                    remaining = endtime - _time()
                    if remaining <= 0.0:
                        raise Full
                    self.not_full.wait(remaining)
            self._put(item)
            self.not_empty.notify()

    def put_nowait(self, item):
        """Put an item into the queue without blocking.

        Only enqueue the item if a free slot is immediately available.
        Otherwise raise the ``Full`` exception.
        """
        return self.put(item, False)

    def get(self, block=True, timeout=None):
        """Remove and return an item from the queue.

        If optional args `block` is True and `timeout` is None (the
        default), block if necessary until an item is available. If
        `timeout` is a positive number, it blocks at most `timeout`
        seconds and raises the ``Empty`` exception if no item was
        available within that time.  Otherwise (`block` is false),
        return an item if one is immediately available, else raise the
        ``Empty`` exception (`timeout` is ignored in that case).

        """
        with self.not_empty:
            if not block:
                if self._empty():
                    raise Empty
            elif timeout is None:
                while self._empty():
                    self.not_empty.wait()
            else:
                if timeout < 0:
                    raise ValueError("'timeout' must be a positive number")
                endtime = _time() + timeout
                while self._empty():
                    remaining = endtime - _time()
                    if remaining <= 0.0:
                        raise Empty
                    self.not_empty.wait(remaining)
            item = self._get()
            self.not_full.notify()
            return item

    def get_nowait(self):
        """Remove and return an item from the queue without blocking.

        Only get an item if one is immediately available. Otherwise
        raise the ``Empty`` exception.
        """

        return self.get(False)

    # Override these methods to implement other queue organizations
    # (e.g. stack or priority queue).
    # These will only be called with appropriate locks held

    # Initialize the queue representation
    def _init(self, maxsize):
        self.maxsize = maxsize
        self.queue = deque()

    def _qsize(self):
        return len(self.queue)

    # Check whether the queue is empty
    def _empty(self):
        return not self.queue

    # Check whether the queue is full
    def _full(self):
        return self.maxsize > 0 and len(self.queue) == self.maxsize

    # Put a new item in the queue
    def _put(self, item):
        self.queue.append(item)

    # Get an item from the queue
    def _get(self):
        if self.use_lifo:
            # LIFO
            return self.queue.pop()
        else:
            # FIFO
            return self.queue.popleft()


class AsyncAdaptedQueue:
    await_ = staticmethod(await_only)

    def __init__(self, maxsize=0, use_lifo=False):
        self.use_lifo = use_lifo
        self.maxsize = maxsize

    def empty(self):
        return self._queue.empty()

    def full(self):
        return self._queue.full()

    def qsize(self):
        return self._queue.qsize()

    @memoized_property
    def _queue(self):
        # Delay creation of the queue until it is first used, to avoid
        # binding it to a possibly wrong event loop.
        # By delaying the creation of the pool we accommodate the common
        # usage pattern of instantiating the engine at module level, where a
        # different event loop is in present compared to when the application
        # is actually run.

        if self.use_lifo:
            queue = asyncio.LifoQueue(maxsize=self.maxsize)
        else:
            queue = asyncio.Queue(maxsize=self.maxsize)
        return queue

    def put_nowait(self, item):
        try:
            return self._queue.put_nowait(item)
        except asyncio.QueueFull as err:
            compat.raise_(
                Full(),
                replace_context=err,
            )

    def put(self, item, block=True, timeout=None):
        if not block:
            return self.put_nowait(item)

        try:
            if timeout is not None:
                return self.await_(asyncio.wait_for(self._queue.put(item), timeout))
            else:
                return self.await_(self._queue.put(item))
        except (asyncio.QueueFull, asyncio.TimeoutError) as err:
            compat.raise_(
                Full(),
                replace_context=err,
            )

    def get_nowait(self):
        try:
            return self._queue.get_nowait()
        except asyncio.QueueEmpty as err:
            compat.raise_(
                Empty(),
                replace_context=err,
            )

    def get(self, block=True, timeout=None):
        if not block:
            return self.get_nowait()

        try:
            if timeout is not None:
                return self.await_(asyncio.wait_for(self._queue.get(), timeout))
            else:
                return self.await_(self._queue.get())
        except (asyncio.QueueEmpty, asyncio.TimeoutError) as err:
            compat.raise_(
                Empty(),
                replace_context=err,
            )


class FallbackAsyncAdaptedQueue(AsyncAdaptedQueue):
    await_ = staticmethod(await_fallback)

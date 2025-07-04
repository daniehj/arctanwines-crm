# testing/asyncio.py
# Copyright (C) 2005-2023 the SQLAlchemy authors and contributors
# <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: https://www.opensource.org/licenses/mit-license.php


# functions and wrappers to run tests, fixtures, provisioning and
# setup/teardown in an asyncio event loop, conditionally based on the
# current DB driver being used for a test.

# note that SQLAlchemy's asyncio integration also supports a method
# of running individual asyncio functions inside of separate event loops
# using "async_fallback" mode; however running whole functions in the event
# loop is a more accurate test for how SQLAlchemy's asyncio features
# would run in the real world.


from functools import wraps
import inspect

from . import config
from ..util.concurrency import _util_async_run
from ..util.concurrency import _util_async_run_coroutine_function

# may be set to False if the
# --disable-asyncio flag is passed to the test runner.
ENABLE_ASYNCIO = True


def _run_coroutine_function(fn, *args, **kwargs):
    return _util_async_run_coroutine_function(fn, *args, **kwargs)


def _assume_async(fn, *args, **kwargs):
    """Run a function in an asyncio loop unconditionally.

    This function is used for provisioning features like
    testing a database connection for server info.

    Note that for blocking IO database drivers, this means they block the
    event loop.

    """

    if not ENABLE_ASYNCIO:
        return fn(*args, **kwargs)

    return _util_async_run(fn, *args, **kwargs)


def _maybe_async_provisioning(fn, *args, **kwargs):
    """Run a function in an asyncio loop if any current drivers might need it.

    This function is used for provisioning features that take
    place outside of a specific database driver being selected, so if the
    current driver that happens to be used for the provisioning operation
    is an async driver, it will run in asyncio and not fail.

    Note that for blocking IO database drivers, this means they block the
    event loop.

    """
    if not ENABLE_ASYNCIO:
        return fn(*args, **kwargs)

    if config.any_async:
        return _util_async_run(fn, *args, **kwargs)
    else:
        return fn(*args, **kwargs)


def _maybe_async(fn, *args, **kwargs):
    """Run a function in an asyncio loop if the current selected driver is
    async.

    This function is used for test setup/teardown and tests themselves
    where the current DB driver is known.


    """
    if not ENABLE_ASYNCIO:
        return fn(*args, **kwargs)

    is_async = config._current.is_async

    if is_async:
        return _util_async_run(fn, *args, **kwargs)
    else:
        return fn(*args, **kwargs)


def _maybe_async_wrapper(fn):
    """Apply the _maybe_async function to an existing function and return
    as a wrapped callable, supporting generator functions as well.

    This is currently used for pytest fixtures that support generator use.

    """

    if inspect.isgeneratorfunction(fn):
        _stop = object()

        def call_next(gen):
            try:
                return next(gen)
                # can't raise StopIteration in an awaitable.
            except StopIteration:
                return _stop

        @wraps(fn)
        def wrap_fixture(*args, **kwargs):
            gen = fn(*args, **kwargs)
            while True:
                value = _maybe_async(call_next, gen)
                if value is _stop:
                    break
                yield value

    else:

        @wraps(fn)
        def wrap_fixture(*args, **kwargs):
            return _maybe_async(fn, *args, **kwargs)

    return wrap_fixture

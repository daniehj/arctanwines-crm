# sqlalchemy/pool.py
# Copyright (C) 2005-2023 the SQLAlchemy authors and contributors
# <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: https://www.opensource.org/licenses/mit-license.php


"""Base constructs for connection pools.

"""

from collections import deque
import time
import weakref

from .. import event
from .. import exc
from .. import log
from .. import util


reset_rollback = util.symbol("reset_rollback")
reset_commit = util.symbol("reset_commit")
reset_none = util.symbol("reset_none")


class _ConnDialect(object):
    """partial implementation of :class:`.Dialect`
    which provides DBAPI connection methods.

    When a :class:`_pool.Pool` is combined with an :class:`_engine.Engine`,
    the :class:`_engine.Engine` replaces this with its own
    :class:`.Dialect`.

    """

    is_async = False
    has_terminate = False

    def do_rollback(self, dbapi_connection):
        dbapi_connection.rollback()

    def do_commit(self, dbapi_connection):
        dbapi_connection.commit()

    def do_terminate(self, dbapi_connection):
        dbapi_connection.close()

    def do_close(self, dbapi_connection):
        dbapi_connection.close()

    def do_ping(self, dbapi_connection):
        raise NotImplementedError(
            "The ping feature requires that a dialect is "
            "passed to the connection pool."
        )

    def get_driver_connection(self, connection):
        return connection


class _AsyncConnDialect(_ConnDialect):
    is_async = True


class Pool(log.Identified):

    """Abstract base class for connection pools."""

    _dialect = _ConnDialect()

    def __init__(
        self,
        creator,
        recycle=-1,
        echo=None,
        logging_name=None,
        reset_on_return=True,
        events=None,
        dialect=None,
        pre_ping=False,
        _dispatch=None,
    ):
        """
        Construct a Pool.

        :param creator: a callable function that returns a DB-API
          connection object.  The function will be called with
          parameters.

        :param recycle: If set to a value other than -1, number of
          seconds between connection recycling, which means upon
          checkout, if this timeout is surpassed the connection will be
          closed and replaced with a newly opened connection. Defaults to -1.

        :param logging_name:  String identifier which will be used within
          the "name" field of logging records generated within the
          "sqlalchemy.pool" logger. Defaults to a hexstring of the object's
          id.

        :param echo: if True, the connection pool will log
         informational output such as when connections are invalidated
         as well as when connections are recycled to the default log handler,
         which defaults to ``sys.stdout`` for output..   If set to the string
         ``"debug"``, the logging will include pool checkouts and checkins.

         The :paramref:`_pool.Pool.echo` parameter can also be set from the
         :func:`_sa.create_engine` call by using the
         :paramref:`_sa.create_engine.echo_pool` parameter.

         .. seealso::

             :ref:`dbengine_logging` - further detail on how to configure
             logging.

        :param reset_on_return: Determine steps to take on
         connections as they are returned to the pool, which were
         not otherwise handled by a :class:`_engine.Connection`.
         Available from :func:`_sa.create_engine` via the
         :paramref:`_sa.create_engine.pool_reset_on_return` parameter.

         :paramref:`_pool.Pool.reset_on_return` can have any of these values:

         * ``"rollback"`` - call rollback() on the connection,
           to release locks and transaction resources.
           This is the default value.  The vast majority
           of use cases should leave this value set.
         * ``"commit"`` - call commit() on the connection,
           to release locks and transaction resources.
           A commit here may be desirable for databases that
           cache query plans if a commit is emitted,
           such as Microsoft SQL Server.  However, this
           value is more dangerous than 'rollback' because
           any data changes present on the transaction
           are committed unconditionally.
         * ``None`` - don't do anything on the connection.
           This setting may be appropriate if the database / DBAPI
           works in pure "autocommit" mode at all times, or if
           a custom reset handler is established using the
           :meth:`.PoolEvents.reset` event handler.
         * ``True`` - same as 'rollback', this is here for
           backwards compatibility.
         * ``False`` - same as None, this is here for
           backwards compatibility.

         For further customization of reset on return, the
         :meth:`.PoolEvents.reset` event hook may be used which can perform
         any connection activity desired on reset.  (requires version 1.4.43
         or greater)

         .. seealso::

            :ref:`pool_reset_on_return`

        :param events: a list of 2-tuples, each of the form
         ``(callable, target)`` which will be passed to :func:`.event.listen`
         upon construction.   Provided here so that event listeners
         can be assigned via :func:`_sa.create_engine` before dialect-level
         listeners are applied.

        :param dialect: a :class:`.Dialect` that will handle the job
         of calling rollback(), close(), or commit() on DBAPI connections.
         If omitted, a built-in "stub" dialect is used.   Applications that
         make use of :func:`_sa.create_engine` should not use this parameter
         as it is handled by the engine creation strategy.

         .. versionadded:: 1.1 - ``dialect`` is now a public parameter
            to the :class:`_pool.Pool`.

        :param pre_ping: if True, the pool will emit a "ping" (typically
         "SELECT 1", but is dialect-specific) on the connection
         upon checkout, to test if the connection is alive or not.   If not,
         the connection is transparently re-connected and upon success, all
         other pooled connections established prior to that timestamp are
         invalidated.     Requires that a dialect is passed as well to
         interpret the disconnection error.

         .. versionadded:: 1.2

        """
        if logging_name:
            self.logging_name = self._orig_logging_name = logging_name
        else:
            self._orig_logging_name = None

        log.instance_logger(self, echoflag=echo)
        self._creator = creator
        self._recycle = recycle
        self._invalidate_time = 0
        self._pre_ping = pre_ping
        self._reset_on_return = util.symbol.parse_user_argument(
            reset_on_return,
            {
                reset_rollback: ["rollback", True],
                reset_none: ["none", None, False],
                reset_commit: ["commit"],
            },
            "reset_on_return",
            resolve_symbol_names=False,
        )

        self.echo = echo

        if _dispatch:
            self.dispatch._update(_dispatch, only_propagate=False)
        if dialect:
            self._dialect = dialect
        if events:
            for fn, target in events:
                event.listen(self, target, fn)

    @util.hybridproperty
    def _is_asyncio(self):
        return self._dialect.is_async

    @property
    def _creator(self):
        return self.__dict__["_creator"]

    @_creator.setter
    def _creator(self, creator):
        self.__dict__["_creator"] = creator
        self._invoke_creator = self._should_wrap_creator(creator)

    def _should_wrap_creator(self, creator):
        """Detect if creator accepts a single argument, or is sent
        as a legacy style no-arg function.

        """

        try:
            argspec = util.get_callable_argspec(self._creator, no_self=True)
        except TypeError:
            return lambda crec: creator()

        defaulted = argspec[3] is not None and len(argspec[3]) or 0
        positionals = len(argspec[0]) - defaulted

        # look for the exact arg signature that DefaultStrategy
        # sends us
        if (argspec[0], argspec[3]) == (["connection_record"], (None,)):
            return creator
        # or just a single positional
        elif positionals == 1:
            return creator
        # all other cases, just wrap and assume legacy "creator" callable
        # thing
        else:
            return lambda crec: creator()

    def _close_connection(self, connection, terminate=False):
        self.logger.debug(
            "%s connection %r",
            "Hard-closing" if terminate else "Closing",
            connection,
        )
        try:
            if terminate:
                self._dialect.do_terminate(connection)
            else:
                self._dialect.do_close(connection)
        except BaseException as e:
            self.logger.error(
                "Exception closing connection %r", connection, exc_info=True
            )
            if not isinstance(e, Exception):
                raise

    def _create_connection(self):
        """Called by subclasses to create a new ConnectionRecord."""

        return _ConnectionRecord(self)

    def _invalidate(self, connection, exception=None, _checkin=True):
        """Mark all connections established within the generation
        of the given connection as invalidated.

        If this pool's last invalidate time is before when the given
        connection was created, update the timestamp til now.  Otherwise,
        no action is performed.

        Connections with a start time prior to this pool's invalidation
        time will be recycled upon next checkout.
        """
        rec = getattr(connection, "_connection_record", None)
        if not rec or self._invalidate_time < rec.starttime:
            self._invalidate_time = time.time()
        if _checkin and getattr(connection, "is_valid", False):
            connection.invalidate(exception)

    def recreate(self):
        """Return a new :class:`_pool.Pool`, of the same class as this one
        and configured with identical creation arguments.

        This method is used in conjunction with :meth:`dispose`
        to close out an entire :class:`_pool.Pool` and create a new one in
        its place.

        """

        raise NotImplementedError()

    def dispose(self):
        """Dispose of this pool.

        This method leaves the possibility of checked-out connections
        remaining open, as it only affects connections that are
        idle in the pool.

        .. seealso::

            :meth:`Pool.recreate`

        """

        raise NotImplementedError()

    def connect(self):
        """Return a DBAPI connection from the pool.

        The connection is instrumented such that when its
        ``close()`` method is called, the connection will be returned to
        the pool.

        """
        return _ConnectionFairy._checkout(self)

    def _return_conn(self, record):
        """Given a _ConnectionRecord, return it to the :class:`_pool.Pool`.

        This method is called when an instrumented DBAPI connection
        has its ``close()`` method called.

        """
        self._do_return_conn(record)

    def _do_get(self):
        """Implementation for :meth:`get`, supplied by subclasses."""

        raise NotImplementedError()

    def _do_return_conn(self, conn):
        """Implementation for :meth:`return_conn`, supplied by subclasses."""

        raise NotImplementedError()

    def status(self):
        raise NotImplementedError()


class _ConnectionRecord(object):

    """Internal object which maintains an individual DBAPI connection
    referenced by a :class:`_pool.Pool`.

    The :class:`._ConnectionRecord` object always exists for any particular
    DBAPI connection whether or not that DBAPI connection has been
    "checked out".  This is in contrast to the :class:`._ConnectionFairy`
    which is only a public facade to the DBAPI connection while it is checked
    out.

    A :class:`._ConnectionRecord` may exist for a span longer than that
    of a single DBAPI connection.  For example, if the
    :meth:`._ConnectionRecord.invalidate`
    method is called, the DBAPI connection associated with this
    :class:`._ConnectionRecord`
    will be discarded, but the :class:`._ConnectionRecord` may be used again,
    in which case a new DBAPI connection is produced when the
    :class:`_pool.Pool`
    next uses this record.

    The :class:`._ConnectionRecord` is delivered along with connection
    pool events, including :meth:`_events.PoolEvents.connect` and
    :meth:`_events.PoolEvents.checkout`, however :class:`._ConnectionRecord`
    still
    remains an internal object whose API and internals may change.

    .. seealso::

        :class:`._ConnectionFairy`

    """

    def __init__(self, pool, connect=True):
        self.__pool = pool
        if connect:
            self.__connect()
        self.finalize_callback = deque()

    fresh = False

    fairy_ref = None

    starttime = None

    dbapi_connection = None
    """A reference to the actual DBAPI connection being tracked.

    May be ``None`` if this :class:`._ConnectionRecord` has been marked
    as invalidated; a new DBAPI connection may replace it if the owning
    pool calls upon this :class:`._ConnectionRecord` to reconnect.

    For adapted drivers, like the Asyncio implementations, this is a
    :class:`.AdaptedConnection` that adapts the driver connection
    to the DBAPI protocol.
    Use :attr:`._ConnectionRecord.driver_connection` to obtain the
    connection objected returned by the driver.

    .. versionadded:: 1.4.24

    """

    @property
    def driver_connection(self):
        """The connection object as returned by the driver after a connect.

        For normal sync drivers that support the DBAPI protocol, this object
        is the same as the one referenced by
        :attr:`._ConnectionRecord.dbapi_connection`.

        For adapted drivers, like the Asyncio ones, this is the actual object
        that was returned by the driver ``connect`` call.

        As :attr:`._ConnectionRecord.dbapi_connection` it may be ``None``
        if this :class:`._ConnectionRecord` has been marked as invalidated.

        .. versionadded:: 1.4.24

        """

        if self.dbapi_connection is None:
            return None
        else:
            return self.__pool._dialect.get_driver_connection(self.dbapi_connection)

    @property
    def connection(self):
        """An alias to :attr:`._ConnectionRecord.dbapi_connection`.

        This alias is deprecated, please use the new name.

        .. deprecated:: 1.4.24

        """
        return self.dbapi_connection

    @connection.setter
    def connection(self, value):
        self.dbapi_connection = value

    _soft_invalidate_time = 0

    @util.memoized_property
    def info(self):
        """The ``.info`` dictionary associated with the DBAPI connection.

        This dictionary is shared among the :attr:`._ConnectionFairy.info`
        and :attr:`_engine.Connection.info` accessors.

        .. note::

            The lifespan of this dictionary is linked to the
            DBAPI connection itself, meaning that it is **discarded** each time
            the DBAPI connection is closed and/or invalidated.   The
            :attr:`._ConnectionRecord.record_info` dictionary remains
            persistent throughout the lifespan of the
            :class:`._ConnectionRecord` container.

        """
        return {}

    @util.memoized_property
    def record_info(self):
        """An "info' dictionary associated with the connection record
        itself.

        Unlike the :attr:`._ConnectionRecord.info` dictionary, which is linked
        to the lifespan of the DBAPI connection, this dictionary is linked
        to the lifespan of the :class:`._ConnectionRecord` container itself
        and will remain persistent throughout the life of the
        :class:`._ConnectionRecord`.

        .. versionadded:: 1.1

        """
        return {}

    @classmethod
    def checkout(cls, pool):
        rec = pool._do_get()
        try:
            dbapi_connection = rec.get_connection()
        except BaseException as err:
            with util.safe_reraise():
                rec._checkin_failed(err, _fairy_was_created=False)

            # never called, this is for code linters
            raise

        echo = pool._should_log_debug()
        fairy = _ConnectionFairy(dbapi_connection, rec, echo)

        rec.fairy_ref = ref = weakref.ref(
            fairy,
            lambda ref: _finalize_fairy
            and _finalize_fairy(
                None, rec, pool, ref, echo, transaction_was_reset=False
            ),
        )
        _strong_ref_connection_records[ref] = rec
        if echo:
            pool.logger.debug("Connection %r checked out from pool", dbapi_connection)
        return fairy

    def _checkin_failed(self, err, _fairy_was_created=True):
        self.invalidate(e=err)
        self.checkin(
            _fairy_was_created=_fairy_was_created,
        )

    def checkin(self, _fairy_was_created=True):
        if self.fairy_ref is None and _fairy_was_created:
            # _fairy_was_created is False for the initial get connection phase;
            # meaning there was no _ConnectionFairy and we must unconditionally
            # do a checkin.
            #
            # otherwise, if fairy_was_created==True, if fairy_ref is None here
            # that means we were checked in already, so this looks like
            # a double checkin.
            util.warn("Double checkin attempted on %s" % self)
            return
        self.fairy_ref = None
        connection = self.dbapi_connection
        pool = self.__pool
        while self.finalize_callback:
            finalizer = self.finalize_callback.pop()
            finalizer(connection)
        if pool.dispatch.checkin:
            pool.dispatch.checkin(connection, self)

        pool._return_conn(self)

    @property
    def in_use(self):
        return self.fairy_ref is not None

    @property
    def last_connect_time(self):
        return self.starttime

    def close(self):
        if self.dbapi_connection is not None:
            self.__close()

    def invalidate(self, e=None, soft=False):
        """Invalidate the DBAPI connection held by this
        :class:`._ConnectionRecord`.

        This method is called for all connection invalidations, including
        when the :meth:`._ConnectionFairy.invalidate` or
        :meth:`_engine.Connection.invalidate` methods are called,
        as well as when any
        so-called "automatic invalidation" condition occurs.

        :param e: an exception object indicating a reason for the
          invalidation.

        :param soft: if True, the connection isn't closed; instead, this
          connection will be recycled on next checkout.

         .. versionadded:: 1.0.3

        .. seealso::

            :ref:`pool_connection_invalidation`

        """
        # already invalidated
        if self.dbapi_connection is None:
            return
        if soft:
            self.__pool.dispatch.soft_invalidate(self.dbapi_connection, self, e)
        else:
            self.__pool.dispatch.invalidate(self.dbapi_connection, self, e)
        if e is not None:
            self.__pool.logger.info(
                "%sInvalidate connection %r (reason: %s:%s)",
                "Soft " if soft else "",
                self.dbapi_connection,
                e.__class__.__name__,
                e,
            )
        else:
            self.__pool.logger.info(
                "%sInvalidate connection %r",
                "Soft " if soft else "",
                self.dbapi_connection,
            )

        if soft:
            self._soft_invalidate_time = time.time()
        else:
            self.__close(terminate=True)
            self.dbapi_connection = None

    def get_connection(self):
        recycle = False

        # NOTE: the various comparisons here are assuming that measurable time
        # passes between these state changes.  however, time.time() is not
        # guaranteed to have sub-second precision.  comparisons of
        # "invalidation time" to "starttime" should perhaps use >= so that the
        # state change can take place assuming no measurable  time has passed,
        # however this does not guarantee correct behavior here as if time
        # continues to not pass, it will try to reconnect repeatedly until
        # these timestamps diverge, so in that sense using > is safer.  Per
        # https://stackoverflow.com/a/1938096/34549, Windows time.time() may be
        # within 16 milliseconds accuracy, so unit tests for connection
        # invalidation need a sleep of at least this long between initial start
        # time and invalidation for the logic below to work reliably.
        if self.dbapi_connection is None:
            self.info.clear()
            self.__connect()
        elif (
            self.__pool._recycle > -1
            and time.time() - self.starttime > self.__pool._recycle
        ):
            self.__pool.logger.info(
                "Connection %r exceeded timeout; recycling",
                self.dbapi_connection,
            )
            recycle = True
        elif self.__pool._invalidate_time > self.starttime:
            self.__pool.logger.info(
                "Connection %r invalidated due to pool invalidation; " + "recycling",
                self.dbapi_connection,
            )
            recycle = True
        elif self._soft_invalidate_time > self.starttime:
            self.__pool.logger.info(
                "Connection %r invalidated due to local soft invalidation; "
                + "recycling",
                self.dbapi_connection,
            )
            recycle = True

        if recycle:
            self.__close(terminate=True)
            self.info.clear()

            self.__connect()
        return self.dbapi_connection

    def _is_hard_or_soft_invalidated(self):
        return (
            self.dbapi_connection is None
            or self.__pool._invalidate_time > self.starttime
            or (self._soft_invalidate_time > self.starttime)
        )

    def __close(self, terminate=False):
        self.finalize_callback.clear()
        if self.__pool.dispatch.close:
            self.__pool.dispatch.close(self.dbapi_connection, self)
        self.__pool._close_connection(self.dbapi_connection, terminate=terminate)
        self.dbapi_connection = None

    def __connect(self):
        pool = self.__pool

        # ensure any existing connection is removed, so that if
        # creator fails, this attribute stays None
        self.dbapi_connection = None
        try:
            self.starttime = time.time()
            self.dbapi_connection = connection = pool._invoke_creator(self)
            pool.logger.debug("Created new connection %r", connection)
            self.fresh = True
        except BaseException as e:
            with util.safe_reraise():
                pool.logger.debug("Error on connect(): %s", e)
        else:
            # in SQLAlchemy 1.4 the first_connect event is not used by
            # the engine, so this will usually not be set
            if pool.dispatch.first_connect:
                pool.dispatch.first_connect.for_modify(
                    pool.dispatch
                ).exec_once_unless_exception(self.dbapi_connection, self)

            # init of the dialect now takes place within the connect
            # event, so ensure a mutex is used on the first run
            pool.dispatch.connect.for_modify(pool.dispatch)._exec_w_sync_on_first_run(
                self.dbapi_connection, self
            )


def _finalize_fairy(
    dbapi_connection,
    connection_record,
    pool,
    ref,  # this is None when called directly, not by the gc
    echo,
    transaction_was_reset=False,
    fairy=None,
):
    """Cleanup for a :class:`._ConnectionFairy` whether or not it's already
    been garbage collected.

    When using an async dialect no IO can happen here (without using
    a dedicated thread), since this is called outside the greenlet
    context and with an already running loop. In this case function
    will only log a message and raise a warning.
    """

    if ref:
        _strong_ref_connection_records.pop(ref, None)
    elif fairy:
        _strong_ref_connection_records.pop(weakref.ref(fairy), None)

    if ref is not None:
        if connection_record.fairy_ref is not ref:
            return
        assert dbapi_connection is None
        dbapi_connection = connection_record.dbapi_connection

    # null pool is not _is_asyncio but can be used also with async dialects
    dont_restore_gced = pool._dialect.is_async and not pool._dialect.has_terminate

    if dont_restore_gced:
        detach = not connection_record or ref
        can_manipulate_connection = not ref
    else:
        detach = not connection_record
        can_manipulate_connection = True

    if dbapi_connection is not None:
        if connection_record and echo:
            pool.logger.debug(
                "Connection %r being returned to pool",
                dbapi_connection,
            )

        try:
            fairy = fairy or _ConnectionFairy(
                dbapi_connection,
                connection_record,
                echo,
            )
            assert fairy.dbapi_connection is dbapi_connection
            if can_manipulate_connection:
                fairy._reset(pool, transaction_was_reset)

            if detach:
                if connection_record:
                    fairy._pool = pool
                    fairy.detach()

                if can_manipulate_connection:
                    if pool.dispatch.close_detached:
                        pool.dispatch.close_detached(dbapi_connection)

                    pool._close_connection(dbapi_connection)
                else:
                    message = (
                        "The garbage collector is trying to clean up "
                        "connection %r. This feature is unsupported on "
                        "unsupported on asyncio "
                        'dbapis that lack a "terminate" feature, '
                        "since no IO can be performed at this stage to "
                        "reset the connection. Please close out all "
                        "connections when they are no longer used, calling "
                        "``close()`` or using a context manager to "
                        "manage their lifetime."
                    ) % dbapi_connection
                    pool.logger.error(message)
                    util.warn(message)

        except BaseException as e:
            pool.logger.error("Exception during reset or similar", exc_info=True)
            if connection_record:
                connection_record.invalidate(e=e)
            if not isinstance(e, Exception):
                raise

    if connection_record and connection_record.fairy_ref is not None:
        connection_record.checkin()


# a dictionary of the _ConnectionFairy weakrefs to _ConnectionRecord, so that
# GC under pypy will call ConnectionFairy finalizers.  linked directly to the
# weakref that will empty itself when collected so that it should not create
# any unmanaged memory references.
_strong_ref_connection_records = {}


class _ConnectionFairy(object):

    """Proxies a DBAPI connection and provides return-on-dereference
    support.

    This is an internal object used by the :class:`_pool.Pool` implementation
    to provide context management to a DBAPI connection delivered by
    that :class:`_pool.Pool`.

    The name "fairy" is inspired by the fact that the
    :class:`._ConnectionFairy` object's lifespan is transitory, as it lasts
    only for the length of a specific DBAPI connection being checked out from
    the pool, and additionally that as a transparent proxy, it is mostly
    invisible.

    .. seealso::

        :class:`._ConnectionRecord`

    """

    def __init__(self, dbapi_connection, connection_record, echo):
        self.dbapi_connection = dbapi_connection
        self._connection_record = connection_record
        self._echo = echo

    dbapi_connection = None
    """A reference to the actual DBAPI connection being tracked.

    .. versionadded:: 1.4.24

    .. seealso::

        :attr:`._ConnectionFairy.driver_connection`

        :attr:`._ConnectionRecord.dbapi_connection`

        :ref:`faq_dbapi_connection`

    """

    _connection_record = None
    """A reference to the :class:`._ConnectionRecord` object associated
    with the DBAPI connection.

    This is currently an internal accessor which is subject to change.

    """

    @property
    def driver_connection(self):
        """The connection object as returned by the driver after a connect.

        .. versionadded:: 1.4.24

        .. seealso::

            :attr:`._ConnectionFairy.dbapi_connection`

            :attr:`._ConnectionRecord.driver_connection`

            :ref:`faq_dbapi_connection`

        """
        return self._connection_record.driver_connection

    @property
    def connection(self):
        """An alias to :attr:`._ConnectionFairy.dbapi_connection`.

        This alias is deprecated, please use the new name.

        .. deprecated:: 1.4.24

        """
        return self.dbapi_connection

    @connection.setter
    def connection(self, value):
        self.dbapi_connection = value

    @classmethod
    def _checkout(cls, pool, threadconns=None, fairy=None):
        if not fairy:
            fairy = _ConnectionRecord.checkout(pool)

            fairy._pool = pool
            fairy._counter = 0

            if threadconns is not None:
                threadconns.current = weakref.ref(fairy)

        if fairy.dbapi_connection is None:
            raise exc.InvalidRequestError("This connection is closed")
        fairy._counter += 1
        if (not pool.dispatch.checkout and not pool._pre_ping) or fairy._counter != 1:
            return fairy

        # Pool listeners can trigger a reconnection on checkout, as well
        # as the pre-pinger.
        # there are three attempts made here, but note that if the database
        # is not accessible from a connection standpoint, those won't proceed
        # here.
        attempts = 2

        while attempts > 0:
            connection_is_fresh = fairy._connection_record.fresh
            fairy._connection_record.fresh = False
            try:
                if pool._pre_ping:
                    if not connection_is_fresh:
                        if fairy._echo:
                            pool.logger.debug(
                                "Pool pre-ping on connection %s",
                                fairy.dbapi_connection,
                            )
                        result = pool._dialect.do_ping(fairy.dbapi_connection)
                        if not result:
                            if fairy._echo:
                                pool.logger.debug(
                                    "Pool pre-ping on connection %s failed, "
                                    "will invalidate pool",
                                    fairy.dbapi_connection,
                                )
                            raise exc.InvalidatePoolError()
                    elif fairy._echo:
                        pool.logger.debug(
                            "Connection %s is fresh, skipping pre-ping",
                            fairy.dbapi_connection,
                        )

                pool.dispatch.checkout(
                    fairy.dbapi_connection, fairy._connection_record, fairy
                )
                return fairy
            except exc.DisconnectionError as e:
                if e.invalidate_pool:
                    pool.logger.info(
                        "Disconnection detected on checkout, "
                        "invalidating all pooled connections prior to "
                        "current timestamp (reason: %r)",
                        e,
                    )
                    fairy._connection_record.invalidate(e)
                    pool._invalidate(fairy, e, _checkin=False)
                else:
                    pool.logger.info(
                        "Disconnection detected on checkout, "
                        "invalidating individual connection %s (reason: %r)",
                        fairy.dbapi_connection,
                        e,
                    )
                    fairy._connection_record.invalidate(e)
                try:
                    fairy.dbapi_connection = fairy._connection_record.get_connection()
                except BaseException as err:
                    with util.safe_reraise():
                        fairy._connection_record._checkin_failed(
                            err,
                            _fairy_was_created=True,
                        )

                        # prevent _ConnectionFairy from being carried
                        # in the stack trace.  Do this after the
                        # connection record has been checked in, so that
                        # if the del triggers a finalize fairy, it won't
                        # try to checkin a second time.
                        del fairy

                attempts -= 1
            except BaseException as be_outer:
                with util.safe_reraise():
                    rec = fairy._connection_record
                    if rec is not None:
                        rec._checkin_failed(
                            be_outer,
                            _fairy_was_created=True,
                        )

                    # prevent _ConnectionFairy from being carried
                    # in the stack trace, see above
                    del fairy

                # never called, this is for code linters
                raise

        pool.logger.info("Reconnection attempts exhausted on checkout")
        fairy.invalidate()
        raise exc.InvalidRequestError("This connection is closed")

    def _checkout_existing(self):
        return _ConnectionFairy._checkout(self._pool, fairy=self)

    def _checkin(self, transaction_was_reset=False):
        _finalize_fairy(
            self.dbapi_connection,
            self._connection_record,
            self._pool,
            None,
            self._echo,
            transaction_was_reset=transaction_was_reset,
            fairy=self,
        )
        self.dbapi_connection = None
        self._connection_record = None

    _close = _checkin

    def _reset(self, pool, transaction_was_reset=False):
        if pool.dispatch.reset:
            pool.dispatch.reset(self, self._connection_record)
        if pool._reset_on_return is reset_rollback:
            if transaction_was_reset:
                if self._echo:
                    pool.logger.debug(
                        "Connection %s reset, transaction already reset",
                        self.dbapi_connection,
                    )
            else:
                if self._echo:
                    pool.logger.debug(
                        "Connection %s rollback-on-return",
                        self.dbapi_connection,
                    )
                pool._dialect.do_rollback(self)
        elif pool._reset_on_return is reset_commit:
            if self._echo:
                pool.logger.debug(
                    "Connection %s commit-on-return",
                    self.dbapi_connection,
                )
            pool._dialect.do_commit(self)

    @property
    def _logger(self):
        return self._pool.logger

    @property
    def is_valid(self):
        """Return True if this :class:`._ConnectionFairy` still refers
        to an active DBAPI connection."""

        return self.dbapi_connection is not None

    @util.memoized_property
    def info(self):
        """Info dictionary associated with the underlying DBAPI connection
        referred to by this :class:`.ConnectionFairy`, allowing user-defined
        data to be associated with the connection.

        The data here will follow along with the DBAPI connection including
        after it is returned to the connection pool and used again
        in subsequent instances of :class:`._ConnectionFairy`.  It is shared
        with the :attr:`._ConnectionRecord.info` and
        :attr:`_engine.Connection.info`
        accessors.

        The dictionary associated with a particular DBAPI connection is
        discarded when the connection itself is discarded.

        """
        return self._connection_record.info

    @property
    def record_info(self):
        """Info dictionary associated with the :class:`._ConnectionRecord
        container referred to by this :class:`.ConnectionFairy`.

        Unlike the :attr:`._ConnectionFairy.info` dictionary, the lifespan
        of this dictionary is persistent across connections that are
        disconnected and/or invalidated within the lifespan of a
        :class:`._ConnectionRecord`.

        .. versionadded:: 1.1

        """
        if self._connection_record:
            return self._connection_record.record_info
        else:
            return None

    def invalidate(self, e=None, soft=False):
        """Mark this connection as invalidated.

        This method can be called directly, and is also called as a result
        of the :meth:`_engine.Connection.invalidate` method.   When invoked,
        the DBAPI connection is immediately closed and discarded from
        further use by the pool.  The invalidation mechanism proceeds
        via the :meth:`._ConnectionRecord.invalidate` internal method.

        :param e: an exception object indicating a reason for the invalidation.

        :param soft: if True, the connection isn't closed; instead, this
         connection will be recycled on next checkout.

         .. versionadded:: 1.0.3

        .. seealso::

            :ref:`pool_connection_invalidation`

        """

        if self.dbapi_connection is None:
            util.warn("Can't invalidate an already-closed connection.")
            return
        if self._connection_record:
            self._connection_record.invalidate(e=e, soft=soft)
        if not soft:
            self.dbapi_connection = None
            self._checkin()

    def cursor(self, *args, **kwargs):
        """Return a new DBAPI cursor for the underlying connection.

        This method is a proxy for the ``connection.cursor()`` DBAPI
        method.

        """
        return self.dbapi_connection.cursor(*args, **kwargs)

    def __getattr__(self, key):
        return getattr(self.dbapi_connection, key)

    def detach(self):
        """Separate this connection from its Pool.

        This means that the connection will no longer be returned to the
        pool when closed, and will instead be literally closed.  The
        containing ConnectionRecord is separated from the DB-API connection,
        and will create a new connection when next used.

        Note that any overall connection limiting constraints imposed by a
        Pool implementation may be violated after a detach, as the detached
        connection is removed from the pool's knowledge and control.
        """

        if self._connection_record is not None:
            rec = self._connection_record
            rec.fairy_ref = None
            rec.dbapi_connection = None
            # TODO: should this be _return_conn?
            self._pool._do_return_conn(self._connection_record)
            self.info = self.info.copy()
            self._connection_record = None

            if self._pool.dispatch.detach:
                self._pool.dispatch.detach(self.dbapi_connection, rec)

    def close(self):
        self._counter -= 1
        if self._counter == 0:
            self._checkin()

    def _close_special(self, transaction_reset=False):
        self._counter -= 1
        if self._counter == 0:
            self._checkin(transaction_was_reset=transaction_reset)

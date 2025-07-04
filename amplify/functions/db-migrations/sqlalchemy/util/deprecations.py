# util/deprecations.py
# Copyright (C) 2005-2023 the SQLAlchemy authors and contributors
# <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: https://www.opensource.org/licenses/mit-license.php

"""Helpers related to deprecation of functions, methods, classes, other
functionality."""

import os
import re
import sys

from . import compat
from .langhelpers import _hash_limit_string
from .langhelpers import _warnings_warn
from .langhelpers import decorator
from .langhelpers import inject_docstring_text
from .langhelpers import inject_param_text
from .. import exc


SQLALCHEMY_WARN_20 = False

SILENCE_UBER_WARNING = False

if os.getenv("SQLALCHEMY_WARN_20", "false").lower() in ("true", "yes", "1"):
    SQLALCHEMY_WARN_20 = True

if compat.py2k:
    SILENCE_UBER_WARNING = True
elif os.getenv("SQLALCHEMY_SILENCE_UBER_WARNING", "false").lower() in (
    "true",
    "yes",
    "1",
):
    SILENCE_UBER_WARNING = True


def _warn_with_version(msg, version, type_, stacklevel, code=None):
    if issubclass(type_, exc.Base20DeprecationWarning) and not SQLALCHEMY_WARN_20:
        if not SILENCE_UBER_WARNING:
            _emit_uber_warning(type_, stacklevel)

        return

    warn = type_(msg, code=code)
    warn.deprecated_since = version

    _warnings_warn(warn, stacklevel=stacklevel + 1)


def _emit_uber_warning(type_, stacklevel):
    global SILENCE_UBER_WARNING

    if SILENCE_UBER_WARNING:
        return

    SILENCE_UBER_WARNING = True

    file_ = sys.stderr

    # source: https://github.com/pytest-dev/pytest/blob/326ae0cd88f5e954c8effc2b0c986832e9caff11/src/_pytest/_io/terminalwriter.py#L35-L37  # noqa: E501
    use_color = (
        hasattr(file_, "isatty") and file_.isatty() and os.environ.get("TERM") != "dumb"
    )

    msg = (
        "%(red)sDeprecated API features detected! "
        "These feature(s) are not compatible with SQLAlchemy 2.0. "
        "%(green)sTo prevent incompatible upgrades prior to updating "
        "applications, ensure requirements files are "
        'pinned to "sqlalchemy<2.0". '
        "%(cyan)sSet environment variable SQLALCHEMY_WARN_20=1 to show all "
        "deprecation warnings.  Set environment variable "
        "SQLALCHEMY_SILENCE_UBER_WARNING=1 to silence this message.%(nocolor)s"
    )

    if use_color:
        msg = msg % {
            "red": "\x1b[31m",
            "cyan": "\x1b[36m",
            "green": "\x1b[32m",
            "magenta": "\x1b[35m",
            "nocolor": "\x1b[0m",
        }
    else:
        msg = msg % {
            "red": "",
            "cyan": "",
            "green": "",
            "magenta": "",
            "nocolor": "",
        }

    # note this is a exc.Base20DeprecationWarning subclass, which
    # will implicitly add the link to the SQLAlchemy 2.0 page in the message
    warn = type_(msg)
    _warnings_warn(warn, stacklevel=stacklevel + 1)


def warn_deprecated(msg, version, stacklevel=3, code=None):
    _warn_with_version(msg, version, exc.SADeprecationWarning, stacklevel, code=code)


def warn_deprecated_limited(msg, args, version, stacklevel=3, code=None):
    """Issue a deprecation warning with a parameterized string,
    limiting the number of registrations.

    """
    if args:
        msg = _hash_limit_string(msg, 10, args)
    _warn_with_version(msg, version, exc.SADeprecationWarning, stacklevel, code=code)


def warn_deprecated_20(msg, stacklevel=3, code=None):
    _warn_with_version(
        msg,
        exc.RemovedIn20Warning.deprecated_since,
        exc.RemovedIn20Warning,
        stacklevel,
        code=code,
    )


def deprecated_cls(version, message, constructor="__init__"):
    header = ".. deprecated:: %s %s" % (version, (message or ""))

    def decorate(cls):
        return _decorate_cls_with_warning(
            cls,
            constructor,
            exc.SADeprecationWarning,
            message % dict(func=constructor),
            version,
            header,
        )

    return decorate


def deprecated_20_cls(
    clsname, alternative=None, constructor="__init__", becomes_legacy=False
):
    message = (
        ".. deprecated:: 1.4 The %s class is considered legacy as of the "
        "1.x series of SQLAlchemy and %s in 2.0."
        % (
            clsname,
            "will be removed" if not becomes_legacy else "becomes a legacy construct",
        )
    )

    if alternative:
        message += " " + alternative

    if becomes_legacy:
        warning_cls = exc.LegacyAPIWarning
    else:
        warning_cls = exc.RemovedIn20Warning

    def decorate(cls):
        return _decorate_cls_with_warning(
            cls,
            constructor,
            warning_cls,
            message,
            warning_cls.deprecated_since,
            message,
        )

    return decorate


def deprecated(
    version,
    message=None,
    add_deprecation_to_docstring=True,
    warning=None,
    enable_warnings=True,
):
    """Decorates a function and issues a deprecation warning on use.

    :param version:
      Issue version in the warning.

    :param message:
      If provided, issue message in the warning.  A sensible default
      is used if not provided.

    :param add_deprecation_to_docstring:
      Default True.  If False, the wrapped function's __doc__ is left
      as-is.  If True, the 'message' is prepended to the docs if
      provided, or sensible default if message is omitted.

    """

    # nothing is deprecated "since" 2.0 at this time.  All "removed in 2.0"
    # should emit the RemovedIn20Warning, but messaging should be expressed
    # in terms of "deprecated since 1.4".

    if version == "2.0":
        if warning is None:
            warning = exc.RemovedIn20Warning
        version = "1.4"
    if add_deprecation_to_docstring:
        header = ".. deprecated:: %s %s" % (
            version,
            (message or ""),
        )
    else:
        header = None

    if message is None:
        message = "Call to deprecated function %(func)s"

    if warning is None:
        warning = exc.SADeprecationWarning

    if warning is not exc.RemovedIn20Warning:
        message += " (deprecated since: %s)" % version

    def decorate(fn):
        return _decorate_with_warning(
            fn,
            warning,
            message % dict(func=fn.__name__),
            version,
            header,
            enable_warnings=enable_warnings,
        )

    return decorate


def moved_20(message, **kw):
    return deprecated("2.0", message=message, warning=exc.MovedIn20Warning, **kw)


def deprecated_20(api_name, alternative=None, becomes_legacy=False, **kw):
    type_reg = re.match("^:(attr|func|meth):", api_name)
    if type_reg:
        type_ = {"attr": "attribute", "func": "function", "meth": "method"}[
            type_reg.group(1)
        ]
    else:
        type_ = "construct"
    message = (
        "The %s %s is considered legacy as of the "
        "1.x series of SQLAlchemy and %s in 2.0."
        % (
            api_name,
            type_,
            "will be removed" if not becomes_legacy else "becomes a legacy construct",
        )
    )

    if ":attr:" in api_name:
        attribute_ok = kw.pop("warn_on_attribute_access", False)
        if not attribute_ok:
            assert kw.get("enable_warnings") is False, (
                "attribute %s will emit a warning on read access.  "
                "If you *really* want this, "
                "add warn_on_attribute_access=True.  Otherwise please add "
                "enable_warnings=False." % api_name
            )

    if alternative:
        message += " " + alternative

    if becomes_legacy:
        warning_cls = exc.LegacyAPIWarning
    else:
        warning_cls = exc.RemovedIn20Warning

    return deprecated("2.0", message=message, warning=warning_cls, **kw)


def deprecated_params(**specs):
    """Decorates a function to warn on use of certain parameters.

    e.g. ::

        @deprecated_params(
            weak_identity_map=(
                "0.7",
                "the :paramref:`.Session.weak_identity_map parameter "
                "is deprecated."
            )

        )

    """

    messages = {}
    versions = {}
    version_warnings = {}

    for param, (version, message) in specs.items():
        versions[param] = version
        messages[param] = _sanitize_restructured_text(message)
        version_warnings[param] = (
            exc.RemovedIn20Warning if version == "2.0" else exc.SADeprecationWarning
        )

    def decorate(fn):
        spec = compat.inspect_getfullargspec(fn)

        if spec.defaults is not None:
            defaults = dict(
                zip(
                    spec.args[(len(spec.args) - len(spec.defaults)) :],
                    spec.defaults,
                )
            )
            check_defaults = set(defaults).intersection(messages)
            check_kw = set(messages).difference(defaults)
        else:
            check_defaults = ()
            check_kw = set(messages)

        check_any_kw = spec.varkw

        @decorator
        def warned(fn, *args, **kwargs):
            for m in check_defaults:
                if (defaults[m] is None and kwargs[m] is not None) or (
                    defaults[m] is not None and kwargs[m] != defaults[m]
                ):
                    _warn_with_version(
                        messages[m],
                        versions[m],
                        version_warnings[m],
                        stacklevel=3,
                    )

            if check_any_kw in messages and set(kwargs).difference(check_defaults):
                _warn_with_version(
                    messages[check_any_kw],
                    versions[check_any_kw],
                    version_warnings[check_any_kw],
                    stacklevel=3,
                )

            for m in check_kw:
                if m in kwargs:
                    _warn_with_version(
                        messages[m],
                        versions[m],
                        version_warnings[m],
                        stacklevel=3,
                    )
            return fn(*args, **kwargs)

        doc = fn.__doc__ is not None and fn.__doc__ or ""
        if doc:
            doc = inject_param_text(
                doc,
                {
                    param: ".. deprecated:: %s %s"
                    % ("1.4" if version == "2.0" else version, (message or ""))
                    for param, (version, message) in specs.items()
                },
            )
        decorated = warned(fn)
        decorated.__doc__ = doc
        return decorated

    return decorate


def _sanitize_restructured_text(text):
    def repl(m):
        type_, name = m.group(1, 2)
        if type_ in ("func", "meth"):
            name += "()"
        return name

    text = re.sub(r":ref:`(.+) <.*>`", lambda m: '"%s"' % m.group(1), text)
    return re.sub(r"\:(\w+)\:`~?(?:_\w+)?\.?(.+?)`", repl, text)


def _decorate_cls_with_warning(
    cls, constructor, wtype, message, version, docstring_header=None
):
    doc = cls.__doc__ is not None and cls.__doc__ or ""
    if docstring_header is not None:
        if constructor is not None:
            docstring_header %= dict(func=constructor)

        if issubclass(wtype, exc.Base20DeprecationWarning):
            docstring_header += (
                " (Background on SQLAlchemy 2.0 at: " ":ref:`migration_20_toplevel`)"
            )
        doc = inject_docstring_text(doc, docstring_header, 1)

        if type(cls) is type:
            clsdict = dict(cls.__dict__)
            clsdict["__doc__"] = doc
            clsdict.pop("__dict__", None)
            clsdict.pop("__weakref__", None)
            cls = type(cls.__name__, cls.__bases__, clsdict)
            if constructor is not None:
                constructor_fn = clsdict[constructor]

        else:
            cls.__doc__ = doc
            if constructor is not None:
                constructor_fn = getattr(cls, constructor)

        if constructor is not None:
            setattr(
                cls,
                constructor,
                _decorate_with_warning(constructor_fn, wtype, message, version, None),
            )
    return cls


def _decorate_with_warning(
    func, wtype, message, version, docstring_header=None, enable_warnings=True
):
    """Wrap a function with a warnings.warn and augmented docstring."""

    message = _sanitize_restructured_text(message)

    if issubclass(wtype, exc.Base20DeprecationWarning):
        doc_only = " (Background on SQLAlchemy 2.0 at: " ":ref:`migration_20_toplevel`)"
    else:
        doc_only = ""

    @decorator
    def warned(fn, *args, **kwargs):
        skip_warning = not enable_warnings or kwargs.pop("_sa_skip_warning", False)
        if not skip_warning:
            _warn_with_version(message, version, wtype, stacklevel=3)
        return fn(*args, **kwargs)

    doc = func.__doc__ is not None and func.__doc__ or ""
    if docstring_header is not None:
        docstring_header %= dict(func=func.__name__)

        docstring_header += doc_only

        doc = inject_docstring_text(doc, docstring_header, 1)

    decorated = warned(func)
    decorated.__doc__ = doc
    decorated._sa_warn = lambda: _warn_with_version(
        message, version, wtype, stacklevel=3
    )
    return decorated

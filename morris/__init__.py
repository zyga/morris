# Copyright 2012-2014 Canonical Ltd.
# Written by:
#   Zygmunt Krynicki <zygmunt.krynicki@canonical.com>
#
# This file is part of Morris.
#
# Morris is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License.
#
# Morris is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Morris.  If not, see <http://www.gnu.org/licenses/>.

"""
:mod:`morris` --  announcement (signal/event) system for Python
===============================================================

This module defines three objects:

    The :class:`Signal` class:
        This class is contains APIs for interacting with existing signals.

    The :class:`signal` function / method decorator descriptor class:
        This class can be used as a function or method decorator to define
        as signal with the same name and a first responder.

    The :class:`SignalTestCase` base class for unit tests that simplify working
    with signals and signal events (firing signals)

Defining Signals
----------------

You can import the ``Signal`` class and use idiomatic code like::

    from morris import Signal

    class Foo(object):  # NOTE: classic python 2.x classes are not supported

        @Signal.define
        def on_foo(self):
            pass

    @Signal.define
    on_bar():
        pass

Or use the ``signal`` decorator directly::

    from morris import signal

    class Foo(object):  # NOTE: classic python 2.x classes are not supported

        @signal
        def on_foo(self):
            pass

    @signal
    on_bar():
        pass


Both declarations are identical and result in identical runtime behavior.
``Signal`` is less likely to clash with a function or module from the standard
library but ``signal`` is shorter. Use whichever you prefer.


Connecting signal listeners
---------------------------

Connecting signals is equally easy. Just use the :meth:`Signal.connect()` and
:meth:`Signal.disconnect` with a listener object::

    @signal
    def on_bar():
        pass


    def bar_handler():
        pass

    on_bar.connect(bar_handler)
    on_bar.disconnect(bar_handler)


Firing signals
--------------

To fire a signal simply *call* the signal object::

    @signal
    def on_bar():
        pass

    on_bar()  # fired!

Typically you will want to pass some additional arguments. Both positional
and keyword arguments are supported::

    @signal
    def on_bar_with_args(arg1, arg2):
        pass

    on_bar_with_args('foo', arg2='bar')  # fired!

If you are working in a tight loop it is slightly faster to construct the list
of positional arguments and the dictionary of keyword arguments and call the
:meth:`Signal.fire()` method directly::

    args = ('foo')
    kwargs = {'arg2': 'bar'}
    for i in range(10000):
        on_bar_with_args.fire(args, kwargs)  # fired!

Threading considerations
------------------------

Morris doesn't do anything related to threads. Threading is diverse enough that
for now it was better to just let uses handle it. There are two things that
are worth mentioning though:

1) :meth:`Signal.connect()` and :meth:`Signal.disconnect()` should be safe to
   call concurrently with :meth:`Signal.fire()` since fire() operates on
   a *copy* of the list of listeners

2) Event handlers are called from the thread calling :meth:`Signal.fire()`,
   not from the thread that was used to connect to the signal handler. If you
   need special provisions for working with signals in a specific thread
   consider calling a thread-library-specific function that calls a callable
   in a specific thread context.
"""

from __future__ import print_function, absolute_import, unicode_literals

import collections
import inspect
import logging
import unittest

__author__ = 'Zygmunt Krynicki'
__email__ = 'zygmunt.krynicki@canonical.com'
__version__ = '1.0'
__all__ = ['Signal', 'signal', 'SignalTestCase']

_logger = logging.getLogger("morris")


listenerinfo = collections.namedtuple('listenerinfo', 'listener pass_signal')


class Signal(object):
    """
    Basic signal that supports arbitrary listeners.

    While this class can be used directly it is best used with the helper
    decorator Signal.define on a function or method. See the documentation
    for the :mod:`morris` module for details.
    """

    def __init__(self, name):
        """
        Construct a signal with the given name
        """
        self._name = name
        self._listeners = []

    def __repr__(self):
        return "<Signal name:{!r}>".format(self._name)

    @property
    def name(self):
        """
        Name of the signal

        For signals constructed manually (i.e. by calling :class:`Signal()`)
        the name is arbitrary. For signals constructed using either
        :meth:`Signal.define()` or :class:`signal` the name is obtained
        from the decorated function.

        On python 3.3+ the qualified name is used (see :pep:`3155`), on earlier
        versions the plain name is used (without the class name)
        """
        return self._name

    @property
    def listeners(self):
        """
        List of :class:`listenerinfo` objects associated with this signal

        The list of listeners is considered part of an implementation detail
        but is exposed for convenience. This is always the real list. Keep
        this in mind while connecting and disconnecting listeners. During
        the time :meth:`fire()` is called the list of listeners can be changed
        but won't take effect until after ``fire()`` returns.
        """
        return self._listeners

    def connect(self, listener, pass_signal=False):
        """
        Connect a new listener to this signal

        :param listener:
            The listener (callable) to add
        :param pass_signal:
            An optional argument that controls if the signal object is
            explicitly passed to this listener when it is being fired.
            If enabled, a ``signal=`` keyword argument is passed to the
            listener function.
        :returns:
            None

        The listener will be called whenever fire() is invoked on the signal.
        The listener is appended to the list of listeners. Duplicates are not
        checked and if a listener is added twice it gets called twice.
        """
        info = listenerinfo(listener, pass_signal)
        self._listeners.append(info)
        _logger.debug("connect %r to %r", str(listener), self._name)
        # Track listeners in the instances only
        if inspect.ismethod(listener):
            listener_object = listener.__self__
            # Ensure that the instance has __listeners__ property
            if not hasattr(listener_object, "__listeners__"):
                listener_object.__listeners__ = collections.defaultdict(list)
            # Append the signals a listener is connected to
            listener_object.__listeners__[listener].append(self)

    def disconnect(self, listener, pass_signal=False):
        """
        Disconnect an existing listener from this signal

        :param listener:
            The listener (callable) to remove
        :param pass_signal:
            An optional argument that controls if the signal object is
            explicitly passed to this listener when it is being fired.
            If enabled, a ``signal=`` keyword argument is passed to the
            listener function.

            Here, this argument simply aids in disconnecting the right
            listener. Make sure to pass the same value as was passed to
            :meth:`connect()`
        :raises ValueError:
            If the listener (with the same value of pass_signal) is not present
        :returns:
            None
        """
        info = listenerinfo(listener, pass_signal)
        self._listeners.remove(info)
        _logger.debug(
            "disconnect %r from %r", str(listener), self._name)
        if inspect.ismethod(listener):
            listener_object = listener.__self__
            if hasattr(listener_object, "__listeners__"):
                listener_object.__listeners__[listener].remove(self)
                # Remove the listener from the list if any signals connected
                if (len(listener_object.__listeners__[listener])) == 0:
                    del listener_object.__listeners__[listener]

    def fire(self, args, kwargs):
        """
        Fire this signal with the specified arguments and keyword arguments.

        Typically this is used by using :meth:`__call__()` on this object which
        is more natural as it does all the argument packing/unpacking
        transparently.
        """
        for info in self._listeners[:]:
            if info.pass_signal:
                info.listener(*args, signal=self, **kwargs)
            else:
                info.listener(*args, **kwargs)

    def __call__(self, *args, **kwargs):
        """
        Call fire() with all arguments forwarded transparently

        This is provided for convenience so that a signal can be fired just
        by a simple method or function call and so that signals can be passed
        to other APIs that don't understand the :meth:`fire()` method.
        """
        self.fire(args, kwargs)

    @classmethod
    def define(cls, first_responder):
        """
        Helper decorator to define a signal descriptor in a class

        The decorated function is used as the first responder of the newly
        defined signal. The signal also inherits the docstring from
        decorated the function.
        """
        return signal(first_responder)


class boundmethod(object):
    """
    A helper class that allows us to emulate a bound method

    This class emulates a bond method by storing an object ``instance``,
    function ``func`` and calling ``instance``.``func``() whenever the
    boundmethod object itself is called.
    """

    def __init__(self, instance, func):
        self.instance = instance
        self.func = func

    def __call__(self, *args, **kwargs):
        return self.func(self.instance, *args, **kwargs)


class signal(object):
    """
    Descriptor for convenient signal access.

    Typically this class is used indirectly, when accessed from Signal.define
    method decorator. It is used to do all the magic required when accessing
    signal name on a class or instance.
    """

    def __init__(self, first_responder):
        if hasattr(first_responder, '__qualname__'):
            self._name = first_responder.__qualname__
        else:
            self._name = first_responder.__name__
        self.first_responder = first_responder
        self.__doc__ = first_responder.__doc__

    def __repr__(self):
        return "<signal for Signal:{!r}>".format(self._name)

    def __get__(self, instance, owner):
        if instance is None:
            return self
        # Ensure that the instance has __signals__ property
        if not hasattr(instance, "__signals__"):
            instance.__signals__ = {}
        # Ensure that the instance signal is defined
        if self._name not in instance.__signals__:
            # Or create it if needed
            signal = Signal(self._name)
            # Connect the first responder function via the trampoline so that
            # the instance's self object is also passed explicitly
            signal.connect(boundmethod(instance, self.first_responder))
            # Ensure we don't recreate signals
            instance.__signals__[self._name] = signal
        return instance.__signals__[self._name]

    def __set__(self, instance, value):
        raise AttributeError("You cannot overwrite signals")

    def __delete__(self, instance):
        raise AttributeError("You cannot delete signals")


class SignalTestCase(unittest.TestCase):
    """
    A :class:`unittest.TestCase` subclass that simplifies testing uses of
    the Morris signals. It provides three assertion methods and one utility
    helper method for observing signal events.
    """

    def _extend_state(self):
        if not hasattr(self, '_events_seen'):
            self._events_seen = []

    def watchSignal(self, signal):
        """
        Setup provisions to watch a specified signal

        :param signal:
            The :class:`Signal` to watch for.

        After calling this method you can use :meth:`assertSignalFired()`
        and :meth:`assertSignalNotFired()` with the same signal.
        """
        self._extend_state()

        def signal_handler(*args, **kwargs):
            self._events_seen.append((signal, args, kwargs))
        signal.connect(signal_handler)
        if hasattr(self, 'addCleanup'):
            self.addCleanup(signal.disconnect, signal_handler)

    def assertSignalFired(self, signal, *args, **kwargs):
        """
        Assert that a signal was fired with appropriate arguments.

        :param signal:
            The :class:`Signal` that should have been fired.
            Typically this is ``SomeClass.on_some_signal`` reference
        :param args:
            List of positional arguments passed to the signal handler
        :param kwargs:
            List of keyword arguments passed to the signal handler
        :returns:
            A 3-tuple (signal, args, kwargs) that describes that event
        """
        event = (signal, args, kwargs)
        self.assertIn(
            event, self._events_seen,
            "\nSignal unexpectedly not fired: {}\n".format(event))
        return event

    def assertSignalNotFired(self, signal, *args, **kwargs):
        """
        Assert that a signal was fired with appropriate arguments.

        :param signal:
            The :class:`Signal` that should not have been fired.
            Typically this is ``SomeClass.on_some_signal`` reference
        :param args:
            List of positional arguments passed to the signal handler
        :param kwargs:
            List of keyword arguments passed to the signal handler
        """
        event = (signal, args, kwargs)
        self.assertNotIn(
            event, self._events_seen,
            "\nSignal unexpectedly fired: {}\n".format(event))

    def assertSignalOrdering(self, *expected_events):
        """
        Assert that a signals were fired in a specific sequence.

        :param expected_events:
            A (varadic) list of events describing the signals that were fired
            Each element is a 3-tuple (signal, args, kwargs) that describes
            the event.

        .. note::
            If you are using :meth:`assertSignalFired()` then the return value
            of that method is a single event that can be passed to this method
        """
        expected_order = [self._events_seen.index(event)
                          for event in expected_events]
        actual_order = sorted(expected_order)
        self.assertEqual(
            expected_order, actual_order,
            "\nExpected order of fired signals:\n{}\n"
            "Actual order observed:\n{}".format(
                "\n".join(
                    "\t{}: {}".format(i, event)
                    for i, event in enumerate(expected_events, 1)),
                "\n".join(
                    "\t{}: {}".format(i, event)
                    for i, event in enumerate(
                        (self._events_seen[idx] for idx in actual_order), 1))))


def remove_signals_listeners(instance):
    """
    utility function that disconnects all listeners from all signals on an
    object
    """
    if hasattr(instance, "__listeners__"):
        for listener in list(instance.__listeners__):
            for signal in instance.__listeners__[listener]:
                signal.disconnect(listener)

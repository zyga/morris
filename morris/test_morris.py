# Copyright 2012-2014 Canonical Ltd.
# Written by:
#   Zygmunt Krynicki <zygmunt.krynicki@canonical.com>
#
# This file is part of Morris.
#
# Morris is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License
#
# Morris is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Morris.  If not, see <http://www.gnu.org/licenses/>.

"""
morris.tests
============
Test definitions for Morris
"""
from __future__ import print_function, absolute_import, unicode_literals

from unittest import TestCase

from morris import boundmethod
from morris import remove_signals_listeners
from morris import Signal
from morris import signal
from morris import SignalTestCase


class FakeSignalTestCase(SignalTestCase):
    """
    A subclass of :class:`morris.SignalTestCase` that defines :meth:`runTest()`
    """

    def runTest(self):
        """
        An empty test method
        """


class SignalTestCaseTest(TestCase):
    """
    Test definitions for the :class:`morris.SignalTestCase` class.
    """

    def setUp(self):
        self.signal = Signal('signal')
        self.case = FakeSignalTestCase()

    def test_watchSignal(self):
        """
        Ensure that calling watchSignal() actually connects a signal listener
        """
        self.assertEqual(len(self.signal.listeners), 0)
        self.case.watchSignal(self.signal)
        self.assertEqual(len(self.signal.listeners), 1)

    def test_assertSignalFired(self):
        """
        Ensure that assertSignalFired works correctly
        """
        self.case.watchSignal(self.signal)
        self.signal.fire((), {})
        sig = self.case.assertSignalFired(self.signal)
        self.assertEqual(sig,  (self.signal, (), {}))

    def test_assertSignalNotFired(self):
        """
        Ensure that assertSignalNotFired works correctly
        """
        self.case.watchSignal(self.signal)
        self.case.assertSignalNotFired(self.signal)

    def test_assertSignalOrdering(self):
        """
        Ensure that assertSignalOrdering works correctly
        """
        self.case.watchSignal(self.signal)
        self.signal('first')
        self.signal('second')
        self.signal('third')
        first = self.case.assertSignalFired(self.signal, 'first')
        second = self.case.assertSignalFired(self.signal, 'second')
        third = self.case.assertSignalFired(self.signal, 'third')
        self.case.assertSignalOrdering(first, second, third)


class C1(object):
    """
    Helper class with two signals defined using :meth:`Signal.define`
    """

    def on_foo(self, *args, **kwargs):
        """
        A signal accepting (ignoring) arbitrary arguments
        """

    on_foo_func = on_foo
    on_foo = Signal.define(on_foo)

    @Signal.define
    def on_bar(self):
        """
        A signal accepting no arguments
        """


class C2(object):
    """
    Helper class with two signals defined using :class:`morris.signal`
    """

    def on_foo(self, *args, **kwargs):
        """
        A signal accepting (ignoring) arbitrary arguments
        """

    on_foo_func = on_foo
    on_foo = signal(on_foo)

    @signal
    def on_bar(self):
        """
        A signal accepting no arguments
        """


class R(object):
    """
    Helper class that collaborates with either :class:`C1` or :class:`C2`
    """

    def __init__(self, c):
        c.on_foo.connect(self._foo)
        c.on_bar.connect(self._bar)
        c.on_bar.connect(self._baz)

    def _foo(self):
        pass

    def _bar(self):
        pass

    def _baz(self):
        pass


class SignalTestsBase(object):
    """
    Set of base test definitions for :class:`morris.Signal` class.
    """

    def setUp(self):
        self.c = self.get_c()

    def get_c(self):
        raise NotImplementedError

    def test_first_responder(self):
        """
        Ensure that using the decorator syntax connects the decorated object
        as the first responder
        """
        self.assertEqual(len(self.c.on_foo.listeners), 1)
        # NOTE: this is a bit hairy. The ``signal`` decorator is always called
        # on the bare function object (so on the ``on_foo`` function, before
        # it becomes a method.
        #
        # To test that we need to extract the bare function (using the __func__
        # property) from the (real) boundmethod that we see as
        # self.c.on_foo_func.
        #
        # Then on top of that, the first responder is treated specially
        # by ``signal.__get__()`` so that it creates a fake boundmethod
        # (implemented in morris, not by python built-in) that stores the
        # signal and the instance manually.
        first_info = self.c.on_foo.listeners[0]
        first_listener = first_info.listener
        self.assertIsInstance(first_listener, boundmethod)
        self.assertEqual(first_listener.instance, self.c)
        self.assertEqual(first_listener.func, self.c.on_foo_func.__func__)
        self.assertEqual(first_info.pass_signal, False)

    def test_connect(self):
        """
        Ensure that connecting signals works
        """
        def handler():
            pass
        self.c.on_foo.connect(handler)
        self.assertIn(
            handler, (info.listener for info in self.c.on_foo.listeners))

    def test_disconnect(self):
        """
        Ensure that disconnecting signals works
        """
        def handler():
            pass
        self.c.on_foo.connect(handler)
        self.c.on_foo.disconnect(handler)
        self.assertNotIn(
            handler, (info.listener for info in self.c.on_foo.listeners))

    def test_calling_signal_fires_them(self):
        """
        Ensure that calling signals fires them
        """
        self.watchSignal(self.c.on_foo)
        self.c.on_foo()
        self.assertSignalFired(self.c.on_foo)

    def test_calling_signals_passes_positional_arguments(self):
        """
        Ensure that calling the signal object with positional arguments works
        """
        self.watchSignal(self.c.on_foo)
        self.c.on_foo(1, 2, 3)
        self.assertSignalFired(self.c.on_foo, 1, 2, 3)

    def test_calling_signals_passes_keyword_arguments(self):
        """
        Ensure that calling the signal object with keyword arguments works
        """
        self.watchSignal(self.c.on_foo)
        self.c.on_foo(one=1, two=2, three=3)
        self.assertSignalFired(self.c.on_foo, one=1, two=2, three=3)

    def test_remove_signals_listeners(self):
        """
        Ensure that calling :func:`remove_signal_listeners()` works
        """
        a = R(self.c)
        b = R(self.c)
        self.assertEqual(len(a.__listeners__), 3)
        self.assertEqual(len(b.__listeners__), 3)
        remove_signals_listeners(a)
        self.assertEqual(len(a.__listeners__), 0)
        self.assertEqual(len(b.__listeners__), 3)


class SignalTestsC1(SignalTestsBase, SignalTestCase):
    """
    Test definitions for :class:`morris.Signal` class that use :class:`C1`
    """

    def get_c(self):
        return C1()


class SignalTestsC2(SignalTestsBase, SignalTestCase):
    """
    Test definitions for :class:`morris.Signal` class that use :class:`C2`
    """

    def get_c(self):
        return C2()

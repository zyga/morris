=========================================================
Morris - an announcement (signal/event) system for Python
=========================================================

.. image:: https://badge.fury.io/py/morris.png
    :target: http://badge.fury.io/py/morris

.. image:: https://travis-ci.org/zyga/morris.png?branch=master
        :target: https://travis-ci.org/zyga/morris

.. image:: https://pypip.in/d/morris/badge.png
        :target: https://pypi.python.org/pypi/morris

Features
========

* Free software: LGPLv3 license
* Documentation: https://morris.readthedocs.org.
* Create signals with a simple decorator :class:`morris.signal`
* Send signals by calling the decorated method or function
* Connect to and disconnect from signals with :meth:`morris.signal.connect()`
  and :meth:`morris.signal.disconnect()`.
* Test your code with :meth:`morris.SignalTestCase.watchSignal()`,
  :meth:`morris.SignalTestCase.assertSignalFired()`,
  :meth:`morris.SignalTestCase.assertSignalNotFired()`
  and :meth:`morris.SignalTestCase.assertSignalOrdering()`

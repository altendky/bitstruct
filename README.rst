|buildstatus|_

About
=====

This module is intended to have a similar interface as the python struct module, but
working on bits instead of normal datatypes (char, int, ...).

Documentation: http://bitstruct.readthedocs.org/en/latest


Installation
============

.. code-block:: python

    pip install bitstruct


Example usage
=============

See the test suite: https://github.com/eerimoq/bitstruct/blob/master/tests/test_bitstruct.py

A basic example of packing/unpacking four integers:

.. code-block:: python

    >>> from bitstruct import *
    >>> pack('u1u3u4s16', 1, 2, 3, -4)
    bytearray(b'\xa3\xff\xfc')
    >>> unpack('u1u3u4s16', bytearray(b'\xa3\xff\xfc'))
    (1, 2, 3, -4)
    >>> calcsize('u1u3u4s16')
    24

Unpacked fields can be named by assigning them to variables or by wrapping the result in a named tuple:

.. code-block:: python

    >>> from bitstruct import *
    >>> from collections import namedtuple
    >>> MyName = namedtuple('myname', [ 'a', 'b', 'c', 'd' ])
    >>> unpacked = unpack('u1u3u4s16', bytearray(b'\xa3\xff\xfc'))
    >>> myname = MyName(*unpacked)
    >>> myname
    myname(a=1, b=2, c=3, d=-4)
    >>> myname.c
    3

An example of packing/unpacking a unsinged integer, a signed integer, a float and a bytearray:

.. code-block:: python

    >>> from bitstruct import *
    >>> pack('u5s5f32b13', 1, -1, 3.75, bytearray(b'\xff\xff'))
    bytearray(b'\x0f\xd0\x1c\x00\x00?\xfe')
    >>> unpack('u5s5f32b13', bytearray(b'\x0f\xd0\x1c\x00\x00?\xfe'))
    (1, -1, 3.75, bytearray(b'\xff\xf8'))
    >>> calcsize('u5s5f32b13')
    55

An example of unpacking from a hexstring and a binary file:

.. code-block:: python

    >>> from bitstruct import *
    >>> from binascii import *
    >>> unpack('s17s13b24', bytearray(unhexlify('0123456789abcdef')))
    (582, -3751, bytearray(b'\xe2j\xf3'))
    >>> with open("test.bin", "rb") as fin:
    ...     unpack('s17s13b24', bytearray(fin.read(8)))
    ...     
    ... 
    (582, -3751, bytearray(b'\xe2j\xf3'))

Change endianess of data and then unpack it:

.. code-block:: python

    >>> from bitstruct import *
    >>> packed = pack('u1u3u4s16', 1, 2, 3, 1)
    >>> unpack('u1u3u4s16', byteswap('12', packed))
    (1, 2, 3, 256)

.. |buildstatus| image:: https://travis-ci.org/eerimoq/bitstruct.svg
.. _buildstatus: https://travis-ci.org/eerimoq/bitstruct

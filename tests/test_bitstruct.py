import unittest
# for testing private members
import bitstruct
from bitstruct import *
import copy
import math

class BitStructTest(unittest.TestCase):

    def test_pack(self):
        '''
        Pack values.
        '''
        packed = pack('u1u1s6u7u9', 0, 0, -2, 65, 22)
        self.assertEqual(packed, bytearray(b'\x3e\x82\x16'))

        packed = pack('u1', 1)
        self.assertEqual(packed, bytearray(b'\x80'))

        packed = pack('u77', 0x100000000001000000)
        ref = bytearray(b'\x00\x80\x00\x00\x00\x00\x08\x00\x00\x00')
        self.assertEqual(packed, ref)

        packed = pack('p1u1s6u7u9', 0, -2, 65, 22)
        self.assertEqual(packed, bytearray(b'\x3e\x82\x16'))

        packed = pack('p1u1s6p7u9', 0, -2, 22)
        self.assertEqual(packed, bytearray(b'\x3e\x00\x16'))

        packed = pack('u1s6f32b43', 0, -2, 3.75, bytearray(b'\x00\xff\x00\xff\x00\xff'))
        self.assertEqual(packed, bytearray(b'\x7c\x80\xe0\x00\x00\x01\xfe\x01\xfe\x01\xc0'))

    def test_unpack(self):
        '''
        Unpack values.
        '''
        unpacked = unpack('u1u1s6u7u9', bytearray(b'\x3e\x82\x16'))
        self.assertEqual(unpacked, (0, 0, -2, 65, 22))

        unpacked = unpack('u1', bytearray(b'\x80'))
        self.assertEqual(unpacked, (1,))

        packed = bytearray(b'\x00\x80\x00\x00\x00\x00\x08\x00\x00\x00')
        unpacked = unpack('u77', packed)
        self.assertEqual(unpacked, (0x100000000001000000,))

        packed = bytearray(b'\x3e\x82\x16')
        unpacked = unpack('p1u1s6u7u9', packed)
        self.assertEqual(unpacked, (0, -2, 65, 22))

        packed = bytearray(b'\x3e\x82\x16')
        unpacked = unpack('p1u1s6p7u9', packed)
        self.assertEqual(unpacked, (0, -2, 22))

        packed = bytearray(b'\x7c\x80\xe0\x00\x00\x01\xfe\x01\xfe\x01\xc0')
        unpacked = unpack('u1s6f32b43', packed)
        self.assertEqual(unpacked, (0, -2, 3.75, bytearray(b'\x00\xff\x00\xff\x00\xe0')))

        # bad float size
        try:
            unpack('f33', bytearray(b'\x00\x00\x00\x00\x00'))
            self.fail()
        except ValueError:
            pass

    def test_pack_unpack(self):
        '''
        Pack and unpack values.
        '''
        packed = pack('u1u1s6u7u9', 0, 0, -2, 65, 22)
        unpacked = unpack('u1u1s6u7u9', packed)
        self.assertEqual(unpacked, (0, 0, -2, 65, 22))

    def test_calcsize(self):
        '''
        Calculate size.
        '''
        size = calcsize('u1u1s6u7u9')
        self.assertEqual(size, 24)

        size = calcsize('u1')
        self.assertEqual(size, 1)

        size = calcsize('u77')
        self.assertEqual(size, 77)

        size = calcsize('u1s6u7u9')
        self.assertEqual(size, 23)

    def test_byteswap(self):
        '''
        Byte swap.
        '''        
        res = bytearray(b'\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a')
        ref = bytearray(b'\x01\x03\x02\x04\x08\x07\x06\x05\x0a\x09')
        self.assertEqual(byteswap('12142', ref), res)

        packed = pack('u1u5u2u16', 1, 2, 3, 4)
        unpacked = unpack('u1u5u2u16', byteswap('12', packed))
        self.assertEqual(unpacked, (1, 2, 3, 1024))

    def iterable_almost_equal(self, first, second, places=6):
        self.assertEqual(len(first), len(second))

        for f, s in zip(first, second):
            if isinstance(f, float) and isinstance(s, float):
                self.assertAlmostEqual(f, s, places)
            else:
                self.assertEqual(f, s)

    def test_endianness_format(self):
        '''
        Endianness format
        '''
        value = -3
        byte_width = 8
        width = 10
        big = '1111111101'
        little = '1111110111'
        self.assertEqual(len(big), width)
        self.assertEqual(len(little), width)

        value = -3
        byte_width = 8
        width = 10
        big = '1111111101'
        little = '1111110111'
        self.assertEqual(len(big),
                         width)
        self.assertEqual(len(little),
                         width)
        self.assertEqual(bitstruct.translate_endianness(little, target='>',
                                                        byte_width=byte_width),
                         big)
        self.assertEqual(bitstruct.translate_endianness(big, target='<',
                                                        byte_width=byte_width),
                         little)
        self.assertEqual(bitstruct._unpack_integer('s', big),
                         value)
        self.assertEqual(bitstruct._unpack_integer('s', big, endianness='>'),
                         bitstruct._unpack_integer('s', little, endianness='<'))
        self.assertEqual(bitstruct.translate_endianness(big, target='<',
                                                        byte_width=byte_width),
                         little)
        self.assertEqual(bitstruct._pack_integer(width, value),
                         big)
        self.assertEqual(bitstruct._pack_integer(width, value, target='<'),
                         little)

        data = (0, 0, -2, 65, 22, math.pi)
        format = 'u1u1<s14<u17>u9<f32'
        packed_a = pack(format, *data)
        unpacked = unpack(format, packed_a)
        self.iterable_almost_equal(unpacked, data)

        # Here is a set of formats which should generate unique results.
        # This is used to verify that the endianness is being applied.
        formats = [
            'u1u1<s14<u17>u9>f32',
            'u1u1<s14>u17>u9>f32',
            'u1u1>s14>u17>u9>f32',
            'u1u1>s14>u17>u9<f32',
        ]

        packed = []
        for f in formats:
            packed.append(pack(f, *data))

        # Verify that the results are all truly unique
        for i, p in enumerate(packed):
            packed_copy = copy.copy(packed)
            del packed_copy[i]
            self.assertNotIn(p, packed_copy)


if __name__ == '__main__':
    unittest.main()

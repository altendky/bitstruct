import copy
import re
import struct


def _parse_format(fmt):
    if isinstance(fmt, list):
        return fmt

    parsed_infos = re.findall(r'([<>]?)([a-zA-Z])(\d+)', fmt)

    # Use big endian as default and use the endianness of the previous
    # value if none is given for the current value.
    infos = []
    endianness = ">"
    for info in parsed_infos:
        if info[0] != "":
            endianness = info[0]
        infos.append((info[1], int(info[2]), endianness))
    
    return infos


def _pack_integer(size, arg, target='>'):
    if arg < 0:
        arg = ((1 << size) + arg)
    bits = '{{:0{}b}}'.format(size).format(arg)
    if target == '<':
        bits = translate_endianness(bits, target='<')
    return bits

def _pack_boolean(size, arg):
    return _pack_integer(size, int(arg))


def _pack_float(size, arg, target='>'):
    if size == 32:
        value = struct.pack(target + 'f', arg)
    elif size == 64:
        value = struct.pack(target + 'd', arg)
    else:
        raise ValueError('Bad float size {}. Must be 32 or 64 bits.'.format(size))
    return _pack_bytearray(size, bytearray(value), target=target)


def _pack_bytearray(size, arg, target='>'):
    bits = ''.join('{:08b}'.format(b)
                   for b in arg)
    bits = bits[0:size]

    if target == '<':
        bits = translate_endianness(bits, target)

    return bits


def _unpack_integer(_type, bits, endianness='>'):
    if endianness == '<':
        bits = translate_endianness(bits, target='>')

    value = int(bits, 2)

    if _type == 's':
        if bits[0] == '1':
            value -= (1 << len(bits))

    return value


def _unpack_boolean(bits):
    value = _unpack_integer('u', bits)

    return bool(value)


def _unpack_float(size, bits, endianness='>'):
    packed = _unpack_bytearray(size, bits, endianness=endianness)

    if size == 32:
        value = struct.unpack(endianness + 'f', packed)[0]
    elif size == 64:
        value = struct.unpack(endianness + 'd', packed)[0]
    else:
        raise ValueError('Bad float size {}. Must be 32 or 64 bits.'.format(size))

    return value

def _unpack_bytearray(size, bits, endianness='>'):
    value = bytearray()

    if endianness == '<':
        bits = translate_endianness(bits, target='<')

    for i in range(size // 8):
        value.append(int(bits[8*i:8*i+8], 2))
    rest = size % 8
    if rest > 0:
        value.append(int(bits[size-rest:], 2) << (8-rest))
    return value


def translate_endianness(bitstring, target, byte_width=8):
    bits = copy.copy(bitstring)
    bytes = []
    chunk_sizes = [byte_width] * int(len(bits) / byte_width)

    partial_len = len(bits) % byte_width
    if partial_len > 0:
        chunk_sizes.insert(0, partial_len)

    if target == '<':
        for size in chunk_sizes:
            chunk = bits[:size]
            bits = bits[size:]
            bytes.insert(0, chunk)
    elif target == '>':
        for size in chunk_sizes:
            chunk = bits[-size:]
            bits = bits[:-size]
            bytes.append(chunk)
    else:
        raise ValueError("Endianness type '{}' not supported.".format(target))

    return ''.join(bytes)


def pack(fmt, *args):
    """Return a bytearray containing the values v1, v2, ... packed
    according to the given format. If the total number of bits are not
    a multiple of 8, padding will be added at the end of the last
    byte.

    :param fmt: Bitstruct format string. See format description below.
    :param args: Variable argument list of values to pack.
    :returns: A bytearray of the packed values.

    `fmt` is a string of byteorder-type-length groups. Byteorder may be
    omitted.

    Byteorder is either ">" or "<", where ">" means MSB first and "<"
    means LSB first. If byteorder is omitted, the previous values'
    byteorder is used for the current value. For example, in the format
    string "u1<u2u3" u1 is MSB first and both u2 and u3 are LSB first.

    There are six types; 'u', 's', 'f', 'b', 'r' and 'p'.

    - 'u' -- unsigned integer
    - 's' -- signed integer
    - 'f' -- floating point number of 32 or 64 bits
    - 'b' -- boolean
    - 'r' -- raw, bytearray
    - 'p' -- padding, ignore

    Length is the number of bits to pack the value into.
    
    Example format string: 'u1u3p7s16'

    """

    bits = ''
    infos = _parse_format(fmt)
    i = 0

    for _type, size, endianness in infos:
        if _type == 'p':
            bits += size * '0'
        else:
            if _type in 'us':
                value_bits = _pack_integer(size, args[i], target=endianness)
            elif _type == 'f':
                value_bits = _pack_float(size, args[i], target=endianness)
            elif _type == 'b':
                value_bits = _pack_boolean(size, args[i])
            elif _type == 'r':
                value_bits = _pack_bytearray(size, args[i], target=endianness)
            else:
                raise ValueError("bad type '{}' in format".format(_type))

            bits += value_bits
            i += 1

    # padding of last byte
    tail = len(bits) % 8
    if tail != 0:
        bits += (8 - tail) * '0'

    return bytearray([int(''.join(bits[i:i+8]), 2)
                      for i in range(0, len(bits), 8)])


def unpack(fmt, data):
    """Unpack the bytearray (presumably packed by pack(fmt, ...))
    according to the given format. The result is a tuple even if it
    contains exactly one item.

    :param fmt: Bitstruct format string. See pack() for details.
    :param data: Bytearray of values to unpack.
    :returns: A tuple of the unpacked values.

    """

    bits = ''.join(['{:08b}'.format(b) for b in data])
    infos = _parse_format(fmt)
    res = []
    i = 0

    for _type, size, endianness in infos:
        if _type == 'p':
            pass
        else:
            value_bits = bits[i:i+size]

            if _type in 'us':
                value = _unpack_integer(_type, value_bits, endianness=endianness)
            elif _type == 'f':
                value = _unpack_float(size, value_bits, endianness=endianness)
            elif _type == 'b':
                value = _unpack_boolean(value_bits)
            elif _type == 'r':
                value = _unpack_bytearray(size, value_bits, endianness=endianness)
            else:
                raise ValueError("bad type '{}' in format".format(_type))
            res.append(value)
        i += size

    return tuple(res)


def calcsize(fmt):
    """Return the size of the bitstruct (and hence of the bytearray)
    corresponding to the given format.

    :param fmt: Bitstruct format string.
    :returns: Number of bits in format string.

    """

    return sum([size for _, size, _ in _parse_format(fmt)])


def byteswap(fmt, data, offset = 0):
    """In place swap bytes in `data` according to `fmt`, starting at byte
    `offset`. `fmt` must be an iterable, iterating over number of
    bytes to swap. For example, the format string "24" applied to the
    bytearray "\x00\x11\x22\x33\x44\x55" will produce the result
    "\x11\x00\x55\x44\x33\x22".

    :param fmt: Swap format string.
    :param data: Bytearray of data to swap.
    :param offset: Start offset into `data`.
    :returns: Bytearray of swapped bytes.

    """

    i = offset

    for f in fmt:
        length = int(f)
        value = data[i:i+length]
        value.reverse()
        data[i:i+length] = value
        i += length

    return data

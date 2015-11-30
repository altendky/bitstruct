import copy
import re
import struct


def _parse_format(fmt):
    types = re.findall(r'[<>]?[a-zA-Z]+', fmt)
    sizes = map(lambda size: int(size),
                re.findall(r'\d+', fmt))
    return zip(types, sizes)


def _pack_integer(size, arg, target='>'):
    if arg < 0:
        arg = ((1 << size) + arg)
    bits = '{{:0{}b}}'.format(size).format(arg)
    if target == '<':
        bits = translate_endianness(bits, target='<')
    return bits


def _pack_float(size, arg, target='>'):
    if size == 32:
        value = struct.pack('>f', arg)
    elif size == 64:
        value = struct.pack('>d', arg)
    else:
        raise ValueError('Bad float size {}. Must be 32 or 64.'.format(size))

    return _pack_bytearray(size, bytearray(value), target=target)

def _pack_bytearray(size, arg, target='>'):
    bits = ''.join('{:08b}'.format(b)
                   for b in arg)
    bits = bits[0:size]

    if target == '<':
        bits = translate_endianness(bits, target)
    elif target == '>':
        pass
    else:
        raise ValueError("Endianness type '{}' not supported.".format(target))

    return bits


def _unpack_integer(type, bits, endianness='>'):
    if endianness == '<':
        bits = translate_endianness(bits, target='>')
    value = int(bits, 2)
    if type == 's':
        if bits[0] == '1':
            value -= (1 << len(bits))
    return value


def _unpack_float(size, bits, endianness='>'):
    packed = _unpack_bytearray(size, bits, endianness=endianness)
    if size == 32:
        value = struct.unpack('>f', packed)[0]
    elif size == 64:
        value = struct.unpack('>d', packed)[0]
    else:
        raise ValueError('Bad float size {}. Must be 32 or 64.'.format(size))
    return value

def _unpack_bytearray(size, bits, target='>', endianness='>'):
    value = bytearray()

    if endianness == '<':
        bits = translate_endianness(bits, target='<')
    elif endianness == '>':
        pass
    else:
        raise ValueError("Endianness type '{}' not supported.".format(target))

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
    '''
    Return a bytearray containing the values v1, v2, ... packed according
    to the given format. The arguments must match the values required by
    the format exactly. If the total number of bits are not a multiple
    of 8, padding will be added at the end of the last byte.

    :param fmt: Bitstruct format string.
    :param args: Variable argument list of values to pack.
    :returns: Bytearray of packed values.
    
    `fmt` is a string of type-length pairs. There are five
    types; 'u', 's', 'f', 'b' and 'p'. Length is the number of bits to pack 
    the value into.
    
    - 'u' -- unsigned integer
    - 's' -- signed integer
    - 'f' -- floating point number of 32 or 64 bits
    - 'b' -- bytearray
    - 'p' -- padding, ignore

    Example format string: 'u1u3p7s16'
    '''
    bits = ''
    infos = _parse_format(fmt)
    i = 0
    for type, size in infos:
        if type[0] in '<>':
            endianness = type[0]
            type = type[1:]
        else:
            endianness = '>'
        if type == 'p':
            bits += size * '0'
        else:
            if type in 'us':
                bits += _pack_integer(size, args[i], target=endianness)
            elif type == 'f':
                bits += _pack_float(size, args[i], target=endianness)
            elif type == 'b':
                bits += _pack_bytearray(size, args[i], target=endianness)
            else:
                raise ValueError("bad type '{}' in format".format(type))
            i += 1

    # padding of last byte
    tail = len(bits) % 8
    if tail != 0:
        bits += (8 - tail) * '0'

    return bytearray([int(''.join(bits[i:i+8]), 2)
                      for i in range(0, len(bits), 8)])


def unpack(fmt, data):
    '''
    Unpack the bytearray (presumably packed by pack(fmt, ...)) according
    to the given format. The result is a tuple even if it contains exactly
    one item.

    :param fmt: Bitstruct format string.
    :param data: Bytearray of values to unpack.
    :returns: Tuple of unpacked values.
    '''
    bits = ''.join(['{:08b}'.format(b) for b in data])
    infos = _parse_format(fmt)
    res = []
    i = 0
    for type, size in infos:
        if type[0] in '<>':
            endianness = type[0]
            type = type[1:]
        else:
            endianness = '>'
        if type == 'p':
            pass
        else:
            if type in 'us':
                value = _unpack_integer(type, bits[i:i+size], endianness=endianness)
            elif type == 'f':
                value = _unpack_float(size, bits[i:i+size], endianness=endianness)
            elif type == 'b':
                value = _unpack_bytearray(size, bits[i:i+size], endianness=endianness)
            res.append(value)
        i += size
    return tuple(res)


def calcsize(fmt):
    '''
    Return the size of the bitstruct (and hence of the bytearray) corresponding
    to the given format.

    :param fmt: Bitstruct format string.
    :returns: Number of bits in format string.
    '''
    return sum([size for _, size in _parse_format(fmt)])


def byteswap(fmt, data, offset = 0):
    '''
    In place swap bytes in `data` according to `fmt`, starting at
    byte `offset`. `fmt` must be an iterable, iterating over
    number of bytes to swap.

    :param fmt: Swap format string.
    :param data: Bytearray of data to swap.
    :param offset: Start offset into `data`.
    :returns: Bytearray of swapped bytes.
    '''
    i = offset
    for f in fmt:
        length = int(f)
        value = data[i:i+length]
        value.reverse()
        data[i:i+length] = value
        i += length
    return data

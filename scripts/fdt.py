# SPDX-License-Identifier: GPL-2.0-only
"""Read compiled FDTs for byte-level comparison. This is not a DTS compiler."""
import struct


def read_fdt(data):
    if len(data) < 40:
        raise ValueError('Truncated FDT header')
    h = struct.unpack('>10I', data[:40])
    magic, total, off_struct, off_strings, off_reserve, version, compatible, boot_cpu, size_strings, size_struct = h
    if magic != 0xd00dfeed or total > len(data) or version < 17 or compatible > 17:
        raise ValueError('Unsupported or invalid FDT header')
    if off_struct + size_struct > total or off_strings + size_strings > total:
        raise ValueError('FDT block outside total size')
    strings = data[off_strings:off_strings + size_strings]
    tree, stack, index = {}, [], off_struct
    end_struct = off_struct + size_struct
    while index + 4 <= end_struct:
        token, = struct.unpack_from('>I', data, index)
        index += 4
        if token == 1:
            end = data.find(b'\0', index, end_struct)
            if end < 0:
                raise ValueError('Unterminated node name')
            stack.append(data[index:end].decode('ascii'))
            path = '/'.join(stack) or '/'
            if path in tree:
                raise ValueError('Duplicate node: ' + path)
            tree[path] = {}
            index = (end + 4) & ~3
        elif token == 2:
            if not stack:
                raise ValueError('Unbalanced FDT nodes')
            stack.pop()
        elif token == 3:
            if not stack or index + 8 > end_struct:
                raise ValueError('Property outside node')
            size, offset = struct.unpack_from('>II', data, index)
            index += 8
            if index + size > end_struct or offset >= len(strings):
                raise ValueError('Invalid property range')
            end = strings.find(b'\0', offset)
            if end < 0:
                raise ValueError('Unterminated property name')
            name = strings[offset:end].decode('ascii')
            props = tree['/'.join(stack) or '/']
            if name in props:
                raise ValueError('Duplicate property: ' + name)
            props[name] = data[index:index + size]
            index = (index + size + 3) & ~3
        elif token == 4:
            continue
        elif token == 9:
            if stack:
                raise ValueError('Unclosed FDT node')
            break
        else:
            raise ValueError('Invalid FDT token')
    else:
        raise ValueError('Missing FDT_END')
    reservations, index = [], off_reserve
    while index + 16 <= total:
        pair = struct.unpack_from('>QQ', data, index)
        index += 16
        if pair == (0, 0):
            return tree, reservations, boot_cpu
        reservations.append(pair)
    raise ValueError('Missing reservation terminator')


def semantic_diff(a, b):
    result = []
    for node in sorted(set(a) | set(b)):
        for prop in sorted(set(a.get(node, {})) | set(b.get(node, {}))):
            av, bv = a.get(node, {}).get(prop), b.get(node, {}).get(prop)
            if av != bv:
                result.append({'node': node, 'property': prop,
                               'base_hex': None if av is None else av.hex(),
                               'other_hex': None if bv is None else bv.hex()})
    return result

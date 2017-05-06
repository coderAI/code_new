import re
import binascii


def hex2int(h):
    if len(h) > 1 and h[0:2] == '0x':
        h = h[2:]
    if len(h) % 2:
        h = "0" + h
    return int(h, 16)


def int2hex(i, l):
    hex_i = hex(i)
    if len(hex_i) > 1 and hex_i[0:2] == '0x':
        hex_i = hex_i[2:]
    if l == 2 and len(hex_i) % 2:
        hex_i = "0" + hex_i
    return hex_i


def hex2intdword(h):
    full = []
    for i in enumerate(h):
        full.extend('f')
    full = ''.join(full)
    return ~ (int(full, 16) - int(h, 16))


def convertasci(line):
    n = 2
    result_line = ""
    data = [line[i:i + n] for i in range(0, len(line), n)]
    for i in data:
        iint = int("0x" + str(i), 16)
        ichar = chr(iint)

        result_line += ichar
    result_line = re.search(r'\w+', result_line).group(0)
    return result_line


def decode(str):
    asci = convertasci(str)
    asci_div_2 = hex(int(asci, 16) / 2)
    if len(asci_div_2) > 0 and asci_div_2[:2] == '0x':
        asci_div_2 = asci_div_2[2:]
    result = hex2int(asci_div_2[2:])
    return "%d" % result


def encode(s):
    if isinstance(s, (str, unicode)):
        s = int(s)
    num2hex = hex(s)
    if len(num2hex) > 0 and num2hex[:2] == '0x':
        num2hex = num2hex[2:]
        num2hex = "0x1a%s" % num2hex
    asci_x2 = hex(int(num2hex, 16) * 2)
    if len(asci_x2) > 0 and asci_x2[:2] == '0x':
        asci_x2 = "0%s\r\n" % asci_x2[2:].upper()
    result = "%s" % binascii.hexlify(asci_x2)
    return result



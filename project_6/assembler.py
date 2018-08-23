import sys


file = open(sys.argv[1])


DEST_LOOKUP = {
    None: '000',
    'M': '001',
    'D': '010',
    'MD': '011',
    'A': '100',
    'AM': '101',
    'AD': '110',
    'AMD': '111',
}

JUMP_LOOKUP = {
    None: '000',
    'JGT': '001',
    'JEQ': '010',
    'JGE': '011',
    'JLT': '100',
    'JNE': '101',
    'JLE': '110',
    'JMP': '111'
}

A_VALUES = (
    'M',
    '!M',
    '-M',
    'M+1',
    'M-1',
    'D+M',
    'D-M',
    'M-D',
    'D&M',
    'D|M'
)

COMP_LOOKUP = {
    '0': '101010',
    '1': '111111',
    '-1': '111010',
    'D': '001100',
    'A': '110000',
    '!D': '001101',
    '!A': '110001',
    '-D': '001111',
    '-A': '110011',
    'D+1': '011111',
    'A+1': '110111',
    'D-1': '001110',
    'A-1': '110010',
    'D+A': '000010',
    'D-A': '010011',
    'A-D': '000111',
    'D&A': '000000',
    'D|A': '010101'
}


def remove_whitespace(line):
    return line.replace(' ', '').split('//')[0].strip()


def parse_c_instruction(c_instruction):
    if '=' in c_instruction:
        return c_instruction.split('=') + [None]
    return [None] + c_instruction.split(';')


def translate(line):
    if line.startswith('@'):
        return f'{bin(int(line[1:]))[2:].zfill(16)}'
    dest, comp, jump = parse_c_instruction(line)
    a = 1 if comp in A_VALUES else 0
    comp = comp.replace('M', 'A')
    return f'111{a}{COMP_LOOKUP[comp]}{DEST_LOOKUP[dest]}{JUMP_LOOKUP[jump]}'


for line in file:
    parsed_line = remove_whitespace(line)
    if parsed_line:
        print(translate(parsed_line))

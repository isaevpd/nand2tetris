import sys
import re

FILE = open(sys.argv[1])
COUNT = 0
CLASS_NAME = FILE.name.split('/')[-1].rstrip('.vm')

MEMORY_SEGMENTS = {
    'local': 'LCL',
    'argument': 'ARG',
    'this': 'THIS',
    'that': 'THAT',
    'temp': 5,
    # pointer mappings
    '0': 'THIS',
    '1': 'THAT'
}


def push_constant(i):
    return '\n'.join([
        '// push constant %s' % i,
        '@%s' % i,
        'D=A',
        '@SP',
        'A=M',
        'M=D',
        '@SP',
        'M=M+1'
    ])


def push_pointer(i):
    return '\n'.join([
        '// push pointer %s' % i,
        '@%s' % MEMORY_SEGMENTS[i],
        'D=M',
        '@SP',
        'A=M',
        'M=D',
        '@SP',
        'M=M+1'
    ])


def push_static(i):
    return '\n'.join([
        '// push static %s' % i,
        '@%s.%s' % (CLASS_NAME, i),
        'D=M',
        '@SP',
        'A=M',
        'M=D',
        '@SP',
        'M=M+1'
    ])


def push_temp(i):
    return '\n'.join([
        '// push temp %s' % i,
        '@%s' % (MEMORY_SEGMENTS['temp'] + int(i)),
        'D=M',
        '@SP',
        'A=M',
        'M=D',
        '@SP',
        'M=M+1'
    ])


def push(segment, i):
    return '\n'.join([
        '// push %s %s' % (segment, i),
        '@%s' % MEMORY_SEGMENTS[segment],
        'A=M',
        'D=A',
        '@%s' % i,
        'D=D+A',
        'A=D',
        'D=M',
        '@SP',
        'A=M',
        'M=D',
        '@SP',
        'M=M+1'
    ])


def pop_temp(i):
    return '\n'.join([
        '// pop temp %s' % i,
        # find value that we need to store
        '@SP',
        'A=M-1',
        'D=M',
        '@SP',
        # decrement stack pointer
        'M=M-1',
        '@%s' % (MEMORY_SEGMENTS['temp'] + int(i)),
        'M=D'
    ])


def pop_pointer(i):
    return '\n'.join([
        '// pop pointer %s' % i,
        '@SP',
        'A=M-1',
        'D=M',
        '@SP',
        'M=M-1',
        '@%s' % MEMORY_SEGMENTS[i],
        'M=D'
    ])


def pop_static(i):
    return '\n'.join([
        '// pop static %s' % i,
        '@SP',
        'A=M-1',
        'D=M',
        '@SP',
        'M=M-1',
        '@%s.%s' % (CLASS_NAME, i),
        'M=D'
    ])


def pop(segment, i):
    return '\n'.join([
        '// pop %s %s' % (segment, i),
        # find value that we need to store
        '@SP',
        'A=M-1',
        'D=M',
        '@SP',
        # decrement stack pointer
        'M=M-1',
        # store it in R13
        '@R13',
        'M=D',
        '@%s' % MEMORY_SEGMENTS[segment],
        'A=M',
        'D=A',
        '@%s' % i,
        'D=D+A',
        # store address where to pop in R14
        '@R14',
        'M=D',
        '@R13',
        'D=M',
        '@R14',
        'A=M',
        'M=D'
    ])


def add():
    return '\n'.join([
        '// add',
        '@SP',
        'A=M-1',
        'D=M',
        '@SP',
        'M=M-1',
        'A=M-1',
        'M=M+D'
    ])


def sub():
    return '\n'.join([
        '// sub',
        '@SP',
        'A=M-1',
        'D=M',
        '@SP',
        'M=M-1',
        'A=M-1',
        'M=M-D'
    ])


def bitwise_or():
    return '\n'.join([
        '// or',
        '@SP',
        'A=M-1',
        'D=M',
        '@SP',
        'M=M-1',
        'A=M-1',
        'M=M|D'
    ])


def bitwise_and():
    return '\n'.join([
        '// and',
        '@SP',
        'A=M-1',
        'D=M',
        '@SP',
        'M=M-1',
        'A=M-1',
        'M=M&D'
    ])


def neg():
    return '\n'.join([
        '// neg',
        '@SP',
        'A=M-1',
        'M=-M'
    ])


def bitwise_not():
    return '\n'.join([
        '// not',
        '@SP',
        'A=M-1',
        'M=!M'
    ])


def eq():
    global COUNT
    translated = '\n'.join([
        '// eq',
        '@SP',
        'A=M-1',
        'D=M',
        '@SP',
        'M=M-1',
        '@SP',
        'A=M-1',
        'D=M-D',
        '@SET_TRUE_%s' % COUNT,
        'D;JEQ',
        '(SET_FALSE_%s)' % COUNT,
        '@SP',
        'A=M-1',
        'M=0',
        '@CONT_%s' % COUNT,
        '0;JMP',
        '(SET_TRUE_%s)' % COUNT,
        '@SP',
        'A=M-1',
        'M=-1',
        '(CONT_%s)' % COUNT
    ])
    COUNT += 1
    return translated


def lt():
    global COUNT
    translated = '\n'.join([
        '// lt',
        '@SP',
        'A=M-1',
        'D=M',
        '@SP',
        'M=M-1',
        '@SP',
        'A=M-1',
        'D=M-D',
        '@SET_TRUE_%s' % COUNT,
        'D;JLT',
        '(SET_FALSE_%s)' % COUNT,
        '@SP',
        'A=M-1',
        'M=0',
        '@CONT_%s' % COUNT,
        '0;JMP',
        '(SET_TRUE_%s)' % COUNT,
        '@SP',
        'A=M-1',
        'M=-1',
        '(CONT_%s)' % COUNT
    ])
    COUNT += 1
    return translated


def gt():
    global COUNT
    translated = '\n'.join([
        '// lt',
        '@SP',
        'A=M-1',
        'D=M',
        '@SP',
        'M=M-1',
        '@SP',
        'A=M-1',
        'D=M-D',
        '@SET_TRUE_%s' % COUNT,
        'D;JGT',
        '(SET_FALSE_%s)' % COUNT,
        '@SP',
        'A=M-1',
        'M=0',
        '@CONT_%s' % COUNT,
        '0;JMP',
        '(SET_TRUE_%s)' % COUNT,
        '@SP',
        'A=M-1',
        'M=-1',
        '(CONT_%s)' % COUNT
    ])
    COUNT += 1
    return translated


def remove_whitespace(line):
    return line.replace(' ', '').split('//')[0].strip()


def translate(line):
    if line.startswith('pushconstant'):
        i = line.lstrip('pushconstant')
        return push_constant(i)
    elif line.startswith('pushtemp'):
        i = line.lstrip('pushtemp')
        return push_temp(i)
    elif line.startswith('pushpointer'):
        i = line.lstrip('pushpointer')
        return push_pointer(i)
    elif line.startswith('pushstatic'):
        i = line.lstrip('pushstatic')
        return push_static(i)
    elif line.startswith('push'):
        segment, i = re.match(
            r'^push([a-zA-Z]+)(\d+)$',
            line
        ).groups()
        return push(segment, i)
    elif line.startswith('poptemp'):
        i = line.lstrip('poptemp')
        return pop_temp(i)
    elif line.startswith('poppointer'):
        i = line.lstrip('poppointer')
        return pop_pointer(i)
    elif line.startswith('popstatic'):
        i = line.lstrip('popstatic')
        return pop_static(i)
    elif line.startswith('pop'):
        segment, i = re.match(
            r'^pop([a-zA-Z]+)(\d+)$',
            line
        ).groups()
        return pop(segment, i)
    elif line == 'add':
        return add()
    elif line == 'eq':
        return eq()
    elif line == 'lt':
        return lt()
    elif line == 'gt':
        return gt()
    elif line == 'sub':
        return sub()
    elif line == 'not':
        return bitwise_not()
    elif line == 'and':
        return bitwise_and()
    elif line == 'or':
        return bitwise_or()
    elif line == 'neg':
        return neg()

    raise NotImplementedError(line)


new_file = open(FILE.name.rstrip('.vm') + '.asm', 'w')
for line in FILE:
    parsed_line = remove_whitespace(line)
    if parsed_line:
        translated_line = translate(parsed_line)
        new_file.write(translated_line)

new_file.close()
FILE.close()

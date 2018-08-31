import sys
import re
import os

FILE_LIST = []
path = sys.argv[1]
IS_DIR = os.path.isdir(path)
if not IS_DIR:
    FILE_LIST.append(path)
else:
    if not path.endswith('/'):
        path = path + '/'
    for filename in os.listdir(path):
        if filename.endswith('vm'):
            path_to_file = os.path.join(path, filename)
            FILE_LIST.append(path_to_file)


COUNT = 0
# FUNCTION_STACK = []
CURRENT_FUNCTION = None
CLASS_NAME = None

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


def get_full_label_name(label_name):
    if not CURRENT_FUNCTION:
        return '%s.%s' % (CLASS_NAME, label_name)
    return '%s$%s' % (CURRENT_FUNCTION, label_name)


def write_label(label_name):
    return '(%s)' % get_full_label_name(label_name)


def if_goto(label_name):
    label_name = get_full_label_name(label_name)
    translated = '\n'.join([
        '// if-goto',
        '@SP',
        'A=M-1',
        'D=M',
        '@SP',
        'M=M-1',
        '@%s' % label_name,
        'D;JNE'
    ])
    return translated


def goto(label_name):
    label_name = get_full_label_name(label_name)
    translated = '\n'.join([
        '// goto',
        '@%s' % label_name,
        '0;JMP'
    ])
    return translated


def write_function(function_name, locals_count):
    global CURRENT_FUNCTION
    generated_locals = [
        push_constant('0')
        for i in range(locals_count)
    ]
    translated = '\n'.join([
        '// function %s %d' % (function_name, locals_count),
        '(%s)' % function_name
    ]) + '\n' + '\n'.join(generated_locals)

    CURRENT_FUNCTION = function_name
    return translated


def write_return():
    global COUNT
    translated = '\n'.join([
        '// return',
        # frame = LCL
        '@LCL',
        'D=M',
        '@FRAME_%d' % COUNT,
        'M=D',
        # retAddr = *(frame-5)
        'D=M',
        '@5',
        'A=D-A',
        'D=M',
        '@RETADDR_%d' % COUNT,
        'M=D',
        # *ARG = pop
        '@SP',
        'A=M-1',
        'D=M',
        '@ARG',
        'A=M',
        'M=D',
        # SP = ARG+1
        '@ARG',
        'D=M+1',
        '@SP',
        'M=D',
        # THAT = *(frame-1)
        '@FRAME_%d' % COUNT,
        'M=M-1',
        'A=M',
        'D=M',
        '@THAT',
        'M=D',
        # THIS = *(frame-2)
        '@FRAME_%d' % COUNT,
        'M=M-1',
        'A=M',
        'D=M',
        '@THIS',
        'M=D',
        # ARG = *(frame-3)
        '@FRAME_%d' % COUNT,
        'M=M-1',
        'A=M',
        'D=M',
        '@ARG',
        'M=D',
        # LCL = *(frame-4)
        '@FRAME_%d' % COUNT,
        'M=M-1',
        'A=M',
        'D=M',
        '@LCL',
        'M=D',
        # goto retAddr
        '@RETADDR_%d' % COUNT,
        'A=M',
        '0;JMP'
    ])
    # FUNCTION_STACK.pop()
    COUNT += 1
    return translated


def write_call(function_name, args_count):
    global COUNT
    translated = '\n'.join([
        '// call %s %s' % (function_name, args_count),
        '// push returnAddr',
        '@%s' % ('returnAddress%d' % COUNT),
        'D=A',
        '@SP',
        'A=M',
        'M=D',
        '@SP',
        'M=M+1',
        '// push LCL',
        '@LCL',
        'D=M',
        '@SP',
        'A=M',
        'M=D',
        '@SP',
        'M=M+1',
        '// push ARG',
        '@ARG',
        'D=M',
        '@SP',
        'A=M',
        'M=D',
        '@SP',
        'M=M+1',
        '// push THIS',
        '@THIS',
        'D=M',
        '@SP',
        'A=M',
        'M=D',
        '@SP',
        'M=M+1',
        '// push THAT',
        '@THAT',
        'D=M',
        '@SP',
        'A=M',
        'M=D',
        '@SP',
        'M=M+1',
        '// ARG = SP - 5 - nArgs',
        '@%d' % (5 + args_count),
        'D=A',
        '@SP',
        'D=M-D',
        '@ARG',
        'M=D',
        '// LCL = SP',
        '@SP',
        'D=M',
        '@LCL',
        'M=D',
        '// goto function name',
        '// goto',
        '@%s' % function_name,
        '0;JMP',
        '(%s)' % ('returnAddress%d' % COUNT)
    ])
    COUNT += 1
    # FUNCTION_STACK.append(function_name)
    return translated


def remove_whitespace(line):
    if line.startswith('call') or line.startswith('function'):
        return line.split('//')[0].strip()
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
    elif line.startswith('label'):
        label_name = line.lstrip('label')
        return write_label(label_name)
    elif line.startswith('if-goto'):
        label_name = line.lstrip('if-goto')
        return if_goto(label_name)
    elif line.startswith('goto'):
        label_name = line.lstrip('goto')
        return goto(label_name)
    elif line.startswith('function'):
        function_name, locals_count = re.match(
            r'^function ([a-zA-Z\.\d]+) ?(\d*)$',
            line
        ).groups()
        return write_function(
            function_name,
            int(locals_count)
        )
    elif line == ('return'):
        return write_return()
    elif line.startswith('call'):
        function_name, args_count = re.match(
            r'^call ([a-zA-Z\.\d]+) ?(\d*)$',
            line
        ).groups()
        return write_call(
            function_name,
            int(args_count)
        )

    raise NotImplementedError(line)


if IS_DIR:
    dir_name = path.rstrip('/').split('/')[-1]
    new_file = open(path + dir_name + '.asm', 'w')
    new_file.write(
        '\n'.join([
            '@256',
            'D=A',
            '@SP',
            'M=D',
            write_call(
                'Sys.init',
                0
            )
        ]) + '\n'
    )
else:
    new_file = open(path.rstrip('.vm') + '.asm', 'w')

for filename in FILE_LIST:
    opened_file = open(filename)
    CLASS_NAME = opened_file.name.split('/')[-1].rstrip('.vm')

    for line in opened_file:
        parsed_line = remove_whitespace(line)
        if parsed_line:
            translated_line = translate(parsed_line)
            new_file.write(translated_line + '\n')

new_file.close()

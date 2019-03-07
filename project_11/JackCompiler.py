import re
import sys
import os

KEYWORDS = {
    'class',
    'constructor',
    'function',
    'method',
    'field',
    'static',
    'var',
    'int',
    'char',
    'boolean',
    'void',
    'true',
    'false',
    'null',
    'this',
    'let',
    'do',
    'if',
    'else',
    'while',
    'return',
}

SYMBOLS = {
    '{', '}', '(', ')', '[', ']', '.',
    ',', ';', '+', '-', '*', '/', '&', '|',
    '<', '>', '=', '~'
}

KEYWORD = 'keyword'
SYMBOL = 'symbol'
IDENTIFIER = 'identifier'
INT_CONST = 'integerConstant'
STRING_CONST = 'stringConstant'

TOKEN_TYPES = (
    KEYWORD,
    SYMBOL,
    IDENTIFIER,
    INT_CONST,
    STRING_CONST
)

SUBROUTINE = 'subroutine'
STATIC = 'static'
FIELD = 'field'
ARG = 'argument'
CLASS = 'class'
VAR = 'local'
USED = 'used'
DEFINED = 'defined'


REGEX_MAPPING = {
    KEYWORD: '(' + r'|'.join(KEYWORDS) + ')\\W',
    SYMBOL: r'([&)\]+\*\-,\/<.}([{;~=|>])',
    INT_CONST: r'(\d+)',
    STRING_CONST: r'(".*?")',
    IDENTIFIER: r'([a-zA-Z_]+[a-zA-Z_\d]*)'
}


class JackTokenizer(object):
    cleaned_input = None

    def __init__(self, f):
        # read whole input into a stream
        input_stream = ''.join(
            self._remove_comments(line)
            for line in f
        ).replace('\n', '').replace('\r', '')
        # get rid of the block comments
        regex = r'(\/\*.*?\*\/)'
        input_stream += '/**/'
        spans = [m.span() for m in re.finditer(regex, input_stream)]
        cleaned_input = ''
        last_hi = 0
        for lo, hi in spans:
            cleaned_input += input_stream[last_hi:lo]
            last_hi = hi

        self.cleaned_input = cleaned_input.lstrip()

    def __iter__(self):
        return self

    def _remove_comments(self, line):
        start_from = 0
        while start_from != -1:
            comment = line.find('//', start_from)
            if comment == -1:
                return line
            # terminate if there is an even
            # number of quotes before comment
            if line[:comment].count('"') % 2 == 0:
                start_from = -1
            else:
                start_from = comment + 1

        return line[:comment].rstrip()

    def match_and_extract(self, token_type, advance=True):
        regex = REGEX_MAPPING[token_type]
        match = re.match(
            regex,
            self.cleaned_input
        )
        if match:
            word = match.groups()[0]
            token = word.strip('"')
            if advance:
                self.cleaned_input = self.cleaned_input.replace(
                    word, '', 1
                ).lstrip()
            return (token, token_type)

    def _next(self, advance=True):
        for token_type in TOKEN_TYPES:
            match = self.match_and_extract(token_type, advance)
            if match:
                return match
        raise RuntimeError

    def next(self):
        if not self.cleaned_input:
            raise StopIteration

        return self._next()

    def peek_next(self):
        return self._next(advance=False)


class ParseTree(object):
    """
    Class to store write-only Parse tree as an XML-formatted string
    """
    TAB_SIZE = 2

    def __init__(self):
        self.representation = ''
        self.level = 0

    def append_tag_with_text(self, tag, text):
        self.representation += self.indentation
        self.representation += '<%s> %s </%s>\n' % (tag, text, tag)

    def open_tag(self, tag):
        self.representation += self.indentation
        self.representation += '<%s>\n' % tag
        self.level += 1

    def close_tag(self, tag):
        self.level -= 1
        self.representation += self.indentation
        self.representation += '</%s>\n' % tag

    @property
    def indentation(self):
        assert self.level >= 0
        return (self.level * self.TAB_SIZE) * ' '

    def __str__(self):
        return self.representation

    def __repr__(self):
        return self.representation


class SymbolTable(object):
    def __init__(self):
        self.class_mapping = {}
        self.subroutine_mapping = {}
        self.count = {
            STATIC: 0,
            FIELD: 0,
            ARG: 0,
            VAR: 0
        }

    def start_subroutine(self):
        self.subroutine_mapping = {}
        self.count[ARG] = 0
        self.count[VAR] = 0

    def define(self, name, id_type, kind):
        assert kind in (STATIC, FIELD, VAR, ARG)
        data = {
            'type': id_type,
            'kind': kind,
            'index': self.count[kind]
        }
        if kind in (ARG, VAR):
            self.subroutine_mapping[name] = data
        else:
            self.class_mapping[name] = data
        self.count[kind] += 1

    def var_count(self, kind):
        return self.count.get(kind)

    def kind_of(self, name):
        return self._property_of(name, 'kind')

    def type_of(self, name):
        return self._property_of(name, 'type')

    def index_of(self, name):
        return self._property_of(name, 'index')

    def _property_of(self, name, prop):
        try:
            if name in self.subroutine_mapping:
                return self.subroutine_mapping[name][prop]
            return self.class_mapping[name][prop]
        except KeyError:
            return None


class VMWriter(object):
    def __init__(self):
        self.representation = ''

    def write_push(self, segment, index):
        self.representation += 'push %s %d\n' % (segment.lower(), int(index))

    def write_pop(self, segment, index):
        self.representation += 'pop %s %d\n' % (segment.lower(), int(index))

    def write_arithmetic(self, command):
        self.representation += command.lower() + '\n'

    def write_label(self, s):
        self.representation += 'label %s\n' % s

    def write_goto(self, s):
        self.representation += 'goto %s\n' % s

    def write_if(self, s):
        self.representation += 'if-goto %s\n' % s

    def write_call(self, name, arg_count):
        self.representation += 'call %s %d\n' % (name, arg_count)

    def write_function(self, name, local_count):
        self.representation += 'function %s %d\n' % (name, local_count)

    def write_return(self):
        self.representation += 'return\n'


class CompilationEngine(object):
    def __init__(self, f):
        self.tokenizer = JackTokenizer(f)
        self.token, self.token_type = next(self.tokenizer)
        self.parse_tree = ParseTree()
        self.symbol_table = SymbolTable()
        self.vm_writer = VMWriter()
        self.class_name = None
        self.while_index = 0
        self.if_index = 0
        # assign tree methods to current class
        # to avoid self.parse_tree boilerplate
        self.append_tag_with_text = self.parse_tree.append_tag_with_text
        self.open_tag = self.parse_tree.open_tag
        self.close_tag = self.parse_tree.close_tag
        self.compile_class()

    def get_identifier_info(self, name, category, action):
        if category not in (CLASS, SUBROUTINE):
            index_of = self.symbol_table.index_of(name)
            category = self.symbol_table.kind_of(name)
            if action is None:
                action = USED
            if index_of is not None:
                return '%s %s %s %s' % (name, category, index_of, action)
            return name
        return '%s %s %s' % (name, category, action)

    def eat(self, token_type, token):
        if self.token != token:
            raise RuntimeError(
                'Unexpected token '
                'self.token: %s, argument token: %s' % (self.token, token)
            )
        if self.token_type != token_type:
            raise RuntimeError(
                'Unexpected token_type '
                'self.token_type: %s, argument token_type: %s' % (
                    self.token_type, token_type
                )
            )
        self.previous_token = self.token
        try:
            self.token, self.token_type = next(self.tokenizer)
        except StopIteration:
            self.token = self.token_type = None

    def eat_and_append_token(self, token_type, token, category=None, action=None):
        self.eat(token_type, token)
        if token_type == IDENTIFIER:
            token = self.get_identifier_info(token, category, action)
        self.append_tag_with_text(
            token_type,
            token
        )

    def compile_class(self):
        self.open_tag('class')
        self.eat_and_append_token(
            KEYWORD,
            'class'
        )

        self.class_name = self.token

        self.eat_and_append_token(
            IDENTIFIER,
            self.token,
            category=CLASS,
            action=DEFINED
        )

        self.eat_and_append_token(
            SYMBOL,
            '{'
        )
        while self.token in ('static', 'field'):
            self.compile_class_var_dec()

        while self.token in ('function', 'method', 'constructor'):
            self.compile_subroutine()

        self.eat_and_append_token(SYMBOL, '}')
        self.close_tag('class')

    def compile_class_var_dec(self):
        self.open_tag('classVarDec')

        kind = self.token
        self.eat_and_append_token(
            self.token_type,
            self.token
        )
        id_type = self.token
        self.eat_and_append_token(
            self.token_type,
            self.token
        )
        self.symbol_table.define(
            self.token, id_type, kind
        )
        # identifier
        self.eat_and_append_token(
            IDENTIFIER,
            self.token,
            category=kind,
            action=DEFINED
        )

        while self.token == ',':
            self.eat_and_append_token(
                SYMBOL,
                ','
            )

            self.symbol_table.define(
                self.token, id_type, kind
            )
            self.eat_and_append_token(
                IDENTIFIER,
                self.token,
                category=kind,
                action=DEFINED
            )

        self.eat_and_append_token(
            SYMBOL,
            ';'
        )
        self.close_tag('classVarDec')

    def compile_subroutine(self):
        self.symbol_table.start_subroutine()
        self.open_tag('subroutineDec')

        subroutine_type = self.token  # method/function/constructor
        self.eat_and_append_token(
            self.token_type,
            self.token,
        )
        # return type
        self.eat_and_append_token(
            self.token_type,
            self.token
        )

        function_name = self.token

        self.eat_and_append_token(
            IDENTIFIER,
            self.token,
            category=SUBROUTINE,
            action=DEFINED
        )

        self.eat_and_append_token(
            SYMBOL,
            '('
        )
        if subroutine_type == 'method':
            self.symbol_table.define(
                'this',
                self.class_name,
                ARG
            )
        self.compile_parameter_list()
        self.eat_and_append_token(
            SYMBOL,
            ')'
        )

        self.open_tag('subroutineBody')

        self.eat_and_append_token(
            SYMBOL,
            '{'
        )

        while self.token == 'var':
            self.compile_var_dec()

        if subroutine_type == 'function':
            self.vm_writer.write_function(
                '%s.%s' % (self.class_name, function_name),
                self.symbol_table.var_count(VAR)
            )
        elif subroutine_type == 'constructor':
            self.vm_writer.write_function(
                '%s.%s' % (self.class_name, function_name),
                self.symbol_table.var_count(VAR)
            )
            number_of_fields = self.symbol_table.var_count(FIELD)
            self.vm_writer.write_push('constant', number_of_fields)
            self.vm_writer.write_call('Memory.alloc', 1)
            self.vm_writer.write_pop('pointer', 0)
        elif subroutine_type == 'method':
            self.vm_writer.write_function(
                '%s.%s' % (self.class_name, function_name),
                self.symbol_table.var_count(VAR)
            )
            self.vm_writer.write_push('argument', 0)  # this
            self.vm_writer.write_pop('pointer', 0)
        else:
            raise NotImplementedError

        self.compile_statements()

        self.eat_and_append_token(
            SYMBOL,
            '}'
        )
        self.close_tag('subroutineBody')
        self.close_tag('subroutineDec')

    def compile_parameter_list(self):
        self.open_tag('parameterList')
        while self.token_type in (IDENTIFIER, KEYWORD):
            self.eat_and_append_token(
                self.token_type, self.token
            )
            self.symbol_table.define(
                self.token,
                self.previous_token,
                ARG
            )
            self.eat_and_append_token(
                IDENTIFIER,
                self.token,
                category=ARG,
                action=DEFINED
            )
            if self.token == ',':
                self.eat_and_append_token(SYMBOL, ',')

        self.close_tag('parameterList')

    def compile_var_dec(self):
        self.open_tag('varDec')
        self.eat_and_append_token(
            KEYWORD,
            'var'
        )

        id_type = self.token
        self.eat_and_append_token(
            self.token_type,
            self.token
        )

        self.symbol_table.define(
            self.token,
            id_type,
            VAR
        )
        self.eat_and_append_token(
            IDENTIFIER,
            self.token,
            category=VAR,
            action=DEFINED

        )
        while self.token == ',':
            self.eat_and_append_token(
                SYMBOL,
                ','
            )

            self.symbol_table.define(
                self.token,
                id_type,
                VAR
            )

            self.eat_and_append_token(
                IDENTIFIER,
                self.token,
                category=VAR,
                action=DEFINED
            )

        self.eat_and_append_token(
            SYMBOL, ';'
        )
        self.close_tag('varDec')

    def compile_statements(self):
        self.open_tag('statements')
        statement_map = {
            'let': self.compile_let,
            'if': self.compile_if,
            'while': self.compile_while,
            'do': self.compile_do,
            'return': self.compile_return
        }
        while self.token in statement_map:
            statement_map[self.token]()

        self.close_tag('statements')

    def compile_subroutine_call(self):
        before_dot_or_paren = self.token
        self.eat_and_append_token(
            IDENTIFIER,
            self.token,
        )
        dot = self.token == '.'
        # . or (
        self.eat_and_append_token(
            SYMBOL,
            self.token
        )
        after_dot_or_paren = self.token
        if dot:
            self.eat_and_append_token(
                IDENTIFIER,
                self.token,
                category=SUBROUTINE,
                action=USED
            )
            self.eat_and_append_token(
                SYMBOL, '('
            )
        else:
            # push this as first argument
            self.vm_writer.write_push(
                'pointer',
                0
            )

        kind_of = self.symbol_table.kind_of(before_dot_or_paren)
        index_of = self.symbol_table.index_of(before_dot_or_paren)
        type_of = self.symbol_table.type_of(before_dot_or_paren)
        if kind_of == FIELD:
            self.vm_writer.write_push(
                'this',
                index_of
            )
        arg_count = self.compile_expression_list()
        if not kind_of:
            # static method(function)
            if dot:
                self.vm_writer.write_call(
                    '%s.%s' % (
                        before_dot_or_paren,
                        after_dot_or_paren
                    ),
                    arg_count
                )
            # object method
            else:
                self.vm_writer.write_call(
                    '%s.%s' % (
                        self.class_name,
                        before_dot_or_paren
                    ),
                    arg_count + 1
                )

        elif kind_of in (ARG, VAR, STATIC):
            self.vm_writer.write_push(kind_of, index_of)
            self.vm_writer.write_call(
                '%s.%s' % (type_of, after_dot_or_paren),
                arg_count + 1
            )
        elif kind_of == FIELD:
            self.vm_writer.write_call(
                '%s.%s' % (type_of, after_dot_or_paren),
                arg_count + 1
            )
        self.eat_and_append_token(
            SYMBOL, ')'
        )

    def compile_do(self):
        self.open_tag('doStatement')

        self.eat_and_append_token(
            KEYWORD, 'do'
        )
        self.compile_subroutine_call()
        self.eat_and_append_token(SYMBOL, ';')
        self.vm_writer.write_pop('temp', '0')
        self.close_tag('doStatement')

    def compile_let(self):
        self.open_tag('letStatement')

        self.eat_and_append_token(
            KEYWORD,
            'let'
        )

        variable = self.token

        self.eat_and_append_token(
            IDENTIFIER,
            self.token,
            action=USED
        )

        is_array_operation = False
        if self.token == '[':
            is_array_operation = True
            kind_of = self.symbol_table.kind_of(variable)
            index_of = self.symbol_table.index_of(variable)
            if kind_of == FIELD:
                kind_of = 'this'

            self.vm_writer.write_push(
                kind_of,
                index_of
            )

            self.eat_and_append_token(
                SYMBOL, '['
            )
            self.compile_expression()
            self.eat_and_append_token(
                SYMBOL, ']'
            )
            self.vm_writer.write_arithmetic('add')

        self.eat_and_append_token(
            SYMBOL,
            '='
        )
        self.compile_expression()
        if is_array_operation:
            self.vm_writer.write_pop('temp', 0)
            self.vm_writer.write_pop('pointer', 1)
            self.vm_writer.write_push('temp', 0)
            self.vm_writer.write_pop('that', 0)
        else:
            kind_of = self.symbol_table.kind_of(variable)
            index_of = self.symbol_table.index_of(variable)
            if kind_of == FIELD:
                kind_of = 'this'
            self.vm_writer.write_pop(
                kind_of,
                index_of
            )
        self.eat_and_append_token(
            SYMBOL,
            ';'
        )

        self.close_tag('letStatement')

    def compile_while(self):
        self.open_tag('whileStatement')
        current_while = self.while_index
        self.while_index += 1
        self.eat_and_append_token(KEYWORD, 'while')

        self.vm_writer.write_label('WHILE_EXP%d' % current_while)

        self.eat_and_append_token(SYMBOL, '(')
        self.compile_expression()
        self.eat_and_append_token(SYMBOL, ')')

        self.vm_writer.write_arithmetic('not')
        self.vm_writer.write_if('WHILE_END%d' % current_while)

        self.eat_and_append_token(SYMBOL, '{')
        self.compile_statements()
        self.vm_writer.write_goto('WHILE_EXP%d' % current_while)
        self.eat_and_append_token(SYMBOL, '}')
        self.vm_writer.write_label('WHILE_END%d' % current_while)
        self.close_tag('whileStatement')

    def compile_return(self):
        self.open_tag('returnStatement')
        self.eat_and_append_token(KEYWORD, 'return')
        if self.token != ';':
            self.compile_expression()
        else:
            self.vm_writer.write_push('constant', 0)
        self.eat_and_append_token(SYMBOL, ';')
        self.vm_writer.write_return()
        self.close_tag('returnStatement')

    def compile_if(self):
        self.open_tag('ifStatement')
        current_if = self.if_index
        self.if_index += 1
        self.eat_and_append_token(KEYWORD, 'if')
        self.eat_and_append_token(SYMBOL, '(')
        self.compile_expression()
        self.eat_and_append_token(SYMBOL, ')')

        self.vm_writer.write_arithmetic('not')

        self.vm_writer.write_if('IF_ELSE%d' % current_if)
        self.eat_and_append_token(SYMBOL, '{')
        self.compile_statements()
        self.eat_and_append_token(SYMBOL, '}')

        self.vm_writer.write_goto('IF_END%d' % current_if)

        if self.token == 'else':
            self.eat_and_append_token(KEYWORD, 'else')
            self.eat_and_append_token(SYMBOL, '{')
            self.vm_writer.write_label('IF_ELSE%d' % current_if)
            self.compile_statements()
            self.eat_and_append_token(SYMBOL, '}')
        else:
            self.vm_writer.write_label('IF_ELSE%d' % current_if)

        self.vm_writer.write_label('IF_END%d' % current_if)
        self.close_tag('ifStatement')

    def compile_expression(self):
        self.open_tag('expression')

        self.compile_term()
        operators = {
            '+': lambda: self.vm_writer.write_arithmetic('add'),
            '-': lambda: self.vm_writer.write_arithmetic('sub'),
            '*': lambda: self.vm_writer.write_call('Math.multiply', 2),
            '/': lambda: self.vm_writer.write_call('Math.divide', 2),
            '&': lambda: self.vm_writer.write_arithmetic('and'),
            '|': lambda: self.vm_writer.write_arithmetic('or'),
            '<': lambda: self.vm_writer.write_arithmetic('lt'),
            '>': lambda: self.vm_writer.write_arithmetic('gt'),
            '=': lambda: self.vm_writer.write_arithmetic('eq')
        }
        while self.token in operators:
            op = self.token
            self.eat_and_append_token(
                SYMBOL,
                self.token
            )
            self.compile_term()
            operators[op]()

        self.close_tag('expression')

    def compile_term(self):
        self.open_tag('term')

        ll_one_constants = (
            'true',
            'false',
            'null',
            'this'
        )
        unary_operators = ('-', '~',)

        if self.token_type == INT_CONST:
            self.vm_writer.write_push('constant', int(self.token))
            self.eat_and_append_token(
                self.token_type,
                self.token
            )
        elif self.token_type == STRING_CONST:
            length = len(self.token)
            self.vm_writer.write_push('constant', length)
            self.vm_writer.write_call('String.new', 1)
            for char in self.token:
                self.vm_writer.write_push('constant', ord(char))
                self.vm_writer.write_call('String.appendChar', 2)
            self.eat_and_append_token(
                self.token_type,
                self.token
            )
        elif self.token in ll_one_constants:
            if self.token == 'true':
                self.vm_writer.write_push('constant', 0)
                self.vm_writer.write_arithmetic('not')
            elif self.token == 'false' or self.token == 'null':
                self.vm_writer.write_push('constant', 0)
            elif self.token == 'this':
                self.vm_writer.write_push('pointer', 0)

            self.eat_and_append_token(
                self.token_type,
                self.token
            )
        elif self.token in unary_operators:
            operator = self.token
            self.eat_and_append_token(
                SYMBOL, self.token
            )
            self.compile_term()
            if operator == '-':
                self.vm_writer.write_arithmetic('neg')
            else:
                self.vm_writer.write_arithmetic('not')
        elif self.token_type == IDENTIFIER:  # LL(2)
            token, _ = self.tokenizer.peek_next()
            if token == '[':
                kind_of = self.symbol_table.kind_of(self.token)
                index_of = self.symbol_table.index_of(self.token)

                self.eat_and_append_token(
                    IDENTIFIER,
                    self.token
                )
                if kind_of == FIELD:
                    kind_of = 'this'
                self.vm_writer.write_push(
                    kind_of,
                    index_of
                )
                self.eat_and_append_token(
                    SYMBOL, '['
                )
                self.compile_expression()
                self.eat_and_append_token(
                    SYMBOL, ']'
                )
                self.vm_writer.write_arithmetic('add')
                self.vm_writer.write_pop('pointer', 1)
                self.vm_writer.write_push('that', 0)
            elif token in ('.', '('):
                self.compile_subroutine_call()
            else:
                segment = self.symbol_table.kind_of(self.token)
                index = self.symbol_table.index_of(self.token)
                assert segment is not None and index is not None
                if segment == FIELD:
                    segment = 'this'
                self.vm_writer.write_push(
                    segment,
                    index
                )
                self.eat_and_append_token(
                    IDENTIFIER, self.token
                )
        elif self.token == '(':
            self.eat_and_append_token(
                SYMBOL, '('
            )
            self.compile_expression()
            self.eat_and_append_token(
                SYMBOL, ')'
            )
        else:
            raise NotImplementedError
        self.close_tag('term')

    def compile_expression_list(self):
        self.open_tag('expressionList')
        arg_count = 0
        while self.token != ')':
            self.compile_expression()
            if self.token == ',':
                self.eat_and_append_token(
                    SYMBOL,
                    ','
                )
            arg_count += 1
        self.close_tag('expressionList')
        return arg_count


file_list = []
path = sys.argv[1]
# print('<tokens>')
# for token, token_type in JackTokenizer(open(path)):
#     print('<%s> %s </%s>' % (token_type, token, token_type))
# print('</tokens>')
is_dir = os.path.isdir(path)
if not is_dir:
    file_list.append(path)
else:
    if not path.endswith('/'):
        path = path + '/'
    for filename in os.listdir(path):
        if filename.endswith('.jack'):
            path_to_file = os.path.join(path, filename)
            file_list.append(path_to_file)


for filename in file_list:
    with open(filename.replace('.jack', '.vm'), 'w') as f:
        current_file = open(filename)
        compiled = CompilationEngine(current_file)
        # print(compiled.vm_writer.representation)
        f.write(str(compiled.vm_writer.representation))
        current_file.close()

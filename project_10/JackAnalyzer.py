import cgi
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


REGEX_MAPPING = {
    KEYWORD: '(' + r'|'.join(KEYWORDS) + ')\\W',
    SYMBOL: r'([&)\]+\*\-,\/<.}([{;~=|>])',
    INT_CONST: r'(\d+)',
    STRING_CONST: r'(".*?")',
    IDENTIFIER: r'([a-zA-Z_]+[a-zA-Z_\d]*)'
}


def remove_comments(line):
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


class JackTokenizer(object):
    cleaned_input = None

    def __init__(self, f):
        # read whole input into a stream
        input_stream = ''.join(
            remove_comments(line)
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

    def match_and_extract(self, token_type, advance=True):
        regex = REGEX_MAPPING[token_type]
        match = re.match(
            regex,
            self.cleaned_input
        )
        if match:
            word = match.groups()[0]
            token = cgi.escape(word).strip('"')
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
    representation = None
    level = 0

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


class CompilationEngine(object):
    tokenizer = None

    token = None
    token_type = None
    parse_tree = None

    def __init__(self, f):
        self.tokenizer = JackTokenizer(f)
        self.token, self.token_type = next(self.tokenizer)
        self.parse_tree = ParseTree()
        # assign tree methods to current class
        # to avoid self.parse_tree boilerplate
        self.append_tag_with_text = self.parse_tree.append_tag_with_text
        self.open_tag = self.parse_tree.open_tag
        self.close_tag = self.parse_tree.close_tag
        self.compile_class()

    def eat_and_append_token(self, token_type, token):
        self.append_tag_with_text(
            token_type,
            token
        )
        self.eat(token_type, token)

    def compile_class(self):
        self.open_tag('class')
        self.eat_and_append_token(
            KEYWORD,
            'class'
        )

        self.eat_and_append_token(
            IDENTIFIER,
            self.token
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
        self.eat_and_append_token(
            self.token_type,
            self.token
        )
        self.eat_and_append_token(
            self.token_type,
            self.token
        )
        # identifier
        self.eat_and_append_token(
            IDENTIFIER,
            self.token
        )

        while self.token == ',':
            self.eat_and_append_token(
                SYMBOL,
                ','
            )

            self.eat_and_append_token(
                IDENTIFIER,
                self.token
            )

        self.eat_and_append_token(
            SYMBOL,
            ';'
        )
        self.close_tag('classVarDec')

    def compile_subroutine(self):
        self.open_tag('subroutineDec')
        self.eat_and_append_token(
            self.token_type,
            self.token
        )
        # return type
        self.eat_and_append_token(
            self.token_type,
            self.token
        )

        self.eat_and_append_token(
            IDENTIFIER,
            self.token
        )

        self.eat_and_append_token(
            SYMBOL,
            '('
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
            self.eat_and_append_token(IDENTIFIER, self.token)
            if self.token == ',':
                self.eat_and_append_token(SYMBOL, ',')

        self.close_tag('parameterList')

    def compile_var_dec(self):
        self.open_tag('varDec')
        self.eat_and_append_token(
            KEYWORD,
            'var'
        )

        self.eat_and_append_token(
            self.token_type,
            self.token
        )

        self.eat_and_append_token(
            IDENTIFIER,
            self.token
        )
        while self.token == ',':
            self.eat_and_append_token(
                SYMBOL,
                ','
            )

            self.eat_and_append_token(
                IDENTIFIER,
                self.token
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
        self.eat_and_append_token(
            IDENTIFIER,
            self.token
        )
        # . or (
        self.eat_and_append_token(
            SYMBOL,
            self.token
        )
        if self.token_type == IDENTIFIER:
            self.eat_and_append_token(
                IDENTIFIER,
                self.token
            )
            self.eat_and_append_token(
                SYMBOL, '('
            )
        self.compile_expression_list()
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
        self.close_tag('doStatement')

    def compile_let(self):
        self.open_tag('letStatement')

        self.eat_and_append_token(
            KEYWORD,
            'let'
        )

        self.eat_and_append_token(
            IDENTIFIER,
            self.token
        )

        if self.token == '[':
            self.eat_and_append_token(
                SYMBOL, '['
            )
            self.compile_expression()
            self.eat_and_append_token(
                SYMBOL, ']'
            )

        self.eat_and_append_token(
            SYMBOL,
            '='
        )
        self.compile_expression()

        self.eat_and_append_token(
            SYMBOL,
            ';'
        )

        self.close_tag('letStatement')

    def compile_while(self):
        self.open_tag('whileStatement')
        self.eat_and_append_token(KEYWORD, 'while')
        self.eat_and_append_token(SYMBOL, '(')
        self.compile_expression()
        self.eat_and_append_token(SYMBOL, ')')
        self.eat_and_append_token(SYMBOL, '{')
        self.compile_statements()
        self.eat_and_append_token(SYMBOL, '}')
        self.close_tag('whileStatement')

    def compile_return(self):
        self.open_tag('returnStatement')
        self.eat_and_append_token(KEYWORD, 'return')
        if self.token != ';':
            self.compile_expression()
        self.eat_and_append_token(SYMBOL, ';')
        self.close_tag('returnStatement')

    def compile_if(self):
        self.open_tag('ifStatement')
        self.eat_and_append_token(KEYWORD, 'if')
        self.eat_and_append_token(SYMBOL, '(')
        self.compile_expression()
        self.eat_and_append_token(SYMBOL, ')')

        self.eat_and_append_token(SYMBOL, '{')
        self.compile_statements()
        self.eat_and_append_token(SYMBOL, '}')

        if self.token == 'else':
            self.eat_and_append_token(KEYWORD, 'else')
            self.eat_and_append_token(SYMBOL, '{')
            self.compile_statements()
            self.eat_and_append_token(SYMBOL, '}')

        self.close_tag('ifStatement')

    def compile_expression(self):
        self.open_tag('expression')

        self.compile_term()
        operators = map(cgi.escape, (
            '+',
            '-',
            '*',
            '/',
            '&',
            '|',
            '<',
            '>',
            '='
        ))
        while self.token in operators:
            self.eat_and_append_token(
                SYMBOL,
                self.token
            )
            self.compile_term()

        self.close_tag('expression')

    def compile_term(self):
        self.open_tag('term')

        ll_one_types = (
            INT_CONST,
            STRING_CONST
        )
        ll_one_constants = (
            'true',
            'false',
            'null',
            'this'
        )
        unary_operators = ('-', '~',)

        if self.token_type in ll_one_types or self.token in ll_one_constants:
            self.eat_and_append_token(
                self.token_type,
                self.token
            )
        elif self.token in unary_operators:
            self.eat_and_append_token(
                SYMBOL, self.token
            )
            self.compile_term()
        elif self.token_type == IDENTIFIER:  # LL(2)
            token, _ = self.tokenizer.peek_next()
            if token == '[':
                self.eat_and_append_token(
                    IDENTIFIER, self.token
                )
                self.eat_and_append_token(
                    SYMBOL, '['
                )
                self.compile_expression()
                self.eat_and_append_token(
                    SYMBOL, ']'
                )
            elif token in ('.', '('):
                self.compile_subroutine_call()
            else:
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
        while self.token != ')':
            self.compile_expression()
            if self.token == ',':
                self.eat_and_append_token(
                    SYMBOL,
                    ','
                )
        self.close_tag('expressionList')

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
        try:
            self.token, self.token_type = next(self.tokenizer)
        except StopIteration:
            self.token = self.token_type = None


file_list = []
path = sys.argv[1]
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
    with open(filename.replace('.jack', '.xml'), 'w') as f:
        current_file = open(filename)
        compiled = CompilationEngine(current_file)
        f.write(str(compiled.parse_tree))
        current_file.close()

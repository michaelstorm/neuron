from neuron.visitor import BrainfuckCompilerVisitor
from neuron.bf import BrainfuckRuntime

from pycparser import parse_file
import re
import sys


def pretty_print_bf(code):
    output = ''
    tabs = 0
    newline = False
    is_color_code = False
    current_color_code = ''
    color_codes = []

    printed_non_space_char = False
    last_non_space_char = None

    for i, c in enumerate(code):
        if c == '\033':
            is_color_code = True
            current_color_code = ''

        if is_color_code:
            current_color_code += c

        else:
            if c == '(' and last_non_space_char != None:
                tabs += 1
                newline = True

            if newline: # and last_non_space_char != ')':
                if printed_non_space_char:
                    output += "\033[0m\n"
                    for color_code in color_codes:
                        output += color_code

                output += "\t" * tabs
                newline = False
                printed_non_space_char = False

        output += c

        if not is_color_code:
            if c == ')':
                tabs -= 1
                newline = True

            if not c.isspace():
                printed_non_space_char = True
                last_non_space_char = c

        elif c == 'm':
            is_color_code = False
            if current_color_code == '\033[39m':
                color_codes = []
            else:
                color_codes.append(current_color_code)

    return output


if __name__ == "__main__":
    filename = sys.argv[1]
    ast = parse_file(filename, use_cpp=True)

    with open(filename, 'r') as f:
        source = f.read()

    brainfuck_compiler_visitor = BrainfuckCompilerVisitor()
    brainfuck_compiler_visitor.visit(ast)

    code, declaration_mapper, symbol_table, static_data, _ = brainfuck_compiler_visitor.to_bf()
    pretty_printed_bf = pretty_print_bf(re.sub(r'\s+', ' ', code))

    runtime = BrainfuckRuntime(declaration_mapper, source, static_data, symbol_table)
    runtime.execute(pretty_printed_bf, debug=True)

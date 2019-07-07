from neuron.visitor import BrainfuckCompilerVisitor
from neuron.bf import BrainfuckRuntime

from pycparser import parse_file
import re


def pretty_print_bf(code):
    output = ''
    tabs = 0
    newline = False
    color_code = False
    printed_non_space_char = False
    last_non_space_char = None

    for i, c in enumerate(code):
        if c == '\033':
            color_code = True

        if not color_code:
            if c == '(' and last_non_space_char != None:
                tabs += 1
                newline = True

            if newline: # and last_non_space_char != ')':
                if printed_non_space_char:
                    output += "\n"

                output += "\t" * tabs
                newline = False
                printed_non_space_char = False

        output += c

        if not color_code:
            if c == ')':
                tabs -= 1
                newline = True

            if not c.isspace():
                printed_non_space_char = True
                last_non_space_char = c

        elif c == 'm':
            color_code = False

    return output


if __name__ == "__main__":
    filename = 'hash.c'
    ast = parse_file(filename, use_cpp=True)

    with open(filename, 'r') as f:
        source = f.read()

    brainfuck_compiler_visitor = BrainfuckCompilerVisitor()
    brainfuck_compiler_visitor.visit(ast)

    code, declaration_mapper, symbol_table, static_data, _ = brainfuck_compiler_visitor.to_bf()
    pretty_printed_bf = pretty_print_bf(re.sub(r'\s+', ' ', code))

    runtime = BrainfuckRuntime(declaration_mapper, source, static_data, symbol_table)
    runtime.execute(pretty_printed_bf, debug=True)

from neuron.visitor import BrainfuckCompilerVisitor
from neuron.bf import BrainfuckRuntime

from pycparser import parse_file
import re


def pretty_print_bf(code):
    output = ''
    tabs = 0
    newline = False
    for i, c in enumerate(code):
        if c == '(' and i > 0:
            tabs += 1
            newline = True

        if c != ')' and newline:
            output += "\n{}".format("\t" * tabs)
            newline = False

        output += c
        if c == ')':
            tabs -= 1
            newline = True
    return output


if __name__ == "__main__":
    filename = 'hash.c'
    ast = parse_file(filename, use_cpp=True)

    with open(filename, 'r') as f:
        source = f.read()

    brainfuck_compiler_visitor = BrainfuckCompilerVisitor()
    brainfuck_compiler_visitor.visit(ast)

    code, declaration_positions, symbol_table, static_data, _ = brainfuck_compiler_visitor.to_bf()
    pretty_printed_bf = pretty_print_bf(re.sub(r'\s+', ' ', code))

    runtime = BrainfuckRuntime(declaration_positions, source, static_data, symbol_table)
    runtime.execute(pretty_printed_bf, debug=True)

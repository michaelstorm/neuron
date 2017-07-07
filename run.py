from neuron.visitor import BrainfuckCompilerVisitor
from neuron.bf import BrainfuckRuntime

from pycparser import parse_file


if __name__ == "__main__":
    filename = 'hash.c'
    ast = parse_file(filename, use_cpp=True)

    with open(filename, 'r') as f:
        source = f.read()

    brainfuck_compiler_visitor = BrainfuckCompilerVisitor()
    brainfuck_compiler_visitor.visit(ast)

    code, symbol_table = brainfuck_compiler_visitor.to_bf()

    runtime = BrainfuckRuntime(brainfuck_compiler_visitor.declarations, source, symbol_table)
    runtime.execute(code)

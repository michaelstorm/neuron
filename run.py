from neuron.visitor import BrainfuckCompilerVisitor
from neuron.bf import BrainfuckRuntime

from pycparser import parse_file


if __name__ == "__main__":
    filename = 'hash.c'
    ast = parse_file(filename, use_cpp=True)

    brainfuck_compiler_visitor = BrainfuckCompilerVisitor()
    brainfuck_compiler_visitor.visit(ast)

    code = brainfuck_compiler_visitor.to_bf()

    runtime = BrainfuckRuntime(brainfuck_compiler_visitor.declarations)
    runtime.execute(code)

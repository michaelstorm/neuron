from pycparser import parse_file
from visitor import PrettyPrintVisitor, BrainfuckCompilerVisitor
from bf import BrainfuckRuntime


if __name__ == "__main__":
    filename = 'hash.c'
    ast = parse_file(filename, use_cpp=True)
    pretty_print_visitor = PrettyPrintVisitor()
    # pretty_print_visitor.visit(ast)

    brainfuck_compiler_visitor = BrainfuckCompilerVisitor()
    brainfuck_compiler_visitor.visit(ast)

    code = brainfuck_compiler_visitor.to_bf()

    runtime = BrainfuckRuntime()
    runtime.execute(code)

from pycparser import parse_file
from visitor import FuncCallVisitor
from bf import BrainfuckRuntime


if __name__ == "__main__":
    filename = 'hash.c'
    ast = parse_file(filename, use_cpp=True)
    v = FuncCallVisitor()
    v.visit(ast)

    code = v.to_bf()

    runtime = BrainfuckRuntime()
    runtime.execute(code)

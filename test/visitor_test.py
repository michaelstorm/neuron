from neuron.bf import BrainfuckRuntime
from neuron.visitor import BrainfuckCompilerVisitor
from neuron.commands import *

from pycparser import c_parser
from unittest import TestCase


class VisitorTest(TestCase):
    def compile_test(self):
        source = """
        int main()
        {
            int x = 2;
            int y;
        }
        """

        ast = c_parser.CParser().parse(source)

        brainfuck_compiler_visitor = BrainfuckCompilerVisitor()
        brainfuck_compiler_visitor.visit(ast)
        code = brainfuck_compiler_visitor.to_bf()

        print(code)

        self.assertEqual(['x', 'x_0'], brainfuck_compiler_visitor.declarations)

        main = brainfuck_compiler_visitor.functions['main']
        self.assertEqual(1, len(main))
        self.assertEqual(0, main[0].index)
        self.assertIsNone(main[0].next)

        self.assertEqual(SetValue(name='x_0', value='2', type='int'), main[0].ops[0])
        self.assertEqual(Zero(name='x'), main[0].ops[1])
        self.assertEqual(Move(from_name='x_0', to_name='x'), main[0].ops[2])

        raise Exception()

    def if_test(self):
        source = """
        int main()
        {
            int x = 2;
            int y = 0;
            if (0) {
                y = 1;
            }
            else {
                if (x) {
                    y = 3;
                }
            }
        }
        """

        ast = c_parser.CParser().parse(source)

        brainfuck_compiler_visitor = BrainfuckCompilerVisitor()
        brainfuck_compiler_visitor.visit(ast)
        code = brainfuck_compiler_visitor.to_bf()

        # runtime = BrainfuckRuntime(brainfuck_compiler_visitor.declarations)
        # runtime.execute(code)

        print(code)

        self.assertEqual(['x', 'x_0', 'y', 'y_0', 'if', 'if_0', 'y_1', 'if_1', 'y_2'],
                         brainfuck_compiler_visitor.declarations)

        main = brainfuck_compiler_visitor.functions['main']
        self.assertEqual(1, len(main))
        self.assertEqual(0, main[0].index)
        self.assertIsNone(main[0].next)

        self.assertEqual(SetValue(name='x_0', value='2', type='int'), main[0].ops[0])
        self.assertEqual(Zero(name='x'), main[0].ops[1])
        self.assertEqual(Move(from_name='x_0', to_name='x'), main[0].ops[2])

        raise Exception()

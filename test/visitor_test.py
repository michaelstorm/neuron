from neuron.bf import BrainfuckRuntime
from neuron.visitor import BrainfuckCompilerVisitor, EndBlock
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
        code, _, blocks = brainfuck_compiler_visitor.to_bf()

        self.assertEqual(['x', 'x_0', 'y'], brainfuck_compiler_visitor.declarations)

        main = brainfuck_compiler_visitor.functions['main']
        self.assertEqual(0, main[0].index)

        self.assertEqual(2, len(blocks))
        end_block = blocks[main[0].next_index]
        self.assertEqual(EndBlock, type(end_block))

        self.assertEqual(SetValue(name='x_0', value='2', type='int', coord=':4'), main[0].ops[0])
        self.assertEqual(Zero(name='x', coord=':4'), main[0].ops[1])
        self.assertEqual(Move(from_name='x_0', to_name='x', coord=':4'), main[0].ops[2])

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
        code, symbol_table, _ = brainfuck_compiler_visitor.to_bf()

        runtime = BrainfuckRuntime(brainfuck_compiler_visitor.declarations, source, symbol_table)
        runtime.execute(code)

        print(code)
        print(runtime.get_declaration_value('y'))

        self.assertEqual(['x', 'x_0', 'y', 'y_0', 'if', 'if_0', 'y_1', 'if_1', 'y_2'],
                         brainfuck_compiler_visitor.declarations)

        main = brainfuck_compiler_visitor.functions['main']
        print('MAIN', main[0])
        print('MAIN', main[1])
        print('MAIN', main[2])

        self.assertEqual(0, main[0].index)
        self.assertIsNone(main[0].next)

        self.assertEqual(SetValue(name='x_0', value='2', type='int'), main[0].ops[0])
        self.assertEqual(Zero(name='x'), main[0].ops[1])
        self.assertEqual(Move(from_name='x_0', to_name='x'), main[0].ops[2])

        raise Exception()

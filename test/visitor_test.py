from neuron.bf import BrainfuckRuntime
from neuron.visitor import BrainfuckCompilerVisitor, EndBlock
from neuron.commands import *

from pycparser import c_parser
from unittest import TestCase


class VisitorTest(TestCase):
    def execute_code(self, source):
        ast = c_parser.CParser().parse(source)

        visitor = BrainfuckCompilerVisitor()
        visitor.visit(ast)
        code, symbol_table, blocks = visitor.to_bf()

        runtime = BrainfuckRuntime(visitor.declarations, source, symbol_table)
        runtime.execute(code)

        return code, symbol_table, blocks, visitor, runtime

    def compile_test(self):
        source = """
        int main()
        {
            int x = 2;
            int y;
        }
        """

        code, symbol_table, blocks, visitor, runtime = self.execute_code(source)

        self.assertEqual(['x', 'x_0', 'y'], visitor.declarations)

        main = visitor.functions['main']
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

        code, symbol_table, blocks, visitor, runtime = self.execute_code(source)

        self.assertEqual(['x', 'x_0', 'y', 'y_0', 'if', 'if_0', 'y_1', 'if_1', 'y_2'],
                         visitor.declarations)

        self.assertEqual(2, runtime.get_declaration_value('x'))
        self.assertEqual(3, runtime.get_declaration_value('y'))

    def chained_if_else_test(self):
        source = """
        int main()
        {
            int y;
            if (3) {
                y = 1;
            }
            else if (1) {
                y = 2;
            }
            else if (0) {
                y = 3;
            }
        }
        """

        code, symbol_table, blocks, visitor, runtime = self.execute_code(source)

        self.assertEqual(1, runtime.get_declaration_value('y'))

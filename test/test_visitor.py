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
        code, declaration_mapper, symbol_table, static_data, blocks = visitor.to_bf()

        runtime = BrainfuckRuntime(declaration_mapper, visitor.declarations, source, symbol_table)
        runtime.execute(code)

        return code, symbol_table, blocks, visitor, runtime

    def test_compile(self):
        source = """
        int main()
        {
            int x = 2;
            int y;
        }
        """

        code, symbol_table, blocks, visitor, runtime = self.execute_code(source)

        self.assertEqual(set(['x', 'x~0', 'y']), set([d.name for d in visitor.declarations]))

        main = visitor.functions['main']
        self.assertEqual(0, main[0].index)

        self.assertEqual(2, len(blocks))
        end_block = blocks[main[0].next_index]
        self.assertEqual(EndBlock, type(end_block))

        self.assertEqual(SetValue(name='x~0', value='2', type='int', coord=':4'), main[0].ops[0])
        self.assertEqual(Zero(name='x', coord=':4'), main[0].ops[1])
        self.assertEqual(Move(from_name='x~0', to_name='x', coord=':4'), main[0].ops[2])

    def test_if(self):
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

        self.assertEqual(set(['x', 'x~0', 'y', 'y~0', 'if', 'if~0', 'y~1', 'if~1', 'y~2']),
                         set([d.name for d in visitor.declarations]))

        self.assertEqual(2, runtime.get_declaration_value('x'))
        self.assertEqual(3, runtime.get_declaration_value('y'))

    def test_chained_if_else(self):
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
            else {
                y = 4;
            }
        }
        """

        *_, runtime = self.execute_code(source)
        self.assertEqual(1, runtime.get_declaration_value('y'))

        source = """
        int main()
        {
            int y;
            if (0) {
                y = 1;
            }
            else if (1) {
                y = 2;
            }
            else if (0) {
                y = 3;
            }
            else {
                y = 4;
            }
        }
        """

        *_, runtime = self.execute_code(source)
        self.assertEqual(2, runtime.get_declaration_value('y'))

        source = """
        int main()
        {
            int y;
            if (0) {
                y = 1;
            }
            else if (0) {
                y = 2;
            }
            else if (0) {
                y = 3;
            }
            else {
                y = 4;
            }
        }
        """

        *_, runtime = self.execute_code(source)
        self.assertEqual(4, runtime.get_declaration_value('y'))

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

        _, _, blocks, visitor, _ = self.execute_code(source)

        self.assertEqual(set(['x', 'x~0', 'y']), set([d.name for d in visitor.declarations]))

        main = visitor.functions['main']
        self.assertEqual(0, main[0].index)

        self.assertEqual(2, len(blocks))
        end_block = blocks[main[0].next_index]
        self.assertEqual(EndBlock, type(end_block))

        self.assertEqual(SetValue(name='x~0', value='2', type='int', coord=':4'), main[0].ops[0])
        self.assertEqual(Zero(name='x', coord=':4'), main[0].ops[1])
        self.assertEqual(Move(from_name='x~0', to_name='x', coord=':4'), main[0].ops[2])

    def test_initlist(self):
        source = """
        int main()
        {
            int x[2] = {2, 3};
        }
        """

        *_, runtime = self.execute_code(source)
        self.assertEqual(2, runtime.get_array_value('x', 0))
        self.assertEqual(3, runtime.get_array_value('x', 1))

    def test_math(self):
        source = "int main() { int x; }"
        *_, runtime = self.execute_code(source)
        self.assertEqual(0, runtime.get_declaration_value('x'))

        source = "int main() { int x = 2; }"
        *_, runtime = self.execute_code(source)
        self.assertEqual(2, runtime.get_declaration_value('x'))

        source = "int main() { int x = 2 * 3; }"
        *_, runtime = self.execute_code(source)
        self.assertEqual(6, runtime.get_declaration_value('x'))

        source = "int main() { int x = 2 * 3 + 5; }"
        *_, runtime = self.execute_code(source)
        self.assertEqual(11, runtime.get_declaration_value('x'))

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

        *_, visitor, runtime = self.execute_code(source)

        self.assertEqual(set(['x', 'x~0', 'y', 'y~0', 'if', 'if~0', 'y~1', 'if~1', 'y~2']),
                         set([d.name for d in visitor.declarations]))

        self.assertEqual(2, runtime.get_declaration_value('x'))
        self.assertEqual(3, runtime.get_declaration_value('y'))

    def test_chained_if_else(self):
        source = """
        int main()
        {
            int y;
            if (3) { y = 1; }
            else if (1) { y = 2; }
            else if (0) { y = 3; }
            else { y = 4; }
        }
        """

        *_, runtime = self.execute_code(source)
        self.assertEqual(1, runtime.get_declaration_value('y'))

        source = """
        int main()
        {
            int y;
            if (0) { y = 1; }
            else if (1) { y = 2; }
            else if (0) { y = 3; }
            else { y = 4; }
        }
        """

        *_, runtime = self.execute_code(source)
        self.assertEqual(2, runtime.get_declaration_value('y'))

        source = """
        int main()
        {
            int y;
            if (0) { y = 1; }
            else if (0) { y = 2; }
            else if (0) { y = 3; }
            else { y = 4; }
        }
        """

        *_, runtime = self.execute_code(source)
        self.assertEqual(4, runtime.get_declaration_value('y'))

    def test_addressable_memory(self):
        source = """
        int main()
        {
            char a;
            char b;
            char c[2];
            c[1] = 4;
            b = c[1];
        }
        """

        *_, visitor, runtime = self.execute_code(source)

        self.assertEqual(set(['a', 'b', 'c', 'c~0', 'c~sub~0', 'c~rvalue~0']),
                         set([d.name for d in visitor.declarations]))

        self.assertEqual(4, runtime.get_declaration_value('b'))
        self.assertEqual(4, runtime.get_array_value('c', 1))

    def test_string(self):
        source = """
        int main()
        {
            char a = "abc";
            puts(a);
        }
        """

        *_, visitor, runtime = self.execute_code(source)

        self.assertEqual(set(['a', 'a~0', 'puts~arg~0', 'puts~arg~0~0']),
                         set([d.name for d in visitor.declarations]))

        self.assertEqual("abc", runtime.states[0].output)

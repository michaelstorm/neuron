from collections import namedtuple
from pycparser import c_parser, c_ast, parse_file
from commands import *
from ordered_set import OrderedSet


class FuncCallVisitor(c_ast.NodeVisitor):
    def __init__(self):
        self.level = 0
        self.in_compound = False
        self.declarations = OrderedSet()
        self.ops = []

        self.modifications_by_decl_name = {}
        self.decl_name_stack = []

    def lprint(self, *msg):
        print('  ' * self.level, end='')
        print(*msg)

    def aprint(self, name, *msg):
        self.lprint('>', name + ':', *msg)

    def visit_children(self, node):
        self.level += 1
        results = [self.visit(c) for (c_name, c) in node.children()]
        self.level -= 1
        return results

    def visit_child(self, node):
        self.level += 1
        result = self.visit(node)
        self.level -= 1
        return result

    def push_decl_mod(self, decl_name):
        mod_count = self.modifications_by_decl_name.get(decl_name, 0)
        self.modifications_by_decl_name[decl_name] = mod_count + 1
        return self.push_sub_decl(mod_count)

    def push_sub_decl(self, suffix):
        decl_name = '{}_{}'.format(self.decl_name_stack[-1], suffix)
        self.push_decl(decl_name)
        return decl_name

    def push_decl(self, decl_name):
        self.declarations.add(decl_name)
        self.decl_name_stack.append(decl_name)

    def pop_decl(self):
        self.decl_name_stack.pop()

    def visit_Decl(self, node):
        self.lprint(node.__class__.__name__)
        self.aprint('name', node.name)

        if self.in_compound:
            self.push_decl(node.name)
            decl_name = self.push_decl_mod(node.name)

            child_results = self.visit_children(node)
            if len(child_results) > 1:
                self.ops.append(Move(from_name=decl_name, to_name=node.name))

            self.pop_decl()
            self.pop_decl()
        else:
            self.visit_children(node)

    def visit_BinaryOp(self, node):
        self.lprint(node.__class__.__name__)
        self.aprint('op', node.op)

        first_name = self.push_sub_decl('a')
        self.visit_child(node.left)
        self.pop_decl()

        second_name = self.push_sub_decl('b')
        self.visit_child(node.right)
        self.pop_decl()

        if node.op == '+':
            self.ops.append(Add(result_name=self.decl_name_stack[-1], first_name=first_name,
                                second_name=second_name))
        elif node.op == '*':
            self.ops.append(Multiply(result_name=self.decl_name_stack[-1], first_name=first_name,
                                     second_name=second_name))

    def visit_Constant(self, node):
        self.lprint(node.__class__.__name__)

        self.ops.append(SetValue(name=self.decl_name_stack[-1], value=node.value))

    def visit_Compound(self, node):
        self.lprint(node.__class__.__name__)

        self.in_compound = True
        self.visit_children(node)
        self.in_compound = False

    def visit_Assignment(self, node):
        self.lprint(node.__class__.__name__)

        result_name = node.lvalue.name

        self.push_decl(result_name)
        decl_name = self.push_decl_mod(result_name)

        self.visit_child(node.rvalue)
        self.ops.append(Zero(name=result_name))
        self.ops.append(Move(from_name=decl_name, to_name=result_name))

        self.pop_decl()

    def generic_visit(self, node):
        self.lprint(node.__class__.__name__)
        self.visit_children(node)

    def to_bf(self):
        print()
        print('self.declarations', self.declarations)
        print('self.modifications_by_decl_name', self.modifications_by_decl_name)
        print('self.ops', self.ops)
        print()

        output = ''

        declaration_positions = {decl_name: index
                                 for (index, decl_name)
                                 in enumerate(self.declarations)}

        print(declaration_positions)
        print()

        for op in self.ops:
            output += op.to_bf(declaration_positions)

        return output

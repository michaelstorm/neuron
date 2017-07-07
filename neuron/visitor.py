from collections import namedtuple, OrderedDict
from pycparser import c_parser, c_ast, parse_file
from .commands import *
from .ordered_set import OrderedSet


class Block:
    def __init__(self, index, ops=[]):
        self.index = index
        self.ops = list(ops)
        self.next = None

    def __repr__(self):
        next_id = self.next.index if self.next else None
        return 'Block(index=%s, ops=%s, next=%s)' % (self.index, self.ops.__repr__(), next_id)


class IfBlock:
    def __init__(self, index, cond_block, true_blocks, false_blocks, decl_name):
        self.index = index
        self.cond_block = cond_block
        self.true_blocks = true_blocks
        self.false_blocks = false_blocks
        self.decl_name = decl_name

    def __str__(self):
        return "IfBlock(index={}, decl_name={}, true_blocks={}, false_blocks={}, cond_block={})".format(
            self.index, self.decl_name, [b.index for b in self.true_blocks or []],
            [b.index for b in self.false_blocks or []], self.cond_block)

    def __repr__(self):
        return self.__str__()


class BrainfuckCompilerVisitor(c_ast.NodeVisitor):
    def __init__(self):
        self.level = 0
        self.next_block_index = 0
        self.declarations = OrderedSet()
        self.functions = {}

        self.modifications_by_decl_name = {}
        self.decl_name_stack = []

    def lprint(self, *msg):
        print('  ' * self.level, end='')
        print(*msg)

    def aprint(self, name, *msg):
        self.lprint('>', name + ':', *msg)

    def visit_children(self, node):
        if node != None:
            self.level += 1
            results = []
            for c_name, c in node.children():
                results.extend(self.visit(c))
            self.level -= 1
            return results

    def visit_child(self, node):
        self.level += 1
        result = self.visit(node)
        self.level -= 1
        return result

    def visit_assignment_body(self, coord, result_name, assignment_body):
        self.push_decl(result_name)

        if assignment_body:
            decl_name = self.push_decl_mod(result_name)

            ops = []
            ops = list(self.visit_child(assignment_body))
            ops += [
                Zero(coord=coord, name=result_name),
                Move(coord=coord, from_name=decl_name, to_name=result_name)
            ]

            self.pop_decl()
            self.pop_decl()

            return ops

        else:
            return []

    def generic_visit(self, node):
        self.lprint(node.__class__.__name__)
        return self.visit_children(node)

    def create_block(self, ops=[]):
        block = Block(self.next_block_index, ops)
        self.next_block_index += 1
        return block

    def create_if_block(self, **if_kwargs):
        block = IfBlock(self.next_block_index, **if_kwargs)
        self.next_block_index += 1
        return block

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

    def visit_Assignment(self, node):
        self.lprint(node.__class__.__name__, node.coord)
        self.aprint('name', node.lvalue.name)

        return self.visit_assignment_body(node.coord, node.lvalue.name, node.rvalue)

    def visit_BinaryOp(self, node):
        self.lprint(node.__class__.__name__, node.coord)
        self.aprint('op', node.op)

        ops = []

        first_name = self.push_sub_decl('a')
        ops.extend(self.visit_child(node.left))
        self.pop_decl()

        second_name = self.push_sub_decl('b')
        ops.extend(self.visit_child(node.right))
        self.pop_decl()

        if node.op == '+':
            ops.append(Add(coord=node.coord, result_name=self.decl_name_stack[-1],
                           first_name=first_name, second_name=second_name))
        elif node.op == '*':
            ops.append(Multiply(coord=node.coord, result_name=self.decl_name_stack[-1],
                                first_name=first_name, second_name=second_name))

        return ops

    def visit_Compound(self, node):
        self.lprint(node.__class__.__name__, node.coord)

        results = self.visit_children(node)

        blocks = [self.create_block()]
        for result in results:
            if isinstance(result, IfBlock):
                next_block = self.create_block()
                result.true_blocks[-1].next = next_block
                if result.false_blocks:
                    result.false_blocks[-1].next = next_block
                blocks[-1].next = result
                blocks.append(result)
                blocks.append(next_block)
            else:
                blocks[-1].ops.append(result)

        return blocks

    def visit_Constant(self, node):
        self.lprint(node.__class__.__name__, node.coord)
        self.aprint('value', node.value)
        self.aprint('type', node.type)

        return [SetValue(coord=node.coord, name=self.decl_name_stack[-1], value=node.value,
                         type=node.type)]

    def visit_Decl(self, node):
        self.lprint(node.__class__.__name__, node.coord)
        self.aprint('name', node.name)

        return self.visit_assignment_body(node.coord, node.name, node.init)

    def visit_ID(self, node):
        self.lprint(node.__class__.__name__, node.coord)
        self.aprint('name', node.name)

        return [
            Zero(coord=node.coord, name=self.decl_name_stack[-1]),
            Copy(coord=node.coord, from_name=node.name, to_name=self.decl_name_stack[-1])
        ]

    def visit_If(self, node):
        self.lprint(node.__class__.__name__, node.coord)

        result_name = 'if'
        self.push_decl(result_name)
        decl_name = self.push_decl_mod(result_name)

        cond_block = self.visit_child(node.cond)

        self.pop_decl()
        self.pop_decl()

        true_blocks = self.visit_child(node.iftrue)
        false_blocks = self.visit_child(node.iffalse)

        if_block = self.create_if_block(
            decl_name = decl_name,
            cond_block = cond_block,
            true_blocks = true_blocks,
            false_blocks = false_blocks
        )

        return [if_block]

    def visit_FuncCall(self, node):
        self.lprint(node.__class__.__name__, node.coord)
        self.aprint('name', node.name.name)

        ops = []

        if node.name.name == 'putchar':
            arg_index = 0
            arg = node.args.exprs[arg_index]

            result_name = '{}_arg_{}'.format(node.name.name, arg_index)
            self.push_decl(result_name)
            decl_name = self.push_decl_mod(result_name)

            ops += list(self.visit_child(arg))
            ops += [Print(coord=node.coord, output_name=decl_name)]

            self.pop_decl()
            self.pop_decl()

        elif node.name.name == 'getchar':
            result_name = '{}_ret'.format(node.name.name)
            self.push_decl(result_name)

            ops += [Input(coord=node.coord, input_name=result_name)]

            self.pop_decl()

            if len(self.decl_name_stack) > 0:
                ops += [Move(coord=node.coord, from_name=result_name,
                             to_name=self.decl_name_stack[-1])]

        return ops

    def visit_FuncDef(self, node):
        self.lprint(node.__class__.__name__, node.coord)

        self.functions[node.decl.name] = self.visit_child(node.body)

        return []

    def to_bf(self):
        print()

        main_blocks = self.functions['main']
        declaration_positions = {decl_name: index
                                 for (index, decl_name)
                                 in enumerate(self.declarations)}

        blocks_by_index = {}
        def add_blocks_to_map(blocks):
            for block in blocks:
                blocks_by_index[block.index] = block
                if isinstance(block, IfBlock):
                    add_blocks_to_map(block.true_blocks)
                    if block.false_blocks:
                        add_blocks_to_map(block.false_blocks)

        add_blocks_to_map(main_blocks)

        def ip_offset(current_index, new_index):
            return ((new_index - current_index) % len(blocks_by_index)) - 1

        start_ip = main_blocks[0].index
        output = ''

        STOP_INDICATOR_INDEX = 0
        KNOWN_ZERO = STOP_INDICATOR_INDEX + 1

        START_IP_WORKSPACE = KNOWN_ZERO + 1
        IP_INDEX = START_IP_WORKSPACE
        IP_ZERO_INDICATOR = IP_INDEX + 1
        END_IP_WORKSPACE = IP_ZERO_INDICATOR + 4

        START_STACK = END_IP_WORKSPACE + 1

        output += '!+{}'.format(
            bf_travel(STOP_INDICATOR_INDEX, IP_INDEX))

        output += ' (IPSetup {}+ 3>+>+ 4<) {} [\n'.format(start_ip,
            bf_travel(IP_INDEX, STOP_INDICATOR_INDEX))

        symbol_table = OrderedDict()

        for index in range(len(blocks_by_index)):
            block = blocks_by_index[index]
            print('%d: %s' % (index, block))

            output += '    ![{} (IPCheck >+< [->->]3>[>] {}) !(Block [-{}'.format(
                bf_travel(STOP_INDICATOR_INDEX, IP_INDEX),
                bf_travel(END_IP_WORKSPACE, IP_ZERO_INDICATOR),
                bf_travel(IP_ZERO_INDICATOR, START_STACK))

            if isinstance(block, IfBlock):
                for op in block.cond_block:
                    start_bf_length = len(output)
                    output += op.to_bf(declaration_positions, len(declaration_positions))
                    end_bf_length = len(output)
                    symbol_table[(start_bf_length, end_bf_length)] = op.coord

                true_ip = ip_offset(block.index, block.true_blocks[0].index)
                false_ip = None
                if block.false_blocks is not None:
                    false_ip = ip_offset(block.index, block.false_blocks[0].index)

                cond_result_pos = START_STACK + declaration_positions[block.decl_name]

                def bf_set_ip(new_ip):
                    return '{}{}+{}'.format(
                        bf_travel(cond_result_pos, IP_INDEX),
                        new_ip,
                        bf_travel(IP_INDEX, cond_result_pos))

                output += ' !{}{} (GoToTrue [[-]{}{}])'.format(
                    bf_travel(START_STACK, cond_result_pos),
                    '>+<' if false_ip is not None else '',
                    bf_set_ip(true_ip),
                    '>-<' if false_ip is not None else '',
                    bf_travel(cond_result_pos, START_STACK))

                if false_ip is not None:
                    output += ' (GoToFalse >[-<{}>]<)'.format(
                        bf_set_ip(false_ip))

                output += ' {}'.format(bf_travel(cond_result_pos, START_STACK))

            else:
                for op in block.ops:
                    start_bf_length = len(output)
                    output += op.to_bf(declaration_positions, len(declaration_positions))
                    end_bf_length = len(output)
                    symbol_table[(start_bf_length, end_bf_length)] = op.coord

                if block.next is None:
                    output += ' !(EndProgram {}-{})'.format(
                        bf_travel(START_STACK, STOP_INDICATOR_INDEX),
                        bf_travel(STOP_INDICATOR_INDEX, START_STACK))
                else:
                    new_ip = ip_offset(block.index, block.next.index)
                    output += ' !(NextBlock {}{}+{})'.format(
                        bf_travel(START_STACK, IP_INDEX),
                        new_ip,
                        bf_travel(IP_INDEX, START_STACK))

            output += ' {}]) {}] {}\n'.format(
                bf_travel(START_STACK, IP_ZERO_INDICATOR),
                bf_travel(IP_ZERO_INDICATOR, KNOWN_ZERO),
                bf_travel(KNOWN_ZERO, STOP_INDICATOR_INDEX))

        output += ']\n'

        print()
        return output, symbol_table
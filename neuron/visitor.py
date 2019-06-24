from collections import namedtuple, OrderedDict
from pycparser import c_parser, c_ast, parse_file
import sys

from .commands import *
from .ordered_set import OrderedSet
from .tape_indices import TapeIndices


class Block:
    def __init__(self, index, ops=[]):
        self.index = index
        self.ops = list(ops)
        self.next_index = None

    def pretty_print(self):
        ret = ['Block(index=%s, next=%s):' % (self.index, self.next_index)]
        if len(self.ops) > 0:
            for op in self.ops:
                ret += ['    ' + op.__repr__()]
        return '\n'.join(ret)

    def __repr__(self):
        return 'Block(index=%s, ops=%s, next=%s)' % (self.index, self.ops.__repr__(), self.next_index)


class EndBlock(Block):
    def __init__(self, index):
        super().__init__(index, [EndProgram()])

    def pretty_print(self):
        return 'EndBlock(index=%s, next=%s)' % (self.index, self.next_index)

    def __repr__(self):
        return 'EndBlock(index=%s, ops=%s, next=%s)' % (self.index, self.ops.__repr__(), self.next_index)


class IfBlock:
    def __init__(self, index, cond_block, true_blocks, false_blocks, decl_name):
        self.index = index
        self.cond_block = cond_block
        self.true_blocks = true_blocks
        self.false_blocks = false_blocks
        self.decl_name = decl_name

    def pretty_print(self):
        ret = ['IfBlock(index={}, decl_name={}):'.format(self.index, self.decl_name)]
        ret += ['    Cond block:']
        for op in self.cond_block:
            ret += ['        ' + op.__repr__()]
        if len(self.true_blocks) > 0:
            ret += ['    True blocks: {}'.format(self.true_blocks)]
        if len(self.false_blocks) > 0:
            ret += ['    False blocks: {}'.format(self.false_blocks)]
        return '\n'.join(ret)

    def __str__(self):
        return "IfBlock(index={}, decl_name={}, true_blocks={}, false_blocks={}, cond_block={})".format(
            self.index, self.decl_name, self.true_blocks, self.false_blocks, self.cond_block)

    def __repr__(self):
        return self.__str__()


class BrainfuckCompilerVisitor(c_ast.NodeVisitor):
    def __init__(self):
        self.level = 0
        self.next_block_index = 0
        self.declarations = OrderedSet()
        self.functions = {}
        self.blocks_by_index = {}
        self.static_data = []

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

    def add_block(self, block):
        self.blocks_by_index[block.index] = block
        self.next_block_index += 1

    def create_block(self, ops=[]):
        block = Block(self.next_block_index, ops)
        self.add_block(block)
        return block

    def create_end_block(self):
        block = EndBlock(self.next_block_index)
        self.add_block(block)
        return block

    def create_if_block(self, **if_kwargs):
        block = IfBlock(self.next_block_index, **if_kwargs)
        self.add_block(block)
        return block

    def push_decl_mod(self, decl_name):
        mod_count = self.modifications_by_decl_name.get(decl_name, 0)
        self.modifications_by_decl_name[decl_name] = mod_count + 1
        return self.push_sub_decl(mod_count)

    def push_sub_decl(self, suffix):
        decl_name = '{}~{}'.format(self.decl_name_stack[-1], suffix)
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

        return self.visit_assignment_body(str(node.coord), node.lvalue.name, node.rvalue)

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
            ops.append(Add(coord=str(node.coord), result_name=self.decl_name_stack[-1],
                           first_name=first_name, second_name=second_name))
        elif node.op == '*':
            ops.append(Multiply(coord=str(node.coord), result_name=self.decl_name_stack[-1],
                                first_name=first_name, second_name=second_name))

        return ops

    def visit_UnaryOp(self, node):
        self.lprint(node.__class__.__name__, node.coord)
        self.aprint('op', node.op)

        ops = []

        if node.op == '&':
            ops.append(AddressOf(coord=str(node.coord), result_name=self.decl_name_stack[-1],
                                 expr=node.expr))

        return ops

    def visit_Compound(self, node):
        self.lprint(node.__class__.__name__, node.coord)

        blocks = [self.create_block()]
        results = self.visit_children(node)

        for result in results:
            if isinstance(result, IfBlock):
                next_block = self.create_block()

                self.blocks_by_index[result.true_blocks[-1]].next_index = next_block.index
                self.blocks_by_index[result.false_blocks[-1]].next_index = next_block.index

                blocks[-1].next_index = result.index
                blocks.append(result)
                blocks.append(next_block)
            else:
                blocks[-1].ops.append(result)

        return blocks

    def visit_Constant(self, node):
        self.lprint(node.__class__.__name__, node.coord)
        self.aprint('value', node.value)
        self.aprint('type', node.type)

        if node.type == 'string':
            value = TapeIndices.LVALUES_COUNT + sum(len(d) for d in self.static_data) + len(self.static_data)
            self.static_data.append(node.value[1:-1])
        else:
            value = node.value

        return [SetValue(coord=str(node.coord), name=self.decl_name_stack[-1], value=value,
                         type=node.type)]

    def visit_Decl(self, node):
        self.lprint(node.__class__.__name__, node.coord)
        self.aprint('name', node.name)
        self.aprint('init', node.init)

        return self.visit_assignment_body(str(node.coord), node.name, node.init)

    def visit_ID(self, node):
        self.lprint(node.__class__.__name__, node.coord)
        self.aprint('name', node.name)

        return [
            Zero(coord=str(node.coord), name=self.decl_name_stack[-1]),
            Copy(coord=str(node.coord), from_name=node.name, to_name=self.decl_name_stack[-1])
        ]

    def visit_If(self, node):
        self.lprint(node.__class__.__name__, node.coord)

        result_name = 'if'
        self.push_decl(result_name)
        decl_name = self.push_decl_mod(result_name)

        cond_block = self.visit_child(node.cond)

        self.pop_decl()
        self.pop_decl()

        true_blocks = [block.index for block in self.visit_child(node.iftrue)]
        if node.iffalse:
            false_blocks = [block.index for block in self.visit_child(node.iffalse)]
        else:
            false_blocks = [self.create_block().index]

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

        function_name = node.name.name

        if function_name == 'getchar':
            result_name = '{}_ret'.format(function_name)
            self.push_decl(result_name)

            ops += [Input(coord=str(node.coord), input_name=result_name)]

            self.pop_decl()

            if len(self.decl_name_stack) > 0:
                ops += [Move(coord=str(node.coord), from_name=result_name,
                             to_name=self.decl_name_stack[-1])]

        elif function_name == 'putchar':
            arg_index = 0
            arg = node.args.exprs[arg_index]

            arg_name = '{}~arg~{}'.format(function_name, arg_index)
            self.push_decl(arg_name)
            decl_name = self.push_decl_mod(arg_name)

            ops += list(self.visit_child(arg))
            ops += [Print(coord=str(node.coord), output_name=decl_name)]

            self.pop_decl()
            self.pop_decl()

        elif function_name == 'puts':
            arg_index = 0
            arg = node.args.exprs[arg_index]

            arg_name = '{}~arg~{}'.format(function_name, arg_index)
            self.push_decl(arg_name)
            decl_name = self.push_decl_mod(arg_name)

            ops += list(self.visit_child(arg))
            ops += [PrintString(coord=str(node.coord), output_name=decl_name)]

            self.pop_decl()
            self.pop_decl()

        else:
            raise Exception('Unknown function call {}'.format(function_name))

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
                                 in enumerate(filter(lambda decl_name: '~' in decl_name, self.declarations))}
        for index, decl_name in enumerate(filter(lambda decl_name: '~' not in decl_name, self.declarations)):
            declaration_positions[decl_name] = (TapeIndices.START_LVALUES - TapeIndices.START_STACK) + index * 3 + 2

        end_block = self.create_end_block()

        for block in self.blocks_by_index.values():
            if isinstance(block, Block) and not isinstance(block, EndBlock) and block.next_index is None:
                block.next_index = end_block.index

        print('blocks_by_index:')
        for index in range(len(self.blocks_by_index)):
            block = self.blocks_by_index[index]
            print('%d: %s' % (index, block))
        print()

        blocks_to_terminal_blocks = {}
        def find_terminal_blocks(block_indexes):
            for block_index in block_indexes:
                block = self.blocks_by_index[block_index]

                if isinstance(block, EndBlock):
                    blocks_to_terminal_blocks[block.index] = block.index

                elif isinstance(block, IfBlock):
                    blocks_to_terminal_blocks[block.index] = block.index
                    find_terminal_blocks(block.true_blocks)
                    find_terminal_blocks(block.false_blocks)

                else:
                    if len(block.ops) == 0:
                        blocks_to_terminal_blocks[block.index] = block.next_index
                    else:
                        blocks_to_terminal_blocks[block.index] = block.index

                    if block.next_index:
                        find_terminal_blocks([block.next_index])

        find_terminal_blocks([block.index for block in main_blocks])

        modified = True
        while modified:
            modified = False
            new_terminal_blocks = {}

            for index, next_index in blocks_to_terminal_blocks.items():
                if next_index is not None and index != next_index and blocks_to_terminal_blocks[index] != blocks_to_terminal_blocks[next_index]:
                    new_terminal_blocks[index] = blocks_to_terminal_blocks[next_index]
                    modified = True
                else:
                    new_terminal_blocks[index] = next_index

            blocks_to_terminal_blocks = new_terminal_blocks

        print('blocks_to_terminal_blocks', blocks_to_terminal_blocks)

        terminal_blocks = set([b for b in blocks_to_terminal_blocks.values() if b is not None])
        print('terminal_blocks', terminal_blocks)
        blocks_to_minimal_blocks = {}
        for minimal_block_index, block_index in enumerate(terminal_blocks):
            if block_index is not None:
                blocks_to_minimal_blocks[block_index] = minimal_block_index

        print('blocks_to_minimal_blocks', blocks_to_minimal_blocks)

        blocks_to_new_blocks = {}
        for block_index in blocks_to_terminal_blocks:
            terminal_block = blocks_to_terminal_blocks[block_index]
            if terminal_block is None:
                blocks_to_new_blocks[block_index] = None
            else:
                blocks_to_new_blocks[block_index] = blocks_to_minimal_blocks[terminal_block]

        print('blocks_to_new_blocks', blocks_to_new_blocks)
        print()

        for block in self.blocks_by_index.values():
            if isinstance(block, IfBlock):
                block.true_blocks = [blocks_to_new_blocks.get(b) for b in block.true_blocks]
                block.false_blocks = [blocks_to_new_blocks.get(b) for b in block.false_blocks]
            else:
                block.next_index = blocks_to_new_blocks.get(block.next_index)

        new_blocks_by_index = {}
        for old_block_index in terminal_blocks:
            new_block_index = blocks_to_new_blocks[old_block_index]
            block = self.blocks_by_index[old_block_index]
            block.index = new_block_index
            new_blocks_by_index[new_block_index] = block

        for block in new_blocks_by_index.values():
            if isinstance(block, IfBlock):
                block.true_blocks = [block_index for n, block_index in enumerate(block.true_blocks) if n == 0 or block.true_blocks[n-1] != block_index]
                block.false_blocks = [block_index for n, block_index in enumerate(block.false_blocks) if n == 0 or block.false_blocks[n-1] != block_index]

        def ip_offset(current_index, new_index):
            return ((new_index - current_index) % len(new_blocks_by_index)) - 1

        print('main_blocks:')
        for block in main_blocks:
            print(block.pretty_print())
            print()

        print('static_data:', self.static_data)
        output = '(StaticSetup !{} '.format(bf_travel(TapeIndices.START, TapeIndices.START_STATIC_SEGMENT))
        for data_index, data in enumerate(self.static_data):
            for c in data:
                output += '>>{}+>'.format(str(ord(c)))
            output += '>>> ' # zero byte
        static_segment_size = 3 * (sum([len(data) for data in self.static_data]) + len(self.static_data))
        output += '{}<'.format(static_segment_size)
        output += '{})'.format(bf_travel(TapeIndices.START_STATIC_SEGMENT, TapeIndices.START))

        start_ip = blocks_to_new_blocks.get(main_blocks[0].index)
        print('start_ip', start_ip)

        output += '!{}+{}'.format(
            bf_travel(TapeIndices.START, TapeIndices.STOP_INDICATOR_INDEX),
            bf_travel(TapeIndices.STOP_INDICATOR_INDEX, TapeIndices.IP_INDEX))

        output += '(IPSetup {}+ 3>+>+ 4<){} [{}'.format(start_ip,
            bf_travel(TapeIndices.IP_INDEX, TapeIndices.STOP_INDICATOR_INDEX),
            bf_travel(TapeIndices.STOP_INDICATOR_INDEX, TapeIndices.FIRST_KNOWN_ZERO))

        symbol_table = OrderedDict()

        print('new_blocks_by_index:')
        for block_index, block in new_blocks_by_index.items():
            print('%d: %s' % (block_index, block.pretty_print()))

            start_bf_length = len(output)
            output += '!{} [{} (IPCheck >+< [->->]3>[>] {})'.format(
                bf_travel(TapeIndices.FIRST_KNOWN_ZERO, TapeIndices.STOP_INDICATOR_INDEX),
                bf_travel(TapeIndices.STOP_INDICATOR_INDEX, TapeIndices.IP_INDEX),
                bf_travel(TapeIndices.END_IP_WORKSPACE, TapeIndices.IP_ZERO_INDICATOR))
            output += '(Block ![-{}'.format(
                bf_travel(TapeIndices.IP_ZERO_INDICATOR, TapeIndices.START_STACK))
            end_bf_length = len(output)

            if isinstance(block, IfBlock):
                coord = block.cond_block[0].coord
            elif len(block.ops) > 0:
                coord = block.ops[0].coord
            else:
                coord = None

            # if coord:
            #     symbol_table[(start_bf_length, end_bf_length)] = coord

            if isinstance(block, IfBlock):
                for op in block.cond_block:
                    start_bf_length = len(output)
                    output += op.to_bf(declaration_positions, len(declaration_positions))
                    end_bf_length = len(output)
                    symbol_table[(start_bf_length, end_bf_length)] = op.coord

                true_ip = ip_offset(block.index, block.true_blocks[0])
                false_ip = ip_offset(block.index, block.false_blocks[0])

                cond_result_pos = TapeIndices.START_STACK + declaration_positions[block.decl_name]

                def bf_set_ip(new_ip):
                    return '{}{}+{}'.format(
                        bf_travel(cond_result_pos, TapeIndices.IP_INDEX),
                        new_ip,
                        bf_travel(TapeIndices.IP_INDEX, cond_result_pos))

                output += '(GoToTrue !{}{} [[-]{}{}])'.format(
                    bf_travel(TapeIndices.START_STACK, cond_result_pos),
                    '>+<' if false_ip is not None else '',
                    bf_set_ip(true_ip),
                    '>-<' if false_ip is not None else '',
                    bf_travel(cond_result_pos, TapeIndices.START_STACK))

                if false_ip is not None:
                    output += '(GoToFalse >[-<{}>]<)'.format(
                        bf_set_ip(false_ip))

                output += ' {}'.format(bf_travel(cond_result_pos, TapeIndices.START_STACK))

            else:
                for op in block.ops:
                    start_bf_length = len(output)
                    output += op.to_bf(declaration_positions, len(declaration_positions))
                    end_bf_length = len(output)
                    symbol_table[(start_bf_length, end_bf_length)] = op.coord

                if block.next_index is not None:
                    new_ip = ip_offset(block.index, block.next_index)
                    output += '(NextBlock !{}{}+{})'.format(
                        bf_travel(TapeIndices.START_STACK, TapeIndices.IP_INDEX),
                        new_ip,
                        bf_travel(TapeIndices.IP_INDEX, TapeIndices.START_STACK))

            output += '{}]){}] <[<]'.format(
                bf_travel(TapeIndices.START_STACK, TapeIndices.IP_ZERO_INDICATOR),
                bf_travel(TapeIndices.IP_ZERO_INDICATOR, TapeIndices.KNOWN_ZERO))

        output += '{}]'.format(
            bf_travel(TapeIndices.FIRST_KNOWN_ZERO, TapeIndices.STOP_INDICATOR_INDEX))

        print()
        return output, declaration_positions, symbol_table, self.static_data, new_blocks_by_index

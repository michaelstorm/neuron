from collections import namedtuple
from pycparser import c_ast

from .console import colored_text, TextColor
from .tape_indices import TapeIndices


def bf_travel(from_pos, to_pos, opposite=False):
    distance = abs(to_pos - from_pos)
    if opposite:
        direction = '<' if to_pos > from_pos else '>'
    else:
        direction = '>' if to_pos > from_pos else '<'

    return '{}{}'.format(distance, direction)


def addressable_offset(declaration_mapper, name):
    position = declaration_mapper[name].position
    return ((position - 2) - (TapeIndices.START_ADDRESSABLE_MEMORY - TapeIndices.START_STACK)) // 3


bf_start_paren = colored_text(TextColor.LIGHT_GRAY, '(')
bf_end_paren = colored_text(TextColor.LIGHT_GRAY, ')')


def format_bf_name(name):
    return colored_text(TextColor.LIGHT_GREEN, name)


def format_bf(name, attrs_object, *bf):
    fields = []
    if attrs_object != None:
        fields = ['{}{}{}'.format(colored_text(TextColor.LIGHT_GRAY, name),
                                  colored_text(TextColor.LIGHT_GRAY, '='),
                                  colored_text(TextColor.LIGHT_YELLOW, getattr(attrs_object, name)))
                  for name in attrs_object._fields if name != 'coord']

    formatted_fields = ''
    if len(fields) > 0:
        formatted_fields = ' {}{}{}'.format(
            colored_text(TextColor.LIGHT_GRAY, '{'),
            ', '.join(fields) if len(fields) > 0 else '',
            colored_text(TextColor.LIGHT_GRAY, '}'))

    return '{}{}{} {}{}'.format(
        bf_start_paren,
        format_bf_name(name),
        formatted_fields,
        bf[0].format(*bf[1:]),
        bf_end_paren)


def commandtuple(name, fields):
    def _format_bf(self, *bf):
        return format_bf(name, self, *bf)

    t = namedtuple(name, fields)
    t.format_bf = _format_bf
    return t


class Move(commandtuple('Move', ['coord', 'from_name', 'to_name'])):
    def to_bf(self, declaration_mapper, stack_index):
        from_pos = declaration_mapper[self.from_name].position
        to_pos = declaration_mapper[self.to_name].position

        return self.format_bf('{}>[-{}+{}]{}<',
            from_pos,
            bf_travel(from_pos, to_pos),
            bf_travel(to_pos, from_pos),
            from_pos)


class Copy(commandtuple('Copy', ['coord', 'from_name', 'to_name'])):
    def to_bf(self, declaration_mapper, stack_index):
        start_pos = declaration_mapper[self.from_name].position
        end_pos = declaration_mapper[self.to_name].position

        staging_pos = stack_index
        move_command = Move(coord=self.coord, from_name=staging_pos, to_name=self.from_name)

        return self.format_bf('{}>[-{}+{}+{}]{}<{}',
            start_pos,
            bf_travel(start_pos, staging_pos),
            bf_travel(staging_pos, end_pos),
            bf_travel(end_pos, start_pos),
            start_pos,
            move_command.to_bf(declaration_mapper, stack_index + 1))


class SetValue(commandtuple('SetValue', ['coord', 'name', 'value', 'type'])):
    def to_bf(self, declaration_mapper, stack_index):
        pos = declaration_mapper[self.name].position

        if self.type in ('int', 'string'):
            bf_value = self.value
        elif self.type == 'char':
            bf_value = ord(self.value[1])
        else:
            raise Exception('Unknown type %s' % self.type)

        # zeroing out value is necessary for comma-separated expression lists to result in the
        # correct value
        return self.format_bf('{}>[-]{}+{}<', pos, bf_value, pos)


class SetArrayValues(commandtuple('SetArrayValues', ['coord', 'name', 'values', 'type'])):
    def to_bf(self, declaration_mapper, stack_index):
        pos = declaration_mapper[self.name].position
        bf = '!{}>'.format(pos)

        for i, value in enumerate(self.values):
            if self.type in ('int', 'string'):
                bf_value = value
            elif self.type == 'char':
                bf_value = ord(value[1])
            else:
                raise Exception('Unknown type %s' % self.type)

            # zeroing out value is necessary for comma-separated expression lists to result in the
            # correct value
            bf += '[-]{}+3>'.format(bf_value)

        bf += '{}<'.format(pos + 3 * len(self.values))
        return self.format_bf(bf)


class AddressOf(commandtuple('SetValue', ['coord', 'result_name', 'expr'])):
    def to_bf(self, declaration_mapper, stack_index):
        expr_type = self.expr.__class__.__name__
        if expr_type != 'ID':
            raise Exception('Unimplemented lvalue type {} for AddressOf operator'.format(expr_type))

        lvalue_pos = addressable_offset(declaration_mapper, self.expr.name)
        result_pos = declaration_mapper[self.result_name].position
        return self.format_bf('{}>[-]{}+{}<', result_pos, lvalue_pos, result_pos)


class Zero(commandtuple('Zero', ['coord', 'name'])):
    def to_bf(self, declaration_mapper, stack_index):
        pos = declaration_mapper[self.name].position
        return self.format_bf('{}>[-]{}<', pos, pos)


class Add(commandtuple('Add', ['coord', 'result_name', 'first_name', 'second_name'])):
    def to_bf(self, declaration_mapper, stack_index):
        first_move = Move(coord=self.coord, from_name=self.first_name, to_name=self.result_name)
        second_move = Move(coord=self.coord, from_name=self.second_name, to_name=self.result_name)
        return self.format_bf('{}{}',
            first_move.to_bf(declaration_mapper, stack_index + 1),
            second_move.to_bf(declaration_mapper, stack_index + 1))


class Multiply(commandtuple('Multiply', ['coord', 'result_name', 'first_name', 'second_name'])):
    def to_bf(self, declaration_mapper, stack_index):
        first_pos = declaration_mapper[self.first_name].position
        second_pos = declaration_mapper[self.second_name].position

        copy_command = Copy(coord=self.coord, from_name=self.second_name, to_name=self.result_name)

        return self.format_bf('{}>[-{}<{}{}>]{}<', first_pos, first_pos,
            copy_command.to_bf(declaration_mapper, stack_index + 1), first_pos, first_pos)


def greater_base(self, declaration_mapper, stack_index, greater_than, or_equal):
    first_move = Move(coord=self.coord, from_name=self.first_name if greater_than else self.second_name, to_name=stack_index + 4)
    second_move = Move(coord=self.coord, from_name=self.second_name if greater_than else self.first_name, to_name=stack_index + 5)
    result_pos = declaration_mapper[self.result_name].position

    # from https://stackoverflow.com/a/13327857
    return self.format_bf('{}{} {} !>>+>> {}>+< [->-[>]<<] <[-{}+{}] <[-<]< {}',
        first_move.to_bf(declaration_mapper, stack_index + 6),
        second_move.to_bf(declaration_mapper, stack_index + 6),
        bf_travel(0, stack_index),
        '+' if or_equal else '',
        bf_travel(stack_index + 2, result_pos),
        bf_travel(result_pos, stack_index + 2),
        bf_travel(stack_index, 0),
    )


class GreaterOrEqual(commandtuple('GreaterOrEqual', ['coord', 'result_name', 'first_name', 'second_name'])):
    def to_bf(self, declaration_mapper, stack_index):
        return greater_base(self, declaration_mapper, stack_index, True, True)


class Greater(commandtuple('Greater', ['coord', 'result_name', 'first_name', 'second_name'])):
    def to_bf(self, declaration_mapper, stack_index):
        return greater_base(self, declaration_mapper, stack_index, True, False)


class LesserOrEqual(commandtuple('LesserOrEqual', ['coord', 'result_name', 'first_name', 'second_name'])):
    def to_bf(self, declaration_mapper, stack_index):
        return greater_base(self, declaration_mapper, stack_index, False, True)


class Lesser(commandtuple('Lesser', ['coord', 'result_name', 'first_name', 'second_name'])):
    def to_bf(self, declaration_mapper, stack_index):
        return greater_base(self, declaration_mapper, stack_index, False, False)


class Print(commandtuple('Print', ['coord', 'output_name'])):
    def to_bf(self, declaration_mapper, stack_index):
        pos = declaration_mapper[self.output_name].position
        return self.format_bf('{}>.{}<', pos, pos)


class ForwardMem(commandtuple('ForwardMem', ['coord'])):
    def to_bf(self, declaration_mapper, stack_index):
        return '[[-3>+3<]3>-] 2>'


class BackMem(commandtuple('BackMem', ['coord'])):
    def to_bf(self, declaration_mapper, stack_index):
        return '<[3<]< {}'.format(
            bf_travel(TapeIndices.START_ADDRESSABLE_MEMORY, TapeIndices.START_STACK)
        )


class GoMem(commandtuple('GoMem', ['coord', 'base_name', 'offset_name'])):
    def to_bf(self, declaration_mapper, stack_index):
        base_pos = addressable_offset(declaration_mapper, self.base_name)
        start_addressable_memory_distance = TapeIndices.START_ADDRESSABLE_MEMORY - TapeIndices.START_STACK
        copy_offset_command = Copy(coord=self.coord, from_name=self.offset_name, to_name=start_addressable_memory_distance)

        return self.format_bf('{}{}+{}{}{} {}',
            bf_travel(TapeIndices.START_STACK, TapeIndices.START_ADDRESSABLE_MEMORY),
            base_pos,
            bf_travel(TapeIndices.START_ADDRESSABLE_MEMORY, TapeIndices.START_STACK),
            copy_offset_command.to_bf(declaration_mapper, stack_index + 2),
            bf_travel(TapeIndices.START_STACK, TapeIndices.START_ADDRESSABLE_MEMORY),
            ForwardMem(coord=self.coord).to_bf(declaration_mapper, stack_index + 3))


class PrintString(commandtuple('PrintString', ['coord', 'output_name'])):
    def to_bf(self, declaration_mapper, stack_index):
        start_addressable_memory_distance = TapeIndices.START_ADDRESSABLE_MEMORY - TapeIndices.START_STACK
        copy_command = Copy(coord=self.coord, from_name=self.output_name, to_name=start_addressable_memory_distance)
        back_mem_command = BackMem(coord=self.coord)

        return self.format_bf('!{}{} {} [.3>] {}',
            copy_command.to_bf(declaration_mapper, stack_index + 1),
            bf_travel(TapeIndices.START_STACK, TapeIndices.START_ADDRESSABLE_MEMORY),
            ForwardMem(coord=self.coord).to_bf(declaration_mapper, stack_index + 3),
            back_mem_command.to_bf(declaration_mapper, stack_index + 1))


class SetAddressableValue(commandtuple('SetAddressableValue', ['coord', 'base_name', 'offset_name', 'rvalue_name'])):
    def to_bf(self, declaration_mapper, stack_index):
        rvalue_pos = declaration_mapper[self.rvalue_name].position + TapeIndices.START_STACK
        go_mem_command = GoMem(coord=self.coord, base_name=self.base_name, offset_name=self.offset_name)

        return self.format_bf('{}[-{}{} + <[3<]< {}] {}',
            bf_travel(TapeIndices.START_STACK, rvalue_pos),
            bf_travel(rvalue_pos, TapeIndices.START_STACK),
            go_mem_command.to_bf(declaration_mapper, stack_index + 1),
            bf_travel(TapeIndices.START_ADDRESSABLE_MEMORY, rvalue_pos),
            bf_travel(rvalue_pos, TapeIndices.START_STACK))


class GetAddressableValue(commandtuple('GetAddressableValue', ['coord', 'base_name', 'offset_name', 'result_name'])):
    def to_bf(self, declaration_mapper, stack_index):
        staging_pos = stack_index
        result_pos = declaration_mapper[self.result_name].position
        go_mem_command = GoMem(coord=self.coord, base_name=self.base_name, offset_name=self.offset_name)
        back_mem_command = BackMem(coord=self.coord)
        set_value_command = SetAddressableValue(coord=self.coord, base_name=self.base_name,
                                                offset_name=self.offset_name, rvalue_name=staging_pos)

        return self.format_bf('!{} ![- <[3<]< {}+ {}+ {}{}] !{} {}',
            go_mem_command.to_bf(declaration_mapper, stack_index + 2),
            bf_travel(TapeIndices.START_ADDRESSABLE_MEMORY - TapeIndices.START_STACK, staging_pos),
            bf_travel(staging_pos, result_pos),
            bf_travel(result_pos, 0),
            go_mem_command.to_bf(declaration_mapper, stack_index + 3),
            back_mem_command.to_bf(declaration_mapper, stack_index + 3),
            set_value_command.to_bf(declaration_mapper, stack_index + 3))


class Input(commandtuple('Input', ['coord', 'input_name'])):
    def to_bf(self, declaration_mapper, stack_index):
        pos = declaration_mapper[self.input_name].position
        return self.format_bf('{} {}>,{}<', pos, pos)


class EndProgram(commandtuple('EndProgram', [])):
    @property
    def coord(self):
        return None

    def to_bf(self, declaration_mapper, stack_index):
        return self.format_bf('{}-{}',
            bf_travel(TapeIndices.START_STACK, TapeIndices.STOP_INDICATOR_INDEX),
            bf_travel(TapeIndices.STOP_INDICATOR_INDEX, TapeIndices.START_STACK))

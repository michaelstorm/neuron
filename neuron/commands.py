from collections import namedtuple

from .tape_indices import TapeIndices


def bf_travel(from_pos, to_pos, opposite=False):
    distance = abs(to_pos - from_pos)
    if opposite:
        direction = '<' if to_pos > from_pos else '>'
    else:
        direction = '>' if to_pos > from_pos else '<'

    return '{}{}'.format(distance, direction)


class Move(namedtuple('Move', ['coord', 'from_name', 'to_name'])):
    def to_bf(self, declaration_mapper, stack_index):
        if isinstance(self.from_name, int):
            from_pos = self.from_name
        else:
            from_pos = declaration_mapper[self.from_name]

        if isinstance(self.to_name, int):
            to_pos = self.to_name
        else:
            to_pos = declaration_mapper[self.to_name]

        travel_forward = bf_travel(from_pos, to_pos)
        travel_backward = bf_travel(from_pos, to_pos, opposite=True)

        return '(Move !{}>[-{}+{}]{}<)'.format(from_pos, travel_forward, travel_backward, from_pos)


class Copy(namedtuple('Copy', ['coord', 'from_name', 'to_name'])):
    def to_bf(self, declaration_mapper, stack_index):
        if isinstance(self.from_name, int):
            start_pos = self.from_name
        else:
            start_pos = declaration_mapper[self.from_name]

        if isinstance(self.to_name, int):
            end_pos = self.to_name
        else:
            end_pos = declaration_mapper[self.to_name]

        staging_pos = stack_index

        start_staging_travel = bf_travel(start_pos, staging_pos)
        staging_end_travel = bf_travel(staging_pos, end_pos)
        end_start_travel = bf_travel(end_pos, start_pos)

        move_command = Move(coord=self.coord, from_name=staging_pos, to_name=self.from_name)

        return '(Copy {}>[-{}+{}+{}]{}<{})'.format(start_pos, start_staging_travel,
            staging_end_travel, end_start_travel, start_pos,
            move_command.to_bf(declaration_mapper, stack_index + 1))


class SetValue(namedtuple('SetValue', ['coord', 'name', 'value', 'type'])):
    def to_bf(self, declaration_mapper, stack_index):
        pos = declaration_mapper[self.name]

        if self.type in ('int', 'string'):
            bf_value = self.value
        elif self.type == 'char':
            bf_value = ord(self.value[1])
        else:
            raise Exception('Unknown type %s' % self.type)

        # zeroing out value is necessary for comma-separated expression lists to result in the
        # correct value
        return '(SetValue {}>[-]{}+{}<)'.format(pos, bf_value, pos)


class AddressOf(namedtuple('SetValue', ['coord', 'result_name', 'expr'])):
    def to_bf(self, declaration_mapper, stack_index):
        expr_type = self.expr.__class__.__name__
        if expr_type != 'ID':
            raise Exception('Unimplemented lvalue type {} for AddressOf operator'.format(expr_type))

        lvalue_pos = ((declaration_mapper[self.expr.name] - 2) - (TapeIndices.START_LVALUES - TapeIndices.START_STACK)) // 3
        result_pos = declaration_mapper[self.result_name]
        return '(AddressOf {}>[-]{}+{}<)'.format(result_pos, lvalue_pos, result_pos)


class Zero(namedtuple('Zero', ['coord', 'name'])):
    def to_bf(self, declaration_mapper, stack_index):
        pos = declaration_mapper[self.name]
        return '(Zero {}>[-]{}<)'.format(pos, pos)


class Add(namedtuple('Add', ['coord', 'result_name', 'first_name', 'second_name'])):
    def to_bf(self, declaration_mapper, stack_index):
        first_move = Move(from_name=self.first_name, to_name=self.result_name)
        second_move = Move(from_name=self.second_name, to_name=self.result_name)
        return '(Add {}{})'.format(first_move.to_bf(declaration_mapper, stack_index + 1),
                                   second_move.to_bf(declaration_mapper, stack_index + 1))


class Multiply(namedtuple('Multiply', ['coord', 'result_name', 'first_name', 'second_name'])):
    def to_bf(self, declaration_mapper, stack_index):
        first_pos = declaration_mapper[self.first_name]
        second_pos = declaration_mapper[self.second_name]

        copy_command = Copy(from_name=self.second_name, to_name=self.result_name)

        return '(Multiply {}>[-{}<{}{}>]{}<)'.format(first_pos, first_pos,
            copy_command.to_bf(declaration_mapper, stack_index + 1), first_pos, first_pos)


class Print(namedtuple('Print', ['coord', 'output_name'])):
    def to_bf(self, declaration_mapper, stack_index):
        pos = declaration_mapper[self.output_name]
        return '(Print !{}>.{}<)'.format(pos, pos)


class PrintString(namedtuple('PrintString', ['coord', 'output_name'])):
    def to_bf(self, declaration_mapper, stack_index):
        pos = declaration_mapper[self.output_name]
        start_static_segment_distance = TapeIndices.START_ADDRESSABLE_MEMORY - TapeIndices.START_STACK
        copy_command = Copy(coord=self.coord, from_name=self.output_name, to_name=start_static_segment_distance)
        return '(PrintString !{}{}![-3>+3<]3>- ![[-3>+3<]>+!2>-] !>+>[.2>+>] !<[-3<]<) !{}'.format(
            copy_command.to_bf(declaration_mapper, stack_index + 1),
            bf_travel(TapeIndices.START_STACK, TapeIndices.START_ADDRESSABLE_MEMORY),
            bf_travel(TapeIndices.START_ADDRESSABLE_MEMORY, TapeIndices.START_STACK))


class Input(namedtuple('Input', ['coord', 'input_name'])):
    def to_bf(self, declaration_mapper, stack_index):
        pos = declaration_mapper[self.input_name]
        return '(Input {}>,{}<)'.format(pos, pos)


class EndProgram(namedtuple('EndProgram', [])):
    @property
    def coord(self):
        return None

    def to_bf(self, declaration_mapper, stack_index):
        return '(EndProgram !{}-{})'.format(
            bf_travel(TapeIndices.START_STACK, TapeIndices.STOP_INDICATOR_INDEX),
            bf_travel(TapeIndices.STOP_INDICATOR_INDEX, TapeIndices.START_STACK))

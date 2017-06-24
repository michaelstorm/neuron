from collections import namedtuple


def bf_travel(from_pos, to_pos, opposite=False):
    distance = abs(to_pos - from_pos)
    if opposite:
        direction = '<' if to_pos > from_pos else '>'
    else:
        direction = '>' if to_pos > from_pos else '<'

    return '{}{}'.format(distance, direction)


class Move(namedtuple('Move', ['from_name', 'to_name'])):
    def to_bf(self, declaration_positions, stack_index):
        if isinstance(self.from_name, int):
            from_pos = self.from_name
        else:
            from_pos = declaration_positions[self.from_name]

        if isinstance(self.to_name, int):
            to_pos = self.to_name
        else:
            to_pos = declaration_positions[self.to_name]

        travel_forward = bf_travel(from_pos, to_pos)
        travel_backward = bf_travel(from_pos, to_pos, opposite=True)

        return '(Move {}[-{}+{}]{})'.format('{}>'.format(from_pos), travel_forward,
                                            travel_backward, '{}<'.format(from_pos))

class Copy(namedtuple('Copy', ['from_name', 'to_name'])):
    def to_bf(self, declaration_positions, stack_index):
        start_pos = declaration_positions[self.from_name]
        end_pos = declaration_positions[self.to_name]
        staging_pos = stack_index

        start_staging_travel = bf_travel(start_pos, staging_pos)
        staging_end_travel = bf_travel(staging_pos, end_pos)
        end_start_travel = bf_travel(end_pos, start_pos)

        move_command = Move(from_name=staging_pos, to_name=self.from_name)

        return '(Copy {}[-{}+{}+{}]{}{})'.format('{}>'.format(start_pos),
                                                 start_staging_travel,
                                                 staging_end_travel, end_start_travel,
                                                 '{}<'.format(start_pos),
                                                 move_command.to_bf(declaration_positions, stack_index + 1))

class SetValue(namedtuple('SetValue', ['name', 'value', 'type'])):
    def to_bf(self, declaration_positions, stack_index):
        pos = declaration_positions[self.name]

        if self.type == 'int':
            bf_value = self.value
        elif self.type == 'char':
            bf_value = ord(self.value[1])
        else:
            raise Exception('Unknown type %s' % self.type)

        return '(SetValue {}{}{})'.format('{}>'.format(pos), '{}+'.format(bf_value),
                                          '{}<'.format(pos))

class Zero(namedtuple('Zero', ['name'])):
    def to_bf(self, declaration_positions, stack_index):
        pos = declaration_positions[self.name]
        return '(Zero {}[-]{})'.format('{}>'.format(pos), '{}<'.format(pos))

class Add(namedtuple('Add', ['result_name', 'first_name', 'second_name'])):
    def to_bf(self, declaration_positions, stack_index):
        first_move = Move(from_name=self.first_name, to_name=self.result_name)
        second_move = Move(from_name=self.second_name, to_name=self.result_name)
        return '(Add {}{})'.format(first_move.to_bf(declaration_positions, stack_index + 1),
                                   second_move.to_bf(declaration_positions, stack_index + 1))

class Multiply(namedtuple('Multiply', ['result_name', 'first_name', 'second_name'])):
    def to_bf(self, declaration_positions, stack_index):
        first_pos = declaration_positions[self.first_name]
        second_pos = declaration_positions[self.second_name]

        copy_command = Copy(from_name=self.second_name, to_name=self.result_name)

        return '(Multiply {}[-{}{}{}]{})'.format('{}>'.format(first_pos),
                                                 '{}<'.format(first_pos),
                                                 copy_command.to_bf(declaration_positions, stack_index + 1),
                                                 '{}>'.format(first_pos),
                                                 '{}<'.format(first_pos))

class Print(namedtuple('Print', ['output_name'])):
    def to_bf(self, declaration_positions, stack_index):
        pos = declaration_positions[self.output_name]
        return '(Print {}.{})'.format('{}>'.format(pos), '{}<'.format(pos))

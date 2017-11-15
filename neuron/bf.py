from .visitor import TapeIndices
import re
import sys


class TextColor:
    DEFAULT = 39
    BLACK = 30


class BackgroundColor:
    DEFAULT = 49
    RED = 41
    LIGHT_GREEN = 102
    LIGHT_MAGENTA = 105
    LIGHT_CYAN = 106


def text_color_code(color):
    return '\033[{}m'.format(color)


def colored_text(color, text):
    default_color = text_color_code(TextColor.DEFAULT)
    return '{}{}{}'.format(text_color_code(color), text, default_color)


def colored_background(color, text):
    default_color = text_color_code(BackgroundColor.DEFAULT)
    return '{}{}{}'.format(text_color_code(color), text, default_color)


def colored_text_background(background_color, text_color, text):
    return colored_background(background_color, colored_text(text_color, text))


class BrainfuckRuntime:
    def __init__(self, declarations, source, symbol_table):
        self.tape = [0] * 32
        self.pointer = 0
        self.output = ''
        self.source = source
        self.symbol_table = symbol_table
        self.declaration_positions = {decl_name: index
                                      for (index, decl_name)
                                      in enumerate(declarations)}

    def print_state(self, instr_count, op_start_index, op_end_index, code):
        source_line_index = None
        for bf_indices, coord in self.symbol_table.items():
            if coord is not None and op_start_index >= bf_indices[0] and op_start_index < bf_indices[1]:
                match = re.match(r'.*:(\d+):.*', coord)
                if match:
                    source_line_index = int(match.group(1))

        for line_index, line in enumerate(self.source.strip().split('\n')):
            if line_index + 1 == source_line_index:
                print(colored_text_background(BackgroundColor.LIGHT_GREEN, TextColor.BLACK,
                                              line))
            else:
                print(line)

        print()

        colored_code = "{}{}{}".format(
            code[:op_start_index],
            colored_text_background(BackgroundColor.LIGHT_CYAN, TextColor.BLACK,
                                    code[op_start_index:op_end_index+1]),
            code[op_end_index+1:])

        code_line_prefix = ' ' * (len(str(instr_count)) + 2)
        code_lines = ('\n' + code_line_prefix).join(colored_code.split('\n'))
        print('{}: {}'.format(instr_count, code_lines))

        tape_sections = [[TapeIndices.START, TapeIndices.END_STOP_INDICATOR],
                         [TapeIndices.START_IP_WORKSPACE, TapeIndices.END_IP_WORKSPACE],
                         [TapeIndices.START_STACK, len(self.tape) - 1]]

        prefix = ' ' * len(str(instr_count)) + '  '
        colored_tape = ''
        for (value_index, value) in enumerate(self.tape):
            if value_index in [section[0] for section in tape_sections]:
                colored_tape += '['

            if value_index == self.pointer:
                colored_tape += colored_text_background(BackgroundColor.LIGHT_MAGENTA,
                                                        TextColor.BLACK, value)
            else:
                colored_tape += str(value)

            if value_index in [section[1] for section in tape_sections]:
                colored_tape += ']'

            colored_tape += ' '

        print('{}{}{}\n'.format(prefix, '({}) '.format(self.pointer).ljust(5), colored_tape))

        # [0] prevents an empty declaration_positions from causing max() to raise error
        max_declaration_length = max([0] + [len(name) for name in self.declaration_positions])
        reversed_declarations = {value: key for (key, value) in self.declaration_positions.items()}
        for position in sorted(reversed_declarations.keys()):
            padded_name = (reversed_declarations[position] + ':').ljust(max_declaration_length+2)
            tape_position = TapeIndices.START_STACK + position
            value = self.tape[tape_position]
            if self.pointer == tape_position:
                value = colored_text_background(BackgroundColor.LIGHT_MAGENTA, TextColor.BLACK, value)
            print('[{}] {}{}'.format(position, padded_name, value))
        print()

        if len(self.output) > 0:
            text = colored_text_background(BackgroundColor.RED, TextColor.DEFAULT, self.output)
            print(text + '\n')

    def get_declaration_value(self, declaration_name):
        position = self.declaration_positions[declaration_name]
        tape_position = TapeIndices.START_STACK + position
        return self.tape[tape_position]

    def execute(self, code, debug=False):
        index = 0
        instr_count = 0
        last_op = None
        step_through = False
        number = None
        op_start_index = 0
        previous_input_line = 'c'
        skip_breakpoints = not debug

        while index < len(code):
            if self.pointer < 0:
                raise Exception("Bad tape pointer: {}".format(self.pointer))

            op = code[index]

            if op == '!' and not skip_breakpoints:
                step_through = True

            elif ord(op) in range(ord('0'), ord('9') + 1):
                digit = ord(op) - ord('0')
                if number is None:
                    number = digit
                else:
                    number = number*10 + digit

            elif op in ('+', '-', '>', '<', '.', ',', '[', ']'):
                if op != last_op:
                    if debug:
                        self.print_state(instr_count, op_start_index, index, code)

                    if step_through:
                        line = input()
                        if len(line) == 0:
                            line = previous_input_line

                        command = line[0]
                        if line == 'c':
                            step_through = False
                        elif line == 'q':
                            sys.exit(0)
                        elif line == 'f':
                            step_through = False
                            skip_breakpoints = True

                        previous_input_line = line

                count = 1 if number is None else number
                for i in range(count):
                    if op == '+':
                        self.tape[self.pointer] += 1
                    elif op == '-':
                        self.tape[self.pointer] -= 1
                    elif op == '>':
                        self.pointer += 1
                    elif op == '<':
                        self.pointer -= 1

                    elif op == '.':
                        value = chr(self.tape[self.pointer])
                        self.output += value

                    elif op == ',':
                        line = ''
                        while len(line) == 0:
                            print('> ', end='')
                            line = input()

                        self.tape[self.pointer] = ord(line[0])

                    elif op == '[':
                        last_op = None
                        if self.tape[self.pointer] == 0:
                            stack = 1
                            while stack > 0:
                                index += 1
                                if code[index] == '[':
                                    stack += 1
                                elif code[index] == ']':
                                    stack -= 1

                    elif op == ']':
                        last_op = None
                        stack = 1
                        while stack > 0:
                            index -= 1
                            if code[index] == '[':
                                stack -= 1
                            elif code[index] == ']':
                                stack += 1

                        index -= 1

                instr_count += 1
                number = None
                op_start_index = index + 1

            else:
                op_start_index = index + 1

            last_op = op
            index += 1

        if debug:
            self.print_state(instr_count, op_start_index, index, code)

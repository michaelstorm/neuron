from .console import BackgroundColor, TextColor,bold_text, colored_text_background
from .visitor import TapeIndices
from pprint import pprint
import re
import sys


class BrainfuckRuntime:
    def __init__(self, declaration_mapper, source, static_data, symbol_table):
        self.tape = [0] * (TapeIndices.START_STATIC_SEGMENT + 16)
        self.pointer = 0
        self.output = ''
        self.source = source
        self.static_data = static_data
        self.symbol_table = symbol_table
        self.declaration_mapper = declaration_mapper
        self.modified_indices = []
        self.breakpoints = []

    def print_source(self, op_start_index):
        source_line_index = None
        for bf_indices, coord in self.symbol_table.items():
            if coord is not None and op_start_index >= bf_indices[0] and op_start_index < bf_indices[1]:
                match = re.match(r'.*:(\d+)', coord)
                if match:
                    source_line_index = int(match.group(1))

        for line_index, line in enumerate(self.source.strip().split('\n')):
            if line_index + 1 == source_line_index:
                print(colored_text_background(BackgroundColor.LIGHT_GREEN, TextColor.BLACK,
                                              line))
            else:
                print(line)

    def print_bf(self, instr_count, op_start_index, op_end_index, code):
        colored_code = ''

        frame_points = [(op_start_index, op_end_index)] + self.breakpoints + [(i, i) for i, c in enumerate(code) if c == '!']
        frame_points.sort(key=lambda t: t[0])

        end = 0
        fp_index = 0
        while end < len(code) and fp_index < len(frame_points):
            fp = frame_points[fp_index]
            colored_code += code[end:fp[0]]

            for i, c in enumerate(code[max(end, fp[0]):fp[1]+1]):
                index = i + fp[0]
                is_breakpoint = c == '!' or self.index_in_breakpoint(index)

                if index >= op_start_index and index <= op_end_index:
                    colored_char = colored_text_background(BackgroundColor.LIGHT_CYAN, TextColor.BLACK, c)
                    if is_breakpoint:
                        colored_char = bold_text(colored_char)
                    colored_code += colored_char
                elif is_breakpoint:
                    colored_code += colored_text_background(100, TextColor.DEFAULT, c)
                else:
                    colored_code += c

            end = max(end, fp[1] + 1)
            fp_index += 1

        colored_code += code[end:]

        code_line_prefix = ' ' * (len(str(instr_count)) + 2)
        code_lines = ('\n' + code_line_prefix).join(colored_code.split('\n'))
        print('{}: {}'.format(instr_count, code_lines))

    def print_tape(self, instr_count):
        tape_sections = [('', [TapeIndices.START, TapeIndices.END_STOP_INDICATOR]),
                         ('ip', [TapeIndices.START_IP_WORKSPACE, TapeIndices.END_IP_WORKSPACE]),
                         ('stack', [TapeIndices.START_STACK, TapeIndices.END_STACK]),
                         ('lvalues', [TapeIndices.START_LVALUES, TapeIndices.END_LVALUES]),
                         ('static', [TapeIndices.START_STATIC_SEGMENT, len(self.tape) - 1])]

        prefix = ' ' * len(str(instr_count)) + '  '
        colored_tape = ''
        offset = 1
        section_names = []
        for (value_index, value) in enumerate(self.tape):
            start_sections = {section[1][0]: section[0] for section in tape_sections}
            if value_index in start_sections:
                section_names.append([start_sections[value_index], offset])
                colored_tape += '['
                offset += 1

            if value_index == self.pointer:
                colored_tape += colored_text_background(BackgroundColor.LIGHT_MAGENTA,
                                                        TextColor.BLACK, value)
            elif value_index in self.modified_indices:
                colored_tape += colored_text_background(BackgroundColor.LIGHT_GREEN,
                                                        TextColor.BLACK, value)
            else:
                colored_tape += str(value)

            if value_index in [section[1][1] for section in tape_sections]:
                colored_tape += ']'
                offset += 1

            colored_tape += ' '
            offset += 2

        section_line = ''
        for section_name in section_names:
            section_line = section_line.ljust(section_name[1]) + section_name[0]

        print('{}{}{}'.format(prefix, '({}) '.format(self.pointer).ljust(5), colored_tape))
        print(prefix + ' ' * 5 + section_line + '\n')

    def print_variables(self):
        # [0] prevents an empty declaration_position from causing max() to raise error
        max_declaration_length = max([0] + [len(name) for name in self.declaration_mapper.positions])
        reversed_declarations = {value: key for (key, value) in self.declaration_mapper.positions.items()}

        for mapped_declaration in sorted(reversed_declarations.keys(), key=lambda d: d.position):
            padded_name = (reversed_declarations[mapped_declaration] + ':').ljust(max_declaration_length+2)
            tape_position = TapeIndices.START_STACK + mapped_declaration.position

            size = mapped_declaration.declaration.size
            if size == 1:
                value = self.tape[tape_position]
            else:
                value = '{{{}}}'.format(', '.join([str(self.tape[tape_position + 3*i]) for i in range(size)]))

            line = '{}{}{}'.format('[{}] '.format(tape_position).rjust(5), padded_name, value)
            if self.pointer == tape_position:
                line = colored_text_background(BackgroundColor.LIGHT_MAGENTA, TextColor.BLACK, line)
            print(line)

    def print_output(self):
        if len(self.output) > 0:
            text = colored_text_background(BackgroundColor.RED, TextColor.DEFAULT, self.output)
            print(text + '\n')

    def print_state(self, instr_count, op_start_index, op_end_index, code):
        self.print_source(op_start_index)
        print()

        self.print_bf(instr_count, op_start_index, op_end_index, code)
        print()

        self.print_tape(instr_count)
        self.print_variables()
        print()

        self.print_output()

    def get_declaration_value(self, declaration_name):
        position = self.declaration_mapper[declaration_name]
        tape_position = TapeIndices.START_STACK + position
        return self.tape[tape_position]

    def get_array_value(self, declaration_name, offset):
        position = self.declaration_mapper[declaration_name]
        tape_position = TapeIndices.START_STACK + position + offset * 3 + 2
        return self.tape[tape_position]

    def index_in_breakpoint(self, index):
        return any([index >= b_start_index and index <= b_end_index for b_start_index, b_end_index in self.breakpoints])

    def execute(self, code, debug=False):
        index = 0
        instr_count = 0
        step_into = False
        step_over = False
        step_over_start = None
        prompt_once = False
        comment = False
        color_code = False
        number = None
        op_start_index = 0
        previous_input_line = 'c'
        skip_breakpoints = not debug

        while index < len(code):
            if self.pointer < 0:
                raise Exception("Bad tape pointer: {}".format(self.pointer))

            op = code[index]

            if op == '{':
                comment = True
            elif op == '}':
                comment = False
            elif op == '\033':
                color_code = True
            elif color_code and op == 'm':
                color_code = False
            elif not comment and not color_code:
                if op == '!' and not skip_breakpoints:
                    step_into = True
                    op_start_index = index + 1

                elif ord(op) in range(ord('0'), ord('9') + 1):
                    digit = ord(op) - ord('0')
                    if number is None:
                        number = digit
                    else:
                        number = number*10 + digit

                elif op in ('+', '-', '>', '<', '.', ',', '[', ']'):
                    get_input_line = ((step_into or step_over) and step_over_start == None) or self.index_in_breakpoint(index) or prompt_once

                    if get_input_line:
                        if debug:
                            self.print_state(instr_count, op_start_index, index, code)

                        prompt_once = False
                        line = input()
                        if len(line) == 0:
                            line = previous_input_line
                        previous_input_line = line

                        command = line[0] if len(line) > 0 else ''
                        if len(command) > 0 and command in 'csnr': # the empty string is a substring of any string
                            self.modified_indices = []

                            step_into = False
                            step_over = False
                            if command == 'c':
                                pass
                            elif command == 's':
                                step_into = True
                            elif command == 'n':
                                step_over = True
                            elif command == 'r':
                                skip_breakpoints = True
                            else:
                                raise Exception('Accidentally captured command {}'.format(command))

                        elif command == 'b':
                            breakpoint = (op_start_index, index)
                            if self.index_in_breakpoint(index):
                                self.breakpoints.remove(breakpoint)
                            else:
                                self.breakpoints.append(breakpoint)

                            prompt_once = True
                            continue

                        elif command == 'q':
                            sys.exit(0)

                        else:
                            prompt_once = True
                            continue

                    count = 1 if number is None else number
                    for i in range(count):
                        if op == '+':
                            self.tape[self.pointer] += 1
                            if not get_input_line:
                                self.modified_indices.append(self.pointer)

                        elif op == '-':
                            self.tape[self.pointer] -= 1
                            if not get_input_line:
                                self.modified_indices.append(self.pointer)

                        elif op == '>':
                            self.pointer += 1
                            if self.pointer == len(self.tape):
                                self.tape.append(0)

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
                            if self.tape[self.pointer] == 0:
                                if step_over_start == index:
                                    step_over_start = None

                                stack = 1
                                while stack > 0:
                                    index += 1
                                    if code[index] == '[' and code[index-1] != '\033':
                                        stack += 1
                                    elif code[index] == ']':
                                        stack -= 1

                            elif step_over and step_over_start == None:
                                step_over_start = index

                        elif op == ']':
                            stack = 1
                            while stack > 0:
                                index -= 1
                                if code[index] == '[' and (index == 0 or code[index-1] != '\033'):
                                    stack -= 1
                                elif code[index] == ']':
                                    stack += 1

                            index -= 1

                    instr_count += 1
                    number = None
                    op_start_index = index + 1

                else:
                    op_start_index = index + 1

            index += 1

        if debug:
            self.print_state(instr_count, op_start_index, index, code)

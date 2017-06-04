class BrainfuckRuntime:
    def __init__(self):
        self.tape = [0] * 32
        self.pointer = 0

    def print_state(self, instr_count, index, code):
        colored_code = [("\033[42m{}\033[49m".format(op) if op_index == index else op)
                        for (op_index, op) in enumerate(code)]
        print('{}: {}'.format(instr_count, ''.join(colored_code)))

        prefix = ' ' * len(str(instr_count)) + '  '
        colored_tape = [("\033[45m{}\033[49m".format(value) if value_index == self.pointer
                         else str(value))
                        for (value_index, value) in enumerate(self.tape)]

        print(prefix + ' '.join(colored_tape))
        print()

    def execute(self, code):
        index = 0
        instr_count = 0
        last_op = None
        while index < len(code):
            op = code[index]

            if op in ('+', '-', '>', '<', '[', ']'):
                if op != last_op:
                    self.print_state(instr_count, index, code)

                if op == '+':
                    self.tape[self.pointer] += 1
                elif op == '-':
                    self.tape[self.pointer] -= 1
                elif op == '>':
                    self.pointer += 1
                elif op == '<':
                    self.pointer -= 1
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

            last_op = op
            index += 1

        self.print_state(instr_count, index, code)

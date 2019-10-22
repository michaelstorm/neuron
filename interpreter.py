from neuron.visitor import DeclarationMapper
from neuron.bf import BrainfuckRuntime
import fileinput


if __name__ == "__main__":
    bf = ''
    for line in fileinput.input():
        bf += line

    declaration_mapper = DeclarationMapper(set())
    runtime = BrainfuckRuntime(declaration_mapper, '', [], {}, print_tape_sections=False)
    runtime.execute(bf, debug=True, start_break=True)

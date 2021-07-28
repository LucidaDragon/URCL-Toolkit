from urcl import *
import sys

args = sys.argv[1:len(sys.argv)]

inputs = []
output = "output.py"
nextArgIsOutput = False
for arg in args:
	if arg.startswith("-"):
		nextArgIsOutput = False
		if arg == "-o":
			nextArgIsOutput = True
		else:
			print("Unknown command line option: " + arg)
			exit(1)
	elif nextArgIsOutput:
		output = arg
		nextArgIsOutput = False
	else:
		inputs += [arg]

from urclpy import PythonEmit
emitter = Emitter(emitTarget=PythonEmit(useDebugger=True))

for file in inputs:
	with open(file) as stream:
		lines = stream.readlines()
		for line in lines:
			inst = ParseInstruction(line)
			if inst != None:
				if emitter.IsLabel(inst):
					emitter.MarkLabel(inst)
				else:
					emitter.Emit(inst.Operation, inst.OperandA, inst.OperandB, inst.OperandC)

with open(output, "w") as file:
    file.write(str(emitter))
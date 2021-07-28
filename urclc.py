from urcl import *

class CEmit:
	def __init__(self, ramSize, stackSize):
		self.Registers = ["SP"]
		self._LocalRegisters = []
		self.Labels = {}
		self.Source = "#pragma once\n#define False 0\n#define True 1\n#define sizeof(x) (sizeof(x) / sizeof(int))\n" + \
			"int RAM[" + str(ramSize) + "];\n" + \
			"int STACK[" + str(stackSize) + "];\n" + \
			"static const char* SUCCESS = \"Success.\";\n" + \
			"static const char* ERR_UNDERFLOW = \"Stack underflow.\";\n" + \
			"int IP = 0;\nint HALT = False;\nint BREAK = False;\nconst char* STATUS = 0;\n\n" + \
			"void Error(const char* msg)\n{\n" + \
			"\tSTATUS = msg;\n}\n\n" + \
			"int Get(int addr)\n{\n" + \
			"\tif (addr < 0)\n\t{\n" + \
			"\t\tif ((-addr - 1) < sizeof(STACK)) return STACK[-addr - 1];\n" + \
			"\t\telse return 0;\n\t}\n" + \
			"\telse if (addr < sizeof(RAM))\n\t{\n" + \
			"\t\treturn RAM[addr];\n\t}\n" + \
			"\telse\n\t{\n" + \
			"\t\tError(\"Data segfault.\");\n" + \
			"\t\treturn 0;\n\t}\n}\n\n" + \
			"void Set(int addr, int value)\n{\n" + \
			"\tif (addr < 0)\n\t{\n" + \
			"\t\tif ((-addr - 1) >= sizeof(STACK)) Error(\"Stack overflow.\");\n" + \
			"\t\tSTACK[-addr - 1] = value;\n\t}\n" + \
			"\telse\n\t{\n" + \
			"\t\tif (addr >= sizeof(RAM)) Error(\"Data segfault.\");\n" + \
			"\t\tRAM[addr] = value;\n\t}\n}\n\n"
		self.Executor = "void Execute()\n{\n" + \
			"\tBREAK = False;\n" + \
			"\tSTATUS = SUCCESS;\n" + \
			"\twhile (!HALT)\n\t{\n" + \
			"\t\tif (IP < 0 || IP >= sizeof(ROM)) Error(\"Code segfault.\");\n" + \
			"\t\tROM[IP]();\n" + \
			"\t\tif (STATUS != SUCCESS) return;\n" + \
			"\t\tIP += 1;\n" + \
			"\t\tif (BREAK) return;\n\t}\n}\n#undef sizeof\n#undef True\n#undef False"
	
	def IsLabel(self, value):
		if value == None:
			return False
		value = str(value)
		return len(value) > 0 and value[0] == '.'
	
	def IsRegister(self, value):
		value = str(value)
		if value == None:
			return False
		elif value != "R0" and (len(value) > 0 and value[0] == "R"):
			try:
				value = int(value[1:len(value)])
				return True
			except:
				return False
		else:
			return value == "SP"
	
	def IncludeInstructionRegisters(self, inst):
		if self.IsRegister(inst.OperandA) and not inst.OperandA in self.Registers:
			self.Registers += [inst.OperandA]
		if self.IsRegister(inst.OperandB) and not inst.OperandB in self.Registers:
			self.Registers += [inst.OperandB]
		if self.IsRegister(inst.OperandC) and not inst.OperandC in self.Registers:
			self.Registers += [inst.OperandC]

	def GetLabelName(self, label):
		return "LABEL_" + label[1:len(label)]
	
	def Stringify(self, text):
		return str(text).replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n")

	def EmitLabelCode(self, label, position):
		if len(label) > 0:
			if self.IsLabel(label):
				self.Source += "const int " + self.GetLabelName(label) + " = " + str(position) + ";\n"
			else:
				self.EmitError("\"" + str(label) + "\" is not a valid label.")
		else:
			self.EmitWarning("Empty label was ignored.")

	def EmitException(self, ex):
		self.Source += "{\n\t\tError(" + str(ex) + ");\n\t\treturn;\n\t}\n"

	def EmitOperation(self, target, a, op, b):
		if target == a:
			self.Source += "\t" + str(target) + " " + str(op) + "= " + str(b) + ";\n"
		else:
			self.Source += "\t" + str(target) + " = " + str(a) + " " + str(op) + " " + str(b) + ";\n"
	
	def EmitAssignment(self, target, source):
		self.EmitOperation(target, target, "", source)
	
	def EmitConditional(self, a, op, b):
		self.Source += "\tif (" + str(a) + " " + str(op) + " " + str(b) + ")\n\t"
	
	def EmitBranch(self, target, a, op, b):
		self.EmitConditional(a, op, b)
		self.EmitOperation("IP", target, "-", 1)

	def EmitLoad(self, target, address):
		self.Source += "\t" + str(target) + " = Get(" + str(address) + ");\n"
	
	def EmitStore(self, address, source):
		self.Source += "\tSet(" + str(address) + ", " + str(source) + ");\n"
	
	def EmitCopy(self, target, source):
		self.Source += "\tSet(" + str(target) + ", Get(" + str(source) + "));\n"

	def EmitPush(self, source):
		self.EmitOperation("SP", "SP", "-", 1)
		self.EmitStore("SP", source)

	def EmitPop(self, target):
		self.EmitConditional("SP", ">=", 0)
		self.EmitException("ERR_UNDERFLOW")
		self.EmitLoad(target, "SP")
		self.EmitOperation("SP", "SP", "+", 1)

	def EmitWarning(self, text):
		self.Source += "//WARNING: " + str(text) + "\n"
		print("WARNING: " + text)
	
	def EmitError(self, text):
		self.Source += "//ERROR: " + str(text) + "\n"
		print("ERROR: " + text)
	
	def ClearRegisters(self):
		self._LocalRegisters = []
	
	def UseRegister(self, reg):
		if not reg in self._LocalRegisters:
			self._LocalRegisters += [reg]

	def ResolveOperand(self, operand):
		if self.IsRegister(operand):
			self.UseRegister(operand)
		elif self.IsLabel(operand):
			operand = self.GetLabelName(operand)
		elif operand == ZERO:
			operand = 0
		return operand

	def EmitInstructionCode(self, inst, position):
		self.ClearRegisters()

		self.Source += "static void INST_" + str(position) + "()\n{\n"

		inst.OperandA = self.ResolveOperand(inst.OperandA)
		inst.OperandB = self.ResolveOperand(inst.OperandB)
		inst.OperandC = self.ResolveOperand(inst.OperandC)

		op = inst.Operation
		isZeroOperand = inst.OperandA == None
		isOneOperand = inst.OperandA != None and inst.OperandB == None
		isTwoOperand = inst.OperandA != None and inst.OperandB != None and inst.OperandC == None
		isThreeOperand = inst.OperandA != None and inst.OperandB != None and inst.OperandC != None

		if isZeroOperand:
			if op == NOP:
				pass
			elif op == HLT:
				self.EmitAssignment("HALT", "True")
			elif op == BRK:
				self.EmitAssignment("BREAK", "True")
			elif op == RET:
				self.EmitPop("IP")
			else:
				self.EmitError("\"" + str(op) + "\" does not take zero operands.")
		elif isOneOperand:
			if op == PSH:
				self.EmitPush(inst.OperandA)
			elif op == POP:
				self.EmitPop(inst.OperandA)
			elif op == JMP:
				self.EmitOperation("IP", inst.OperandA, "-", 1)
			elif op == CAL:
				self.EmitPush("IP")
				self.EmitOperation("IP", inst.OperandA, "-", 1)
			else:
				self.EmitError("\"" + str(op) + "\" does not take one operand.")
		elif isTwoOperand:
			if op == LOD:
				self.EmitLoad(inst.OperandA, inst.OperandB)
			elif op == STR:
				self.EmitStore(inst.OperandA, inst.OperandB)
			elif op == MOV or op == IMM:
				self.EmitOperation(inst.OperandA, inst.OperandA, "", inst.OperandB)
			elif op == LSH:
				self.EmitOperation(inst.OperandA, inst.OperandB, "<<", 1)
			elif op == RSH:
				self.EmitOperation(inst.OperandA, inst.OperandB, ">>", 1)
			elif op == INC:
				self.EmitOperation(inst.OperandA, inst.OperandB, "+", 1)
			elif op == DEC:
				self.EmitOperation(inst.OperandA, inst.OperandB, "-", 1)
			elif op == NOT:
				self.EmitAssignment(inst.OperandA, "~" + str(inst.OperandB))
			elif op == BRZ:
				self.EmitBranch(inst.OperandA, inst.OperandB, "==", 0)
			elif op == BNZ:
				self.EmitBranch(inst.OperandA, inst.OperandB, "!=", 0)
			elif op == CPY:
				self.EmitCopy(inst.OperandA, inst.OperandB)
			else:
				self.EmitError("\"" + str(op) + "\" does not take two operands.")
		elif isThreeOperand:
			if op == ADD:
				self.EmitOperation(inst.OperandA, inst.OperandB, "+", inst.OperandC)
			elif op == SUB:
				self.EmitOperation(inst.OperandA, inst.OperandB, "-", inst.OperandC)
			elif op == MLT:
				self.EmitOperation(inst.OperandA, inst.OperandB, "*", inst.OperandC)
			elif op == DIV:
				self.EmitOperation(inst.OperandA, inst.OperandB, "/", inst.OperandC)
			elif op == MOD:
				self.EmitOperation(inst.OperandA, inst.OperandB, "%", inst.OperandC)
			elif op == AND:
				self.EmitOperation(inst.OperandA, inst.OperandB, "&", inst.OperandC)
			elif op == OR:
				self.EmitOperation(inst.OperandA, inst.OperandB, "|", inst.OperandC)
			elif op == XOR:
				self.EmitOperation(inst.OperandA, inst.OperandB, "^", inst.OperandC)
			elif op == BSL:
				self.EmitOperation(inst.OperandA, inst.OperandB, "<<", inst.OperandC)
			elif op == BSR:
				self.EmitOperation(inst.OperandA, inst.OperandB, ">>", inst.OperandC)
			elif op == BRE:
				self.EmitBranch(inst.OperandA, inst.OperandB, "==", inst.OperandC)
			elif op == BNE:
				self.EmitBranch(inst.OperandA, inst.OperandB, "!=", inst.OperandC)
			elif op == BRL:
				self.EmitBranch(inst.OperandA, inst.OperandB, "<", inst.OperandC)
			elif op == BRG:
				self.EmitBranch(inst.OperandA, inst.OperandB, ">", inst.OperandC)
			elif op == BLE:
				self.EmitBranch(inst.OperandA, inst.OperandB, "<=", inst.OperandC)
			elif op == BGE:
				self.EmitBranch(inst.OperandA, inst.OperandB, ">=", inst.OperandC)
			else:
				self.EmitError("\"" + str(op) + "\" does not take three operands.")
		else:
			self.EmitError("Invalid instruction \"" + str(inst) + "\".")
		
		self.Source += "}\n\n"
		return "INST_" + str(position)

	def Emit(self, emitter):
		for inst in emitter.Instructions:
			self.IncludeInstructionRegisters(inst)
		
		for reg in self.Registers:
			self.Source += "int " + str(reg) + " = 0;\n"

		for position in emitter.Labels:
			for label in emitter.Labels[position]:
				self.EmitLabelCode(label, position)
		
		self.Source += "\n"

		instructions = []
		for position in range(len(emitter.Instructions)):
			instructions += [self.EmitInstructionCode(emitter.Instructions[position], position)]

		self.Source += "void (*ROM[])() = { "
		first = True
		for inst in instructions:
			if first:
				self.Source += inst
				first = False
			else:
				self.Source += ", " + inst

		self.Source += " };\n\n" + self.Executor

		return self.Source
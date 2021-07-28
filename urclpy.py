from urcl import *

class PythonEmit:
	def __init__(self, useDebugger=False, printURCLToConsole=False, printRegisterStatesToConsole=False, singleStep=False):
		self.PrintURCLToConsole = printURCLToConsole
		self.PrintRegisterStatesToConsole = printRegisterStatesToConsole
		self.SingleStep = singleStep
		self.UseDebugger = useDebugger
		self.Registers = ["SP"]
		self._LocalRegisters = []
		self.Labels = {}
		self.Source = "RAM = {}\nROM = {}\nIP = 0\nHALT = False\nBREAK = False\nSTEP = False\nSTACK = []\n" + \
			"ERR_UNDERFLOW = ValueError(\"Stack underflow occured.\")\n\n" + \
			"def Get(addr):\n" + \
			"\tglobal RAM\n\tglobal STACK\n" + \
			"\tif addr < 0:\n" + \
			"\t\tif (-addr - 1) < len(STACK):\n" + \
			"\t\t\treturn STACK[-addr - 1]\n" + \
			"\t\telse:\n" + \
			"\t\t\treturn 0\n" + \
			"\telif addr in RAM:\n" + \
			"\t\treturn RAM[addr]\n" + \
			"\telse:\n" + \
			"\t\treturn 0\n\n" + \
			"def Set(addr, value):\n" + \
			"\tglobal RAM\n\tglobal STACK\n" + \
			"\tif addr < 0:\n" + \
			"\t\twhile (-addr - 1) >= len(STACK):\n" + \
			"\t\t\tSTACK += [0]\n" + \
			"\t\tSTACK[-addr - 1] = value\n" + \
			"\telse:\n" + \
			"\t\tRAM[addr] = value\n\n" + \
			"def Execute():\n" + \
			"\tglobal ROM\n" + \
			"\tglobal IP\n" + \
			"\tglobal HALT\n" + \
			"\tglobal BREAK\n" + \
			"\tglobal STEP\n\n" + \
			"\tBREAK = False\n" + \
			"\twhile not HALT:\n" + \
			"\t\tif not IP in ROM:\n" + \
			"\t\t\traise ValueError(\"Instruction pointer is out of bounds.\")\n" + \
			"\t\tROM[IP]()\n" + \
			"\t\tIP += 1\n" + \
			"\t\tif STEP or BREAK:\n" + \
			"\t\t\treturn\n\n"
	
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
				self.Source += self.GetLabelName(label) + " = " + str(position) + "\n"
			else:
				self.EmitError("\"" + str(label) + "\" is not a valid label.")
		else:
			self.EmitWarning("Empty label was ignored.")

	def EmitException(self, ex):
		self.Source += "\traise " + str(ex) + "\n"

	def EmitOperation(self, target, a, op, b):
		if target == a:
			self.Source += "\t" + str(target) + " " + str(op) + "= " + str(b) + "\n"
		else:
			self.Source += "\t" + str(target) + " = " + str(a) + " " + str(op) + " " + str(b) + "\n"
	
	def EmitAssignment(self, target, source):
		self.EmitOperation(target, target, "", source)
	
	def EmitConditional(self, a, op, b):
		self.Source += "\tif " + str(a) + " " + str(op) + " " + str(b) + ":\n\t"
	
	def EmitBranch(self, target, a, op, b):
		self.EmitConditional(a, op, b)
		self.EmitOperation("IP", target, "-", 1)

	def EmitLoad(self, target, address):
		self.Source += "\t" + str(target) + " = Get(" + str(address) + ")\n"
	
	def EmitStore(self, address, source):
		self.Source += "\tSet(" + str(address) + ", " + str(source) + ")\n"
	
	def EmitCopy(self, target, source):
		self.Source += "\tSet(" + str(target) + ", Get(" + str(source) + "))\n"

	def EmitPush(self, source):
		self.EmitOperation("SP", "SP", "-", 1)
		self.EmitStore("SP", source)

	def EmitPop(self, target):
		self.EmitConditional("SP", ">=", 0)
		self.EmitException("ERR_UNDERFLOW")
		self.EmitLoad(target, "SP")
		self.EmitOperation("SP", "SP", "+", 1)
	
	def EmitGlobal(self, target):
		if self.IsRegister(target):
			self.UseRegister(target)
		self.Source += "\tglobal " + str(target) + "\n"

	def EmitPrint(self, text):
		self.Source += "\tprint(\"" + self.Stringify(text) + "\")\n"
	
	def EmitPrintValue(self, source):
		self.Source += "\tprint(\"" + self.Stringify(source) + " = \" + str(" + str(source) + "))\n"

	def EmitWarning(self, text):
		self.Source += "#WARNING: " + str(text) + "\n"
		print("WARNING: " + text)
	
	def EmitError(self, text):
		self.Source += "#ERROR: " + str(text) + "\n"
		print("ERROR: " + text)
	
	def ClearRegisters(self):
		self._LocalRegisters = []
	
	def UseRegister(self, reg):
		if not reg in self._LocalRegisters:
			self._LocalRegisters += [reg]

	def ResolveOperand(self, operand):
		if self.IsRegister(operand):
			self.EmitGlobal(operand)
			self.UseRegister(operand)
		elif self.IsLabel(operand):
			operand = self.GetLabelName(operand)
			self.EmitGlobal(operand)
		elif operand == ZERO:
			operand = 0
		return operand

	def EmitInstructionCode(self, inst, position):
		self.ClearRegisters()

		originalSource = str(inst)
		self.Source += "def INST_" + str(position) + "():\n"

		if self.PrintURCLToConsole:
			self.EmitPrint("\n" + str(inst))

		inst.OperandA = self.ResolveOperand(inst.OperandA)
		inst.OperandB = self.ResolveOperand(inst.OperandB)
		inst.OperandC = self.ResolveOperand(inst.OperandC)

		if self.PrintRegisterStatesToConsole and len(self._LocalRegisters) > 0:
			self.EmitPrint("Pre-operation registers:")
			for reg in self._LocalRegisters:
				self.EmitPrintValue(reg)
		
		if self.SingleStep:
			self.Source += "\tinput(\"Press enter to execute...\")\n"

		op = inst.Operation
		isZeroOperand = inst.OperandA == None
		isOneOperand = inst.OperandA != None and inst.OperandB == None
		isTwoOperand = inst.OperandA != None and inst.OperandB != None and inst.OperandC == None
		isThreeOperand = inst.OperandA != None and inst.OperandB != None and inst.OperandC != None

		if isZeroOperand:
			if op == NOP:
				pass
			elif op == HLT:
				self.EmitGlobal("HALT")
				self.EmitAssignment("HALT", "True")
			elif op == BRK:
				self.EmitGlobal("BREAK")
				self.EmitAssignment("BREAK", "True")
			elif op == RET:
				self.EmitGlobal("IP")
				self.EmitGlobal("SP")
				self.EmitPop("IP")
			else:
				self.EmitError("\"" + str(op) + "\" does not take zero operands.")
		elif isOneOperand:
			if op == PSH:
				self.EmitGlobal("SP")
				self.EmitPush(inst.OperandA)
			elif op == POP:
				self.EmitGlobal("SP")
				self.EmitGlobal("ERR_UNDERFLOW")
				self.EmitPop(inst.OperandA)
			elif op == JMP:
				self.EmitGlobal("IP")
				self.EmitOperation("IP", inst.OperandA, "-", 1)
			elif op == CAL:
				self.EmitGlobal("IP")
				self.EmitGlobal("SP")
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
				self.EmitGlobal("IP")
				self.EmitBranch(inst.OperandA, inst.OperandB, "==", 0)
			elif op == BNZ:
				self.EmitGlobal("IP")
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
				self.EmitOperation(inst.OperandA, inst.OperandB, "//", inst.OperandC)
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
		
		if self.PrintRegisterStatesToConsole and len(self._LocalRegisters) > 0:
			self.EmitPrint("Post-operation registers:")
			for reg in self._LocalRegisters:
				self.EmitPrintValue(reg)

		self.Source += "\treturn\nINST_" + str(position) + ".Source = \"" + self.Stringify(originalSource) + "\"\nROM[" + str(position) + "] = INST_" + str(position) + "\n\n"

	def Emit(self, emitter):
		for inst in emitter.Instructions:
			self.IncludeInstructionRegisters(inst)
		
		for reg in self.Registers:
			self.Source += str(reg) + " = 0\n"

		for position in emitter.Labels:
			for label in emitter.Labels[position]:
				self.EmitLabelCode(label, position)
		
		self.Source += "\n"

		for position in range(len(emitter.Instructions)):
			self.EmitInstructionCode(emitter.Instructions[position], position)

		if self.UseDebugger:
			return self.Source
		else:
			return self.Source + "Execute()"
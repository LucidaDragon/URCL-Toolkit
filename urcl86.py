NextLabelID = 0

def NewLabel():
	global NextLabelID
	label = "x86_lbl_" + str(NextLabelID)
	NextLabelID += 1
	return label

def REFSIZE(bits):
	if bits == 16:
		return "word"
	elif bits == 32:
		return "dword"
	elif bits == 64:
		return "qword"
	elif bits == 0:
		return "anyword"
	else:
		return ""

def REF(value, bits=0):
	return REFSIZE(bits) + " [" + str(value) + "]"

AX = "ax"
BX = "bx"
CX = "cx"
DX = "dx"
SI = "si"
DI = "di"
BP = "bp"
SP = "sp"

REGISTERS = [AX, BX, CX, DX, SI, DI, BP, SP]

REG_SP = REF("REG_SP")

ARGA = "%1"
ARGB = "%2"
ARGC = "%3"

MACRO = "macro"
BITS = "bits"
WORDSHIFT = "wordshift"

NOP = "nop"
HLT = "hlt"

MOV = "mov"

ADD = "add"
SUB = "sub"
MUL = "mul"
DIV = "div"
AND = "and"
OR = "or"
XOR = "xor"
NOT = "not"
NEG = "neg"
SHL = "shl"
SHR = "shr"
CMP = "cmp"

JMP = "jmp"
JZ = "jz"
JNZ = "jnz"
JA = "ja"
JB = "jb"
JAE = "jae"
JBE = "jbe"

MEMORYOFFSET = NewLabel()

class I86:
	def __init__(self, op=NOP, a=None, b=None):
		self.Operation = op
		self.OperandA = a
		self.OperandB = b
	
	def UpgradeRegister(self, reg, bits, expand=False, args=[], localLabel=""):
		reg = str(reg)
		if reg.startswith("anyword "):
			reg = reg.replace("anyword", REFSIZE(bits), 1)
		parts = reg.split(" ")
		lastRaw = parts[len(parts) - 1].strip("[]")
		if lastRaw in REGISTERS:
			if bits == 16:
				return reg
			elif bits == 32:
				return reg.replace(lastRaw, "e" + lastRaw)
			elif bits == 64:
				return reg.replace(lastRaw, "r" + lastRaw)
			else:
				raise ValueError("Word width of " + str(bits) + " is not valid.")
		elif reg == BITS:
			return str(bits)
		elif reg == WORDSHIFT:
			if bits == 16:
				return "1"
			elif bits == 32:
				return "2"
			elif bits == 64:
				return "3"
			else:
				raise ValueError("Word width of " + str(bits) + " is not valid.")
		elif expand:
			if reg.startswith("%%"):
				return localLabel
			elif reg == ARGA:
				if args[0] == ARGA:
					raise ValueError("Recursive macro.")
				return self.UpgradeRegister(args[0], bits, expand, args)
			elif reg == ARGB:
				if args[1] == ARGB:
					raise ValueError("Recursive macro.")
				return self.UpgradeRegister(args[1], bits, expand, args)
			elif reg == ARGC:
				if args[2] == ARGC:
					raise ValueError("Recursive macro.")
				return self.UpgradeRegister(args[2], bits, expand, args)
		return reg
	
	def Compile(self, bits, expand=False, args=[], localLabel=""):
		if self.Operation == MACRO:
			if expand:
				result = ""
				localLabel = NewLabel()
				for inst in self.OperandA.Body:
					childArgs = []
					for arg in self.OperandB:
						childArgs += [self.UpgradeRegister(arg, bits, expand, args, localLabel)]
					result += inst.Compile(bits, expand, childArgs, localLabel)
				return result
			else:
				result = self.OperandA.Name
				first = True
				for arg in self.OperandB:
					if first:
						result += " " + str(arg)
					else:
						result += ", " + str(arg)
					first = False
				return result + "\n"
		else:
			if expand and str(self.Operation).startswith("%%"):
				return localLabel + ":\n"
			if self.OperandA == None:
				return self.Operation + "\n"
			elif self.OperandB == None:
				return self.Operation + " " + self.UpgradeRegister(str(self.OperandA), bits, expand, args, localLabel) + "\n"
			else:
				return self.Operation + " " + self.UpgradeRegister(str(self.OperandA), bits, expand, args, localLabel) + ", " + self.UpgradeRegister(str(self.OperandB), bits, expand, args, localLabel) + "\n"

class Macro:
	def __init__(self, name, argumentCount=0, body=[]):
		self.Name = name
		self.ArgumentCount = argumentCount
		self.Body = body

	def Compile(self, bits, expanded=False, args=[]):
		localLabel = ""
		if expanded:
			localLabel = NewLabel()
		else:
			result = "%macro " + str(self.Name) + " " + str(self.ArgumentCount) + "\n"
		for inst in self.Body:
			result += inst.Compile(bits, expanded, args, localLabel)
		if not expanded:
			result += "%endmacro\n"
		return result

MACRO_ADD = Macro("URCL_ADD", 3, [
	I86(MOV, AX, ARGB),
	I86(ADD, AX, ARGC),
	I86(MOV, ARGA, AX)
])

MACRO_SUB = Macro("URCL_SUB", 3, [
	I86(MOV, AX, ARGB),
	I86(SUB, AX, ARGC),
	I86(MOV, ARGA, AX)
])

MACRO_MLT = Macro("URCL_MLT", 3, [
	I86(MOV, AX, ARGB),
	I86(MUL, ARGC),
	I86(MOV, ARGA, AX)
])

MACRO_DIV = Macro("URCL_DIV", 3, [
	I86(XOR, DX, DX),
	I86(MOV, AX, ARGB),
	I86(DIV, ARGC),
	I86(MOV, ARGA, AX)
])

MACRO_MOD = Macro("URCL_MOD", 3, [
	I86(XOR, DX, DX),
	I86(MOV, AX, ARGB),
	I86(DIV, ARGC),
	I86(MOV, ARGA, DX)
])

MACRO_AND = Macro("URCL_AND", 3, [
	I86(MOV, AX, ARGB),
	I86(AND, AX, ARGC),
	I86(MOV, ARGA, AX)
])

MACRO_OR = Macro("URCL_OR", 3, [
	I86(MOV, AX, ARGB),
	I86(OR, AX, ARGC),
	I86(MOV, ARGA, AX)
])

MACRO_XOR = Macro("URCL_XOR", 3, [
	I86(MOV, AX, ARGB),
	I86(XOR, AX, ARGC),
	I86(MOV, ARGA, AX)
])

MACRO_NOT = Macro("URCL_NOT", 2, [
	I86(MOV, AX, ARGB),
	I86(NOT, AX),
	I86(MOV, ARGA, AX)
])

MACRO_NEG = Macro("URCL_NEG", 2, [
	I86(MOV, AX, ARGB),
	I86(NEG, AX),
	I86(MOV, ARGA, AX)
])

MACRO_INC = Macro("URCL_INC", 2, [
	I86(MOV, AX, ARGB),
	I86(ADD, AX, 1),
	I86(MOV, ARGA, AX)
])

MACRO_DEC = Macro("URCL_DEC", 2, [
	I86(MOV, AX, ARGB),
	I86(SUB, AX, 1),
	I86(MOV, ARGA, AX)
])

MACRO_LSH = Macro("URCL_LSH", 2, [
	I86(MOV, AX, ARGB),
	I86(SHL, AX, 1),
	I86(MOV, ARGA, AX)
])

MACRO_RSH = Macro("URCL_RSH", 2, [
	I86(MOV, AX, ARGB),
	I86(SHR, AX, 1),
	I86(MOV, ARGA, AX)
])

MACRO_LOD = Macro("URCL_LOD", 2, [
	I86(MOV, BX, ARGB),
	I86(SHL, BX, WORDSHIFT),
	I86(MOV, BX, REF(BX)),
	I86(MOV, ARGA, BX)
])

MACRO_STR = Macro("URCL_STR", 2, [
	I86(MOV, AX, ARGB),
	I86(MOV, BX, ARGA),
	I86(SHL, BX, WORDSHIFT),
	I86(ADD, BX, MEMORYOFFSET),
	I86(MOV, REF(BX), AX)
])

MACRO_MOV = Macro("URCL_MOV", 2, [
	I86(MOV, AX, ARGB),
	I86(MOV, ARGA, AX)
])

MACRO_IMM = Macro("URCL_IMM", 2, [
	I86(MOV, ARGA, ARGB)
])

MACRO_PSH = Macro("URCL_PSH", 1, [
	I86(MACRO, MACRO_DEC, [REG_SP, 1]),
	I86(MACRO, MACRO_STR, [REG_SP, ARGA])
])

MACRO_POP = Macro("URCL_POP", 1, [
	I86(MACRO, MACRO_LOD, [ARGA, REG_SP]),
	I86(MACRO, MACRO_INC, [REG_SP, 1])
])

MACRO_JMP = Macro("URCL_JMP", 1, [
	I86(JMP, ARGA)
])

MACRO_BRZ = Macro("URCL_BRZ", 2, [
	I86(MOV, AX, ARGB),
	I86(CMP, AX, 0),
	I86(JNZ, "%%skip"),
	I86(MACRO, MACRO_JMP, [ARGA]),
	I86("%%skip:")
])

MACRO_BNZ = Macro("URCL_BNZ", 2, [
	I86(MOV, AX, ARGB),
	I86(CMP, AX, 0),
	I86(JZ, "%%skip"),
	I86(MACRO, MACRO_JMP, [ARGA]),
	I86("%%skip:")
])

MACRO_BRL = Macro("URCL_BRL", 3, [
	I86(MOV, AX, ARGB),
	I86(CMP, AX, 0),
	I86(JAE, "%%skip"),
	I86(MACRO, MACRO_JMP, [ARGA]),
	I86("%%skip:")
])

MACRO_BRG = Macro("URCL_BRG", 3, [
	I86(MOV, AX, ARGB),
	I86(CMP, AX, 0),
	I86(JBE, "%%skip"),
	I86(MACRO, MACRO_JMP, [ARGA]),
	I86("%%skip:")
])

MACRO_BLE = Macro("URCL_BLE", 3, [
	I86(MOV, AX, ARGB),
	I86(CMP, AX, 0),
	I86(JA, "%%skip"),
	I86(MACRO, MACRO_JMP, [ARGA]),
	I86("%%skip:")
])

MACRO_BGE = Macro("URCL_BGE", 3, [
	I86(MOV, AX, ARGB),
	I86(CMP, AX, 0),
	I86(JB, "%%skip"),
	I86(MACRO, MACRO_JMP, [ARGA]),
	I86("%%skip:")
])

MACRO_CAL = Macro("URCL_CAL", 1, [
	I86(MACRO, MACRO_DEC, [REG_SP, 1]),
	I86(MOV, AX, "%%retAddr"),
	I86(MACRO, MACRO_STR, [REG_SP, AX]),
	I86(MACRO, MACRO_JMP, [ARGA]),
	I86("%%retAddr:")
])

MACRO_RET = Macro("URCL_RET", 0, [
	I86(MOV, AX, REG_SP),
	I86(MACRO, MACRO_INC, [REG_SP, 1]),
	I86(JMP, AX)
])

MACRO_HLT = Macro("URCL_HLT", 0, [
	I86(HLT),
	I86(JMP, "$")
])

class X86Emit:
	def __init__(self, bits=32, useSections=False, expandMacros=False):
		self.Macros = {}
		self.Instructions = []
		self.Registers = ["REG_SP"]
		self.Labels = {}
		self.NextLabelID = 0
		self.Bits = bits
		self.UseSections = useSections
		self.ExpandMacros = expandMacros
		vars = globals()
		for key in vars:
			if key.startswith("MACRO_") and len(key) > 6:
				self.Macros[key[6:len(key)]] = vars[key]
	
	def FormatLabel(self, label):
		if label.startswith("."):
			label = label[1:len(label)]
		return label.strip().replace(" ", "_").replace(".", "_")

	def MarkLabel(self, label):
		label = self.FormatLabel(str(label))

		if len(self.Instructions) in self.Labels:
			self.Labels[len(self.Instructions)] += [label]
		else:
			self.Labels[len(self.Instructions)] = [label]
	
	def GetDataReferenceType(self, bits):
		if bits == 16:
			return "word"
		elif bits == 32:
			return "dword"
		elif bits == 64:
			return "qword"
		else:
			return "byte"
	
	def GetDataWordType(self, bits):
		if bits == 16:
			return "dw"
		elif bits == 32:
			return "dd"
		elif bits == 64:
			return "dq"
		else:
			return "db"
	
	def IsRegister(self, value):
		if value == None:
			return False
		value = str(value)
		if value.startswith("R") or value == "SP":
			return value != "R0"
	
	def IsLabel(self, value):
		return value != None and str(value).startswith(".")

	def EmitURCLInstruction(self, inst):
		operands = []
		for operand in inst.GetOperands():
			if operand == None:
				break
			operand = str(operand)
			if self.IsRegister(operand):
				operand = "REG_" + operand
				if not operand in self.Registers:
					self.Registers += [operand]
				operand = REF(operand, self.Bits)
			elif self.IsLabel(operand):
				operand = self.FormatLabel(operand)
			operands += [operand]

		if inst.Operation in self.Macros:
			macro = self.Macros[inst.Operation]
			if macro.ArgumentCount == len(operands):
				self.Instructions += [I86(MACRO, macro, operands)]
			else:
				print("ERROR: " + str(inst.Operation) + " does not take " + str(inst.GetOperandCount()) + " operands.")
		else:
			print("ERROR: " + str(inst.Operation) + " is not a valid instruction.")

	def Emit(self, emitter):
		for i in range(len(emitter.Instructions)):
			if i in emitter.Labels:
				for j in range(len(emitter.Labels[i])):
					self.MarkLabel(str(emitter.Labels[i][j]))
			self.EmitURCLInstruction(emitter.Instructions[i])
		if len(emitter.Instructions) in emitter.Labels:
			for i in range(len(emitter.Labels[len(emitter.Instructions)])):
				self.MarkLabel(str(emitter.Labels[len(emitter.Instructions)][i]))
		
		result = "R0 equ 0\n\n"
		if self.UseSections:
			result += "section .text\n"

		if not self.ExpandMacros:
			for macroName in self.Macros:
				result += self.Macros[macroName].Compile(self.Bits) + "\n"

		for i in range(len(self.Instructions)):
			if i in self.Labels:
				for j in range(len(self.Labels[i])):
					result += str(self.Labels[i][j]) + ":\n"
			result += self.Instructions[i].Compile(self.Bits, self.ExpandMacros)
		if len(self.Instructions) in self.Labels:
			for i in range(len(self.Labels[len(self.Instructions)])):
				result += str(self.Labels[len(self.Instructions)][i]) + ":\n"

		if self.UseSections:
			result += "\nsection .data\n"

		for reg in self.Registers:
			result += str(reg).strip("[]") + ":\n" + self.GetDataWordType(self.Bits) + " 0\n"

		result += MEMORYOFFSET + ":"

		return result
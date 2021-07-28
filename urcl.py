SP = "SP"
ZERO = "R0"

NOP = "NOP"
HLT = "HLT"
BRK = "BRK"

ADD = "ADD"
SUB = "SUB"
INC = "INC"
DEC = "DEC"
MLT = "MLT"
DIV = "DIV"
MOD = "MOD"
OR = "OR"
AND = "AND"
XOR = "XOR"
NOT = "NOT"
LSH = "LSH"
RSH = "RSH"
BSL = "BSL"
BSR = "BSR"

MOV = "MOV"
IMM = "IMM"
LOD = "LOD"
STR = "STR"
CPY = "CPY"

PSH = "PSH"
POP = "POP"
CAL = "CAL"
RET = "RET"

JMP = "JMP"
BRZ = "BRZ"
BNZ = "BNZ"
BRE = "BRE"
BNE = "BNE"
BRL = "BRL"
BLE = "BLE"
BRG = "BRG"
BGE = "BGE"

class Class:
	"""Represents a compile-time class."""
	def __init__(self, name="className", parentClass=None, fields=[], sealed=False):
		self.Name = name
		if (parentClass != None) and (parentClass.Sealed):
			raise ValueError("Class '" + parentClass.Name + "' is sealed and can not be inherited.")
		self.ParentClass = parentClass
		self.Fields = fields
		self.Sealed = sealed
		self._ValueType = False
		self._Pending = False
	
	def GetSize(self):
		"""Get the size of this class in memory."""
		if self._Pending:
			raise ValueError("Can not get size of pending type.")
		result = len(self.Fields)
		if self.ParentClass != None:
			result += self.ParentClass.GetSize()
		return result

def GetWordClass():
	"""Get the type that represents a native word."""
	result = Class("WORD", sealed=True)
	result._ValueType = True
	return result

def GetPendingClass():
	"""Get the type that can be replaced by another class later."""
	result = Class("PENDING", sealed=True)
	result._Pending = True
	return result

WORD = GetWordClass()
PENDING = GetPendingClass()

class Field:
	"""Represents a compile-time field."""
	def __init__(self, type=PENDING, name="fieldName"):
		self.Type = type
		self.Name = name
	
	def IsValue(self):
		"""Returns true if the field is a value type."""
		return self.Type._ValueType

	def IsPointer(self):
		"""Returns true if the field is a pointer type."""
		return not self.Type._ValueType

class RegisterMap:
	"""An allocator for registers."""
	def __init__(self):
		self._RegistersStart = 1
		self._NextRegister = self._RegistersStart
		self._FreeRegisters = []

	def New(self):
		"""Allocate a register for use."""
		if len(self._FreeRegisters) > 0:
			return str(self._FreeRegisters.pop())
		else:
			result = self._NextRegister
			self._NextRegister += 1
			return "R" + str(result)

	def Free(self, reg):
		"""Make a register available for use."""
		self._FreeRegisters.append(reg)
	
	def Reset(self):
		"""Free all registers currently in use."""
		self._NextRegister = self._RegistersStart
		self._FreeRegisters = []

class Instruction:
	"""Represents an URCL instruction."""
	def __init__(self, operation="NOP", operandA=None, operandB=None, operandC=None):
		self.Operation = operation
		self.OperandA = operandA
		self.OperandB = operandB
		self.OperandC = operandC
	
	def GetOperandCount(self):
		"""Get the number of operands in this instruction."""
		if self.OperandA == None:
			return 0
		elif self.OperandB == None:
			return 1
		elif self.OperandC == None:
			return 2
		else:
			return 3
	
	def GetOperands(self):
		"""Get a list of the operands in this instruction."""
		if self.OperandA == None:
			return []
		elif self.OperandB == None:
			return [self.OperandA]
		elif self.OperandC == None:
			return [self.OperandA, self.OperandB]
		else:
			return [self.OperandA, self.OperandB, self.OperandC]
	
	def __str__(self):
		"""Convert the instruction to a string."""
		if self.OperandA == None:
			return self.Operation
		elif self.OperandB == None:
			return self.Operation + " " + str(self.OperandA)
		elif self.OperandC == None:
			return self.Operation + " " + str(self.OperandA) + " " + str(self.OperandB)
		else:
			return self.Operation + " " + str(self.OperandA) + " " + str(self.OperandB) + " " + str(self.OperandC)

class URCLEmit:
	"""The default emitter target type. Outputs emitter instructions as plain URCL."""
	def Emit(self, emitter):
		result = ""
		for i in range(len(emitter.Instructions)):
			if i in emitter.Labels:
				for j in range(len(emitter.Labels[i])):
					result += str(emitter.Labels[i][j]) + "\n"
			result += str(emitter.Instructions[i]) + "\n"
		if len(emitter.Instructions) in emitter.Labels:
			for i in range(len(emitter.Labels[len(emitter.Instructions)])):
				result += str(emitter.Labels[len(emitter.Instructions)][i]) + "\n"
		return result

DEFAULT_TARGET = URCLEmit()

def ParseInstruction(text):
	"""Parse an URCL instruction from a string. Returns None is the instruction is a comment or empty line."""
	text = str(text).strip()
	if len(text) <= 0:
		return None
	if text.startswith("//"):
		return None
	if text.startswith(".") and not (' ' in text):
		return text
	text = text.replace(",", " ").replace("//", " //").replace("  ", " ").split(" ")
	comment = False
	for i in range(4):
		if i >= len(text):
			text.append(None)
		elif text[i].startswith("//") or comment:
			text[i] = None
			comment = True
	return Instruction(text[0].upper(), text[1], text[2], text[3])

class Emitter:
	"""An emitter for URCL instructions."""
	def __init__(self, emitTarget=DEFAULT_TARGET, useR1AsBasePointer=False, memoryManagerMinAddress=0, memoryManagerMaxAddress=18446744073709551615, inlineMemoryManagement=True):
		self.Instructions = []
		self.Labels = {}
		self._Registers = RegisterMap()
		self._EmitterTarget = emitTarget

		if useR1AsBasePointer:
			self.BP = self._Registers.New()
		else:
			self.BP = None

		self._NextAnonLabel = 0

		if memoryManagerMaxAddress < memoryManagerMinAddress:
			swap = memoryManagerMinAddress
			memoryManagerMinAddress = memoryManagerMaxAddress
			memoryManagerMaxAddress = swap
			
		self._MemoryManagerMinAddress = memoryManagerMinAddress
		self._MemoryManagerMaxAddress = memoryManagerMaxAddress
		self._InlineMemoryManagement = inlineMemoryManagement
		self._MemoryManagerAllocate = None
		self._MemoryManagerFree = None
		self._MemoryManagerRegister = None
		self._PushRegistersOnMemManage = False

		if not inlineMemoryManagement:
			self._InlineMemoryManagement = True
			self._PushRegistersOnMemManage = True

			entryPoint = self.NewLabel()
			self._MemoryManagerAllocate = self.NewLabel()
			self._MemoryManagerFree = self.NewLabel()
			self._MemoryManagerRegister = self.NewRegister()

			self.Emit(STR, self._MemoryManagerMinAddress, ZERO)
			self.Emit(JMP, entryPoint)

			self.MarkLabel(self._MemoryManagerAllocate)
			self.NewPointer(self._MemoryManagerRegister, self._MemoryManagerRegister)
			self.Emit(RET)

			self.MarkLabel(self._MemoryManagerFree)
			self.FreePointer(self._MemoryManagerRegister)
			self.Emit(RET)

			self.MarkLabel(entryPoint)

			self._InlineMemoryManagement = False

	def GetBasePointer(self):
		"""Get or allocate a register designated as the stack base pointer."""
		if self.BP == None:
			self.BP = self.NewRegister()
		return self.BP

	def NewLabel(self, name=""):
		"""Create a new label with an optional custom name."""
		if len(name) == 0:
			name = "_anonlabel_" + str(self._NextAnonLabel)
			self._NextAnonLabel += 1
		return "." + name
	
	def MarkLabel(self, label):
		"""Mark a label at the current emit location."""
		if len(self.Instructions) in self.Labels:
			self.Labels[len(self.Instructions)] += [label]
		else:
			self.Labels[len(self.Instructions)] = [label]
	
	def IsRegister(self, value):
		"""Determine if a value is an URCL register."""
		value = str(value)
		if (len(value) > 0 and value[0] == "R") or value == "SP":
			return True
		else:
			return False
	
	def IsLabel(self, value):
		"""Determine if a value is an URCL label."""
		value = str(value)
		return len(value) > 0 and value[0] == "." and not " " in value

	def NewRegister(self):
		"""Allocate a register for use."""
		return self._Registers.New()
	
	def FreeRegister(self, reg):
		"""Make a register available for use."""
		self._Registers.Free(reg)
	
	def NewPointer(self, inSize=ZERO, outPointer=ZERO):
		"""Allocate a block of memory. It is advisable to use inlineMemoryManagement=False in the emitter options if calling this more than once."""
		if self._InlineMemoryManagement:
			searchLoop = self.NewLabel()
			createNew = self.NewLabel()
			outOfMemory = self.NewLabel()
			finish = self.NewLabel()
			currentBlock = self.NewRegister()
			length = self.NewRegister()
			value = self.NewRegister()

			if self._PushRegistersOnMemManage:
				self.Emit(PSH, currentBlock)
				self.Emit(PSH, length)
				self.Emit(PSH, value)

			self.Emit(IMM, currentBlock, self._MemoryManagerMinAddress)
			self.Emit(MOV, length, ZERO)

			self.MarkLabel(searchLoop)
			#Offset the current block to the next block based on the previous block's length.
			self.Emit(ADD, currentBlock, currentBlock, length)
			#Fetch the length from the current block.
			self.Emit(LOD, length, currentBlock)
			#If the length isn't zero, check the block, otherwise create a new one. (Zero is end of blocks)
			self.Emit(BRZ, createNew, length)
			#Extract the in-use bit from the length.
			self.Emit(AND, value, length, 1)
			#Shift the in-use bit out of the length.
			self.Emit(RSH, length, length)
			#If the in-use bit is set, go to the next block.
			self.Emit(BNZ, searchLoop, value)
			#If the block is too small, go to the next block.
			self.Emit(BRL, searchLoop, length, inSize)
			#Add the in-use bit to the length.
			self.Emit(LSH, length, length)
			self.Emit(OR, length, length, 1)
			#Update the length field in memory.
			self.Emit(STR, currentBlock, length)
			#Point to the data in the block.
			self.Emit(ADD, outPointer, currentBlock, 1)
			self.Emit(JMP, finish)

			self.MarkLabel(outOfMemory)
			self.Emit(MOV, outPointer, ZERO)
			self.Emit(JMP, finish)

			self.MarkLabel(createNew)
			#Get the size of the block including the length field.
			self.Emit(ADD, length, inSize, 1)
			#Push it to the stack so it can be used again.
			self.Emit(PSH, length)
			#Get the address the block has to be below without running out of memory.
			self.Emit(SUB, value, self._MemoryManagerMaxAddress, length)
			#If there isn't enough space, return a null pointer.
			self.Emit(BRL, outOfMemory, value, currentBlock)
			#Add the in-use bit to the length.
			self.Emit(LSH, length, length)
			self.Emit(OR, length, length, 1)
			#Set the new length field in memory.
			self.Emit(STR, currentBlock, length)
			#Point to the data in the block.
			self.Emit(ADD, outPointer, currentBlock, 1)
			#Get the size of the block again.
			self.Emit(POP, length)
			#Get the next block. (Not initialized, so we need to initialize it.)
			self.Emit(ADD, currentBlock, currentBlock, length)
			#Set the next block's length field to zero.
			self.Emit(STR, currentBlock, ZERO)

			self.MarkLabel(finish)
			if self._PushRegistersOnMemManage:
				self.Emit(POP, value)
				self.Emit(POP, length)
				self.Emit(POP, currentBlock)
			
			self.FreeRegister(currentBlock)
			self.FreeRegister(length)
			self.FreeRegister(value)
		else:
			if self.IsRegister(inSize):
				self.Emit(MOV, self._MemoryManagerRegister, inSize)
			else:
				self.Emit(IMM, self._MemoryManagerRegister, inSize)
			self.Emit(CAL, self._MemoryManagerAllocate)
			self.Emit(MOV, outPointer, self._MemoryManagerRegister)

	def FreePointer(self, inPointer=ZERO):
		"""Free a block of memory. It is advisable to use inlineMemoryManagement=False in the emitter options if calling this more than once."""
		if self._InlineMemoryManagement:
			finish = self.NewLabel()
			currentBlock = self.NewRegister()
			length = self.NewRegister()

			if self._PushRegistersOnMemManage:
				self.Emit(PSH, currentBlock)
				self.Emit(PSH, length)

			#If pointer is null, ignore.
			self.Emit(BRZ, finish, inPointer)
			#Get the block location from the data pointer.
			self.Emit(SUB, currentBlock, inPointer, 1)
			#Get the length field of the block.
			self.Emit(LOD, length, currentBlock)
			#Zero out the in-use bit.
			self.Emit(AND, length, length, -2)
			#Update the length field in memory.
			self.Emit(STR, currentBlock, length)
			self.MarkLabel(finish)

			if self._PushRegistersOnMemManage:
				self.Emit(POP, length)
				self.Emit(POP, currentBlock)

			self.FreeRegister(currentBlock)
			self.FreeRegister(length)
		else:
			if self.IsRegister(inPointer):
				self.Emit(MOV, self._MemoryManagerRegister, inPointer)
			else:
				self.Emit(IMM, self._MemoryManagerRegister, inPointer)
			self.Emit(CAL, self._MemoryManagerFree)
	
	def NewObject(self, type=PENDING, outPointer=ZERO):
		"""Allocate a block of memory for the specified type."""
		self.NewPointer(type.GetSize(), outPointer)

	def Emit(self, operation="NOP", operandA=None, operandB=None, operandC=None):
		"""Emit an URCL instruction with the specified operation and operands."""
		self.Instructions.append(Instruction(operation, operandA, operandB, operandC))
	
	def _CallFunctionDefaultArguments(self, arg):
		return 0

	def CallFunction(self, label, emitArgsFunc=_CallFunctionDefaultArguments, emitArgsFuncArg=None, outCount=0):
		"""Emit a function call that passes the arguments pushed onto the stack by the specified emitArgsFunc(emitter, emitArgsFuncArg), which returns the number of arguments that was pushed."""
		self.Emit(SUB, SP, SP, outCount)
		inCount = emitArgsFunc(self, emitArgsFuncArg)
		self.Emit(CAL, label)
		self.Emit(ADD, SP, SP, inCount)
	
	def _EmitFunctionDefaultBody(self, arg, returnLabel):
		return
	
	def EmitFunction(self, label, localCount=0, emitBodyFunc=_EmitFunctionDefaultBody, emitBodyFuncArg=None):
		"""Emit a function that executes the code emitted by emitBodyFunc(emitter, emitBodyFuncArg, returnLabel)."""
		self.MarkLabel(label)
		self.Emit(PSH, self.GetBasePointer())
		self.Emit(MOV, self.GetBasePointer(), SP)
		self.Emit(SUB, SP, SP, localCount)
		returnLabel = self.NewLabel()
		emitBodyFunc(self, emitBodyFuncArg, returnLabel)
		self.MarkLabel(returnLabel)
		self.Emit(MOV, SP, self.GetBasePointer())
		self.Emit(POP, self.GetBasePointer())
		self.Emit(RET)
	
	def EmitGetArgument(self, argumentCount=0, argumentIndex=0, outValue=ZERO):
		"""Get the value of the function argument with the specified total arguments and argument index."""
		self.Emit(ADD, outValue, self.GetBasePointer(), (argumentCount - argumentIndex) + 1)
		self.Emit(LOD, outValue, outValue)
	
	def EmitGetLocal(self, localIndex=0, outValue=ZERO):
		"""Get the value of the function local with the specified local index."""
		self.Emit(SUB, outValue, self.GetBasePointer(), localIndex)
		self.Emit(LOD, outValue, outValue)
	
	def EmitSetLocal(self, localIndex=0, inValue=ZERO):
		"""Set the value of the function local with the specified local index and value."""
		localPointer = self.NewRegister()
		self.Emit(SUB, localPointer, self.GetBasePointer(), localIndex)
		self.Emit(STR, localPointer, inValue)
		self.FreeRegister(localPointer)
	
	def EmitGetObjectField(self, inPointer=ZERO, fieldIndex=0, outValue=ZERO):
		"""Get the value of the object field with the specified pointer and field index."""
		fieldPointer = self.NewRegister()
		self.Emit(ADD, fieldPointer, inPointer, fieldIndex)
		self.Emit(LOD, outValue, fieldPointer)
		self.FreePointer(fieldPointer)
	
	def EmitSetObjectField(self, inPointer=ZERO, fieldIndex=0, inValue=ZERO):
		"""Set the value of the object field with the specified pointer and field index."""
		fieldPointer = self.NewRegister()
		self.Emit(ADD, fieldPointer, inPointer, fieldIndex)
		self.Emit(STR, fieldPointer, inValue)
		self.FreeRegister(fieldPointer)

	def Compile(self):
		"""Compile the emitter instructions with the emitter target."""
		return str(self)

	def __str__(self):
		"""Compile the emitter instructions with the emitter target."""
		return self._EmitterTarget.Emit(self)
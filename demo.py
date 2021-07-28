from urcl import *

#Create linked list class.
linkedListClass = Class("LinkedList", None, [Field(PENDING, "Next"), Field(WORD, "Value")])
linkedListClass.Fields[0].Type = linkedListClass

#Configure emitter.
ext = "py"
from urclpy import PythonEmit
emitter = Emitter(emitTarget=PythonEmit(useDebugger=True), memoryManagerMaxAddress=65535, inlineMemoryManagement=False)

#Allocate registers for variables.
nodeA = emitter.NewRegister()
nodeB = emitter.NewRegister()
nodeC = emitter.NewRegister()

#Allocate objects in memory.
emitter.NewObject(linkedListClass, nodeA)
emitter.NewObject(linkedListClass, nodeB)
emitter.NewObject(linkedListClass, nodeC)

#Set object fields.
emitter.EmitSetObjectField(nodeA, 0, nodeB)
emitter.EmitSetObjectField(nodeA, 1, 1)
emitter.EmitSetObjectField(nodeB, 0, nodeC)
emitter.EmitSetObjectField(nodeB, 1, 2)
emitter.EmitSetObjectField(nodeC, 0, ZERO)
emitter.EmitSetObjectField(nodeC, 1, 3)

emitter.Emit(HLT)

outputFile = "./build/output." + ext
#Compile and save.
import os
os.makedirs(os.path.dirname(outputFile), exist_ok=True)
with open(outputFile, "w") as file:
    file.write(str(emitter))
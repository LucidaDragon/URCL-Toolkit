import collections
from sys import argv
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter import filedialog as fd
from urcl import Emitter, ParseInstruction
from urclpy import PythonEmit

root = tk.Tk()
root.title("URCL Debugger")

class MenuItem:
	def __init__(self, text, action=None, children=[]):
		self.Text = text
		self.Action = action
		self.Children = children

def CreateMenu(root, menuItems=[]):
	menuroot = tk.Menu(root, tearoff="off")
	for item in menuItems:
		text = item.Text
		action = item.Action
		if action == None:
			child = CreateMenu(menuroot, item.Children)
			menuroot.add_cascade(label=text, menu=child)
		else:
			menuroot.add_command(label=text, command=action)
		
	return menuroot

def CreateScrollableFrame(root, row, column):
	container = ttk.Frame(root)
	canvas = tk.Canvas(container)
	scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
	scrollable = ttk.Frame(canvas)

	scrollable.bind(
		"<Configure>",
		lambda e: canvas.configure(
			scrollregion=canvas.bbox("all")
		)
	)

	canvas.create_window((0, 0), window=scrollable, anchor="nw")

	canvas.configure(yscrollcommand=scrollbar.set)

	container.grid(row=row, column=column, sticky="nsew")
	canvas.pack(side="left", fill="both", expand=True)
	scrollbar.pack(side="right", fill="y")
	scrollable.ScrollBar = scrollbar
	return scrollable

def ScrollTo(scrollarea, position):
	scrollbar = scrollarea.ScrollBar
	start, end = scrollbar.get()
	if position < start or position > end:
		scrollbar.set(position, position + (end - start))
		root.nametowidget(scrollarea.winfo_parent()).yview_moveto(position)

def ImportFile(file):
	file = str(file)
	if file.lower().endswith(".py"):
		with open(file) as stream:
			exec(stream.read(), globals())
	elif file.lower().endswith(".urcl"):
		emitter = Emitter(emitTarget=PythonEmit(useDebugger=True))
		with open(file) as stream:
			lines = stream.readlines()
			for line in lines:
				inst = ParseInstruction(line)
				if inst != None:
					if emitter.IsLabel(inst):
						emitter.MarkLabel(inst)
					else:
						emitter.Emit(inst.Operation, inst.OperandA, inst.OperandB, inst.OperandC)
		exec(str(emitter), globals())
	else:
		messagebox.showerror(title="Import Error", message="File format is not supported.")
	UpdateUI()

def OnOpen():
	file = fd.askopenfilename()
	if len(file) > 0:
		ImportFile(file)

def OnExit():
	exit(0)

IP = 0
SP = 0
STACK = []
ROM = {}
RAM = {}
STEP = True
HALT = False
BREAK = False

_IsTimerExecuting = False
_ShouldTimerStop = False

def Execute():
	messagebox.showwarning(title="Engine Exception", message="Engine Exception: name 'Execute' is not defined.")

def OnStep():
	global STEP
	STEP = True
	Execute()
	UpdateUI()

def OnRun():
	global _ShouldTimerStop
	if not _IsTimerExecuting:
		_ShouldTimerStop = False
		OnClock()

def OnInterrupt():
	global _ShouldTimerStop
	if _IsTimerExecuting:
		_ShouldTimerStop = True

def OnClock():
	global _ShouldTimerStop
	global _IsTimerExecuting
	if _ShouldTimerStop:
		_ShouldTimerStop = False
		_IsTimerExecuting = False
		return
	else:
		_IsTimerExecuting = True
	OnStep()
	if BREAK or HALT:
		_IsTimerExecuting = False
	else:
		root.after(100, OnClock)

MenuBar = CreateMenu(root, [
	MenuItem("File", None, [
		MenuItem("Open", OnOpen),
		MenuItem("Exit", OnExit)
	]),
	MenuItem("Step", OnStep),
	MenuItem("Run", OnRun),
	MenuItem("Interrupt", OnInterrupt)
])
root.config(menu=MenuBar)
root.rowconfigure(0, weight=1)
root.rowconfigure(1, weight=1)
root.columnconfigure(0, weight=1)
root.columnconfigure(1, weight=1)

RegistersArea = CreateScrollableFrame(root, 0, 0)
ROMArea = CreateScrollableFrame(root, 0, 1)
StackArea = CreateScrollableFrame(root, 1, 0)
RAMArea = CreateScrollableFrame(root, 1, 1)

RegisterValues = {}
RAMValues = {}

def Clear(root):
	for child in root.winfo_children():
		child.destroy()

def UpdateRegisters():
	Clear(RegistersArea)
	fields = globals()
	fieldNames = list(fields.keys())
	fieldNames.sort(key=len)
	row = 0
	for key in fieldNames:
		if not key.startswith("_"):
			value = fields[key]
			if isinstance(value, int) or isinstance(value, bool):
				color = "IndianRed1"
				if key in RegisterValues and RegisterValues[key] == value:
					color = "gray94"
				else:
					RegisterValues[key] = value
				ttk.Label(RegistersArea, text=(key + " = " + str(value)), background=color).grid(row=row, sticky="nsew")
				row += 1

def UpdateInstructions():
	Clear(ROMArea)
	row = 0
	for addr in ROM:
		color = "gray94"
		if addr == IP:
			color = "light goldenrod"
		label = ttk.Label(ROMArea, text=ROM[addr].Source, background=color)
		if addr == IP:
			position = row / len(ROM)
			ScrollTo(ROMArea, position)
		label.grid(row=row, sticky="nsew")
		row += 1

def UpdateStack():
	Clear(StackArea)
	addr = 0
	for value in STACK:
		color = "gray94"
		if (-SP - 1) == addr:
			color = "light sky blue"
		ttk.Label(StackArea, text=str(value), background=color).grid(row=addr, sticky="nsew")
		addr += 1

def UpdateRAM():
	Clear(RAMArea)
	row = 0
	last = -1
	ram = collections.OrderedDict(sorted(RAM.items()))
	for addr in ram:
		value = RAM[addr]
		color = "PaleGreen1"
		if addr in RAMValues and RAMValues[addr] == value:
			color = "gray94"
		else:
			RAMValues[addr] = value
		if addr != last + 1:
			ttk.Label(RAMArea, text="...").grid(row=row, columnspan=2, sticky="nsew")
			row += 1
		last = addr
		ttk.Label(RAMArea, text=str(addr), background=color).grid(row=row, column=0, sticky="nsew")
		ttk.Label(RAMArea, text=str(value), background=color).grid(row=row, column=1, sticky="nsew")
		row += 1

def UpdateUI():
	UpdateRegisters()
	UpdateInstructions()
	UpdateStack()
	UpdateRAM()

for file in argv[1:len(argv)]:
	ImportFile(file)

root.mainloop()
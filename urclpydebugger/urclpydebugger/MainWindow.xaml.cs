using IronPython.Hosting;
using Microsoft.Scripting.Hosting;
using Microsoft.Win32;
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Timers;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;

namespace urclpydebugger
{
	public partial class MainWindow : Window
	{
		private readonly List<string> LoadedFiles = new List<string>();
		private readonly ScriptEngine Engine = Python.CreateEngine();
		private readonly Timer Stepper = new Timer { AutoReset = true, Interval = 100 };
		private bool Stepping = false;
		private ScriptScope GlobalScope;
		private readonly Dictionary<dynamic, dynamic> MemoryValues = new Dictionary<dynamic, dynamic>();
		private readonly OpenFileDialog OpenDialog = new OpenFileDialog
		{
			Title = "Open Python Module",
			Filter = "Python Files (*.py)|*.py|All Files (*.*)|*.*"
		};

		public MainWindow()
		{
			InitializeComponent();
			GlobalScope = Engine.CreateScope();
			Stepper.Elapsed += (s, e) => Step();

			var args = Environment.GetCommandLineArgs();
			for (var i = 1; i < args.Length; i++)
			{
				if (!LoadScriptFile(args[i])) Environment.Exit(1);
			}

			UpdateUI();
		}

		public void Step()
		{
			if (!Stepping)
			{
				Stepping = true;

				Dispatcher.Invoke(() =>
				{
					GlobalScope.SetVariable("STEP", true);

					try
					{
						Engine.Execute("Execute()", GlobalScope);

						if (GlobalScope.TryGetVariable("HALT", out dynamic haltedValue))
						{
							if (GlobalScope.TryGetVariable("BREAK", out dynamic breakValue))
							{
								Stepper.Enabled = Stepper.Enabled && breakValue is bool brk && !brk;
							}

							Stepper.Enabled = Stepper.Enabled && haltedValue is bool halted && !halted;
						}
						else
						{
							Stepper.Enabled = false;
						}
					}
					catch (Exception ex)
					{
						Stepper.Enabled = false;
						MessageBox.Show($"Engine Exception: {ex.Message}", "Engine Exception", MessageBoxButton.OK);
					}

					UpdateUI();
				});

				Stepping = false;
			}
		}

		public bool LoadScriptFile(string path)
		{
			try
			{
				Engine.ExecuteFile(path, GlobalScope);
				LoadedFiles.Add(path);
				UpdateUI();
			}
			catch (Exception ex)
			{
				if (MessageBox.Show($"Could not load script \"{path}\": {ex.Message}", "Import Error", MessageBoxButton.OKCancel, MessageBoxImage.Warning) == MessageBoxResult.Cancel)
				{
					return false;
				}
			}

			return true;
		}

		public void Reload()
		{
			Unload(-1);
		}

		public void Unload(int fileIndex)
		{
			if (fileIndex >= 0)
			{
				LoadedFiles.RemoveAt(fileIndex);
			}

			GlobalScope = Engine.CreateScope();
			var loaded = LoadedFiles.ToArray();
			LoadedFiles.Clear();
			RegisterList.Children.Clear();
			MemoryValues.Clear();

			for (var i = 0; i < loaded.Length; i++)
			{
				if (!LoadScriptFile(loaded[i]))
				{
					GlobalScope = Engine.CreateScope();
					MemoryValues.Clear();
					LoadedFiles.Clear();
					break;
				}
			}

			UpdateUI();
		}

		public void UpdateUI()
		{
			UpdateRegisters();
			UpdateInstructions();
			UpdateStackValues();
			UpdateMemory();
			UpdateUnloadMenu();
		}

		public void UpdateRegisters()
		{
			var keys = new List<string>();
			for (var i = 0; i < RegisterList.Children.Count; i++)
			{
				keys.Add(GetRegisterKey(i));
			}

			var vars = GlobalScope.GetVariableNames().ToArray();
			Array.Sort(vars, (a, b) => a.Length.CompareTo(b.Length) == 0 ? a.CompareTo(b) : a.Length.CompareTo(b.Length));
			foreach (var key in vars)
			{
				var value = GlobalScope.GetVariable(key);
				var valueText = value == null ? "<null>" : ((object)value).ToString();

				if (int.TryParse(valueText, out _) || bool.TryParse(valueText, out _))
				{
					var index = keys.IndexOf(key);
					if (index < 0)
					{
						AddRegister(key, valueText);
					}
					else
					{
						SetRegisterValue(index, valueText);
					}
				}
			}
		}

		public void UpdateInstructions()
		{
			InstructionList.Children.Clear();

			try
			{
				if (GlobalScope.TryGetVariable("ROM", out _) && GlobalScope.TryGetVariable("IP", out dynamic value) && value is int ip)
				{
					var length = Engine.Execute("len(ROM)", GlobalScope);
					TextBlock target = null;

					for (var i = 0; i < length; i++)
					{
						var inst = (string)Engine.Execute($"str(ROM[{i}].Source)", GlobalScope);
						var block = new TextBlock { Text = inst, Background = i == ip ? Brushes.LightYellow : Brushes.Transparent };
						if (i == ip) target = block;
						InstructionList.Children.Add(block);
					}

					if (target != null) target.BringIntoView();
				}
			}
			catch { }
		}

		public void UpdateUnloadMenu()
		{
			UnloadMenu.Items.Clear();
			UnloadMenu.IsEnabled = LoadedFiles.Count > 0;
			foreach (var file in LoadedFiles)
			{
				var item = new MenuItem
				{
					Header = Path.GetFileName(file),
					Tag = file
				};

				item.Click += (s, e) =>
				{
					var m = (MenuItem)s;
					if (MessageBox.Show($"Are you sure you want to unload \"{m.Tag}\"?", "Confirm Unload", MessageBoxButton.YesNo, MessageBoxImage.Question) == MessageBoxResult.Yes)
					{
						Unload(LoadedFiles.IndexOf(m.Tag as string));
					}
				};

				UnloadMenu.Items.Add(item);
			}
		}

		public void UpdateStackValues()
		{
			StackList.Children.Clear();

			try
			{
				if (GlobalScope.TryGetVariable("STACK", out _) && GlobalScope.TryGetVariable("SP", out dynamic v) && v is int sp)
				{
					var length = Engine.Execute("len(STACK)", GlobalScope);
					TextBlock target = null;

					for (var i = 0; i < length; i++)
					{
						var value = (string)Engine.Execute($"str(STACK[{i}])", GlobalScope);
						var block = new TextBlock { Text = value, Background = i == (-sp - 1) ? Brushes.LightBlue : Brushes.Transparent };
						if (i == (-sp - 1)) target = block;
						StackList.Children.Add(block);
					}

					if (target != null) target.BringIntoView();
				}
			}
			catch { }
		}

		public void UpdateMemory()
		{
			MemoryList.Children.Clear();

			try
			{
				if (GlobalScope.TryGetVariable("RAM", out dynamic ram))
				{
					Grid target = null;

					var sorted = new List<dynamic>();
					foreach (var value in ram) sorted.Add(value);
					sorted.Sort();

					dynamic lastIndex = -1;
					foreach (var value in sorted)
					{
						if (value - 1 != lastIndex)
						{
							MemoryList.Children.Add(new TextBlock { Text = "..." });
						}

						lastIndex = value;
						var newValue = ram[value];
						var updated = !MemoryValues.TryGetValue(value, out dynamic oldValue) || oldValue != newValue;

						MemoryValues[value] = newValue;

						var group = new Grid { Background = updated ? Brushes.LightGreen : Brushes.Transparent };
						group.ColumnDefinitions.Add(new ColumnDefinition());
						group.ColumnDefinitions.Add(new ColumnDefinition());
						var addressBlock = new TextBlock { Text = value == null ? "<null>" : value.ToString() };
						var valueBlock = new TextBlock { Text = ram[value] == null ? "<null>" : ram[value].ToString() };
						Grid.SetColumn(valueBlock, 1);
						group.Children.Add(addressBlock);
						group.Children.Add(valueBlock);
						MemoryList.Children.Add(group);

						if (updated) target = group;
					}

					if (target != null) target.BringIntoView();
				}
			}
			catch { }
		}

		private string GetRegisterKey(int index)
		{
			return ((TextBlock)((StackPanel)RegisterList.Children[index]).Children[0]).Text;
		}

		private string GetRegisterValue(int index)
		{
			return ((TextBlock)((StackPanel)RegisterList.Children[index]).Children[2]).Text;
		}

		private void SetRegisterValue(int index, string value)
		{
			var group = (StackPanel)RegisterList.Children[index];
			var block = (TextBlock)group.Children[2];
			var previous = GetRegisterValue(index);
			group.Background = previous != value ? Brushes.LightSalmon : Brushes.Transparent;
			block.Text = value;
		}

		private void AddRegister(string key, string value)
		{
			var item = new StackPanel { Orientation = Orientation.Horizontal };
			item.Children.Add(new TextBlock { Text = key, Foreground = Foreground });
			item.Children.Add(new TextBlock { Text = " = ", Foreground = Foreground });
			item.Children.Add(new TextBlock { Text = value, Foreground = Foreground });
			RegisterList.Children.Add(item);
		}

		private void MenuItem_Click(object sender, RoutedEventArgs e)
		{
			Environment.Exit(0);
		}

		private void MenuItem_Click_1(object sender, RoutedEventArgs e)
		{
			if ((bool)OpenDialog.ShowDialog())
			{
				LoadScriptFile(OpenDialog.FileName);
			}
		}

		private void MenuItem_Click_2(object sender, RoutedEventArgs e)
		{
			Step();
		}

		private void MenuItem_Click_3(object sender, RoutedEventArgs e)
		{
			Stepper.Start();
		}

		private void MenuItem_Click_4(object sender, RoutedEventArgs e)
		{
			Reload();
		}
	}
}

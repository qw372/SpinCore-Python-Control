import tkinter as tk
import tkinter.ttk as ttk
from tkinter import filedialog, messagebox
import time
import configparser
import os
import logging
import numpy as np
import nidaqmx
import nidaqmx.constants as const
from spinapi import *

channel_num = 24 # number of TTL output channels of SpinCore PulseBlasterUSB
wincolor = 'Gray95' # main window background color
bgcolorlist = ['lavender', 'honeydew'] # TTL output channel background color
duration_unit = ["ms", "us", "ns"]
opcodes = ["CONTINUE", "STOP", "LOOP", "END_LOOP", "JSR", "RTS", "BRANCH", "LONG_DELAY", "WAIT"]


# the first column of this GUI, which are mainly descriptive labels
class Descr(tk.LabelFrame):
    def __init__(self, master=None):
        super().__init__(master)
        self.configure(relief='flat', borderwidth=0, highlightthickness=0)
        self.place_duration() # argument "self" is automatically passed to these functions
        self.place_note()
        self.place_channels()
        self.place_opcode()
        self.place_opdata()
        self.place_instrnum()

    def place_duration(self):
        self.du = tk.Label(self, text='Duration:', bg=wincolor)
        self.du.grid(row=0, column=1, padx=0, ipady=1)

    def place_note(self):
        self.un = tk.Label(self, text='Note:', bg=wincolor)
        self.un.grid(row=1, column=1, padx=0, ipady=1)

    def place_channels(self):
        self.ch_label_list = []
        for i in range(channel_num):
            bgcolor = bgcolorlist[i%2]
            ch_label = tk.Entry(self, width=12)
            ch_label.grid(row=2+i, column=0, padx=8, sticky='e')
            self.ch_label_list.append(ch_label)
            self.ch = tk.Label(self, text='Channel '+str(i), bg=bgcolor, anchor="center")
            self.ch.grid(row=2+i, column=1, ipady=2, sticky='news')

    def place_opcode(self):
        self.opc = tk.Label(self, text='Op code:', bg=wincolor)
        self.opc.grid(row=channel_num+2, column=1)

    def place_opdata(self):
        self.opd = tk.Label(self, text='Op data:', bg=wincolor)
        self.opd.grid(row=channel_num+3, column=1)

    def place_instrnum(self):
        self.ins = tk.Label(self, text='Instruction #:', bg=wincolor)
        self.ins.grid(row=channel_num+4, column=1)

    def compile_ch_label_text(self):
        self.ch_label_text = []
        for i in reversed(range(channel_num)):
            self.ch_label_text.append(self.ch_label_list[i].get())


# the 2rd to nth column of this gui, which are instruction data that will be pased to PulseBlasterUSB
class Instr(tk.LabelFrame):
    def __init__(self, master, instr_num):
        super().__init__(master)
        self.configure(relief='flat', borderwidth=0, highlightthickness=0)
        self.instr_num = instr_num
        self.place_duration()
        self.place_note()
        self.place_checkboxes()
        self.place_opcode()
        self.place_opdata()
        self.place_instrnum()

    def place_duration(self):
        label_frame = tk.LabelFrame(self, width=9, relief='flat')
        label_frame.grid(row=0, column=0, padx=0)
        self.du = tk.Entry(label_frame, width=6)
        self.du.insert(0, "10")
        self.du.grid(row=0, column=0, padx=0)
        self.un = ttk.Combobox(label_frame, values=duration_unit, width=3, state="readonly")
        self.un.grid(row=0, column=1, padx=0)
        self.un.current(0)

    def place_note(self):
        self.note = tk.Entry(self, width=12)
        self.note.grid(row=1, column=0)

    def place_checkboxes(self):
        self.cbvarlist = []
        self.cblist = []
        for i in range(channel_num):
            bgcolor = bgcolorlist[i%2]
            self.cbvarlist.append(tk.IntVar())
            self.cblist.append(tk.Checkbutton(self, bg=bgcolor, anchor="center", variable=self.cbvarlist[i]))
            self.cblist[i].grid(row=i+2, column=0, padx=0, pady=0, sticky='news')

    def place_opcode(self):
        self.opc = ttk.Combobox(self, values=opcodes, width=10, state="readonly")
        self.opc.grid(row=channel_num+2, column=0, padx=8, sticky="news")
        self.opc.current(0)

    def place_opdata(self):
        self.opd = tk.Entry(self, width=2)
        self.opd.grid(row=channel_num+3, column=0)
        self.opd.insert(0, "0")

    def place_instrnum(self):
        self.ins = tk.Label(self, text=str(self.instr_num), bg=wincolor)
        self.ins.grid(row=channel_num+4, column=0)

    def compile_instr(self):
        # collect user defined values and compile tham as a list, it will later be passed to PulseBlaterUSB
        self.values = [0, 0, 0, 0, 0] # instr note, channel output, opcode, opdata and duration with unit for each channel
        self.values[0] = self.note.get()
        self.values[1] = 0
        for i in range(channel_num):
            self.values[1] += self.cbvarlist[i].get() * (2**i)
        self.values[2] = self.opc.current()
        self.values[3] = int(self.opd.get())
        self.values[4] = float(self.du.get()) * (1000**(2-self.un.current()))


class Scanner(tk.LabelFrame):
    def __init__(self, MainWindow):
        super().__init__(MainWindow.frame)
        self.configure(relief='groove', text='Linear Scanner', font='Helvetica 10 bold')
        self.main = MainWindow
        self.scan_elem_num = 3
        self.scan_elem_list = []

        self.place_add_del()
        self.place_scan_button()
        self.place_sample_num()
        self.place_repetition()
        self.place_DAQ_ch()
        self.place_scan_elem()


    class scan_elem(tk.LabelFrame):
        def __init__(self, master):
            super().__init__(master)
            self.configure(relief='groove')

            local_label_frame = tk.LabelFrame(self, relief='flat')
            local_label_frame.grid(row=0, column=0, columnspan=2)
            instr_label = tk.Label(local_label_frame, text=r'Instruction #:')
            instr_label.grid(row=0, column=0)
            self.instr_entry = tk.Entry(local_label_frame, width=5)
            self.instr_entry.insert(0, '0')
            self.instr_entry.grid(row=0, column=1)

            start_label = tk.Label(self, text='Start:')
            start_label.grid(row=1, column=0)
            start_label_frame = tk.LabelFrame(self, width=9, relief='flat')
            start_label_frame.grid(row=1, column=1, padx=0, sticky='w')
            self.start_du = tk.Entry(start_label_frame, width=6)
            self.start_du.insert(0, "1")
            self.start_du.grid(row=0, column=0, padx=0)
            self.start_un = ttk.Combobox(start_label_frame, values=duration_unit, width=3, state="readonly")
            self.start_un.grid(row=0, column=1, padx=0)
            self.start_un.current(0)

            end_label = tk.Label(self, text='End:')
            end_label.grid(row=2, column=0)
            end_label_frame = tk.LabelFrame(self, width=9, relief='flat')
            end_label_frame.grid(row=2, column=1, padx=0, sticky='w')
            self.end_du = tk.Entry(end_label_frame, width=6)
            self.end_du.insert(0, "10")
            self.end_du.grid(row=0, column=0, padx=0)
            self.end_un = ttk.Combobox(end_label_frame, values=duration_unit, width=3, state="readonly")
            self.end_un.grid(row=0, column=1, padx=0)
            self.end_un.current(0)

        def compile(self):
            self.start = float(self.start_du.get()) * (1000**(2-self.start_un.current()))
            self.end = float(self.end_du.get()) * (1000**(2-self.end_un.current()))
            self.instr = int(self.instr_entry.get())

    def place_add_del(self):
        add_del_label = tk.Label(self, text='Add/Delete a scan slot:')
        add_del_label.grid(row=0, column=0, pady=0)
        self.del_button = tk.Button(self, text="-", width=6, bg="white", command=self.del_scan_slot)
        self.del_button.grid(row=0, column=1, sticky='e')
        add_button = tk.Button(self, text="+", width=6, bg="white", command=self.add_scan_slot)
        add_button.grid(row=0, column=2, sticky='e')

    def place_sample_num(self):
        sample_label = tk.Label(self, text='Sample number:')
        sample_label.grid(row=1, column=0, pady=3, sticky='e')
        self.sample_num = tk.Entry(self, width=8)
        self.sample_num.insert(0, "10")
        self.sample_num.grid(row=1, column=1, padx=0, sticky='w')

    def place_repetition(self):
        rep_label = tk.Label(self, text='Repetition:', bg=wincolor, anchor='e', width=12)
        rep_label.grid(row=1, column=2, padx=0, sticky='e')
        self.repetition = tk.Entry(self, width=8)
        self.repetition.insert(0, "20")
        self.repetition.grid(row=1, column=3, sticky='w')

    def place_DAQ_ch(self):
        daq_label = tk.Label(self, text='DAQ DIO channel:', width=17, anchor='e')
        daq_label.grid(row=1, column=4, sticky='e')
        self.daq_ch = tk.Entry(self, width=18)
        self.daq_ch.insert(0, "Dev1/port0/line0")
        self.daq_ch.grid(row=1, column=5, sticky='w')

    def place_scan_button(self):
        self.scan_button = tk.Button(self, text="Scan", width=6, bg="white", command=self.scan)
        self.scan_button.grid(row=0, column=4)

    def place_scan_elem(self):
        self.elem_frame = tk.LabelFrame(self, relief='flat')
        self.elem_frame.grid(row=2, column=0, columnspan=100, sticky='nw')
        for i in range(3):
            self.scan_elem_list.append(self.scan_elem(self.elem_frame))
            self.scan_elem_list[i].grid(row=0, column=i)

    def del_scan_slot(self):
        self.scan_elem_list[-1].destroy()
        del self.scan_elem_list[-1]
        self.scan_elem_num -= 1
        if self.scan_elem_num == 1:
            self.del_button["state"] = "disabled"

    def add_scan_slot(self):
        self.scan_elem_list.append(self.scan_elem(self.elem_frame))
        self.scan_elem_list[self.scan_elem_num].grid(row=0, column=self.scan_elem_num)
        self.scan_elem_num +=1
        if (self.del_button["state"] == "disabled") and (self.scan_elem_num > 1):
            self.del_button["state"] = "normal"

    def scan(self):
        # generate randomized scan parameters
        samp_num = int(self.sample_num.get())
        rep = int(self.repetition.get())
        self.scan_elem_list[0].compile()
        self.scan_param = np.linspace(self.scan_elem_list[0].start, self.scan_elem_list[0].end, samp_num)
        if self.scan_elem_num > 1:
            for i in range(self.scan_elem_num-1):
                self.scan_elem_list[i+1].compile()
                s = np.linspace(self.scan_elem_list[i+1].start, self.scan_elem_list[i+1].end, samp_num)
                scan_param = np.vstack((self.scan_param, s))

        # instruction number sanity check
        for i in range(self.scan_elem_num):
            if self.scan_elem_list[i].instr > self.main.num_instr-1:
                logging.warning("(Scanner) Instruction number doesn't exist")
                return

        self.scan_param = np.repeat(self.scan_param, rep, axis=0)
        np.random.shuffle(self.scan_param)
        # if scan_param is a 1-dim array, it will be turned into 2-dim
        # if scan_param is a 2-dim array, it won't change
        self.scan_param = np.reshape(self.scan_param, (len(self.scan_param), -1))

        # stop and reset spincore
        pb_stop()
        pb_reset()

        # set up a counter for number of points that have been scanned
        self.counter = 0

        # load spincore the first scan parameters
        self.load_param()

        # a DAQ is used to read Spincore "running" signal, a falling edge will be used to trigger loading
        self.task = nidaqmx.Task()
        ch = self.daq_ch.get()
        self.task.di_channels.add_di_chan(ch)
        self.task.timing.cfg_change_detection_timing(falling_edge_chan=ch,
                                                    sample_mode=const.AcquisitionType.CONTINUOUS
                                                    )
        self.task.register_signal_event(const.Signal.CHANGE_DETECTION_EVENT, self.load_param)
        self.task.start()

    def load_param(self, task_handle=None, signal_type=None, callback_date=None):
        for i in range(self.scan_elem_num):
            instr = self.scan_elem_list[i].instr
            # every element in scan_elem_list is supposed to be compiled before
            unit = self.scan_elem_list[i].start_un.current()
            self.main.instrlist[instr].un.current(unit)
            self.main.instrlist[instr].du.delete(0, 'end')
            self.main.instrlist[instr].du.insert(0, str(self.scan_param[self.counter][i]/(1000**(2-unit))))

        self.counter += 1
        # self.main.loadboard()
        if self.counter == len(self.scan_param):
            self.close()


class MainWindow(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.master.title("SpinCore PulseBlasterUSB")
        self.master.geometry('600x800')
        self.num_instr = 6 # number of instructions (one instruction is one column in this GUI)
        self.instrlist = [] # used to save all the instructions
        self.pack()
        self.place_scrollbar()
        self.place_control_widgets()
        self.place_scanner()
        self.place_main_cols()
        # self.init_spincore()

    def place_scrollbar(self):
        # Create scrollbars
        # Followed the following threads to add scroll bars:
        # https://stackoverflow.com/questions/3085696/adding-a-scrollbar-to-a-group-of-widgets-in-tkinter
        # https://stackoverflow.com/questions/17355902/tkinter-binding-mousewheel-to-scrollbar
        self.canvas = tk.Canvas(self.master, borderwidth=0, background="gray95")
        self.frame = tk.Frame(self.canvas, background="gray95")
        self.frame.configure(relief='flat', borderwidth=0, highlightthickness=0)
        vsb = tk.Scrollbar(self.master, orient="vertical", command=self.canvas.yview)
        hsb = tk.Scrollbar(self.master, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=vsb.set)
        self.canvas.configure(xscrollcommand=hsb.set)

        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas.create_window((4,4), window=self.frame, anchor="nw")

        self.frame.bind("<Configure>", lambda event: self.onFrameConfigure())
        self.canvas.bind_all("<MouseWheel>", lambda event: self.on_mousewheel(event))

    def place_control_widgets(self):
        self.control_frame = tk.LabelFrame(self.frame, relief='groove', text='General Control', font='Helvetica 10 bold')
        self.control_frame.grid(row=0, column=0, ipadx=5, ipady=2, columnspan=1)
        # Create top control widgets
        add_del_label = tk.Label(self.control_frame, text=r"Add/Delete an instruction: ")
        add_del_label.grid(row=0, column=0, columnspan=2, sticky='e')

        # delete the last instruction column
        self.del_button = tk.Button(self.control_frame, text="-", width=6, bg="white", command=self.del_instr)
        self.del_button.grid(row=0, column=2)

        # add an instruction olumn after the last one
        add_button = tk.Button(self.control_frame, text="+", width=6, bg="white", command=self.add_instr)
        add_button.grid(row=0, column=3, sticky='w')

        # load instructions into PulseBlasterUSB
        loadboard_button = tk.Button(self.control_frame, text="load board", width=10, bg="white", command=self.loadboard)
        loadboard_button.grid(row=0, column=5, sticky='e')

        # software trigger PulseBlasterUSB
        softtrig_button = tk.Button(self.control_frame, text="software trig", width=10, bg="white", command=self.software_trig)
        softtrig_button.grid(row=0, column=6)

        # toggle scanner widgets
        softtrig_button = tk.Button(self.control_frame, text="toggle scanner", width=13, bg="white", command=self.toggle_scanner)
        softtrig_button.grid(row=0, column=7)

        # file location label
        location_label = tk.Label(self.control_frame, text="location to load file: ")
        location_label.grid(row=2, rowspan=2, column=0, columnspan=2, sticky='e')

        # location of .txt to load
        self.location_text = tk.Text(self.control_frame, height=3, width=65)
        self.location_text.grid(row=2, rowspan =2, column=2, columnspan=5)

        # browse and choose a .txt file
        browsefile_button = tk.Button(self.control_frame, text="browse files", width=10, bg="white", command=self.browse_file)
        browsefile_button.grid(row=2, column=7, padx=5, pady=5, sticky='e')

        # load configuraion from a .txt file to this GUI
        loadconfig_button = tk.Button(self.control_frame, text="load configs", width=10, bg="white", command=self.load_config)
        loadconfig_button.grid(row=3, column=7, padx=5, pady=5, sticky='e')

        # saved file name label
        filename_label = tk.Label(self.control_frame, text="file name to save as: ")
        filename_label.grid(row=4, column=0, columnspan=2, sticky='e')

        # name to append to file name when saving
        self.filename_entry = tk.Entry(self.control_frame, width=32)
        self.filename_entry.insert(0, "PulseBlasterUSB_configs")
        self.filename_entry.grid(row=4, column=2, columnspan=2, sticky='w')

        # whether to append date/time to saved file name
        self.datetime_var = tk.IntVar()
        self.datetime_var.set(1)
        self.datetime_cb = tk.Checkbutton(self.control_frame, variable=self.datetime_var, text=r"auto append data & time")
        self.datetime_cb.grid(row=4, column=4, columnspan=3, sticky='w')

        # save configuraion to a .txt file
        save_button = tk.Button(self.control_frame, text="save configs", width=10, bg="white", command=self.save_config)
        save_button.grid(row=4, column=7, padx=5, pady=2, sticky='e')

        for i in range(4):
            bottom_empty_label = tk.Label(self.frame, text="")
            bottom_empty_label.grid(row=100+i, column=0)

    def place_scanner(self):
        self.scanner = Scanner(self)
        self.scanner.grid(row=1, column=0, ipadx=5, ipady=2, columnspan=100, sticky='nw')
        # self.scanner.grid_remove()

    def place_main_cols(self):
        # create main columns in this GUI
        self.instr_frame = tk.LabelFrame(self.frame, relief='flat')
        self.instr_frame.grid(row=2, column=0, columnspan=100, sticky='nw')
        # add a sub frame here so when instruction columns are added/deleted,
        # main frame column size doesn't change

        # Create the first column: decriptive labels
        self.descr_col = Descr(self.instr_frame)
        self.descr_col.grid(row=0, column=0)

        # Create 2nd to nth columns: Spincore instruction data
        for i in range(self.num_instr):
            self.instrlist.append(Instr(self.instr_frame, i))
            self.instrlist[i].grid(row=0, column=i+1)

    # initiate Spincore PulseBlaster USB
    def init_spincore(self):
        # downloaded form http://www.spincore.com/support/SpinAPI_Python_Wrapper/Python_Wrapper_Main.shtml
        # And modified by Qian W., July 24, 2020
        # Enable the SpinCore log file
        pb_set_debug(1)

        print("Using SpinAPI Library version %s" % pb_get_version())
        print("Found %d board(s) in the system.\n" % pb_count_boards())
        print("This program maniputales the TTL outputs of the PulseBlasterUSB.\n\n")

        pb_select_board(0)

        # pb_init() function has to be called before any programming/start/stop instructions
        if pb_init() != 0:
        	print("Error initializing board: %s" % pb_get_error())
        	input("Please press a key to continue.")
        	exit(-1)

        # Configure the core clock, in MHz
        pb_core_clock(100.0)

    # scrollbar funtion
    def onFrameConfigure(self):
        '''Reset the scroll region to encompass the inner frame'''
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    # scrollbar function
    def on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    # delete the last instruction column
    def del_instr(self):
        self.instrlist[-1].destroy()
        del self.instrlist[-1]
        self.num_instr -= 1
        if self.num_instr == 1:
            self.del_button["state"] = "disabled"

    # add an instruction column after the last one
    def add_instr(self):
        self.instrlist.append(Instr(self.instr_frame, self.num_instr))
        self.num_instr += 1
        self.instrlist[-1].grid(row=0, column=self.num_instr)
        # both 'num_instr' and 'instrlist' are lists, in this way, the list can be manipulated
        if (self.del_button["state"] == "disabled") and (self.num_instr > 1):
            self.del_button["state"] = "normal"

    # load instrctions into PulseBlasterUSB
    def loadboard(self):
        pb_start_programming(PULSE_PROGRAM)
        for i in range(self.num_instr):
            self.instrlist[i].compile_instr()
            pb_inst_pbonly(*self.instrlist[i].values[1:5])
        pb_stop_programming()

    # software trigger PulseBlasterUSB
    def software_trig(self):
        pb_start()

    # toggle scanner widgets
    def toggle_scanner(self):
        if self.scanner.winfo_viewable():
            self.scanner.grid_remove()
        else:
            self.scanner.grid()

    # browse and choose a .txt file
    def browse_file(self):
        file_loca = filedialog.askopenfilename(initialdir="saved_configs", title="Select a file",
                                                filetypes=(("config files", "*.ini"), ("all files", "*.*")))
        if len(file_loca) > 0:
            self.location_text.delete(1.0, 'end')
            self.location_text.insert(1.0, file_loca)

    # this function is used when a saved configuration is loaded to GUI, it's used to make the number of instruction correct
    def chop_instr(self, new_num_instr):
        while new_num_instr < self.num_instr:
            self.del_instr()
        while new_num_instr > self.num_instr:
            self.add_instr()

    def load_config(self):
        file_loca = self.location_text.get(1.0, 'end')[:-1]
        if not os.path.exists(file_loca):
            tk.messagebox.showerror("Error", "File doesn't exist.")
            return

        config = configparser.ConfigParser()
        config.read(file_loca) # remove '\n' at the end of location_text.get()
        dev_name = [dev.strip() for dev in config["Devices"]["devices"].split(',')]
        for i in range(channel_num):
            self.descr_col.ch_label_list[i].delete(0, 'end')
            self.descr_col.ch_label_list[i].insert(0, dev_name[channel_num-1-i])
        self.chop_instr(len(config.sections())-1)
        for i in range(self.num_instr):
            self.instrlist[i].note.delete(0, 'end')
            self.instrlist[i].note.insert(0, config[f"Instr {i}"].get("instr note"))
            self.instrlist[i].du.delete(0, 'end')
            self.instrlist[i].du.insert(0, config[f"Instr {i}"].get("duration time"))
            self.instrlist[i].un.current(duration_unit.index(config[f"Instr {i}"].get("duration unit")))
            self.instrlist[i].opd.delete(0, 'end')
            self.instrlist[i].opd.insert(0, config[f"Instr {i}"].get("op data"))
            self.instrlist[i].opc.current(opcodes.index(config[f"Instr {i}"].get("op code")))
            for j in range(channel_num):
                self.instrlist[i].cbvarlist[j].set(int(config[f"Instr {i}"]["ttl output pattern"][channel_num+1-j]))

    def save_config(self):
        file_name = ""
        if self.filename_entry.get():
            file_name += self.filename_entry.get()
        if self.datetime_var.get():
            if file_name != "":
                file_name += "_"
            file_name += time.strftime("%Y%m%d_%H%M%S")
        file_name += ".ini"
        file_name = r"saved_configs"+"\\"+file_name
        if os.path.exists(file_name):
            overwrite = tk.messagebox.askyesno("Warning", "File name exits. Continue to overwrite it?", default='no')
            if not overwrite:
                return

        config = configparser.ConfigParser(allow_no_value=True)
        # config["Settings"] = {}
        # config["Settings"]["spinapi lib version"] = str(pb_get_version())
        # config["Settings"]["number of boards in system"] = str(pb_count_boards())
        self.descr_col.compile_ch_label_text()
        config["Devices"] = {}
        config["Devices"]["# form channel {:d} to channel 0".format(channel_num-1)] = None
        config["Devices"]["devices"] = ", ".join(self.descr_col.ch_label_text)
        for i in range(self.num_instr):
            self.instrlist[i].compile_instr()
            config[f"Instr {i}"] = {}
            config[f"Instr {i}"]["instr note"] = self.instrlist[i].values[0]
            config[f"Instr {i}"]["ttl output pattern"] = '0b' + str(bin(self.instrlist[i].values[1]))[2:].zfill(channel_num)
            config[f"Instr {i}"]["op code"] = opcodes[self.instrlist[i].values[2]]
            config[f"Instr {i}"]["op data"] = str(self.instrlist[i].values[3])
            config[f"Instr {i}"]["duration time"] = self.instrlist[i].du.get()
            config[f"Instr {i}"]["duration unit"] = duration_unit[self.instrlist[i].un.current()]

        configfile = open(file_name, "w")
        config.write(configfile)
        configfile.close()



root = tk.Tk()
mygui = MainWindow(root)
mygui.mainloop()

# pb_close function has to be called at the end of any programming/start/stop instructions
# pb_close()

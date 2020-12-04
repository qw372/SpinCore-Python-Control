import PulseBlasterUSB as pbusb
import tkinter as tk
from spinapi import *

root = tk.Tk()
pb_gui = pbusb.PulseBlaster_GUI(root)

class newwin:
    def __init__(self, pb_gui):
        self.pb_gui = pb_gui
        newWindow = tk.Toplevel(root)
        newWindow.title("New Window")
        newWindow.geometry("200x200")
        self.en = tk.Entry(newWindow, width=30)
        self.en.pack()
        bu = tk.Button(newWindow, text="update", command=self.update_en)
        bu.pack()

    def update_en(self):
        s = self.pb_gui.instrlist[0].du.get()
        self.en.delete(0, 'end')
        self.en.insert(0, s)

new = newwin(pb_gui)

root.mainloop()

# pb_close function has to be called at the end of any programming/start/stop instructions
pb_close()

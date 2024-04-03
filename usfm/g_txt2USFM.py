# -*- coding: utf-8 -*-
# Implements Txt2USFM and Text2USFM_Frame, which are the controller and frame
# for operating the txt2USFM.py script.
# GUI interface for merging BTTW text files and converting to USFM

from tkinter import *
from tkinter import ttk
from tkinter import font
from tkinter import filedialog
from idlelib.tooltip import Hovertip
import os
import g_util
import g_step

stepname = 'Txt2USFM'   # equals the main class name in this module

class Txt2USFM(g_step.Step):
    def __init__(self, mainframe, mainapp):
        super().__init__(mainframe, mainapp, stepname, "Convert text files to USFM")
        self.frame = Text2USFM_Frame(parent=mainframe, controller=self)
        self.frame.grid(row=1, column=0, sticky="nsew")

    def name(self):
        return stepname

    def onExecute(self, values):
        self.enablebutton(2, False)
        self.values = values
        count = g_util.count_folders(values['source_dir'], f"{values['language_code']}_[\w][\w][\w].*_reg|_ulb$")
        self.mainapp.execute_script("txt2USFM", count)
        self.frame.clear_status()

    def onNext(self):
        copyparms = {'language_code': self.values['language_code'], 'source_dir': self.values['target_dir']}
        self.mainapp.step_next(copyparms)

    # Called by the main app.
    def onScriptEnd(self, status: str):
        if not status:
            status = f"The conversion is done.\nAdvance to USFM verification and cleanup."
        self.frame.show_progress(status)
        self.frame.onScriptEnd()
                
class Text2USFM_Frame(g_step.Step_Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)

        self.language_code = StringVar()
        self.source_dir = StringVar()
        self.target_dir = StringVar()
        for var in (self.language_code, self.source_dir, self.target_dir):
            var.trace_add("write", self._onChangeEntry)
        for col in [2,3]:
            self.columnconfigure(col, weight=1)   # keep column 1 from expanding
        self.columnconfigure(4, minsize=94)

        language_code_label = ttk.Label(self, text="Language code:", width=20)
        language_code_label.grid(row=3, column=1, sticky=W, pady=2)
        language_code_entry = ttk.Entry(self, width=20, textvariable=self.language_code)
        language_code_entry.grid(row=3, column=2, sticky=W)
        source_dir_label = ttk.Label(self, text="Location of text files:", width=20)
        source_dir_label.grid(row=4, column=1, sticky=W, pady=2)
        source_dir_entry = ttk.Entry(self, width=47, textvariable=self.source_dir)
        source_dir_entry.grid(row=4, column=2, columnspan=3, sticky=W)
        target_dir_Tip = Hovertip(source_dir_entry, hover_delay=1000,
                text="Folder containing the files to be converted")
        src_dir_find = ttk.Button(self, text="...", width=2, command=self._onFindSrcDir)
        src_dir_find.grid(row=4, column=4, sticky=W)

        target_dir_label = ttk.Label(self, text="Location for .usfm files:", width=21)
        target_dir_label.grid(row=5, column=1, sticky=W, pady=2)
        target_dir_entry = ttk.Entry(self, width=47, textvariable=self.target_dir)
        target_dir_entry.grid(row=5, column=2, columnspan=3, sticky=W)
        target_dir_Tip = Hovertip(target_dir_entry, hover_delay=1000,
                text="Folder for the new usfm files. The folder will be created if it doesn't exist.")
        target_dir_find = ttk.Button(self, text="...", width=2, command=self._onFindTargetDir)
        target_dir_find.grid(row=5, column=4, sticky=W)

        language_code_entry.focus()

    # Called when the frame is first activated. Populate the initial values.
    def show_values(self, values):
        self.values = values
        self.language_code.set(values['language_code'])
        self.source_dir.set(values['source_dir'])
        self.target_dir.set(values['target_dir'])
        
        # Create buttons
        self.controller.showbutton(1, "<<<", cmd=self._onBack)
        self.controller.showbutton(2, "CONVERT", tip="Run the conversion script now.", cmd=self._onExecute)
        self.controller.showbutton(3, "Source folder",
                                   tip="Open the folder containing the files to be converted.", cmd=self._onOpenTextDir)
        self.controller.showbutton(4, "Usfm folder", cmd=self._onOpenTargetDir)
        self.controller.showbutton(5, ">>>", tip="Verify USFM", cmd=self._onSkip)
        self._set_button_status()

    # Called by the controller when script execution begins.
    def clear_status(self):
        self.message_area['state'] = NORMAL   # enables insertions to message area
        self.message_area.delete('1.0', 'end')

    # Caches the current parameters in self.values and calls the mainapp to save them in the config file.
    def _save_values(self):
        self.values['language_code'] = self.language_code.get()
        self.values['source_dir'] = self.source_dir.get()
        self.values['target_dir'] = self.target_dir.get()
        self.controller.mainapp.save_values(stepname, self.values)
        self._set_button_status()

    def _onFindSrcDir(self, *args):
        self.controller.askdir(self.source_dir)
    def _onFindTargetDir(self, *args):
        self.controller.askdir(self.target_dir)
    def _onChangeEntry(self, *args):
        self._set_button_status()
    def _onOpenTextDir(self, *args):
        os.startfile(self.source_dir.get())
    def _onOpenTargetDir(self, *args):
        self._save_values()
        os.startfile(self.values['target_dir'])
    def onScriptEnd(self):
        self.message_area['state'] = DISABLED   # prevents insertions to message area
        self.controller.showbutton(5, ">>>", tip="Verify USFM", cmd=self._onNext)
        self._set_button_status()

    def _set_button_status(self):
        good_sourcedir = os.path.isdir(self.source_dir.get())
        okay = (self.language_code.get() and good_sourcedir and self.target_dir.get())
        self.controller.enablebutton(2, okay)
        self.controller.enablebutton(3, good_sourcedir)
        self.controller.enablebutton(4, os.path.isdir(self.target_dir.get()))

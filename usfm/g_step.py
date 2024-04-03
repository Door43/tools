# -*- coding: utf-8 -*-
# Base class for graphical user interface classes for USFM steps.

from tkinter import *
from tkinter import ttk
from tkinter import font
from tkinter import filedialog
from abc import ABC, abstractmethod
import os
import g_util

class Step(ABC):
    def __init__(self, mainframe, mainapp, stepname, title):
        self.main_frame = mainframe
        self.mainapp = mainapp
        self.steptitle = title  # Descriptive, displayable title for the step
        self.buttons = mainapp.buttonsframe
        self.frame = None

    @abstractmethod
    def name(self) -> str:
        return None

    def show(self, values):
        self.values = values
        self.frame.show_values(values)
        self.frame.tkraise()

    def title(self):
        return self.steptitle

    def onBack(self):
        self.mainapp.step_back()
    def onSkip(self):
        self.mainapp.step_next()
    # Advance to next step, defaulting the values of the named parameters, if any.
    def onNext(self, *parms):
        copyparms = {parm: self.values[parm] for parm in parms} if parms else None
        self.mainapp.step_next(copyparms)

    # Default implementation, only for Steps that don't execute,. i.e. SelectProcess
    def onExecute(self):
        pass
    def showbutton(self, psn, text, tip=None, cmd=None):
        self.buttons.show(psn, text, tip, cmd)
    def hidebutton(self, *psns):
        for psn in psns:
            self.buttons.hide(psn)
    def enablebutton(self, psn, enable=True):
        if enable:
            self.buttons.enable(psn)
        else:
            self.buttons.disable(psn)

    # Called by the main app.
    # Displays the specified string in the message area.
    def onScriptMessage(self, progress):
        self.frame.show_progress(progress)

    # Called by the main app.
    def onScriptEnd(self, status: str):
        if status:
            self.frame.show_progress(status)
        self.frame.onScriptEnd()

    # Prompts the user for a folder, using the parent of the specified default folder as the starting point.
    # Sets dirpath to the selected folder, or leaves it unchanged if the user cancels.
    def askdir(self, dirpath: StringVar):
        initdir = dirpath.get()
        if os.path.isdir(initdir):
            initdir = os.path.dirname(initdir)
        path = filedialog.askdirectory(initialdir=initdir, mustexist=False, title = "Select Folder")
        if path:
            dirpath.set(path)

    # Prompts the user to locate a usfm file in the specified source_dir.
    # Sets filename to the selected file, or leaves it unchanged if the user cancels.
    def askusfmfile(self, source_dir: StringVar, filename: StringVar):
        path = filedialog.askopenfilename(initialdir=source_dir.get(), title = "Select usfm file",
                                           filetypes=[('Usfm file', '*.usfm')])
        if path:
            filename.set(os.path.basename(path))

class Step_Frame(ttk.Frame, ABC):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        # Set up message area
        self.message_area = Text(self, height=10, width=30, wrap="word")
        self.message_area['borderwidth'] = 2
        self.message_area['relief'] = 'sunken'
        self.message_area['background'] = 'grey97'
        self.message_area.grid(row=88, column=1, columnspan=5, sticky='nsew', pady=6)
        self.rowconfigure(88, minsize=170, weight=1)  # let the message expand vertically
        ys = ttk.Scrollbar(self, orient = 'vertical', command = self.message_area.yview)
        ys.grid(column = 6, row = 88, sticky = 'ns')
        self.message_area['yscrollcommand'] = ys.set

    @abstractmethod
    def show_values(self, values):
        raise NotImplementedError("show_values() not implemented")
    @abstractmethod
    def _save_values(self, values):
        raise NotImplementedError("_save_values() not implemented")

    def show_progress(self, status):
        self.message_area.insert('end', status + '\n')
        self.message_area.see('end')

    def _onBack(self, *args):
        self._save_values()
        self.controller.onBack()
    def _onSkip(self, *args):
        self._save_values()
        self.controller.onSkip()
    def _onNext(self, *args):
        self._save_values()
        self.controller.onNext()
    def _onExecute(self, *args):
        self._save_values()
        self.controller.onExecute(self.values)

    @abstractmethod
    def onScriptEnd(self):
        raise NotImplementedError("onScriptEnd() not implemented")

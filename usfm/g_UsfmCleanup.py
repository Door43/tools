# -*- coding: utf-8 -*-
# GUI interface for automated USFM file cleanup
#

from tkinter import *
from tkinter import ttk
from tkinter import font
from tkinter import filedialog
from idlelib.tooltip import Hovertip
import g_util
import g_step
import os
import time

stepname = 'UsfmCleanup'   # equals the main class name in this module

class UsfmCleanup(g_step.Step):
    def __init__(self, mainframe, mainapp):
        super().__init__(mainframe, mainapp, stepname, "USFM Cleanup")
        self.frame = UsfmCleanup_Frame(mainframe, self)
        self.frame.grid(row=1, column=0, sticky="nsew")

    def name(self):
        return stepname

    def onNext(self):
        super().onNext('source_dir', 'filename')
    
    def onExecute(self, values):
        self.enablebutton(2, False)
        count = 1
        if not values['filename']:
            count = g_util.count_files(values['source_dir'], ".*sfm$")
        self.mainapp.execute_script("usfm_cleanup", count)
        self.frame.clear_status()

    # Runs the revertChanges script to revert usfm_cleanup changes.
    def revertChanges(self):
        sec = {'source_dir': self.values['source_dir'],
               'backupExt': ".usfm.orig",
               'correctExt': ".usfm"}
        self.mainapp.save_values('RevertChanges', sec)
        self.mainapp.execute_script("revertChanges", 1)
        self.frame.clear_status()

class UsfmCleanup_Frame(g_step.Step_Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)

        self.source_dir = StringVar()
        self.filename = StringVar()
        self.std_titles = StringVar()
        for var in (self.filename, self.source_dir):
            var.trace_add("write", self._onChangeEntry)
        self.std_titles.trace_add("write", self._onChangeTitles)
        self.enable = [BooleanVar(value = False) for i in range(9)]
        self.enable[3].trace_add("write", self._onChangeQuotes)
        self.enable[4].trace_add("write", self._onChangeQuotes)

        source_dir_label = ttk.Label(self, text="Location of .usfm files:", width=20)
        source_dir_label.grid(row=4, column=1, sticky=W, pady=2)
        self.source_dir_entry = ttk.Entry(self, width=44, textvariable=self.source_dir)
        self.source_dir_entry.grid(row=4, column=2, columnspan=3, sticky=W)
        src_dir_find = ttk.Button(self, text="...", width=2, command=self._onFindSrcDir)
        src_dir_find.grid(row=4, column=4, sticky=W)

        file_label = ttk.Label(self, text="File name:", width=20)
        file_label.grid(row=5, column=1, sticky=W, pady=2)
        self.file_entry = ttk.Entry(self, width=22, textvariable=self.filename)
        self.file_entry.grid(row=5, column=2, sticky=W)
        file_Tip = Hovertip(self.file_entry, hover_delay=500,
             text="Leave filename blank to clean all .usfm files in the folder.")
        file_find = ttk.Button(self, text="...", width=2, command=self._onFindFile)
        file_find.grid(row=5, column=3, sticky=W)
        
        std_titles_label = ttk.Label(self, text="Standard chapter title:", width=20)
        std_titles_label.grid(row=6, column=1, sticky=E)
        std_titles_entry = ttk.Entry(self, width=18, textvariable=self.std_titles)
        std_titles_entry.grid(row=6, column=2, sticky=W)
        std_title_Tip = Hovertip(std_titles_entry, hover_delay=500,
             text="Leave blank if unknown.")

        subheadingFont = font.Font(size=10, slant='italic')     # normal size is 9
        enable_label = ttk.Label(self, text="Enable these fixes?", font=subheadingFont)
        enable_label.grid(row=10, column=1, columnspan=2, sticky=W, pady=(4,2))

        enable1_checkbox = ttk.Checkbutton(self, text='Spaces', variable=self.enable[1],
                                             onvalue=True, offvalue=False)
        enable1_checkbox.grid(row=11, column=1, sticky=W)
        enable1_Tip = Hovertip(enable1_checkbox, hover_delay=500,
             text="Add spaces between comma/period/colon and a letter (recommended for most languages).")

        enable2_checkbox = ttk.Checkbutton(self, text='Punctuation', variable=self.enable[2],
                                             onvalue=True, offvalue=False)
        enable2_checkbox.grid(row=11, column=2, sticky=W)
        enable2_Tip = Hovertip(enable2_checkbox, hover_delay=500,
             text="Fix double periods, doubled angle brackets, other \"safe\" substitutions (recommended for most languages).")

        self.enable3_checkbox = ttk.Checkbutton(self, text='Double quotes          ', variable=self.enable[3],
                                             onvalue=True, offvalue=False)
        self.enable3_checkbox.grid(row=11, column=3, sticky=W)
        enable3_Tip = Hovertip(self.enable3_checkbox, hover_delay=500,
             text="Promote straight double quotes to curly quotes.")
        self.grid_columnconfigure(2, minsize=40, weight=1)

        self.enable4_checkbox = ttk.Checkbutton(self, text='All straight quotes', variable=self.enable[4],
                                             onvalue=True, offvalue=False)
        self.enable4_checkbox.grid(row=11, column=4, sticky=W)
        enable4_Tip = Hovertip(self.enable4_checkbox, hover_delay=500,
             text="Promote single and double straight quotes to curly quotes, except word-medial.")

        enable5_checkbox = ttk.Checkbutton(self, text='Capitalization', variable=self.enable[5],
                                             onvalue=True, offvalue=False)
        enable5_checkbox.grid(row=12, column=1, sticky=W)
        enable5_Tip = Hovertip(enable5_checkbox, hover_delay=500,
             text="Enforce capitalization of the first word in sentences, disregarding footnotes.")

        enable6_checkbox = ttk.Checkbutton(self, text='\s5 markers', variable=self.enable[6],
                                             onvalue=True, offvalue=False)
        enable6_checkbox.grid(row=12, column=2, sticky=W)
        enable6_Tip = Hovertip(enable6_checkbox, hover_delay=500,
             text="Remove \s5 markers (recommended for all text except GLs).")

        enable7_checkbox = ttk.Checkbutton(self, text='Section titles', variable=self.enable[7],
                                             onvalue=True, offvalue=False)
        enable7_checkbox.grid(row=12, column=3, sticky=W)
        enable7_Tip = Hovertip(enable7_checkbox, hover_delay=500,
             text="Mark obvious section titles with \s. (not implemented yet)")
        enable7_checkbox.state(['disabled'])

        self.enable8_checkbox = ttk.Checkbutton(self, text='Chapter labels', variable=self.enable[8],
                                             onvalue=True, offvalue=False)
        self.enable8_checkbox.grid(row=12, column=4, sticky=W)
        enable8_Tip = Hovertip(self.enable8_checkbox, hover_delay=500,
             text="Standardize chapter labels.")
        self.enable8_checkbox.state(['disabled'])

    def show_values(self, values):
        self.values = values
        self.source_dir.set(values.get('source_dir', fallback=""))
        self.filename.set(values.get('filename', fallback=""))
        self.std_titles.set(values.get('standard_chapter_title', fallback=""))
        for i in range(len(self.enable)):
            configvalue = f"enable{i}"
            self.enable[i].set( values.get(configvalue, fallback = False))

        # Create buttons
        self.controller.showbutton(1, "<<<", tip="Verify usfm", cmd=self._onBack)
        self.controller.showbutton(2, "CLEAN", tip="Run the USFM cleanup script now.", cmd=self._onExecute)
        self.controller.showbutton(3, "Open usfm folder", cmd=self._onOpenSourceDir)
        self.controller.showbutton(4, "Undo", tip="Restore any and all .usfm.orig backup files.",
                                   cmd=self._onUndo)
        self.controller.showbutton(5, ">>>", tip="Mark paragraphs", cmd=self._onNext)
        self._set_button_status()
        self._onChangeTitles()

    def onScriptEnd(self):
        self.message_area['state'] = DISABLED   # prevents insertions to message area
        self.controller.enablebutton(2, True)
        nChanged = g_util.count_files(self.source_dir.get(), ".*\.usfm\.orig$")
        self.controller.enablebutton(4, nChanged > 0)

    # Called by the controller when script execution begins.
    def clear_status(self):
        self.message_area['state'] = NORMAL   # enables insertions to message area
        self.message_area.delete('1.0', 'end')

    def _onChangeQuotes(self, *args):
        if promote_all := self.enable[4].get():    # promote all straight quotes
            self.enable[3].set(True)
        self.enable3_checkbox.state(['disabled'] if promote_all else ['!disabled'])
        if not self.enable[3].get():
            self.enable[4].set(False)

    def _save_values(self):
        self.values['source_dir'] = self.source_dir.get()
        self.values['filename'] = self.filename.get()
        self.values['standard_chapter_title'] = self.std_titles.get()
        for si in range(len(self.enable)):
            configvalue = f"enable{si}"
            self.values[configvalue] = str(self.enable[si].get())
        self.controller.mainapp.save_values(stepname, self.values)
        self._set_button_status()

    def _onFindSrcDir(self, *args):
        self.controller.askdir(self.source_dir)
    def _onFindFile(self, *args):
        path = filedialog.askopenfilename(initialdir=self.source_dir.get(), title = "Select usfm file",
                                           filetypes=[('Usfm file', '*.usfm')])
        if path:
            self.filename.set(os.path.basename(path))
    def _onChangeEntry(self, *args):
        self._set_button_status()
    def _onOpenSourceDir(self, *args):
        self._save_values()
        os.startfile(self.values['source_dir'])
    def _onUndo(self, *args):
        self._save_values()
        self.controller.revertChanges()
        self.controller.enablebutton(4, False)

    # When there is no standard chapter title, disable the 'Fix chapter titles" button.
    def _onChangeTitles(self, *args):
        if not self.std_titles.get():
            self.enable[8].set(False)
        self.enable8_checkbox.state(['!disabled'] if self.std_titles.get() else ['disabled'])

    def _onOpenIssues(self, *args):
        self._save_values()
        path = os.path.join(self.values['source_dir'], "issues.txt")
        os.startfile(path)

    def _set_button_status(self):
        good_source = os.path.isdir(self.source_dir.get())
        backup_count = g_util.count_files(self.source_dir.get(), ".*\.usfm\.orig$")
        self.controller.enablebutton(3, good_source)
        self.controller.enablebutton(4, backup_count > 0)

        if good_source and self.filename.get():
            path = os.path.join(self.source_dir.get(), self.filename.get())
            good_source = os.path.isfile(path)
        self.controller.enablebutton(2, good_source)

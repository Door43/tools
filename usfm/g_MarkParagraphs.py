# -*- coding: utf-8 -*-
# GUI interface for marking paragraphs
#

from tkinter import *
from tkinter import ttk
from tkinter import font
from tkinter import filedialog
from idlelib.tooltip import Hovertip
import g_util
import g_step
import os
import subprocess
import time

stepname = 'MarkParagraphs'   # equals the main class name in this module

class MarkParagraphs(g_step.Step):
    def __init__(self, mainframe, mainapp):
        super().__init__(mainframe, mainapp, stepname, "Mark paragraphs and poetry")
        self.frame = MarkParagraphs_Frame(mainframe, self)
        self.frame.grid(row=1, column=0, sticky="nsew")

    def name(self):
        return stepname

    def onExecute(self, values):
        self.enablebutton(2, False)
        self.enablebutton(3, False)
        self.values = values
        count = 1
        if not values['filename']:
            count = g_util.count_files(values['source_dir'], ".*sfm$")
        self.script = "mark_paragraphs"
        self.mainapp.execute_script(self.script, count*2)
        self.frame.clear_status()

    # Runs the revertChanges script to revert mark_paragraphs changes.
    def revertChanges(self):
        sec = {'source_dir': self.values['source_dir'],
               'backupExt': ".usfmorig",
               'correctExt': ".usfm"}
        self.mainapp.save_values('RevertChanges', sec)
        self.script = "revertChanges"
        self.mainapp.execute_script(self.script, 1)
        self.frame.clear_status()

    # Called by the mainapp.
    def onScriptEnd(self, status):
        if status:
            self.frame.show_progress(status)
        nIssues = 0
        if self.script == "mark_paragraphs":
            issuespath = os.path.join(self.values['source_dir'], "issues.txt")
            if time.time() - os.path.getmtime(issuespath) < 10:     # issues.txt is recent
                nIssues = 1
            else:
                msg = "No issues reported. This is a good time to reverify the USFM files."
                self.frame.show_progress(msg)
        self.enablebutton(2, True)
        self.enablebutton(3, True)
        self.enablebutton(4, True)
        self.frame.onScriptEnd(nIssues)

class MarkParagraphs_Frame(g_step.Step_Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)

        self.source_dir = StringVar()
        self.model_dir = StringVar()
        self.filename = StringVar()
        self.copy_nb = BooleanVar(value = False)
        self.remove_s5 = BooleanVar(value = True)
        self.sentence_sensitive = BooleanVar(value = True)
        for var in (self.model_dir, self.source_dir, self.filename):
            var.trace_add("write", self._onChangeEntry)
        self.columnconfigure(3, weight=1)   # keep column 1 from expanding
        self.columnconfigure(4, minsize=115)

        model_dir_label = ttk.Label(self, text="Location of model files:", width=21)
        model_dir_label.grid(row=3, column=1, sticky=(W,E), pady=2)
        self.model_dir_entry = ttk.Entry(self, width=43, textvariable=self.model_dir)
        self.model_dir_entry.grid(row=3, column=2, columnspan=3, sticky=W)
        model_dir__Tip = Hovertip(self.model_dir_entry, hover_delay=500,
             text="Folder containing USFM files with well marked paragraphs, e.g. English UDB folder")
        model_dir_find = ttk.Button(self, text="...", width=2, command=self._onFindModelDir)
        model_dir_find.grid(row=3, column=4, sticky=W)

        source_dir_label = ttk.Label(self, text="Location of files\n to be marked:", width=15)
        source_dir_label.grid(row=4, column=1, sticky=W, pady=2)
        self.source_dir_entry = ttk.Entry(self, width=43, textvariable=self.source_dir)
        self.source_dir_entry.grid(row=4, column=2, columnspan=3, sticky=W)
        src_dir_find = ttk.Button(self, text="...", width=2, command=self._onFindSrcDir)
        src_dir_find.grid(row=4, column=4, sticky=W)

        file_label = ttk.Label(self, text="File name:", width=20)
        file_label.grid(row=5, column=1, sticky=W, pady=2)
        self.file_entry = ttk.Entry(self, width=18, textvariable=self.filename)
        self.file_entry.grid(row=5, column=2, sticky=W)
        file_Tip = Hovertip(self.file_entry, hover_delay=500,
             text="Leave filename blank to mark all .usfm files in the folder.")
        file_find = ttk.Button(self, text="...", width=2, command=self._onFindFile)
        file_find.grid(row=5, column=3, sticky=W, padx=5)

        subheadingFont = font.Font(size=10, slant='italic')     # normal size is 9
        enable_label = ttk.Label(self, text="Options:", font=subheadingFont)
        enable_label.grid(row=6, column=1, sticky=W, pady=(4,2))

        copy_nb_checkbox = ttk.Checkbutton(self, text=r'Copy \m, nb and b', variable=self.copy_nb,
                                             onvalue=True, offvalue=False)
        copy_nb_checkbox.grid(row=7, column=1, sticky=W)
        copy_nb_Tip = Hovertip(copy_nb_checkbox, hover_delay=500,
             text=r"Copy \m, \nb and \b markers from model text? (Not usually recommended)")
        remove_s5_checkbox = ttk.Checkbutton(self, text='Eliminate \s5', variable=self.remove_s5,
                                             onvalue=True, offvalue=False)
        remove_s5_checkbox.grid(row=7, column=2, sticky=W)
        remove_s5_Tip = Hovertip(remove_s5_checkbox, hover_delay=500,
             text="Always recommended except for GL source texts")

        sentence_sensitive_checkbox = ttk.Checkbutton(self, text='Sentence sensitive',
                                                      variable=self.sentence_sensitive, onvalue=True, offvalue=False)
        sentence_sensitive_checkbox.grid(row=7, column=3, sticky=W)
        sentence_sensitive_Tip = Hovertip(sentence_sensitive_checkbox, hover_delay=500,
             text="Only insert \p marks *between punctuated sentences. (Recommended)")

        self.model_dir_entry.focus()

    def show_values(self, values):
        self.values = values
        self.source_dir.set(values.get('source_dir', fallback=""))
        self.model_dir.set(values.get('model_dir', fallback=""))
        self.filename.set(values.get('filename', fallback=""))
        self.copy_nb.set(values.get('copy_nb', fallback=False))
        self.remove_s5.set(values.get('removes5markers', fallback=True))
        self.sentence_sensitive.set(values.get('sentence_sensitive', fallback=True))

        # Create buttons
        self.controller.showbutton(1, "<<<", tip="Verify usfm", cmd=self._onBack)
        self.controller.showbutton(2, "MARK", tip="Mark paragraphs now.", cmd=self._onExecute)
        self.controller.showbutton(3, "Open issues file", tip="Open the issues file (which may be from the previous step).",
                                   cmd=self._onOpenIssues)
        self.controller.showbutton(4, "Undo", tip="Restore any and all .usfmorig backup files in the folder.",
                                   cmd=self._onUndo)
        self.controller.enablebutton(4, False)
        self.controller.showbutton(5, ">>>", tip="Verify manifest", cmd=self._onNext)
        self._set_button_status()

    def onScriptEnd(self, nIssues):
        issuespath = os.path.join(self.values['source_dir'], "issues.txt")
        if nIssues > 0:
            self.message_area.insert('end', "Now issues.txt contains the list of issues encountered in marking paragraphs.\n")
            self.message_area.insert('end', "Resolve as appropriate.\n")
            self.message_area.see('end')
        self.message_area['state'] = DISABLED   # prevents insertions to message area

    # Called by the controller when script execution begins.
    def clear_status(self):
        self.message_area['state'] = NORMAL   # enables insertions to message area
        self.message_area.delete('1.0', 'end')

    def _save_values(self):
        self.values['source_dir'] = self.source_dir.get()
        self.values['model_dir'] = self.model_dir.get()
        self.values['filename'] = self.filename.get()
        self.values['copy_nb'] = str(self.copy_nb.get())
        self.values['removeS5markers'] = str(self.remove_s5.get())
        self.values['sentence_sensitive'] = str(self.sentence_sensitive.get())
        self.controller.mainapp.save_values(stepname, self.values)
        self._set_button_status()

    def _onFindModelDir(self, *args):
        self.controller.askdir(self.model_dir)
    def _onFindSrcDir(self, *args):
        self.controller.askdir(self.source_dir)
    def _onFindFile(self, *args):
        self.controller.askusfmfile(self.source_dir, self.filename)
    def _onChangeEntry(self, *args):
        self._set_button_status()

    def _onOpenIssues(self, *args):
        self._save_values()
        path = os.path.join(self.values['source_dir'], "issues.txt")
        os.startfile(path)

    def _onUndo(self, *args):
        self._save_values()
        self.controller.revertChanges()
        self.controller.enablebutton(4, False)

    def _set_button_status(self):
        good_model = os.path.isdir(self.model_dir.get())
        good_source = os.path.isdir(self.source_dir.get())
        self.controller.enablebutton(4, good_source)
        if good_source and self.filename.get():
            path = os.path.join(self.source_dir.get(), self.filename.get())
            good_source = os.path.isfile(path)
        self.controller.enablebutton(2, good_model and good_source)

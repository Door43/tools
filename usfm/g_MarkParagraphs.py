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

    def onExecute(self, values):
        self.values = values
        count = 2
        if not values['filename']:
            count = g_util.count_files(values['source_dir'], ".*sfm$") * 2
        self.script = "mark_paragraphs"
        self.mainapp.execute_script(self.script, count)
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
        self.frame.onScriptEnd(nIssues)

class MarkParagraphs_Frame(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        self.source_dir = StringVar()
        self.model_dir = StringVar()
        self.filename = StringVar()
        self.copy_nb = BooleanVar(value = False)
        self.remove_s5 = BooleanVar(value = True)
        self.sentence_sensitive = BooleanVar(value = True)
        for var in (self.model_dir, self.source_dir, self.filename):
            var.trace_add("write", self._onChangeEntry)
        self.columnconfigure(2, weight=1)   # keep column 1 from expanding
        self.rowconfigure(88, minsize=170, weight=1)  # let the message expand vertically

        model_dir_label = ttk.Label(self, text="Location of model files:", width=21)
        model_dir_label.grid(row=3, column=1, sticky=(W,E), pady=2)
        self.model_dir_entry = ttk.Entry(self, width=43, textvariable=self.model_dir)
        self.model_dir_entry.grid(row=3, column=2, columnspan=3, sticky=W)
        model_dir__Tip = Hovertip(self.model_dir_entry, hover_delay=500,
             text="Folder containing USFM files with well marked paragraphs, e.g. English UDB folder")
        model_dir_find = ttk.Button(self, text="...", width=2, command=self._onFindModelDir)
        model_dir_find.grid(row=3, column=4)

        source_dir_label = ttk.Label(self, text="Location of files\n to be marked:", width=15)
        source_dir_label.grid(row=4, column=1, sticky=W, pady=2)
        self.source_dir_entry = ttk.Entry(self, width=43, textvariable=self.source_dir)
        self.source_dir_entry.grid(row=4, column=2, columnspan=3, sticky=W)
        src_dir_find = ttk.Button(self, text="...", width=2, command=self._onFindSrcDir)
        src_dir_find.grid(row=4, column=4)

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

        self.message_area = Text(self, height=10, width=30, wrap="word")
        self.message_area['borderwidth'] = 2
        self.message_area['relief'] = 'sunken'
        self.message_area['background'] = 'grey97'
        self.message_area.grid(row=88, column=1, columnspan=5, sticky='nsew', pady=6)
        ys = ttk.Scrollbar(self, orient = 'vertical', command = self.message_area.yview)
        ys.grid(column = 6, row = 88, sticky = 'ns')
        self.message_area['yscrollcommand'] = ys.set

        prev_button = ttk.Button(self, text="<<<", command=self._onBack)
        prev_button.grid(row=99, column=1, sticky=(W,N,S))  #, pady=5)
        prev_button_Tip = Hovertip(prev_button, hover_delay=500, text="Previous step")

        self.execute_button = ttk.Button(self, text="MARK",
                                          command=self._onExecute, padding=5)
        self.execute_button['padding'] = (5, 5) # internal padding!
        self.execute_button.grid(row=99, column=2, sticky=(W,N,S))  #, padx=10, pady=5)
        self.execute_button_Tip = Hovertip(self.execute_button, hover_delay=500,
                text="Mark paragraphs now.")

        self.undo_button = ttk.Button(self, text="Undo", command=self._onUndo)
        self.undo_button.grid(row=99, column=3, sticky=(W,N,S))  #, padx=0, pady=5)
        self.undo_button['padding'] = (3, 3) # internal padding!
        self.undo_button_Tip = Hovertip(self.undo_button, hover_delay=500,
                text=f"Restore any and all .usfmorig backup files in the folder.")
        self.undo_button['state'] = DISABLED
        self.issues_button= ttk.Button(self, text="Open issues file", command=self._onOpenIssues)
        self.issues_button.grid(row=99, column=4, sticky=(W,N,S))
        self.undo_button_Tip = Hovertip(self.issues_button, hover_delay=500,
                text=f"Open the issues file, which may be from the previous step!")

        next_button = ttk.Button(self, text=">>>", command=self._onNext, padding=10)
        next_button.grid(row=99, column=5, sticky=(N,S,E)) #, padx=0, pady=5)
        next_button_Tip = Hovertip(next_button, hover_delay=500, text="Verify manifest")

        # for child in parent.winfo_children():
        #     child.grid_configure(padx=25, pady=5)
        self.model_dir_entry.focus()

    def show_values(self, values):
        self.values = values
        self.source_dir.set(values.get('source_dir', fallback=""))
        self.model_dir.set(values.get('model_dir', fallback=""))
        self.filename.set(values.get('filename', fallback=""))
        self.copy_nb.set(values.get('copy_nb', fallback=False))
        self.remove_s5.set(values.get('removes5markers', fallback=True))
        self.sentence_sensitive.set(values.get('sentence_sensitive', fallback=True))
        self._set_button_status()

    # Displays status messages from the running script.
    def show_progress(self, status):
        self.message_area.insert('end', status + '\n')
        self.message_area.see('end')
        self.execute_button['state'] = DISABLED
        self.issues_button['state'] = DISABLED

    def onScriptEnd(self, nIssues):
        issuespath = os.path.join(self.values['source_dir'], "issues.txt")
        if nIssues > 0:
            self.message_area.insert('end', "Now issues.txt contains the list of issues encountered in marking paragraphs.\n")
            self.message_area.insert('end', "Resolve as appropriate.\n")
            self.message_area.see('end')
        self.message_area['state'] = DISABLED   # prevents insertions to message area
        self.execute_button['state'] = NORMAL
        self.issues_button['state'] = NORMAL
        self.undo_button['state'] = NORMAL

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

    def _onExecute(self, *args):
        self._save_values()
        self.controller.onExecute(self.values)

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

    def _onBack(self, *args):
        self.undo_button['state'] = DISABLED
        self._save_values()
        self.controller.onBack()
    def _onNext(self, *args):
        self.undo_button['state'] = DISABLED
        self._save_values()
        self.controller.onNext()
    def _onUndo(self, *args):
        self._save_values()
        self.controller.revertChanges()
        self.undo_button['state'] = DISABLED

    def _set_button_status(self):
        good_model = os.path.isdir(self.model_dir.get())
        good_source = os.path.isdir(self.source_dir.get())
        # self.undo_button['state'] = NORMAL if good_source else DISABLED
        if good_source and self.filename.get():
            path = os.path.join(self.source_dir.get(), self.filename.get())
            good_source = os.path.isfile(path)
        self.execute_button['state'] = NORMAL if good_model and good_source else DISABLED

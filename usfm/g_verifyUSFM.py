# -*- coding: utf-8 -*-
# GUI interface for USFM file verification
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

stepname = 'VerifyUSFM'   # equals the main class name in this module

class VerifyUSFM(g_step.Step):
    def __init__(self, mainframe, mainapp):
        super().__init__(mainframe, mainapp, stepname, "Verify USFM")
        self.frame = VerifyUSFM_Frame(mainframe, self)
        self.frame.grid(row=1, column=0, sticky="nsew")
        self.executed = False

    def name(self):
        return stepname

    def onNext(self):
        if self.executed:
            super().onNext('source_dir', 'filename', 'language_code', 'standard_chapter_title')
        else:
            super().onNext()
        self.executed = False

    def onExecute(self, values):
        self.enablebutton(2, False)
        self.enablebutton(3, False)
        # self.values = values    # redundant, they were the same dict to begin with
        count = 1
        if not values['filename']:
            count = g_util.count_files(values['source_dir'], ".*sfm$")
        self.mainapp.execute_script("verifyUSFM", count)
        self.frame.clear_status()
        self.executed = True
    
    def executeInventoryLabels(self, folder):
        self.mainapp.execute_script("inventory_chapter_labels", 0)
        self.frame.clear_status()

class VerifyUSFM_Frame(g_step.Step_Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        # self.controller = controller

        self.language_code = StringVar()
        self.source_dir = StringVar()
        self.filename = StringVar()
        self.std_titles = StringVar()
        for var in (self.language_code, self.source_dir, self.filename):
            var.trace_add("write", self._onChangeEntry)
        self.suppress = [BooleanVar(value = False) for i in range(12)]
        self.suppress[6].trace_add("write", self._onChangeQuotes)
        self.suppress[7].trace_add("write", self._onChangeQuotes)
        for col in [2,3,4]:
            self.columnconfigure(col, weight=1)   # keep column 1 from expanding
        # self.rowconfigure(88, minsize=170, weight=1)  # let the message expand vertically

        language_code_label = ttk.Label(self, text="Language code:", width=20)
        language_code_label.grid(row=3, column=1, sticky=(W,E,N), pady=2)
        language_code_entry = ttk.Entry(self, width=18, textvariable=self.language_code)
        language_code_entry.grid(row=3, column=2, sticky=W)
        std_titles_label = ttk.Label(self, text="Standard chapter title:", width=20)
        std_titles_label.grid(row=3, column=3, sticky=E)
        std_titles_entry = ttk.Entry(self, width=18, textvariable=self.std_titles)
        std_titles_entry.grid(row=3, column=4, sticky=W)
        std_titles_helper = ttk.Button(self, text="...", width=2, command=self._onInventoryLabels)
        std_titles_helper.grid(row=3, column=5, sticky=W)
        helper_Tip = Hovertip(std_titles_helper, hover_delay=500,
            text="Inventory existing chapter labels")
        
        source_dir_label = ttk.Label(self, text="Location of .usfm files:", width=20)
        source_dir_label.grid(row=4, column=1, sticky=W, pady=2)
        source_dir_entry = ttk.Entry(self, width=43, textvariable=self.source_dir)
        source_dir_entry.grid(row=4, column=2, columnspan=3, sticky=W)
        src_dir_find = ttk.Button(self, text="...", width=2, command=self._onFindSrcDir)
        src_dir_find.grid(row=4, column=4, sticky=W)
        file_label = ttk.Label(self, text="File name:", width=20)
        file_label.grid(row=5, column=1, sticky=W, pady=2)
        file_entry = ttk.Entry(self, width=20, textvariable=self.filename)
        file_entry.grid(row=5, column=2, columnspan=3, sticky=W)
        file_Tip = Hovertip(file_entry, hover_delay=500,
             text="Leave filename blank to verify all .usfm files in the folder.")
        file_find = ttk.Button(self, text="...", width=2, command=self._onFindFile)
        file_find.grid(row=5, column=3, sticky=W, padx=12)

        subheadingFont = font.Font(size=10, slant='italic')     # normal size is 9
        suppressions_label = ttk.Label(self, text="Suppress these warnings?", font=subheadingFont)
        suppressions_label.grid(row=10, column=1, columnspan=2, sticky=W, pady=(4,2))

        suppress1_checkbox = ttk.Checkbutton(self, text='Numbers', variable=self.suppress[1],
                                             onvalue=True, offvalue=False)
        suppress1_checkbox.grid(row=11, column=1, sticky=W)
        suppress1_Tip = Hovertip(suppress1_checkbox, hover_delay=500,
             text="Suppress all warnings about numbers. (possible verse number in verse, space in number, number prefix/suffix, etc.)")
        suppress2_checkbox = ttk.Checkbutton(self, text=r'No \p after \c', variable=self.suppress[2],
                                             onvalue=True, offvalue=False)
        suppress2_checkbox.grid(row=11, column=2, sticky=W)
        suppress2_Tip = Hovertip(suppress2_checkbox, hover_delay=500,
             text=r"Suppress warnings about missing paragraph marker before verse 1. (needed by PTX-Print)")
        suppress3_checkbox = ttk.Checkbutton(self, text=r'Punctuation', variable=self.suppress[3],
                                             onvalue=True, offvalue=False)
        suppress3_checkbox.grid(row=11, column=3, sticky=W)
        suppress3_Tip = Hovertip(suppress3_checkbox, hover_delay=500,
             text=r"Suppress most warnings about punctuation")
        suppress4_checkbox = ttk.Checkbutton(self, text=r'Useless markers', variable=self.suppress[4],
                                             onvalue=True, offvalue=False)
        suppress4_checkbox.grid(row=11, column=4, sticky=W)
        suppress4_Tip = Hovertip(suppress4_checkbox, hover_delay=500,
             text=r"Suppress warnings about useless markers before section/title markers")
        suppress5_checkbox = ttk.Checkbutton(self, text=r'Verse counts', variable=self.suppress[5],
                                             onvalue=True, offvalue=False)
        suppress5_checkbox.grid(row=12, column=1, sticky=W)
        suppress5_Tip = Hovertip(suppress5_checkbox, hover_delay=500,
             text=r"Suppress checks for verse counts")
        suppress6_checkbox = ttk.Checkbutton(self, text=r'Straight quotes', variable=self.suppress[6],
                                             onvalue=True, offvalue=False)
        suppress6_checkbox.grid(row=12, column=2, sticky=W)
        suppress6_Tip = Hovertip(suppress6_checkbox, hover_delay=500,
             text=r"Suppress warnings about straight double and single quotes")

        self.suppress7_checkbox = ttk.Checkbutton(self, text=r'Straight single quotes', variable=self.suppress[7],
                                             onvalue=True, offvalue=False)
        self.suppress7_checkbox.grid(row=12, column=3, sticky=W)
        suppress7_Tip = Hovertip(self.suppress7_checkbox, hover_delay=500,
             text=r"Suppress warnings about straight single quotes  (report straight double quotes only)")
        
        suppress8_checkbox = ttk.Checkbutton(self, text=r'Book titles', variable=self.suppress[8],
                                             onvalue=True, offvalue=False)
        suppress8_checkbox.grid(row=12, column=4, sticky=W)
        suppress8_Tip = Hovertip(suppress8_checkbox, hover_delay=500,
             text=r"Suppress warnings about UPPER CASE BOOK TITLES")
        
        suppress9_checkbox = ttk.Checkbutton(self, text=r'ASCII content', variable=self.suppress[9],
                                             onvalue=True, offvalue=False)
        suppress9_checkbox.grid(row=13, column=1, sticky=W)
        suppress9_Tip = Hovertip(suppress9_checkbox, hover_delay=500,
             text=r"Suppress warnings about ASCII content")
        
        suppress10_checkbox = ttk.Checkbutton(self, text=r'Capitalization', variable=self.suppress[10],
                                             onvalue=True, offvalue=False)
        suppress10_checkbox.grid(row=13, column=2, sticky=W)
        suppress10_Tip = Hovertip(suppress10_checkbox, hover_delay=500,
             text=r'Suppress "First word not capitalized" warnings; report totals only')
        
        suppress11_checkbox = ttk.Checkbutton(self, text=r'Paragraph termination', variable=self.suppress[11],
                                             onvalue=True, offvalue=False)
        suppress11_checkbox.grid(row=13, column=3, sticky=W)
        suppress11_Tip = Hovertip(suppress11_checkbox, hover_delay=500,
             text=r'Suppress "Punctuation missing at end of paragraph" warnings; report totals only')

        self.message_area['wrap'] = "none"
        xs = ttk.Scrollbar(self, orient = 'horizontal', command = self.message_area.xview)
        xs.grid(row=89, column = 1, columnspan=4, sticky = 'ew')
        self.message_area['xscrollcommand'] = xs.set

    def show_values(self, values):
        self.values = values
        self.language_code.set(values.get('language_code', fallback=""))
        self.source_dir.set(values.get('source_dir', fallback=""))
        self.filename.set(values.get('filename', fallback=""))
        self.std_titles.set(values.get('standard_chapter_title', fallback=""))
        for si in range(len(self.suppress)):
            configvalue = f"suppress{si}"
            self.suppress[si].set( values.get(configvalue, fallback = False))

        # Create buttons
        self.controller.showbutton(1, "<<<", tip="Previous step", cmd=self._onBack)
        self.controller.showbutton(2, "VERIFY", tip="Check the USFM files now.", cmd=self._onExecute)
        self.controller.showbutton(3, "Open issues.txt", tip="Open issues.txt file in your default editor",
                                   cmd=self._onOpenIssues)
        nextstep = self.controller.mainapp.nextstepname()
        if nextstep == "Usfm2Usx":
            tip = "Convert to resource container"
        else:
            tip = "Automated USFM file cleanup"
        self.controller.showbutton(5, ">>>", tip=tip, cmd=self._onNext)
        self._set_button_status()

    def onScriptEnd(self):
        issuespath = os.path.join(self.values['source_dir'], "issues.txt")
        exists = os.path.isfile(issuespath)
        self.controller.enablebutton(3, exists)
        if exists:
            if time.time() - os.path.getmtime(issuespath) < 10:     # issues.txt is recent
                self.message_area.insert('end', "issues.txt contains the list of issues found.\n")
                self.message_area.insert('end', "Make corrections using your text editor, or go to\n  Next Step to do automated cleanup.\n")
                self.message_area.see('end')
        self.message_area['state'] = DISABLED   # prevents insertions to message area
        self.controller.enablebutton(2, True)

    # Called by the controller when script execution begins.
    def clear_status(self):
        self.message_area['state'] = NORMAL   # enables insertions to message area
        self.message_area.delete('1.0', 'end')

    # Copies current values from GUI into self.values dict, and calls mainapp to save
    # them to the configuration file.
    def _save_values(self):
        self.values['language_code'] = self.language_code.get()
        self.values['source_dir'] = self.source_dir.get()
        self.values['filename'] = self.filename.get()
        self.values['standard_chapter_title'] = self.std_titles.get()
        for si in range(len(self.suppress)):
            configvalue = f"suppress{si}"
            self.values[configvalue] = str(self.suppress[si].get())
        self.controller.mainapp.save_values(stepname, self.values)
        self._set_button_status()

    def _onInventoryLabels(self, *args):
        self._save_values()
        self.controller.executeInventoryLabels(self.values['source_dir'])

    def _onFindSrcDir(self, *args):
        self.controller.askdir(self.source_dir)
    def _onFindFile(self, *args):
        path = filedialog.askopenfilename(initialdir=self.source_dir.get(), title = "Select usfm file",
                                           filetypes=[('Usfm file', '*.usfm')])
        if path:
            self.filename.set(os.path.basename(path))

    def _onChangeEntry(self, *args):
        self._set_button_status()
    def _onChangeQuotes(self, *args):
        if suppress_all := self.suppress[6].get():    # suppress all straight quotes
            self.suppress[7].set(True)
        self.suppress7_checkbox.state(['disabled'] if suppress_all else ['!disabled'])
        if not self.suppress[7].get():
            self.suppress[6].set(False)

    def _onOpenIssues(self, *args):
        self._save_values()
        path = os.path.join(self.values['source_dir'], "issues.txt")
        os.startfile(path)
    # Opens usfm folder, or specific usfm file
    def _onOpenUsfmFile(self, *args):
        path = os.path.join(self.source_dir.get(), self.filename.get())
        os.startfile(path)

    def _set_button_status(self):
        good_dir = os.path.isdir(self.source_dir.get())
        namedfile = self.filename.get()
        good_subject = good_dir and not namedfile
        if good_dir and namedfile:
            filepath = os.path.join(self.source_dir.get(), namedfile)
            good_subject = os.path.isfile(filepath)
        self.controller.enablebutton(2, self.language_code.get() and good_subject)
        if good_dir:
            title = namedfile if namedfile and good_subject else "Usfm folder"
            self.controller.showbutton(4, title, tip=f"Open {title}", cmd=self._onOpenUsfmFile)
        else:
            self.controller.hidebutton(4)

        issuespath = os.path.join(self.source_dir.get(), "issues.txt")
        self.controller.enablebutton(3, os.path.isfile(issuespath))

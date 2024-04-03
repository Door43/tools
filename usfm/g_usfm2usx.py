# -*- coding: utf-8 -*-
# GUI interface for USFM to USX file conversion.
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

stepname = 'Usfm2Usx'   # equals the main class name in this module

class Usfm2Usx(g_step.Step):
    def __init__(self, mainframe, mainapp):
        super().__init__(mainframe, mainapp, stepname, "Generate resource container")
        self.frame = Usfm2Usx_Frame(mainframe, self)
        self.frame.grid(row=1, column=0, sticky="nsew")

    def name(self):
        return stepname

    def onExecute(self, values):
        self.enablebutton(2, False)
        # self.values = values    # redundant, they were the same dict to begin with
        count = 1
        if not values['filename']:
            count = g_util.count_files(values['source_dir'], ".*sfm$")
        self.mainapp.execute_script("usfm2usx", count)
        self.frame.clear_status()

    # Called by the main app.
    def onScriptEnd(self, status: str):
        if status:
            self.frame.show_progress(status)
        msg = "\nIf the process completed successfully...\n" +\
            "Test one or more of the generated “resource containers” by using it as a source text in BTT-Writer."
        self.frame.show_progress(msg)
        self.frame.onScriptEnd()
        self.enablebutton(2, True)

class Usfm2Usx_Frame(g_step.Step_Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)

        self.language_code = StringVar()
        self.language_name = StringVar()
        self.direction = StringVar()
        self.bible_name = StringVar()
        self.bible_id = StringVar()
        self.pub_date = StringVar()
        self.license = StringVar()
        self.version = StringVar()
        self.source_dir = StringVar()
        self.filename = StringVar()
        self.rc_dir = StringVar()
        for var in (self.language_code, self.language_name, self.bible_id, self.pub_date,
                    self.license, self.version, self.source_dir, self.filename, self.rc_dir):
            var.trace_add("write", self._onChangeEntry)
        self.bible_name.trace_add("write", self._onChangeBible)

        self.grid_columnconfigure(4, weight=1)
        self.grid_columnconfigure(5, weight=0)

        language_code_label = ttk.Label(self, text="Language code:", width=20)
        language_code_label.grid(row=3, column=1, sticky=(W,E,N), pady=2)
        language_code_entry = ttk.Entry(self, width=20, textvariable=self.language_code)
        language_code_entry.grid(row=3, column=2, sticky=W)
        language_label = ttk.Label(self, text="Language name:", width=20)
        language_label.grid(row=4, column=1, sticky=(W,E,N), pady=2)
        language_entry = ttk.Entry(self, width=20, textvariable=self.language_name)
        language_entry.grid(row=4, column=2, sticky=W)

        subheadingFont = font.Font(size=10, slant='italic')     # normal size is 9
        direction_label = ttk.Label(self, text="Text direction:", font=subheadingFont)
        direction_label.grid(row=5, column=1, sticky=(W,E,N), pady=2)
        ltr_rb = ttk.Radiobutton(self, text='Left to right', variable=self.direction, value='ltr')
        ltr_rb.grid(row=6, column=1, sticky=N)
        rtl_rb = ttk.Radiobutton(self, text='Right to left', variable=self.direction, value='rtl')
        rtl_rb.grid(row=6, column=2, sticky=N)

        bible_name_label = ttk.Label(self, text="Bible name:", width=15)
        bible_name_label.grid(row=3, column=3, sticky=(W,E,N), pady=2)
        bible_name_entry = ttk.Entry(self, width=20, textvariable=self.bible_name)
        bible_name_entry.grid(row=3, column=4, sticky=W)
        bible_id_label = ttk.Label(self, text="Bible ID:", width=15)
        bible_id_label.grid(row=4, column=3, sticky=(W,E,N), pady=2)
        bible_id_entry = ttk.Entry(self, width=20, textvariable=self.bible_id)
        bible_id_entry.grid(row=4, column=4, sticky=W)

        date_label = ttk.Label(self, text="Publication date:", width=15)
        date_label.grid(row=5, column=3, sticky=(W,E,N), pady=2)
        date_entry = ttk.Entry(self, width=20, textvariable=self.pub_date)
        date_entry.grid(row=5, column=4, sticky=W)
        version_label = ttk.Label(self, text="Version:", width=15)
        version_label.grid(row=6, column=3, sticky=(W,E,N), pady=2)
        version_entry = ttk.Entry(self, width=20, textvariable=self.version)
        version_entry.grid(row=6, column=4, sticky=W)

        license_label = ttk.Label(self, text="License:", width=15)
        license_label.grid(row=7, column=3, sticky=(W,E,N), pady=2)
        license_entry = ttk.Entry(self, width=20, textvariable=self.license)
        license_entry.grid(row=7, column=4, sticky=W)

        source_dir_label = ttk.Label(self, text="Location of .usfm files:", width=20)
        source_dir_label.grid(row=8, column=1, sticky=W, pady=2)
        source_dir_entry = ttk.Entry(self, width=61, textvariable=self.source_dir)
        source_dir_entry.grid(row=8, column=2, columnspan=3, sticky=W)
        src_dir_find = ttk.Button(self, text="...", width=2, command=self._onFindSrcDir)
        src_dir_find.grid(row=8, column=5, sticky=W)

        file_label = ttk.Label(self, text="File name:", width=20)
        file_label.grid(row=9, column=1, sticky=W, pady=2)
        file_entry = ttk.Entry(self, width=19, textvariable=self.filename)
        file_entry.grid(row=9, column=2, sticky=W)
        file_Tip = Hovertip(file_entry, hover_delay=500,
             text="Leave filename blank to convert all .usfm files in the folder.")
        file_find = ttk.Button(self, text="...", width=2, command=self._onFindFile)
        file_find.grid(row=9, column=3, sticky=W)
        
        rc_dir_label = ttk.Label(self, text="RC folder:", width=20)
        rc_dir_label.grid(row=10, column=1, sticky=W, pady=2)
        rc_dir_entry = ttk.Entry(self, width=61, textvariable=self.rc_dir)
        rc_dir_entry.grid(row=10, column=2, columnspan=4, sticky=W)
        rc_dir_Tip = Hovertip(rc_dir_entry, hover_delay=500,
             text="BTT-Writer application data folder for Resource Containers")
        rc_dir_find = ttk.Button(self, text="...", width=2, command=self._onFindRcDir)
        rc_dir_find.grid(row=10, column=5, sticky=W)
        
    def show_values(self, values):
        self.values = values
        self.language_code.set(values.get('language_code', fallback=""))
        self.language_name.set(values.get('language_name', fallback=""))
        self.direction.set(values.get('direction', fallback="ltr"))
        self.bible_name.set(values.get('bible_name', fallback=""))
        self.bible_id.set(values.get('bible_id', fallback=""))
        self.pub_date.set(values.get('pub_date', fallback=""))
        self.license.set(values.get('license', fallback=""))
        self.version.set(values.get('version', fallback=""))
        self.source_dir.set(values.get('source_dir', fallback=""))
        self.filename.set(values.get('filename', fallback=""))
        self.rc_dir.set(values.get('rc_dir', fallback=""))

        # Create buttons
        self.controller.showbutton(1, "<<<", tip="Reverify original USFM file(s)", cmd=self._onBack)
        self.controller.showbutton(2, "CONVERT", tip="Convert to USX now; overwrite existing .usx files, if any.",
                                   cmd=self._onExecute)
        self.controller.hidebutton(3,4,5)
        self._set_button_status()

    def onScriptEnd(self):
        self.message_area['state'] = DISABLED   # prevents insertions to message area

    # Called by the controller when script execution begins.
    def clear_status(self):
        self.message_area['state'] = NORMAL   # enables insertions to message area
        self.message_area.delete('1.0', 'end')

    # Copies current values from GUI into self.values dict, and calls mainapp to save
    # them to the configuration file.
    def _save_values(self):
        self.values['language_code'] = self.language_code.get()
        self.values['language_name'] = self.language_name.get()
        self.values['bible_name'] = self.bible_name.get()
        self.values['bible_id'] = self.bible_id.get()
        self.values['direction'] = self.direction.get()
        self.values['pub_date'] = self.pub_date.get()
        self.values['license'] = self.license.get()
        self.values['version'] = self.version.get()
        self.values['source_dir'] = self.source_dir.get()
        self.values['filename'] = self.filename.get()
        self.values['rc_dir'] = self.rc_dir.get()
        self.controller.mainapp.save_values(stepname, self.values)
        self._set_button_status()

    def _onFindSrcDir(self, *args):
        self.controller.askdir(self.source_dir)
    def _onFindFile(self, *args):
        path = filedialog.askopenfilename(initialdir=self.source_dir.get(), title = "Select usfm file",
                                           filetypes=[('Usfm file', '*.usfm')])
        if path:
            self.filename.set(os.path.basename(path))
        
    def _onFindRcDir(self, *args):
        if not self.rc_dir.get() and os.name == 'nt':
            self.rc_dir.set(r"~\AppData\Local\BTT-Writer\library")
        self.controller.askdir(self.rc_dir)

    def _onChangeEntry(self, *args):
        self._set_button_status()
    # Called when the Bible name changes
    def _onChangeBible(self, *args):
        if len(self.bible_name.get()) > 3 and not self.bible_id:
            self.bible_id.set( self.bible_name.get().lower()[0:3] )
        self._set_button_status()

    def _set_button_status(self):
        dirs_ok = os.path.isdir(self.source_dir.get()) and os.path.isdir(self.rc_dir.get())
        if dirs_ok and self.filename.get():
            path = os.path.join(self.source_dir.get(), self.filename.get())
            dirs_ok = os.path.isfile(path)
        language_ok = self.language_code.get() and self.language_name.get()
        pubdetails_ok = self.bible_id.get() and self.bible_name.get() and\
                        self.pub_date.get() and self.license.get() and self.version.get()
        self.controller.enablebutton(2, dirs_ok and language_ok and pubdetails_ok)

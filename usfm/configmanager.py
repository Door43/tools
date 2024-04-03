# -*- coding: utf-8 -*-
# Config file manager

from configparser import ConfigParser
import os
import io

class ToolsConfigManager:
    def __init__(self):
        # self.configpath = os.path.expanduser("~/Documents/tools_config.ini")
        path = os.path.expanduser("~/AppData/Local/usfm_wizard")
        if not os.path.exists(path):
            os.mkdir(path)
        self.configpath = os.path.join(path, "tools_config.ini")
        self.config = ConfigParser()
        self._init_config()

    def __repr__(self):
        return f'ToolsConfigManager({self.configpath})'

    # Creates default config file if it is empty or doesn't exist.
    # Reads the config file.
    def _init_config(self):
        self.config.read(self.configpath, encoding='utf-8')
        if not self.config.sections():
            self._make_default_config()
            self.config.read(self.configpath, encoding='utf-8')

    def _make_default_config(self):
        for section in ['MarkParagraphs','Plaintext2Usfm','RenameParatextFiles','RevertChanges',
                        'Txt2USFM','Usfm2Usx','UsfmCleanup','VerifyManifest','VerifyUSFM']:
            self.config.add_section(section)
            self.config[section] = self.default_section(section)
        with io.open(self.configpath, "tw", encoding='utf-8', newline='\n') as file:
            self.config.write(file)

    # Sets config file path to a new value, if one is specified.
    # Returns the (possibly new) config path.
    def config_path(self, newpath = None):
        if newpath and newpath != self.configpath:
            self.configpath = newpath
            self._init_config()
        return self.configpath

    def get_section(self, sectionname):
        if sectionname not in self.config or len(self.config[sectionname]) == 0:
            values = self.default_section(sectionname)
            self.write_section(sectionname, values)
        return self.config[sectionname]     # returning local variable values is wrong
    
    def write_section(self, sectionname, sec):
        self.config[sectionname] = sec
        with io.open(self.configpath, "tw", encoding='utf-8', newline='\n') as file:
            self.config.write(file)

    def default_section(self, sectionname):
        match sectionname:
            case 'MarkParagraphs':
                sec = {'model_dir': "",
                    'source_dir': "",
                    'filename': "",
                    'copy_nb': False,
                    'removeS5markers': True,
                    'sentence_sensitive': True }
            case 'Plaintext2Usfm':
                sec = {'source_dir': "",
                       'filename': "",
                       'target_dir': ""}
            case 'RenameParatextFiles':
                sec = {}
            case 'RevertChanges':
                sec = {'source_dir': "",
                    'backupExt': "",
                    'correctExt': ".usfm" }
            case 'SelectProcess':
                sec = {'selection': 'Txt2USFM'}
            case 'Txt2USFM':
                sec = {'source_dir': "",
                       'target_dir': "",
                       'mark_chunks': False,
                       'language_code': "" }
            case 'UsfmCleanup':
                sec = {'source_dir': "",
                    'filename': "",
                    'standard_chapter_title': "",
                    'enable1': True,
                    'enable2': True,
                    'enable3': False,
                    'enable4': False,
                    'enable5': False,
                    'enable6': True,
                    'enable7': False,
                    'enable8': False,
                    'sourcetext_dir': "" }
            case 'Usfm2Usx':
                sec = {'source_dir': "",
                       'rc_dir': "",
                       'language_name': "",
                       'language_code': "",
                       'bible_name': "",
                       'bible_id': "",
                       'direction': "ltr",
                       'pub_date': "",
                       'license': "",
                       'version': "" }
            case 'VerifyManifest':
                sec = {'source_dir': "",
                       'expectascii': "" }
            case 'VerifyUSFM':
                sec = {'source_dir': "",
                       'filename': "",
                       'language_code': "",
                       'standard_chapter_title': "",
                       'usfm_version': "2.0",
                       'suppress1': False,
                       'suppress2': False,
                       'suppress3': False,
                       'suppress4': False,
                       'suppress5': False,
                       'suppress6': False,
                       'suppress7': False,
                       'suppress8': False,
                       'suppress9': False,
                       'suppress10': False,
                       'suppress11': False }
            case _:
                sec = {}
        return sec

# -*- coding: utf-8 -*-
# This script converts plain text files containing books of the Bible to usfm files.
# The text files must be prepared to meet these conditions:
#    Each file contains a single book of the Bible, and no extraneous text.
#    The file names match XXX.txt, where XXX is the 3-character book id.
#    UTF-8 encoding is required.
#    The first line of each file contains the book title, with no other characters.
#    Chapter and verse numbers are in Arabic numerals (0-9).
#    Input text file does not contain USFM markers.
# The script performs these operations:
#    Populates the USFM headers based on the text file name and first line.
#    Standardizes the names of .usfm files. For example 41-MAT.usfm and 42-MRK.usfm.
#    Converts multiple books at once if there are multiple books.
#    Reports failure when chapter 1 is not found, and other errors.
# The script does not mark chunks. If that is desired. run usfm2rc.py later.

import configmanager
import usfm_verses
import re
import operator
import io
import os
import sys
import json
from pathlib import Path

config = None
gui = None
state = None
projects = []
issues_file = None

# Entities
ID = 1
TITLE = 2
CHAPTER = 3
VERSE = 4
TEXT = 5
EOF = 6

class State:
    def __init__(self):
        self.ID = ""
        self.data = ""
        self.title = ""
        self.chapter = 0
        self.verse = 0
        self.reference = ""
        self.lastRef = ""
        self.lastEntity = None
        self.neednext = ID
        self.priority = ID
        self.usfm_file = None
        self.missing_chapters = []

    # Resets state data for a new book
    def addID(self, id):
        self.ID = id
        self.data = ""
        self.title = ""
        self.chapter = 0
        self.verse = 0
        self.missing_chapters = []
        self.lastRef = self.reference + "0"
        self.lastEntity = ID
        self.neednext = {TITLE}
        self.priority = TITLE
        self.usfm_file = io.open(makeUsfmPath(id), "tw", encoding='utf-8', newline='\n')

    def addTitle(self, title, lineno):
        if len(self.data):
            self.data += ' '
        self.data += title
        self.title += title
        self.lastEntity = TITLE
        self.neednext = {CHAPTER, TITLE}
        if lineno > 7:
            self.neednext = {CHAPTER}
        self.priority = CHAPTER

    def addChapter(self, nchap):
        self.data = ""
        self.chapter = nchap
        self.verse = 0
        self.lastRef = self.reference
        self.reference = self.ID + " " + str(nchap) + ":"
        self.lastEntity = CHAPTER
        self.neednext = {VERSE}
        self.priority = VERSE

    def missingChapter(self, nchap):
        self.missing_chapters.append(nchap)

    # Adds the line of text as is without touching any other state
    # Supports texts where chapter labels or section headings are tagged: \cl or \s
    def addMarkedLine(self, text):
        self.data += "\n" + text

    def addVerse(self, vstr):
        self.data = ""
        self.verse = int(vstr)
        self.lastRef = self.reference
        self.reference = self.ID + " " + str(self.chapter) + ":" + vstr
        self.lastEntity = VERSE
        self.neednext = {TEXT}
        self.priority = TEXT

    def addText(self, text):
        if len(self.data) > 0:
            self.data += ' '
        text = text.lstrip(". ")   # lose period after preceding verse number
        self.data += text.strip()  # lose other leading and trailing white space
        if self.lastEntity != TEXT:
            self.neednext = {VERSE, CHAPTER, TEXT}
            self.priority = whatsNext(self.ID, self.chapter, self.verse)
            self.lastEntity = VERSE

    # Called when the end of file is reached
    def addEOF(self):
        self.usfm_file.close()
        self.lastRef = self.reference
        self.lastEntity = EOF
        self.neednext = {ID}
        self.priority = ID
        if self.chapter == 0:
            self.title = ""
            self.lastref = self.ID + " 0"

# Determines whether a verse or a chapter is expected next.
# Based on the current book, chapter and verse as specified by the arguments.
# Not all languages and translation follow the same versification scheme, however.
# Returns VERSE, CHAPTER, or EOF
def whatsNext(book, chapter, verse):
    if verse < usfm_verses.verseCounts[book]['verses'][chapter-1]:
        next = VERSE
    elif chapter < usfm_verses.verseCounts[book]['chapters']:
        next = CHAPTER
    else:
        next = EOF
    return next

vv_re = re.compile(r'([0-9]+)-([0-9]+)')

# cstr is the entire chapter label, often just the chapter number.
def takeChapter(cstr, nchap):
    if state.lastEntity == TITLE:
        writeHeader(state.usfm_file, state.ID, state.data)
    elif state.data:
        state.usfm_file.write(re.sub(" +", " ", state.data) + "\n")
    state.usfm_file.write("\\c " + str(nchap) + "\n")
    if len(cstr) > len(str(nchap)):
        state.usfm_file.write("\\cl " + cstr + "\n")
    state.addChapter(nchap)

vrange_re = re.compile(r'([0-9])+-([0-9]+)')

# vstr contains only the verse number, or a verse number range
def takeVerse(vstr):
    if state.data:
        state.usfm_file.write(re.sub(" +", " ", state.data) + "\n")
    if state.verse == 0:
        state.usfm_file.write("\\p\n")
    state.usfm_file.write("\\v " + vstr + " ")
    if range := vrange_re.search(vstr):
        state.addVerse(range.group(1))
        state.addVerse(range.group(2))
    else:
        state.addVerse(vstr)

def takeLine(line, lineno):
    if line.startswith(r'\c '):
        cstr = line[3:]
        takeChapter(cstr, int(cstr))
    elif line.startswith(r'\s'):
        state.addMarkedLine(line)
    else:
        take(line, lineno)

# Handles the next bit of text, which may be a line or part of a line.
# Uses recursion to handle complex lines.
def take(s, lineno):
    if state.priority == EOF:
        state.priority = TEXT
    if state.priority == TITLE:
        state.addTitle(s, lineno)
    elif state.priority == CHAPTER:
        if hasnumber(s, state.chapter+1) >= 0 and len(s) < 25:    # may have to allow longer s
            takeChapter(s, state.chapter+1)
        elif TITLE in state.neednext:   # haven't reached chapter 1 yet
            state.addTitle(s, lineno)
        elif VERSE in state.neednext:
            (pretext, vv, remainder) = getvv(s, state.verse+1)
            if vv:
                if pretext:
                    take(pretext, lineno)
                takeVerse(vv)
                if remainder:
                    take(remainder, lineno)
            elif TEXT in state.neednext:
                state.addText(s)
        elif TEXT in state.neednext:
            state.addText(s)
        else:
            state.missingChapter(state.chapter+1)
    elif state.priority == VERSE:
        (pretext, vv, remainder) = getvv(s, state.verse+1)
        if not vv and state.verse+1 < usfm_verses.verseCounts[state.ID]['verses'][state.chapter-1]:
            (pretext, vv, remainder) = getvv(s, state.verse+2)
            missingVerse = f"{state.ID} {state.chapter}:{state.verse+1}"
            if vv:
                reportError(f"Skipping {missingVerse}.")
        if vv:
            if pretext:
                take(pretext, lineno)
            takeVerse(vv)
            if remainder:
                take(remainder, lineno)
        elif CHAPTER in state.neednext and hasnumber(s, state.chapter+1) >= 0:
            takeChapter(s, state.chapter+1)
        elif TEXT in state.neednext:
            state.addText(s)
        else:
            reportError("Expected verse not found. (" + state.reference + str(state.verse+1) + ", line " + str(lineno) + ")")
            if state.chapter > 0 and state.verse == 0:
                reportError(f"Is {state.ID} {state.chapter-1}:{state.chapter} missing?")
    elif state.priority == TEXT:
        (pretext, vv, remainder) = getvv(s, state.verse+1)
        if not vv and state.verse+1 < usfm_verses.verseCounts[state.ID]['verses'][state.chapter-1]:
            (pretext, vv, remainder) = getvv(s, state.verse+2)
            missingVerse = f"{state.ID} {state.chapter}:{state.verse+1}"
            if vv:
                reportError(f"Skipping {missingVerse}.")
        if vv:
            if pretext:
                state.addText(pretext)
            takeVerse(vv)
            if remainder:
                take(remainder, lineno)
        else:
            state.addText(s)
    else:
        reportError("Internal error at line " + str(lineno) + " in the text.")

# Extracts specified verse number or verse range beginning with that number.
# Return a (pretext, vv, remainder) tuple.
# If the specified verse is not found, returns ("","","")
def getvv(s, n):
    pos = hasnumber(s, n)
    if pos < 0:
        pretext = ""
        vv = ""
        remainder = ""
    else:
        pretext = s[0:pos]
        range = vrange_re.match(s[pos:])
        if range:
            vv = s[pos:range.end()]
        else:
            vv = str(n)
        if len(s) > pos + len(vv):
            remainder = s[pos + len(vv):]
        else:
            remainder = ""
    return (pretext, vv, remainder)


# Searches for the specified number in the string.
# Returns the position of the specified number in the string, or -1
def hasnumber(s, n):
    s = isolateNumbers(s)
    nstr = str(n)
    if s == nstr or s.startswith(nstr + " "):
        pos = 0
    elif s.endswith(" " + nstr):
        pos = len(s) - len(nstr)
    else:
        pos = s.find(" " + nstr + " ")
        if pos >= 0:
            pos += 1
    return pos

# Returns a string with all non-numeric characters changed to a space,
def isolateNumbers(s):
    t = ""
    for i in range(0,len(s)):
        if s[i] in "0123456789,.":
            t += s[i]
        else:
            t += ' '
    return t

# Writes error message to stderr and to issues.txt.
def reportError(msg):
    reportToGui('<<ScriptMessage>>', msg)
    write(msg, sys.stderr)
    openIssuesFile().write(msg + "\n")

# Sends a progress message to the GUI, and to stdout.
def reportProgress(msg):
    reportToGui('<<ScriptProgress>>', msg)
    write(msg, sys.stdout)

# Sends a status message to the GUI, and to stdout.
def reportStatus(msg):
    reportToGui('<<ScriptMessage>>', msg)
    write(msg, sys.stdout)

def reportToGui(event, msg):
    if gui:
        with gui.progress_lock:
            gui.progress = msg if not gui.progress else f"{gui.progress}\n{msg}"
        gui.event_generate(event, when="tail")

# This little function streams the specified message and handles UnicodeEncodeError
# exceptions, which are common in Indian language texts. 2/5/24.
def write(msg, stream):
    try:
        stream.write(msg + "\n")
    except UnicodeEncodeError as e:
        stream.write(state.reference + ": (Unicode...)\n")

# If issues.txt file is not already open, opens it for writing.
# First renames existing issues.txt file to issues-oldest.txt unless
# issues-oldest.txt already exists.
# Returns file pointer.
def openIssuesFile():
    global issues_file
    if not issues_file:
        path = os.path.join(config['source_dir'], "issues.txt")
        if os.path.exists(path):
            bakpath = os.path.join(config['source_dir'], "issues-oldest.txt")
            if not os.path.exists(bakpath):
                os.rename(path, bakpath)
        issues_file = io.open(path, "tw", buffering=2048, encoding='utf-8', newline='\n')
    return issues_file

# Parses the book id from the file name.
# Return upper case bookId, or empty string on failure.
def getBookId(filename):
    bookId = None
    (id, ext) = os.path.splitext(filename)
    if ext == ".txt" and len(id) == 3 and id.upper() in usfm_verses.verseCounts:
        bookId = id.upper()
    else:
        reportError(f"Cannot identify book from file name: {filename}.\n  Use XXX.txt where XXX is book ID.")
    return bookId

# Appends information about the current book to the global projects list.
def appendToProjects(bookId, bookTitle):
    global projects
    testament = 'nt'
    if usfm_verses.verseCounts[bookId]['sort'] < 40:
        testament = 'ot'
    project = { "title": bookTitle, "id": bookId.lower(), "sort": usfm_verses.verseCounts[bookId]["sort"], \
                "path": "./" + makeUsfmFilename(bookId), "category": "[ 'bible-" + testament + "' ]" }
    projects.append(project)

# Writes list of projects converted to the specified file.
# The resulting file can be used as the projects section of manifest.yaml.
def dumpProjects(path):
    projects.sort(key=operator.itemgetter('sort'))

    manifest = io.open(path, "tw", buffering=1, encoding='utf-8', newline='\n')
    manifest.write("projects:\n")
    for p in projects:
        manifest.write("  -\n")
        manifest.write("    title: '" + p['title'] + "'\n")
        manifest.write("    versification: ufw\n")
        manifest.write("    identifier: '" + p['id'] + "'\n")
        manifest.write("    sort: " + str(p['sort']) + "\n")
        manifest.write("    path: '" + p['path'] + "'\n")
        manifest.write("    categories: " + p['category'] + "\n")
    manifest.close()

def shortname(longpath):
    source_dir = Path(config['source_dir'])
    shortname = Path(longpath)
    if shortname.is_relative_to(source_dir):
        shortname = shortname.relative_to(source_dir)
    return str(shortname)

# Generates name for usfm file
def makeUsfmPath(bookId):
    return os.path.join(config['target_dir'], makeUsfmFilename(bookId))

    # Generates name for usfm file
def makeUsfmFilename(bookId):
    num = usfm_verses.verseCounts[bookId]['usfm_number']
    return num + '-' + bookId + '.usfm'

def writeHeader(usfmfile, bookId, bookTitle):
    usfmfile.write("\\id " + bookId + "\n\\ide UTF-8")
    usfmfile.write("\n\\h " + bookTitle)
    usfmfile.write("\n\\toc1 " + bookTitle)
    usfmfile.write("\n\\toc2 " + bookTitle)
    usfmfile.write("\n\\toc3 " + bookId.lower())
    usfmfile.write("\n\\mt1 " + bookTitle + "\n\n")

# This method is called to convert the specified file to usfm.
# Returns the book title.
def convertBook(path, bookId):
    reportProgress(f"Converting: {shortname(path)}...")
    sys.stdout.flush()
    state.addID(bookId)

    with io.open(path, "tr", 1, encoding='utf-8-sig') as input:
        lines = input.readlines()
    lineno = 0
    for line in lines:
        lineno += 1
        line = line.strip()
        if len(line) > 0:
            takeLine(line, lineno)
    if state.data and state.chapter > 0:
        state.usfm_file.write(re.sub(" +", " ", state.data) + '\n')
    state.addEOF()
    if state.missing_chapters:
        reportError("Chapter number " + str(state.chapter+1) + " not found in " + shortname(path))
    return state.title

def convertFolder(folder):
    for entry in os.listdir(folder):
        path = os.path.join(folder, entry)
        if os.path.isdir(path) and entry[0] != '.':
            convertFolder(path)
        elif os.path.isfile(path) and entry.endswith(".txt") and not entry.startswith("issues"):
            bookId = getBookId(entry)
            if bookId:
                title = convertBook(path, bookId)
            if bookId and title:
                appendToProjects(bookId, title)
            else:
                if not bookId:
                    reportError("Unable to identify " + shortname(path) + " as a Bible book.")
                elif not title:
                    reportError("Invalid file: " + shortname(path))

def main(app = None):
    global gui
    gui = app
    global config
    config = configmanager.ToolsConfigManager().get_section('Plaintext2Usfm')
    if config:
        global state
        state = State()
        source_dir = config['source_dir']
        file = config['filename']
        target_dir = config['target_dir']
        Path(target_dir).mkdir(exist_ok=True)

        if file:
            path = os.path.join(source_dir, file)
            if os.path.isfile(path):
                bookId = getBookId(file)
                if bookId:
                    title = convertBook(path, bookId)
                if not title:
                    reportError(f"Invalid file, cannot convert: {path}")
            else:
                reportError(f"No such file: {path}")
        else:
            convertFolder(source_dir)
            if projects:
                dumpProjects( os.path.join(target_dir, "projects.yaml") )

    reportStatus("\nDone.")
    sys.stdout.flush()
    if gui:
        gui.event_generate('<<ScriptEnd>>', when="tail")

# Processes each directory and its files one at a time
if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
# This program cleans up common issuss in USFM files.
# Backs up the .usfm files being modified.
# Outputs .usfm files of the same name in the same location.
#
# Moves standalone \p \m and \q markers which occur just before an \s# marker
#    to the next line after the \s# marker.
# Promote straight quotes to open and closed quotes. (optional)
# Capitalizes first word in sentences. (optional)

import configmanager
import re       # regular expression module
import io
import os
import shutil
import sys
import substitutions
import quotes
import doublequotes
import parseUsfm
import sentences
import usfmFile
from datetime import date

gui = None
config = None
enable = [True]*9
schapter = ""
std_titles = ""
nChanged = 0
aligned_usfm = False
needcaps = True
in_footnote = False
issuesFile = None

def shortname(longpath):
    source_dir = config['source_dir']
    shortname = str(longpath)
    if shortname.startswith(source_dir):
        shortname = os.path.relpath(shortname, source_dir)
    return shortname

# Writes message to gui, stderr, and issues.txt.
def reportError(msg):
    reportStatus(msg)     # message to gui
    sys.stderr.write(msg + "\n")
    if issues := openIssuesFile():
        issues.write(msg + "\n")

# Sends a progress report to the GUI, and to stdout.
def reportProgress(msg):
    global gui
    if gui:
        with gui.progress_lock:
            gui.progress = msg if not gui.progress else f"{gui.progress}\n{msg}"
        gui.event_generate('<<ScriptProgress>>', when="tail")
    print(msg)

# Sends a status message to the GUI, and to stdout.
def reportStatus(msg):
    global gui
    if gui:
        with gui.progress_lock:
            gui.progress = msg if not gui.progress else f"{gui.progress}\n{msg}"
        gui.event_generate('<<ScriptMessage>>', when="tail")
    print(msg)

# If issues.txt file is not already open, opens it for writing.
# Overwrites existing issues.txt file, if any.
# Returns new file pointer.
def openIssuesFile():
    global issuesFile
    if not issuesFile:
        source_dir = config['source_dir']
        if os.path.isdir(source_dir):
            path = os.path.join(source_dir, "issues.txt")
            issuesFile = io.open(path, "tw", buffering=4096, encoding='utf-8', newline='\n')
            issuesFile.write(f"Issues detected by usfmCleanup, {date.today()}, {source_dir}\n-------------------\n")
    return issuesFile

#  Move paragraph marker before section marker to follow the section marker
movepq_re = re.compile(r'\n(\\[pqm][i1-9]*?)\n+(\\s[1-9 ].*?)\n', flags=re.UNICODE+re.DOTALL)

# Moves standalone \p \m and \q markers which occur just before an \s# marker
#    to the next line after the \s# marker.
def usfm_move_pq(str):
    newstr = ""
    found = movepq_re.search(str)
    while found:
        newstr += str[0:found.start()] + '\n' + found.group(2) + '\n' + found.group(1) + '\n'
        str = str[found.end():]
        found = movepq_re.search(str)
    newstr += str
    return newstr

#losepq_re = re.compile(r'\n(\\[pqm][i1-9]?)\n+(\\[pqm][i1-9 ]?.*?)\n', flags=re.UNICODE+re.DOTALL)
losepq_re = re.compile(r'\n\\[pqm][i1-9]? *\n+(\\[^v].*?\n)', flags=re.UNICODE)

# Remove standalone paragraph markers not followed by verse marker.
def usfm_remove_pq(str):
    newstr = ""
    found = losepq_re.search(str)
    while found:
        newstr += str[:found.start()] + "\n" + found.group(1)
        str = str[found.end():]
        found = losepq_re.search(str)
    newstr += str
    return newstr

s5_re = re.compile(r'\n\\s5 *?\n', flags=re.UNICODE+re.DOTALL)

# Removes \s5 markers
def usfm_remove_s5(str):
    newstr = ""
    found = s5_re.search(str)
    while found:
        newstr += str[:found.start()] + "\n"
        str = str[found.end():]
        found = s5_re.search(str)
    newstr += str
    return newstr

# Finds \toc, \h and \mt lines, and changes the title on those lines to title case.
def fix_booktitles_x(str, compiled_expression):
    pos = 0
    title_line = compiled_expression.search(str, pos)
    while title_line:
        pos = title_line.start()
        title = title_line.group(2)
        if not title.istitle():     # not title case already
            title = title.title().replace("Iii", 'III')
            title = title.replace("Ii", 'II')
            str = str[:pos] + title_line.group(1) + title + str[title_line.end():]
        pos += 5
        title_line = compiled_expression.search(str, pos)
    return str

# Finds \toc, \h and \mt lines, and changes the title on those lines to title case.
def fix_booktitles(str):
    str = fix_booktitles_x(str, re.compile(r'(\\toc[12] )([^\n]+\n)'))
    str = fix_booktitles_x(str, re.compile(r'(\\h )([^\n]+\n)'))
    str = fix_booktitles_x(str, re.compile(r'(\\mt1? )([^\n]+\n)'))
    return str

spacey3_re = re.compile(r'\\v [0-9]+ ([\(\'"«“‘])[\s]', re.UNICODE)    # verse starts with free floating quote mark
jammedparen_re = re.compile(r'[^\s]\(')

# Replaces substrings from substitutions module
# Reduces double periods to single periods
# Removes space after quote or left paren at beginning of verse.
def fix_punctuation(str):
    for pair in substitutions.subs:
        str = str.replace(pair[0], pair[1])
    pos = str.find("..", 0)
    while pos >= 0:
        if pos != str.find("...", pos):
            str = str[:pos] + str[pos+1:]
        pos = str.find("..", pos+2)
    pos = 0
    if bad := spacey3_re.search(str):
        pos = bad.end()
        str = str[:pos-1] + str[pos:]
    if bad := jammedparen_re.search(str):
        pos = bad.start() + 1
        str = str[:pos] + ' ' + str[pos:]
    return str

# spacing_list is a list of compiled expressions where a space needs to be inserted
spacing_list = [ re.compile(r'[\.,;:][A-Za-z]') ]

# Adds spaces where needed. spacing_list contrals what happens.
# spacing_list may need to be customized for every language.
def add_spaces(str):
    for sub_re in spacing_list:
        found = sub_re.search(str)
        while found:
            pos = found.start() + 1
            str = str[:pos] + ' ' + str[pos:]
            found = sub_re.search(str)
    return str


# Rewrites file and returns True if any changes are made.
def convert_wholefile(path):
    global aligned_usfm

    input = io.open(path, "tr", encoding="utf-8-sig")
    alltext = input.read()
    origtext = alltext
    input.close()
    aligned_usfm = ("lemma=" in alltext)
    changed = False

    if enable[6]:
        alltext = usfm_remove_s5(alltext)
    alltext = usfm_move_pq(alltext)
    alltext = usfm_remove_pq(alltext)
    alltext = fix_booktitles(alltext)
    if not aligned_usfm:
        if enable[2]:
            alltext = fix_punctuation(alltext)
        if enable[1]:
            alltext = add_spaces(alltext)
        if enable[4]:
            alltext = quotes.promoteQuotes(alltext)
        elif enable[3]:
            alltext = doublequotes.promoteQuotes(alltext)
    if alltext != origtext:
        output = io.open(path, "tw", buffering=1, encoding='utf-8', newline='\n')
        output.write(alltext)
        output.close()
        changed = True
    return changed

# Returns the complementary quote character
def matechar(quote):
    leftquote  = "\"'«“‘"
    rightquote = "\"'»”’"
    pos = leftquote.find(quote)
    if pos >= 0:
        mate = rightquote[pos]
    else:
        pos = rightquote.find(quote)
        mate = leftquote[pos]   # works even if pos is -1
    return mate

# Returns position of the matching quote mark, before or after specified quote position.
# Returns -1 if matching quote is not found.
def find_mate(quote, pos, line):
    mate = matechar(quote)
    nFollowing = line[pos+1:].count(mate)
    nPreceding = line[:pos-1].count(mate)
    if nFollowing % 2 == 1 and nPreceding % 2 == 0:
        matepos = line.find(mate, pos+1)
    elif nFollowing % 2 == 0 and nPreceding % 2 == 1:
        matepos = line.rfind(mate, 0, pos-1)
    else:
        matepos = -1
    return matepos

quotemedial_re = re.compile(r'[\w][\.\?!;\:,](["\'«“‘’”»])[\w]', re.UNICODE)    # adjacent punctuation where second char is a quote mark

# Finds sequences of phrase-ending punctuation followed by a quote,
#   adjacent to word-forming characters on both sides.
# Inserts space before or after the quotes, as appropriate.
def change_quote_medial(line):
    pos = 0
    changed = False
    while bad := quotemedial_re.search(line):
        pos = bad.start() + 2
        matepos = find_mate(bad.group(1), pos, line)
        if matepos > pos:
            line = line[:pos] + ' ' + line[pos:]
            changed = True
        elif 0 <= matepos < pos:
            line = line[:pos+1] + ' ' + line[pos+1:]
            changed = True
        bad = quotemedial_re.search(line)
        if bad and bad.start() <= pos:
            break
    return (changed, line)

quotefloat_re = re.compile(r' (["\'«“‘’”»])[\s]', re.UNICODE)

# Deals with quotes surrounded by white space on both sides.
# Removes one of the spaces if a matching quote is found in the same line.
def change_floating_quotes(line):
    pos = 0
    changed = False
    while bad := quotefloat_re.search(line):
        pos = bad.start() + 1
        matepos = find_mate(bad.group(1), pos, line)
        if matepos > pos:
            line = line[:pos+1] + line[pos+2:]
            changed = True
        elif 0 <= matepos < pos:
            line = line[:pos-1] + line[pos:]
            changed = True
        bad = quotefloat_re.search(line)
        if bad and bad.start() <= pos:
            break
    return (changed, line)

verse_re = re.compile(r'\\v +(0-9)+')
textstart_re = re.compile(r' *[^\\<\n]')
# Returns True if the specified line is unmarked text.
def mark_sections(line):
    if not hasattr(mark_sections, "prevline"):
        mark_sections.prevline = "xx"
        mark_sections.verse = "0"

    if line.find("\\c ") >= 0:
        mark_sections.verse = "0"
    if v := verse_re.search(line):
        mark_sections.verse = v.group(1)

    changed = False
    if textstart_re.match(line):    # line starts with text
        if mark_sections.verse == "0" or not prevline:
            line = "\\s " + line.lstrip()
            changed = True
    prevline = line
    return (changed, line)

# Rewrites the file line by line, making changes to individual lines
# Returns True if any changes are made
def convert_by_line(path):
    with io.open(path, "tr", encoding="utf-8-sig") as input:
        lines = input.readlines()
    output = io.open(path, "tw", encoding='utf-8', newline='\n')
    changedfile = False

    for line in lines:
        (changed1, line) = change_quote_medial(line)
        (changed2, line) = change_floating_quotes(line)
        (changed3, line) = mark_sections(line)
        if changed1 or changed2 or changed3:
            changedfile = True
        output.write(line)
    output.close()
    return (changedfile)

# Returns true if token is part of a footnote or cross reference
def isFootnote(token):
    return token.isF_S() or token.isF_E() or token.isFR() or token.isFT() or token.isFP() or \
token.isFE_S() or token.isFE_E() or token.isRQS() or token.isRQE()

def takeFootnote(key, value, usfm):
    global in_footnote
    if key in {"f", "fr", "ft", "fp", "fe", "rq"}:
        in_footnote = True
    elif key in {"f*", "fe*", "rq*"}:
        in_footnote = False
    usfm.writeUsfm(key, value)

def capitalizeAsNeeded(str):
    global needcaps
    str = sentences.capitalize(str, needcaps)
    needcaps = (sentences.endsSentence(str) and not sentences.endsQuotedSentence(str))
    return str

cl_pattern = re.compile(r'(.*)([\d]+)(.*)')

def fix_chapter_label(label):
    global schapter
    global std_titles
    lab = cl_pattern.match(label.strip())
    if lab:
        part1 = std_titles + " " if len(lab.group(1)) > 0 else ""
        part2 = schapter if lab.group(2).isascii() else lab.group(2)
        part3 = " " + std_titles if len(lab.group(3)) > 0 else ""
        label = f"{part1}{part2}{part3}"
    return label

# May change the label.
# Writes the tag and label to the usfm file.
def takeCL(label, usfm):
    origlabel = label
    if enable[8]:
        label = fix_chapter_label(label)
    usfm.writeUsfm("cl", label)
    return (label != origlabel)

def takeText(str, usfm):
    origstr = str
    global in_footnote
    if enable[5] and not in_footnote:
        str = capitalizeAsNeeded(str)
    usfm.writeStr(str)
    return (str != origstr)

def take(token, usfm):
    changed = False
    if token.isTEXT():
        changed = takeText(token.value, usfm)
    elif token.isC():
        global schapter
        schapter = token.value
        usfm.writeUsfm(token.type, token.value)
    elif token.isCL():
        if takeCL(token.value, usfm):
            changed = True
    elif isFootnote(token):
        takeFootnote(token.type, token.value, usfm)
    else:
        usfm.writeUsfm(token.type, token.value)
    return 1 if changed else 0

# Parses and rewrites the usfm file with corrections to capitalization
# and/or chapter titles.
# Returns True if any changes are made.
def convert_by_token(path):
    changes = 0
    with io.open(path, "tr", 1, encoding="utf-8-sig") as input:
        str = input.read(-1)

    from usfmFile import usfmFile
    usfm = usfmFile(path)
    usfm.setInlineTags({"f", "ft", "f*", "rq", "rq*", "fe", "fe*", "fr", "fk", "fq", "fqa", "fqa*"})
    global needcaps
    needcaps = True
    tokens = parseUsfm.parseString(str)
    for token in tokens:
        changes += take(token, usfm)
    usfm.close()
    # sys.stdout.write(f"{changes} strings in {path} were changed by convert_by_token()\n")
    return (changes > 0)

# Corrects issues in the USFM file
def convertFile(path):
    global nChanged
    reportProgress(f"Checking {shortname(path)}")

    prev_nChanged = nChanged
    tmppath = path + ".tmp"
    if os.path.exists(tmppath):
        os.remove(tmppath)
    os.rename(path, tmppath)    # to preserve time stamp
    shutil.copyfile(tmppath, path)

    if convert_wholefile(path):
        nChanged += 1
    if convert_by_line(path):
        nChanged += 1
    if enable[5] or enable[8]:   # capitalization or chapter titles
        if convert_by_token(path):
            nChanged += 1

    if nChanged > prev_nChanged:
        nChanged = prev_nChanged + 1
        reportStatus(f"Changed {shortname(path)}")
        sys.stdout.flush()
        bakpath = path + ".orig"
        if not os.path.isfile(bakpath):
            os.rename(tmppath, bakpath)
        else:
            os.remove(tmppath)
    else:       # no changes to file
        os.remove(path)
        os.rename(tmppath, path)

# Recursive routine to convert all files under the specified folder
def convertFolder(folder):
    if aligned_usfm:
        return
    for entry in os.listdir(folder):
        if entry[0] != '.':
            path = os.path.join(folder, entry)
            if os.path.isdir(path):
                convertFolder(path)
            elif entry.lower().endswith("sfm"):
                convertFile(path)

def main(app = None):
    global gui
    global config
    global std_titles

    gui = app
    config = configmanager.ToolsConfigManager().get_section('UsfmCleanup')
    if config:
        std_titles = config['standard_chapter_title']
        source_dir = config['source_dir']
        for i in range(1, len(enable)):
            enable[i] = config.getboolean('enable'+str(i), fallback = True)
        file = config['filename']
        if file:
            path = os.path.join(source_dir, file)
            if os.path.isfile(path):
                convertFile(path)
            else:
                reportError(f"No such file: {path}")
        else:
            convertFolder(source_dir)
        reportStatus("\nDone. Changed " + str(nChanged) + " files.")

    if aligned_usfm:
        reportError("Sorry, cannot deal with aligned USFM.")
    if gui:
        gui.event_generate('<<ScriptEnd>>', when="tail")

# Processes all .usfm files in specified directory, one at a time
if __name__ == "__main__":
    main()

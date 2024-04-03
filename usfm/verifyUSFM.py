# -*- coding: utf-8 -*-
# Script for verifying proper USFM.
# Reports errors to stderr and issues.txt.
# Uses these config values:
#   source_dir
#   file  (optional)
#   language_code
#   standard_chapter_title (optional)
#   suppress1 thru suppress11 (optional)
# Detects whether files are aligned USFM.

config = None
suppress = [False]*12
std_titles = None
state = None
gui = None

lastToken = None
aligned_usfm = False
usfm_version = 2
issuesFile = None
issues: dict = {}   # Can't put in State because we want to accumulate issues across all files.
wordlist = dict()

import configmanager
import os
from pathlib import Path
import sys
import parseUsfm
import io
import operator
import footnoted_verses
import usfm_verses
import re
import unicodedata
import usfm_utils
import sentences
from datetime import date

# Marker types
PP = 1      # paragraph or quote
QQ = 2      # poetry
B = 3       # \b for blank line; no titles, text, or verse markers may immediately follow
C = 4       # \c
OTHER = 9

# Manages the verify state for a single usfm file.
class State:
    def __init__(self):
        self.IDs = []
        self.ID = ""
        self.titles = []
        self.chaptertitles = []
        self.nChapterLabels = 0
        self.nParagraphs = 0
        self.nPoetry = 0
        self.chapter = 0
        self.verse = 0
        self.lastVerse = 0
        self.startChunkVerse = 1
        self.needPP = False
        self.needQQ = False
        self.needVerseText = False
        self.textLength = 0
        self.textOkayHere = False
        self.sentenceEnd = True
        self.quotedSentenceEnd = False
        self.footnote_starts = 0
        self.footnote_ends = 0
        self.endnote_starts = 0
        self.endnote_ends = 0
        self.reference = ""
        self.lastRef = ""
        self.startChunkRef = ""
        self.errorRefs = set()
        self.currMarkerType = OTHER
        self.prevMarkerType = OTHER
        self.currMarker = None
        self.prevMarker = None

    def __repr__(self):
        return f'State({self.reference})'

    # Resets state data for a new book
    def addID(self, id):
        self.IDs.append(id)
        self.ID = id
        self.booktitles = []
        self.chaptertitles = []
        self.nChapterLabels = 0
        self.nParagraphs = 0
        self.nPoetry = 0
        self.chapter = 0
        self.lastVerse = 0
        self.verse = 0
        self.startChunkVerse = 1
        self.footnote_starts = 0
        self.footnote_ends = 0
        self.endnote_starts = 0
        self.endnote_ends = 0
        self.needVerseText = False
        self.textLength = 0
        self.textOkayHere = False
        self.sentenceEnd = True
        self.quotedSentenceEnd = False
        self.lastRef = self.reference
        self.startChunkRef = ""
        self.reference = id + " header/intro"
        self.currMarkerType = OTHER
        self.prevMarkerType = OTHER
        self.toc3 = None
        self.upperCaseReported = False

    def getIDs(self):
        return self.IDs

    def addTitle(self, bookTitle):
        self.booktitles.append(bookTitle)
        self.prevMarkerType = self.currMarkerType
        self.currMarkerType = OTHER

    def addToc3(self, toc3):
        self.toc3 = toc3

    def addB(self):
        self.prevMarkerType = self.currMarkerType
        self.currMarkerType = B

    def addChapter(self, c):
        self.lastChapter = self.chapter
        self.chapter = int(c)
        self.needPP = True
        self.lastVerse = 0
        self.verse = 0
        self.needVerseText = False
        self.textOkayHere = False
        self.lastRef = self.reference
        self.reference = self.ID + " " + c
        self.startChunkRef = self.reference + ":1"
        self.prevMarkerType = self.currMarkerType
        self.currMarkerType = C

    # Isolate the word/phrase for "chapter" from the given string.
    # Add it to the list of chapter titles.
    def addChapterLabel(self, title):
        tokens = title.split()
        for token in tokens:
            if decimal_value(token) == state.chapter:
                pos = title.find(token)
                title = (title[:pos] + title[pos+len(token):]).strip()
                if title not in self.chaptertitles:
                    self.chaptertitles.append(title)
                    break
        self.nChapterLabels += 1
        return title    # without chapter number, but spacing unchanged

    def addNB(self):
        self.needPP = False
        self.textOkayHere = True
        self.prevMarkerType = self.currMarkerType
        self.currMarkerType = PP

    def addParagraph(self):
        self.nParagraphs += 1
        self.needPP = False
        self.needQQ = False
        self.textOkayHere = True
        self.sentenceEnd = True
        self.prevMarkerType = self.currMarkerType
        self.currMarkerType = PP

    def addPoetry(self):
        self.nPoetry += 1
        self.nParagraphs += 1
        self.needQQ = False
        self.needPP = False
        self.textOkayHere = True
        self.prevMarkerType = self.currMarkerType
        self.currMarkerType = QQ

    def addSection(self):
        self.prevMarkerType = self.currMarkerType
        self.currMarkerType = OTHER

    # Records the start of a new chunk
    def addS5(self):
        self.startChunkVerse = self.verse + 1
        self.startChunkRef = self.ID + " " + str(self.chapter) + ":" + str(self.startChunkVerse)

    # Keeps track of the current and previous token types.
    # Returns False if there is a repetition of tokens that should not repeat.
    def addMarker(self, type):
        okay = (type != self.currMarker or repeatableMarker(type))
        self.prevMarker = self.currMarker
        self.currMarker = type
        return okay

    def addVerse(self, v):
        self.lastVerse = self.verse
        self.verse = int(v)
        self.needVerseText = True
        self.textLength = 0
        self.textOkayHere = True
        self.lastRef = self.reference
        self.reference = self.ID + " " + str(self.chapter) + ":" + v
        self.prevMarkerType = self.currMarkerType
        self.currMarkerType = OTHER
        self.asciiVerse = True   # until proven False

    def addAcrosticHeading(self):
        self.textOkayHere = True
        self.needQQ = True

    # Resets needQQ flag so that errors are not repeated verse after verse
    def resetPoetry(self):
        self.needQQ = False

    def textOkay(self):
        return self.textOkayHere

    def needText(self):
        return self.needVerseText

    def needCaps(self):
        return self.sentenceEnd and not self.quotedSentenceEnd

    def sentenceEnded(self):
        return self.sentenceEnd

    def getTextLength(self):
        return self.textLength

    def addText(self, text):
        self.prevMarkerType = self.currMarkerType
        self.currMarkerType = OTHER
        self.needVerseText = False
        self.textLength += len(text)
        self.textOkayHere = True
        if not text.isascii():
          self.asciiVerse = False

#    def footnotes_started(self):
#        return self.footnote_starts
#    def footnotes_ended(self):
#        return self.footnote_ends

    def inFootnote(self):
        return self.footnote_starts > self.footnote_ends or self.endnote_starts > self.endnote_ends

    # Increments \f counter
    def addFootnoteStart(self):
        self.footnote_starts += 1
        self.prevMarkerType = self.currMarkerType
        self.currMarkerType = OTHER
        self.needVerseText = False
        self.textOkayHere = True

    # Increments \f* counter
    def addFootnoteEnd(self):
        self.footnote_ends += 1
        self.needVerseText = False
        self.textOkayHere = True

    # Increments \fe counter
    def addEndnoteStart(self):
        self.endnote_starts += 1
        self.prevMarkerType = self.currMarkerType
        self.currMarkerType = OTHER
        self.needVerseText = False
        self.textOkayHere = True

    # Increments \fe* counter
    def addEndnoteEnd(self):
        self.endnote_ends += 1
        self.needVerseText = False
        self.textOkayHere = True

    # Adds the specified reference to the set of error references
    # Returns True if reference can be added
    # Returns False if reference was previously added
    def addError(self, ref):
        success = False
        if ref not in self.errorRefs:
            self.errorRefs.add(ref)
            success = True
        return success

    # Specifies whether the current piece of text ends a sentence.
    def endSentence(self, end):
        self.sentenceEnd = end
    def endQuotedSentence(self, end):
        self.sentenceEnd = end
        self.quotedSentenceEnd = end

    def reportedUpperCase(self):
        self.upperCaseReported = True

# Returns True if it is normal for two markers of the specified type to occur in succession.
def repeatableMarker(marker):
    return (marker == 'v')

# Tries to interpret the specified string as an integer, regardless of language.
# Returns 0 if unable to interpret.
def decimal_value(s):
    value = 0
    for i in range(len(s)):
        d = unicodedata.digit(s[i], -1)
        if d >= 0:
            value = value * 10 + d
        else:
            value = 0
            break
    return value

# Returns the number of chapters that the specified book should contain
def nChapters(id):
    return usfm_verses.verseCounts[id]['chapters']

# Returns the number of verses that the specified chapter should contain
def nVerses(id, chap):
    chaps = usfm_verses.verseCounts[id]['verses']
    n = chaps[chap-1]
    return n

# Returns the English title for the specified book
def bookTitleEnglish(id):
    return usfm_verses.verseCounts[id]['en_name']

def shortname(longpath):
    source_dir = Path(config['source_dir'])
    shortname = Path(longpath)
    if shortname.is_relative_to(source_dir):
        shortname = shortname.relative_to(source_dir)
    return str(shortname)

# If issues.txt file is not already open, opens it for writing.
# First renames existing issues.txt file to issues-oldest.txt unless
# issues-oldest.txt already exists.
# Returns file pointer.
def openIssuesFile():
    global issuesFile
    if not issuesFile:
        source_dir = config['source_dir']
        path = os.path.join(source_dir, "issues.txt")
        if os.path.exists(path):
            bakpath = os.path.join(source_dir, "issues-oldest.txt")
            if not os.path.exists(bakpath):
                os.rename(path, bakpath)
        issuesFile = io.open(path, "tw", encoding='utf-8', newline='\n')
        issuesFile.write(f"Issues detected by verifyUSFM, {date.today()}, {source_dir}\n-------------------\n")
    return issuesFile

# Returns the longest common substring at the start of s1 and s2
def long_substring(s1, s2):
    if s1.startswith(s2):
        return s2
    i = 0
    while i < len(s1) and i < len(s2) and s1[i] == s2[i]:
        i += 1
    return s1[0:i]

# Writes error message to stderr and to issues.txt.
# Keeps track of how many errors of each type.
def reportError(msg, errorId=0, summarize_only=False):
    if not summarize_only:
        reportToGui('<<ScriptMessage>>', msg)
        write(msg, sys.stderr)
        openIssuesFile().write(msg + "\n")

    if errorId > 0:
        global issues
        if errorId in issues:
            newmsg = long_substring(msg, issues[errorId][0])
            newcount = issues[errorId][1] + 1
        else:
            newmsg = msg
            newcount = 1
        issues[errorId] = (newmsg, newcount)

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

# Write summary of issues to issuesFile
def reportIssues():
    global issues
    total = 0
    issuesfile = openIssuesFile()
    issuesfile.write("\nSUMMARY:\n")
    for issue in sorted(issues.items(), key=lambda kv: kv[1][1], reverse=True):
        total += issue[1][1]
        issuesfile.write(f"{issue[1][0]}...:  {issue[1][1]} occurrence(s).\n")
    issuesfile.write(f"\n{total} issues found.")

# Writes the word list to a file.
def dumpWords():
    path = os.path.join(config['source_dir'], "wordlist.txt")
    with io.open(path, "tw", encoding='utf-8', newline = '\n') as file:
        file.write("For better viewing, used a fixed-width font if available.\n")
        file.write("---------------------------------------------------------\n")

        for entry in sorted(wordlist.items(), key=wordkey):
            line = f"{entry[0]:20}  {entry[1][0]}"
            if entry[1][0] < 3:
                line = line + ",   " + entry[1][1]
            file.write(line + '\n')

# Returns sort key for the specified item. 
def wordkey(item):
    word = item[0].lstrip("' .,:;!?-[]{}()<>\"“‘’”*/")
    word2 = item[0].lstrip("'")
    assert(word == word2)
    return str.lower(word)

# Report missing text or all ASCII text, in previous verse
def previousVerseCheck():
    if not isOptional(state.reference) and state.getTextLength() < 10 and state.verse != 0:
        if state.getTextLength() == 0:
            reportError("Empty verse: " + state.reference, 1)
        elif not isShortVerse(state.reference):
            reportError("Verse fragment: " + state.reference, 2)
    if not suppress[9] and state.asciiVerse and state.getTextLength() > 0:
        reportError("Verse is entirely ASCII: " + state.reference, 3)

def longChunkCheck():
    max_chunk_length = 400  # set lower if this is ever needed again
    if not aligned_usfm and state.verse - (max_chunk_length-1) > state.startChunkVerse:
        reportError("Long chunk: " + state.startChunkRef + "-" + str(state.verse) + "   (" + str(state.verse-state.startChunkVerse+1) + " verses)", 4)


# Verifies that at least one book title is specified, other than the English book title.
# This method is called just before chapter 1 begins, so there has been every
# opportunity for the book title to be specified.
def verifyBookTitle():
    title_ok = False
    en_name = bookTitleEnglish(state.ID)
    for title in state.booktitles:
        if title and title != en_name:
            title_ok = True
    if not title_ok:
        reportError("No non-English book title for " + state.ID, 5)

# Reports inconsistent chapter titling
def verifyChapterTitles():
    global std_titles
    if len(state.chaptertitles) > 1 and len(state.chaptertitles) != len(std_titles):
        reportError(f"Inconsistent chapter titling: {state.chaptertitles} in {state.ID}", 6)
    if state.nChapterLabels > 1 and state.nChapterLabels != state.chapter:
        reportError(f"Some chapters do not have chapter labels but {state.nChapterLabels} do.", 7)

# Verifies correct number of verses for the current chapter.
# This method is called just before the next chapter begins.
def verifyVerseCount():
    if state.chapter > 0 and state.verse != nVerses(state.ID, state.chapter):
        # Acts may have 40 o4 41 verses, normally 41.
        # 2 Cor. may have 13 or 14 verses, normally 14.
        # 3 John may have 14 or 15 verses, normally 14.
        # Revelation 12 may have 17 or 18 verses, normally 17.
        if state.reference != 'REV 12:18' and state.reference != '3JN 1:15' and state.reference != '2CO 13:13' \
            and state.reference != 'ACT 19:40':
            reportError(f"Chapter normally has {nVerses(state.ID, state.chapter)} verses: {state.reference}", 8)

def verifyFootnotes():
    if state.footnote_starts != state.footnote_ends:
        reportError("Mismatched footnote tags (" + str(state.footnote_starts) + " started and " + str(state.footnote_ends) + " ended) in " + state.ID, 9)
    if state.endnote_starts != state.endnote_ends:
        reportError("Mismatched endnote tags (" + str(state.endnote_starts) + " started and " + str(state.endnote_ends) + " ended) in " + state.ID, 10)

# Checks whether the entire file was empty or unreadable
def verifyNotEmpty(filename):
    if not state.ID or state.chapter == 0:
        if not state.ID in {'FRT','BAK'}:
            reportError("File may be empty, or open in another program: " + filename, 11)

def verifyChapterCount():
    if state.ID and state.chapter != nChapters(state.ID):
        reportError("There should be " + str(nChapters(state.ID)) + " chapters in " + state.ID + " but " + str(state.chapter) + " chapters are found.", 12)

# \b is used to indicate additional white space between paragraphs.
# No text or verse marker should follow this marker
# and it should not be used before or after titles to indicate white space.
def takeB():
    state.addB()

# Processes a chapter tag
def takeC(c):
    # Report missing text in previous verse
    if c != "1":
        previousVerseCheck()
        # longChunkCheck()
    state.addChapter(c)
    if len(state.IDs) == 0:
        reportError("Missing ID before chapter: " + c, 13)
    if state.chapter < state.lastChapter:
        reportError("Chapter out of order: " + state.reference, 14)
    elif state.chapter == state.lastChapter:
        reportError("Duplicate chapter: " + state.reference, 15)
    elif state.chapter > state.lastChapter + 2:
        reportError("Missing chapters before: " + state.reference, 16)
    elif state.chapter > state.lastChapter + 1:
        reportError("Missing chapter(s) between: " + state.lastRef + " and " + state.reference, 17)

# Processes a chapter label
def takeCL(label):
    global std_titles
    # Report missing text in previous verse
    title = state.addChapterLabel(label.rstrip())   # gets title without chapter number, but spacing unchanged
    if len(std_titles) > 0:
        if title not in std_titles:
            reportError(f"Non-standard chapter label at {state.reference}: {label}", 42)

# Handles all the footnote and endnote token types
def takeFootnote(token):
    if token.isF_S() or token.isRQS():
        if state.footnote_starts != state.footnote_ends:
            reportError(f"Footnote starts before previous one is terminated at {state.reference}", 18)
        state.addFootnoteStart()
    elif token.isFE_S():
        if state.endnote_starts != state.endnote_ends:
            reportError(f"Endnote starts before previous one is terminated at {state.reference}", 19)
        reportError(f"Warning: endnote \\fe ... \\fe* at {state.reference} may break USFM Converter and Scripture App Builder.", 20)
        state.addEndnoteStart()
    elif token.isF_E() or token.isRQE():
        state.addFootnoteEnd()
    elif token.isFE_E():
        state.addEndnoteEnd()
    else:
        if not state.inFootnote():
            reportError(f"Footnote marker ({token.type}) not between \\f ... \\f* pair at {state.reference}", 21)
    takeText(token.value, footnote=True)

def takeID(id):
    if len(id) < 3:
        reportError("Invalid ID: " + id, 22)
    id = id[0:3].upper()
    if id in state.getIDs():
        reportError("Duplicate ID: " + id, 23)
    state.addID(id)

def reportParagraphMarkerErrors(type):
    if state.currMarkerType in {QQ,PP} and not suppress[4]:
        reportError("Warning: back to back paragraph/poetry markers after: " + state.reference, 24)
    if state.needText() and not isOptional(state.reference):
        reportError("Paragraph marker after verse marker, or empty verse: " + state.reference, 25)
    if type == 'nb' and state.currMarkerType != C:
        reportError("\\nb marker should follow chapter marker: " + state.reference, 25.1)

def takeP(type):
    reportParagraphMarkerErrors(type)
    if not aligned_usfm and not suppress[3] and not state.sentenceEnded():
        if state.verse > 0:
            reportError(f"Punctuation missing at end of paragraph: {state.reference}", 26, suppress[11])
        else:
            reportError(f"Punctuation missing at end of paragraph before {state.reference}", 26.1, suppress[11])
    state.addParagraph() if type != 'nb' else state.addNB()

def takeQ(type):
    reportParagraphMarkerErrors(type)
    state.addPoetry()

def takeS5():
    # longChunkCheck()
    state.addS5()
    takeSection('s5')

def takeSection(tag):
    if not suppress[4]:
        if state.currMarkerType == PP:
            reportError(f"Warning: useless paragraph (p,m,nb) marker before \\{tag} marker at: {state.reference}", 27)
        elif state.currMarkerType == QQ:
            reportError(f"Warning: useless \q before \\{tag} marker at: {state.reference}", 28)
        elif state.currMarkerType == B:
            reportError(f"\\b may not be used before or after section heading. {state.reference}", 29)
    state.addSection()

def takeTitle(token):
    if token.isTOC3():
        state.addToc3(token.value)
        global usfm_version
        if usfm_version == 2:
            if (len(token.value) != 3 or not token.value.isascii()):
                reportError("Invalid toc3 value in " + state.reference, 64)
            elif token.value.upper() != state.ID:
                reportError(f"toc3 value ({token.value}) not the same as book ID in {state.reference}", 64.5)
    else:
        state.addTitle(token.value)
    if token.isMT() and token.value.isascii() and not suppress[9]:
        reportError("mt token has ASCII value in " + state.reference, 30)
    if token.value.isupper() and not state.upperCaseReported and not suppress[8]:
        reportError("Upper case book title in " + state.reference, 31)
        state.reportedUpperCase()
    if token.value.startswith("Ii"):
        reportError(f"Mixed case roman numerals in \\{token.type} field", 31.1)
    if state.currMarkerType == B:
        reportError("\\b may not be used before or after titles or headings. " + state.reference, 32)

vv_re = re.compile(r'([0-9]+)-([0-9]+)')
vinvalid_re = re.compile(r'[^\d\-]')

# Receives a string containing a verse number or range of verse numbers.
# Reports missing text in previous verse.
# Reports errors related to the verse number(s), such as missing or duplicated verses.
def takeV(vstr):
    if state.currMarkerType == B:
        reportError(f"\\b should be used only between paragraphs. {state.reference}", 33)
    if vstr != "1":
        previousVerseCheck()   # Checks previous verse
    vlist = []
    if vstr.find('-') > 0:
        vv_range = vv_re.search(vstr)
        if vv_range:
            vnStart = int(vv_range.group(1))
            vnEnd = int(vv_range.group(2))
            # while vn <= vnEnd:
            #     vlist.append(vn)
            #     vn += 1
            for vn in range(vnStart, vnEnd + 1):
                vlist.append(vn)
        else:
            reportError("Problem in verse range near " + state.reference, 34)
    else:
        vlist.append(int(vstr))

    for vn in vlist:
        v = str(vn)
        state.addVerse(str(vn))
        if len(state.IDs) == 0 and state.chapter == 0:
            reportError("Missing ID before verse: " + v, 35)
        if state.chapter == 0:
            reportError("Missing chapter tag: " + state.reference, 36)
        if state.verse == 1 and state.needPP:
            reportError("Need paragraph marker before: " + state.reference, 37, suppress[2])
        if state.needQQ:
            reportError("Need \\q or \\p after acrostic heading before: " + state.reference, 38)
            state.resetPoetry()
        if state.verse < state.lastVerse and state.addError(state.lastRef):
            reportError("Verse out of order: " + state.reference + " after " + state.lastRef, 39)
            state.addError(state.reference)
        elif state.verse == state.lastVerse:
            reportError("Duplicated verse number: " + state.reference, 40)
        elif state.verse == state.lastVerse + 2 and not isOptional(state.reference, True):
            if state.addError(state.lastRef):
                reportError("Missing verse between: " + state.lastRef + " and " + state.reference, 41)
        elif state.verse > state.lastVerse + 2 and state.addError(state.lastRef):
            reportError("Missing verses between: " + state.lastRef + " and " + state.reference, 41.1)

reference_re = re.compile(r'[\d]+[\s]*:[\s]*[\d]+', re.UNICODE)
bracketed_re = re.compile(r'\[ *([^\]]+) *\]', re.UNICODE)

# Looks for possible verse references and square brackets in the text, not preceded by a footnote marker.
# This function is only called when parsing a piece of text preceded by a verse marker.
def reportFootnotes(text):
    global lastToken
    if not isFootnote(lastToken):
        if ref := reference_re.search(text):
            reportFootnote(ref.group(0))
        elif ('(' in text or '[' in text or ')' in text) and (isOptional(state.reference) or state.reference in footnoted_verses.footnotedVerses):
            reportFootnote('(')
        elif "[" in text:
            fn = bracketed_re.search(text)
            if not fn or ' ' in fn.group(1):    # orphan [, or more than one word between brackets
                reportFootnote('[')

def reportFootnote(trigger):
    reference = state.reference
    if ':' in trigger:
        reportError(f"Probable chapter:verse reference ({trigger}) at {reference} belongs in a footnote", 43)
    elif isOptional(reference) or reference in footnoted_verses.footnotedVerses:
        reportError(f"Bracket or parens found in {reference}, a verse that is often footnoted", 43.1)
    else:
        reportError(f"Optional text or untagged footnote at {reference}", 43.2)

# Warns when a paragraph break appears in what seems to be the middle of a sentence.
# Warns when the specified string is supposed to start a sentence but the first word is not capitalized.
# Warns when a sentence later in the string does not start with a capital letter.
def reportCaps(s):
    if state.needCaps():
        word = sentences.firstword(s)
        if word and word[0].islower():
            if state.currMarkerType == PP or state.prevMarkerType == PP:
                reportError(f"First word of paragraph not capitalized near {state.reference}", 44, suppress[10])
            else:
                reportError(f"First word in sentence is not capitalized: \"{word}\" at {state.reference}", 44.1, suppress[10])
    for word in sentences.nextfirstwords(s):
        if word[0].islower():
            reportError(f"First word in sentence is not capitalized: \"{word}\" in {state.reference}", 44.1, suppress[10])

# Returns a string containing text preceding specified start position and following end position
def context(text, start, end):
    start = 0 if start < 0 else 1 + text.rfind(' ', 0, start)
    end = text.find(' ', end, -1)
    return text[start:end] if end > start else text[start:]

#adjacent_re = re.compile(r'([\.\?!;\:,][\.\?!;\:,])', re.UNICODE)
punctuation_re = re.compile(r'([.?!;:,][^\s\u200b\)\]\'"’”»›])', re.UNICODE)     # phrase ending punctuation that doesn't actually end
# note: \u200b indicates word boundaries in scripts that do not use explicit spacing, but is used (seemingly incorrectly) like a space in Laotian
spacey_re = re.compile(r'[\s\n]([\.\?!;\:,\)’”»›])', re.UNICODE)    # space before phrase-ending mark
spacey2_re = re.compile(r'[\s][\[\]\(\'"«“‘’”»›][\s]', re.UNICODE)    # free floating marks
spacey3_re = re.compile(r'[\(\'"«“‘’”»›][\s]', re.UNICODE)       # quote-space at beginning of verse
spacey4_re = re.compile(r'[\s][\(\'"«“‘’”»›]$', re.UNICODE)       # quote-space at end of verse
#wordmedial_punct_re = re.compile(r'[\w][\.\?!;\:,\(\)\[\]"«“‘’”»›][\.\?!;\:,\(\)\[\]\'"«“‘’”»›]*[\w]', re.UNICODE)
wordmedial_punct_re = re.compile(r'[\w][.?!;:,()\[\]"«“‘”»›][.?!;:,()\[\]\'"«“‘’”»›]*[\w]')
outsidequote_re = re.compile(r'([\'"’”»›][\.!])', re.UNICODE)   # Period or exclamation outside closing quote.

def reportPunctuation(text):
    global lastToken
    if bad := punctuation_re.search(text):
        i = bad.start()
        if text[i:i+3] != '...' or text[i:i+4] == "....":
            chars = bad.group(1)
            if not (chars[0] in ',.' and chars[1] in "0123456789"):   # it's a number
                if not (chars[0] == ":" and chars[1] in "0123456789"):
                    reportError("Check the punctuation at " + state.reference + ": " + chars, 45)
                elif not (state.inFootnote() or lastToken.getType().startswith('io') \
                          or lastToken.getType().startswith('ip')):
                    s = context(text, bad.start()-2, bad.end()+1)
                    reportError(f"Untagged footnote (probable) at {state.reference}: {s}", 46)
    #if bad := adjacent_re.search(text):
        #i = bad.start()
        #if text[i:i+3] != "..." or text[i:i+4] == "....":   # Don't report proper ellipses ...
            #reportError("Check repeated punctuation at " + state.reference + ": " + bad.group(1), 47)
    if bad := spacey_re.search(text):
        reportError("Space before phrase ending mark at " + state.reference + ": " + bad.group(1), 48)
    if bad := outsidequote_re.search(text):
        i = bad.start()
        if text[i+1:i+4] != "...":
            reportError(f"Punctuation after quote mark at {state.reference}: {bad.group(1)}", 50)

    if bad := spacey2_re.search(text):
        s = context(text, bad.start()-2, bad.end()+2)
    elif bad := spacey3_re.match(text):
        s = context(text, 0, bad.end()+2)
    elif bad := spacey4_re.search(text):
        s = context(text, bad.start()-2, len(text))
    if bad:
        reportError(f"Free floating mark at {state.reference}: {s}", 49)

    if "''" in text or '""' in text:
        reportError("Repeated quotes at " + state.reference, 51)
    bad = wordmedial_punct_re.search(text)
    if bad and text[bad.end()-1] not in "0123456789":
        s = context(text, bad.start(), bad.end())
        reportError(f"Word medial punctuation in {state.reference}: {s}", 52)
    if '/' in text:
        reportError(f"Forward slash in {state.reference}", 52.1)
    if '\\' in text:
        reportError(f"Backslash in {state.reference}", 52.2)
    if '=' in text:
        reportError(f"Equals sign (=) in {state.reference}", 52.3)

numberembed_re = re.compile(r'[^\s,:\.\d\(\[\-]+[\d]+[^\s,;\.\d\)\]]+')
numberprefix_re = re.compile(r'[^\s,\.\d\(\[][\d]+', re.UNICODE)
numbersuffix_re = re.compile(r'[\d]+[^\s,;:.\-?!"\d\)\]]', re.UNICODE)
unsegmented_re = re.compile(r'[\d][\d][\d][\d]+')
numberformat_re = re.compile(r'[\d]+[.,]?\s[.,]?[\d]+')    # space between digits
leadingzero_re = re.compile(r'[\s]0[0-9,]*', re.UNICODE)
number_re = re.compile(r'[^\d](\d+)[^\d,]')       # possible verse number in text
chapverse_re = re.compile(r'(\d+)([:\-])(\d+)')

def reportNumbers(t, footnote):
    verseflag = False
    if not footnote:
        if t.startswith(str(state.verse) + " "):
            reportError("Verse number in text (probable): " + state.reference, 59)
            verseflag = True
        elif v := number_re.search(t):
            while v:
                if v.group(1) == str(state.verse) or v.group(1) == str(state.verse+1):
                    reportError(f"Possible verse number ({v.group(1)}) in text at {state.reference}", 59.1)
                    verseflag = True
                v = number_re.search(t, v.end()-1)
        if not verseflag:
            chapverse = chapverse_re.search(t)
            while chapverse:
                if chapverse.group(2) == ":" or int(chapverse.group(3)) > int(chapverse.group(1)):
                    reportError(f"Likely verse reference ({chapverse.group(0)}) in text at {state.reference}", 59.2)
                    verseflag = True
                chapverse = chapverse_re.search(t, chapverse.end())
    if embed := numberembed_re.search(t):
        reportError(f"Embedded number in word: {embed.group(0)} at {state.reference}", 60)
    elif not verseflag:
        if suffixed := numbersuffix_re.search(t):
            if not footnote:
                reportError(f"Invalid number suffix: {suffixed.group(0)} at {state.reference}", 60.2)
        if prefixed := numberprefix_re.search(t):
            if not footnote or (prefixed.group(0)[0] not in {':','-'}):
                reportError(f"Invalid number prefix: {prefixed.group(0)} at {state.reference}", 60.1)
    if unsegmented := unsegmented_re.search(t):
        if len(unsegmented.group(0)) > 4:
            reportError(f"Unsegmented number: {unsegmented.group(0)} at {state.reference}", 61.5)
    if fmt := numberformat_re.search(t):
        reportError(f"Space in number {fmt.group(0)} at {state.reference}", 61.6)
    elif leadzero := leadingzero_re.search(t):
        reportError(f"Invalid leading zero: {leadzero.group(0)} at {state.reference}", 61)

period_re = re.compile(r'[\s]*[\.,;:!\?]', re.UNICODE)  # detects phrase-ending punctuation standing alone or starting a phrase

# Performs checks on some text, at most a verse in length.
def takeText(t, footnote=False):
    global lastToken
    if not state.textOkay() and not isTextCarryingToken(lastToken):
        if t[0] == '\\':
            reportError("Uncommon or invalid marker near " + state.reference, 53)
        else:
            # print u"Missing verse marker before text: <" + t.encode('utf-8') + u"> around " + state.reference
            # reportError(u"Missing verse marker or extra text around " + state.reference + u": <" + t[0:10] + u'>.')
            reportError("Missing verse marker or extra text near " + state.reference, 54)
        if lastToken:
            reportError("  preceding Token was \\" + lastToken.getValue(), 0)
        else:
            reportError("  no preceding Token", 0)
    if state.textOkay() and state.verse == 0:
        reportError(f"Unmarked text before {state.reference + ':1'}", 76)
    if "<" in t and not ">" in t:
        if "<< HEAD" in t:
            reportError("Unresolved translation conflict near " + state.reference, 55)
        else:
            reportError("Angle bracket not closed at " + state.reference, 56)
    if "Conflict Parsing Error" in t:
        reportError("BTT Writer artifact in " + state.reference, 57)
    if not suppress[3] and not aligned_usfm:    # report punctuation issues
        reportPunctuation(t)
    if period := period_re.match(t):    # text starts with a period
        if len(t) <= period.end() + 1:
            reportError(f"Orphaned punctuation at {state.reference}", 58)
        else:
            reportError("Text begins with phrase-ending punctuation in " + state.reference, 58.1)
    if lastToken.isV() and not aligned_usfm:
        reportFootnotes(t)
    if not suppress[1]:
        reportNumbers(t, footnote)
    if not footnote:
        reportCaps(t)
        state.endSentence( sentences.endsSentence(t) )
    state.addText(t)
    addWords(t)

allpunc = ".,:;!?-\[\]{}()<>'\"“‘’”`*/"
quoteend_re = re.compile(r"[.,:;!?-\[\]{}()<>'\"“‘’”`*/]'$")
notnumberinfootnote_re = re.compile(r'[^\d:\-.,]')

def addWords(t):
    for item in t.split():
        word = item.strip(".,:;!?+-[]{}()<>\"“‘’”*/")
        if quoteend_re.search(word):
            word = word.rstrip(allpunc)
        if word:
            if not state.inFootnote() or notnumberinfootnote_re.search(word):
                (count, ref) = wordlist.get(word, (0, None))
                ref = state.reference if count == 0 else ""
                wordlist[word] = (count+1, ref)

# Returns true if token is part of a footnote
def isFootnote(token):
    return (token.getType().startswith("f") and token.getType() != "fig") or token.getType().startswith("rq")
    #return token.isF_S() or token.isF_E() or token.isFR() or token.isFT() or token.isFP() or token.isFE_S() or token.isFE_E()

# Returns true if token is part of a cross reference
def isCrossRef(token):
    return token.isX_S() or token.isX_E() or token.isXO() or token.isXT()

# Returns True if the specified verse reference is an optional verse.
# Pass previous=True to check the previous verse.
def isOptional(ref, previous=False):
    if previous:
        # Returns True if the specified reference immediately FOLLOWS a verse that does not appear in some manuscripts.
        # Does not handle optional passages, such as John 7:53-8:11, or Mark 16:9-20.
        return ref in { 'MAT 17:22', 'MAT 18:12', 'MAT 23:15', 'MRK 7:17', 'MRK 9:45', 'MRK 9:47',\
'MRK 11:27', 'MRK 15:29', 'LUK 17:37', 'LUK 23:18', 'JHN 5:5', 'ACT 8:38', 'ACT 15:35',\
'ACT 24:8', 'ACT 28:30', 'ROM 16:25' }
    else:
        # May not handle the optional John 7:53-8:11 passage
        return ref in { 'MAT 17:21', 'MAT 18:11', 'MAT 23:14', 'MRK 7:16', 'MRK 9:44', 'MRK 9:46',\
'MRK 16:9', 'MRK 16:10', 'MRK 16:11', 'MRK 16:12', 'MRK 16:13', 'MRK 16:14', 'MRK 16:15', 'MRK 16:16',\
'MRK 16:17', 'MRK 16:18', 'MRK 16:19', 'MRK 16:20',
'MRK 11:26', 'MRK 15:28', 'LUK 17:36', 'LUK 23:17', 'JHN 5:4', 'JHN 7:53', 'JHN 8:1', 'ACT 8:37', 'ACT 15:34',\
'ACT 24:7', 'ACT 28:29', 'ROM 16:24', 'REV 12:18' }

def isShortVerse(ref):
    return ref in { 'LEV 11:15', 'DEU 5:19', \
'JOB 3:2', 'JOB 9:1', 'JOB 12:1', 'JOB 16:1', 'JOB 19:1', 'JOB 21:1', 'JOB 27:1', 'JOB 29:1', 'LUK 20:30' }

def isPoetry(token):
    return token.isQ() or token.isQ1() or token.isQ2() or token.isQ3() or token.isQA() or \
           token.isQR() or token.isQC()

def isIntro(token):
    return token.is_is() or token.is_ip() or token.is_iot() or token.is_io() or token.is_im()

def isSpecialText(token):
    return token.isWJS() or token.isADDS() or token.isNDS() or token.isPNS() or token.isQTS() or token.is_k_s()

def isTextCarryingToken(token):
    return token.isB() or token.isM() or isSpecialText(token) or token.isD() or token.isSP() or \
           isFootnote(token) or isCrossRef(token) or isPoetry(token) or isIntro(token)

def isTitleToken(token):
    return token.isH() or token.isTOC1() or token.isTOC2() or token.isTOC3() or token.isMT() or token.is_imt()

# Returns True if the token value should be checked for Arabic numerals
def isNumericCandidate(token):
    return token.isTEXT() or isTitleToken(token) or token.isCL() or token.isCP() or token.isFT()

def take(token):
    global lastToken
    global usfm_version

    if not token.isTEXT():
        if not state.addMarker(token.type):
            reportError(f"Back to back markers of type {token.type} at {state.reference}", 62)
    else:
        takeText(token.value, state.inFootnote())

    if token.isID():
        takeID(token.value)
    elif token.isC():
        if not suppress[5]:
            verifyVerseCount()  # for the preceding chapter
        if not state.ID:
            reportError("Missing book ID: " + state.reference, 62.1)
            sys.exit(-1)
        if token.value == "1":
            verifyBookTitle()
        takeC(token.value)
    elif token.isCL():
        takeCL(token.value)
    elif token.isP() or token.isPI() or token.isPC() or token.isNB() or token.isM():
        takeP(token.type)
        if token.value:     # paragraph markers can be followed by text
            reportError("Unexpected: text returned as part of paragraph token." +  state.reference, 63)
            takeText(token.value)
    elif token.isV():
        takeV(token.value)
    elif isFootnote(token):
        takeFootnote(token)
    elif token.isS5():
        takeS5()
    elif token.isS() or token.isMR() or token.isMS() or token.isD() or token.isSP():
        takeSection(token.type)
    elif token.isQA():
        state.addAcrosticHeading()
    elif isPoetry(token):
        takeQ(token.type)
    elif token.isB():
        takeB()
    elif isTitleToken(token):
        takeTitle(token)
    elif token.isUSFM():    # non-standard USFM token but is used by UnfoldingWord software
        usfm_version = int(token.value[0])
    elif token.isUnknown():
        if token.value == "p":
            reportError("Orphaned paragraph marker after " + state.reference, 65)
        elif token.value == "v":
            reportError("Unnumbered verse after " + state.reference, 66)
        elif usfm_version == 2:
            reportError("Invalid USFM token (\\" + token.value + ") near " + state.reference, 67)

    if config['language_code'] in {"ur"} and isNumericCandidate(token) and re.search(r'[0-9]', token.value):
        reportError("Arabic numerals in footnote at " + state.reference, 68)

    lastToken = token

bad_chapter_re1 = re.compile(r'[^\n](\\c\s*\d+)', re.UNICODE)
bad_chapter_re2 = re.compile(r'(\\c[0-9]+)', re.UNICODE)
bad_chapter_re3 = re.compile(r'(\\c\s*\d+)[^\d\s]+[\n\r]', re.UNICODE)
bad_verse_re1 = re.compile(r'([^\n\r\s]\\v\s*\d+)', re.UNICODE)
bad_verse_re2 = re.compile(r'(\\v[0-9]+)', re.UNICODE)
bad_verse_re3 = re.compile(r'(\\v\s*[-0-9]+[^-\d\s])', re.UNICODE)

# Receives the text of an entire book as input.
# Reports bad patterns.
def verifyChapterAndVerseMarkers(text, path):
    for badactor in bad_chapter_re1.finditer(text):
        reportError("Missing newline before chapter marker: " + badactor.group(1) + " in " + path, 69)
    for badactor in bad_chapter_re2.finditer(text):
        reportError("Missing space before chapter number: " + badactor.group(0) + " in " + path, 70)
    for badactor in bad_chapter_re3.finditer(text):
        reportError("Missing space after chapter number: " + badactor.group(1) + " in " + path, 71)
    for badactor in bad_verse_re1.finditer(text):
        s = badactor.group(1)
        if s[0] < ' ' or s[0] > '~': # not printable ascii
            s = s[1:]
        reportError("Missing white space before verse marker: " + s + " in " + path, 72)
    for badactor in bad_verse_re2.finditer(text):
        reportError("Missing space before verse number: " + badactor.group(0) + " in " + path, 73)
    for badactor in bad_verse_re3.finditer(text):
        s = badactor.group(1)
#        if s[-1] < ' ' or s[-1] > '~': # not printable ascii
#            s = s[:-1]
        reportError("Missing space after verse number: " + s + " in " + path, 74)

def verifyParagraphCount():
    if state.nParagraphs / state.chapter <= 2.5 and state.nPoetry / state.chapter <= 15:
        reportError(f"Low paragraph count ({state.nParagraphs + state.nPoetry}) for {state.ID}", 73.5)

orphantext_re = re.compile(r'\n\n[^\\]', re.UNICODE)
embeddedquotes_re = re.compile(r"\w'\w")

# Receives the text of an entire book as input.
# Verifies things that are better done as a whole file.
# Can't report verse references because we haven't started to parse the book yet.
def verifyWholeFile(contents, path):
    verifyChapterAndVerseMarkers(contents, path)

    lines = contents.split('\n')
    orphans = orphantext_re.search(contents)
    if orphans:
        reportOrphans(lines, path)

    if not suppress[6]:
        nembedded = len(embeddedquotes_re.findall(contents))
        nsingle = contents.count("'") - nembedded
        ndouble = contents.count('"')
        if ndouble > 0:
            if nsingle == 0 or suppress[7]:
                reportError(f"Straight quotes in {shortname(path)}: {ndouble} doubles.", 75)
            else:
                reportError(f"Straight quotes in {shortname(path)}: {ndouble} doubles, {nsingle} singles not counting {nembedded} word-medial.", 75)
        elif nsingle > 0 and not suppress[7]:
            reportError(f"Straight quotes in {shortname(path)}: {nsingle} singles not counting {nembedded} word-medial.", 75)


conflict_re = re.compile(r'<+ HEAD', re.UNICODE)   # conflict resolution tag

def reportOrphans(lines, path):
    prevline = "xx"
    lineno = 0
    for line in lines:
        lineno += 1
        if not prevline and line and line[0] != '\\':
            if not conflict_re.match(line):
                reportError("Unmarked text at line " + str(lineno) + " in " + path, 76)
            # else:
                #  Will be reported later as an unresolved translation conflict
        prevline = line

wjwj_re = re.compile(r' \\wj +\\wj\*', flags=re.UNICODE)
backslasheol_re = re.compile(r'\\ *\n')

# Corresponding entry point in tx-manager code is verify_contents_quiet()
def verifyFile(path):
    global aligned_usfm
    input = io.open(path, "r", buffering=1, encoding="utf-8-sig")
    contents = input.read(-1)
    input.close()

    if wjwj_re.search(contents):
        reportError("Empty \\wj \\wj* pair(s) in " + shortname(path), 77)
    if backslasheol_re.search(contents):
        reportError("Stranded backslash(es) at end of line(s) in " + shortname(path), 78)
    if '\x00' in contents:
        reportError("Null bytes found in " + shortname(path), 79)
    aligned_usfm = ("lemma=" in contents or "x-occurrences" in contents)
    if aligned_usfm:
        contents = usfm_utils.unalign_usfm(contents)

    if len(contents) < 100:
        reportError("Incomplete file: " + shortname(path), 80)
    else:
        reportProgress(f"CHECKING {shortname(path)}...")
        sys.stdout.flush()
        tokens = parseUsfm.parseString(contents)    # Slow!
        verifyWholeFile(contents, shortname(path))  # placed after parseUsfm so that its error messages come after the long parsing time pause
        for token in tokens:
            take(token)
        if (usfm_version == 2 or aligned_usfm) and not state.toc3:
            reportError("No \\toc3 tag in " + shortname(path), 81)
        previousVerseCheck()       # checks last verse in the file
        verifyNotEmpty(path)
        if not suppress[5]:
            verifyVerseCount()      # for the last chapter
        verifyChapterCount()
        verifyFootnotes()
        verifyChapterTitles()
        verifyParagraphCount()
        state.addID("")
        sys.stderr.flush()

# Verifies all .usfm files under the specified folder.
def verifyDir(dir):
    dirpath = Path(dir)
    for path in dirpath.iterdir():
        if path.name[0] != '.':         # ignore hidden files
            if path.is_dir():
                # It's a directory, recurse into it
                verifyDir(path)
            elif path.is_file() and path.name[-3:].lower() == 'sfm':
                verifyFile(path)

def main(app=None):
    global config
    global suppress
    global language_code
    global gui

    gui = app
    config = configmanager.ToolsConfigManager().get_section('VerifyUSFM')   # configmanager version
    if config:
        source_dir = config['source_dir']
        for i in range(1, len(suppress)):
            suppress[i] = config.getboolean('suppress'+str(i), fallback = False)
        language_code = config['language_code']
        if language_code in {'diu','en','es','es-419','gl','ha','hr','id','kcn','kpj','nag','plt','pmy','pt-br','sw','tl','tpi'}:    # ASCII content
            suppress[9] = True
        if language_code in {'as','bn','gu','hi','kn','ml','mr','nag','ne','or','pa','ru','ta','te','zh'}:    # ASCII content
            suppress[9] = False
        global std_titles
        std_titles = [ config.get('standard_chapter_title', fallback = '') ]
        if std_titles == ['']:
            std_titles = []
        uv = config.get('usfm_version', fallback = "2")
        usfm_version = int(uv[0])

        global state
        state = State()
        global issues
        issues = dict()

        file = config['filename']    # configmanager version

        if file:
            path = os.path.join(source_dir, file)
            if os.path.isfile(path):
                verifyFile(path)
            else:
                reportError(f"No such file: {path}")
        else:
            verifyDir(source_dir)

        global issuesFile
        if issuesFile:
            reportIssues()
            issuesFile.close()
            issuesFile = None
        else:
            reportStatus("No issues to report.")
        dumpWords()
        reportStatus("\nDone.")
        sys.stdout.flush()
    if gui:
        gui.event_generate('<<ScriptEnd>>', when="tail")

if __name__ == "__main__":
    main()

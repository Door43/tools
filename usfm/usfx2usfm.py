# -*- coding: utf-8 -*-
# This script parses a single USFX files to generate a set of USFM text files.
# Uses xml.sax.

# Global variables
usfm_path = r'C:\DCS\Gallego\usfx\NT.xml'
target_dir = r'C:\DCS\Gallego\usfm.NT'
id_extra = "Reina-Valera 1909"

import xml.sax
import io
import re
import sys
import os
import usfm_verses

class UsfxErrorHandler(xml.sax.ErrorHandler):
    def error(e):
        print(e)
        sys.stderr.write("Error reported by parser")

    def warning(e):
        print(e)
        sys.stderr.write("Warning reported by parser")
    
class UsfxHandler(xml.sax.ContentHandler):
    # Implements ContentHandler.startDocument
    def startDocument(self):
        UsfxHandler.id = ""
        UsfxHandler.toclevel = ""
        UsfxHandler.sfm = ""
        UsfxHandler.lastchar = "."

    # Implements ContentHandler.startElement
    def startElement(self, name, attrs):
        UsfxHandler.name = name
        if name == "book":
            UsfxHandler.openOutput(self, attrs)
        elif name == "id" and getValue(attrs, 'id'):
            UsfxHandler.id = attrs['id']
        elif name == "toc":
            UsfxHandler.toclevel = attrs['level']
        elif name == "p":
            if getValue(attrs, 'sfm'):
                UsfxHandler.sfm = attrs['sfm']
            else:
                UsfxHandler.writeP(self)
        elif name == "c":
            UsfxHandler.chap = attrs['id']
        elif name == "v":
            UsfxHandler.verse = attrs['id']
            
    # Implements ContentHandler.endElement
    def endElement(self, name):
        if name == "book":
            UsfxHandler.output.close()
        elif name == "id":
            UsfxHandler.writeId(self)
        elif name == "h":
            UsfxHandler.writeH(self)
        elif name == "toc":
            UsfxHandler.writeToc(self)
        elif name == "p":
            if UsfxHandler.sfm:
                UsfxHandler.writeMt(self)
                UsfxHandler.sfm = ""
        elif name == "c":
            UsfxHandler.writeC(self)
        elif name == "v":
            UsfxHandler.writeV(self)
        else:
            if name not in {"w", "ve", "add", "usfx", "languageCode"}:
                sys.stdout.write("endElement(" + name + ": " + UsfxHandler.content + ") not processed.\n")

        UsfxHandler.content = ""

    # Implements ContentHandler.characters
    def characters(self, content):
        if content.strip():
            UsfxHandler.content = content.strip()
            if UsfxHandler.name in {"w","add","v"}:
                UsfxHandler.writeText(self)
            
    # Create and open the usfm file for the book specified in attrs.
    # Remember the book id.
    def openOutput(self, attrs):
        UsfxHandler.id = attrs["id"]
        if UsfxHandler.id:
            path = makeUsfmPath(UsfxHandler.id)
            UsfxHandler.output = io.open(path, "tw", encoding="utf-8", newline='\n')
            sys.stdout.write("Creating " + path + "\n")

    # Write the \id and \ide fields in the usfm file.
    def writeId(self):
        idfield = UsfxHandler.id
        if UsfxHandler.content:
            idfield += " " + UsfxHandler.content
        if id_extra:
            idfield += " - " + id_extra
        UsfxHandler.output.write("\\id " + idfield + "\n\\ide UTF-8")
        
    # Write the \h field in the usfm file.
    def writeH(self):
        if UsfxHandler.content:
            UsfxHandler.output.write("\n\\h " + UsfxHandler.content)
            
    def writeToc(self):
        if UsfxHandler.content and UsfxHandler.toclevel:
            UsfxHandler.output.write("\n\\toc" + UsfxHandler.toclevel + " " + UsfxHandler.content)
            UsfxHandler.toclevel = ""

    def writeMt(self):
        if UsfxHandler.content:
            UsfxHandler.output.write("\n\\mt " + UsfxHandler.content)

    def writeC(self):
        UsfxHandler.output.write("\n\\c " + UsfxHandler.chap)

    def writeP(self):
        UsfxHandler.output.write("\n\\p")

    def writeV(self):
        UsfxHandler.output.write("\n\\v " + UsfxHandler.verse)

    # Writes the current bit of text to the usfm file, with a space character inserted as needed.
    # When the xml.sax.handler sends back a word in two pieces (presumably due to buffering)
    # the logic of this function inserts an undesired space in the middle of that word.
    # Fix this, if the script becomes frequently used.
    # Interim workaround: run the script twice with a slightly modified input file, then diff
    # the two output files. The extra spaces are easily spotted and easily removed.
    def writeText(self):
        if text := UsfxHandler.content:
            if UsfxHandler.lastchar not in "(¿¡‘“" and text[0] not in ".),;:?!’”":
                text = ' ' + text
            UsfxHandler.output.write(text)
            UsfxHandler.lastchar = text[-1]

# Returns the value corresponding to the specified key in attrs
# attrs must be a list of (key,value) pairs)
def getValue(attrs, key):
    value = None
    for (k,v) in attrs.items():
        if k == key:
            value = v
            break
    return value

# Returns file name for usfm file in current folder
def makeUsfmPath(bookId):
    num = usfm_verses.verseCounts[bookId]['usfm_number']
    path = os.path.join(target_dir, num + '-' + bookId + '.usfm')
    return path

def convertFile(usfxpath):
    print("Converting: " + usfxpath)
    parser = xml.sax.make_parser()
    parser.setContentHandler(UsfxHandler())
    parser.setErrorHandler(UsfxErrorHandler())
    with io.open(usfxpath, "tr", encoding="utf-8-sig") as usfxfile:
        parser.parse(usfxfile)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] != 'hard-coded-path':
        usfm_path = sys.argv[1]

    if os.path.isfile(usfm_path):
        source_dir = os.path.dirname(usfm_path)
        convertFile(usfm_path)
        sys.stdout.write("Done.\n")
        sys.stdout.write("About once every 20 chapters this program may insert a space in the middle of a word. See UsfxHandler.writeText() comments for a workaround.\n")
    else:
        sys.stderr.write("Usage: python usfx2usfm.py <usfx-path>\n  Or hard code the path.\n")

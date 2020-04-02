# -*- coding: utf-8 -*-
# This Python 3 script cleans up a few kinds of markdown formatting problems in column 9
# of the TSV tN files. It is only a partial solution.
# When translators alter the number of hash marks, they break the Markdown heading conventions.
# For example, the header jumps from level 1 with level 4 with no level 2 and 3 in between.
# This program intends to eliminate the jumps in heading levels by applying some
# informed guessing as to what the levels should have been. The algorithm is not perfect.
# The goal is to reduce the Errors and Warnings generated by the Door43 page builds
# while restoring the heading levels closer to their intended order.
# Correct operation of the algorithm depends on the consistency of the translator in assigning
# heading levels.
#
# This script also removes leading spaces from the first markdown header in each row.
# Also removes double quotes that surround fields that should begin with just a markdown header.
# Adds space after markdown header hash marks, if missing.
#
# This script was written for TSV notes files.
# Backs up the files being modified.
# Outputs files of the same name in the same location.

import re       # regular expression module
import io
import os
import sys
import tsv

# Globals
max_files = 99     # How many files do you want to process
source_dir = r'E:\DCS\Bengali\TN\Stage 3'  # Where are the files located

nProcessed = 0
filename_re = re.compile(r'.*\.tsv$')


def shortname(longpath):
    shortname = longpath
    if source_dir in longpath:
        shortname = longpath[len(source_dir)+1:]
    return shortname

# Calculates and returns the new header level.
# Updates the truelevel list.
def shuffle(truelevel, nmarks, currlevel):
    newlevel = currlevel
    if nmarks > currlevel and truelevel[nmarks] > currlevel:
        newlevel = currlevel + 1
    elif truelevel[nmarks] < currlevel:
        newlevel = truelevel[nmarks]
    
    # Adjust the array
    while nmarks > 1 and truelevel[nmarks] > newlevel:
        truelevel[nmarks] = newlevel
        nmarks -= 1
    return newlevel    

header_re = re.compile(r'(#+) ', flags=re.UNICODE)

# Converts and returns a single line
def fixHeadingLevels(note):
    currlevel = 0
    truelevel = [0,1,2,3,4,5,6,7,8,9]
    header = header_re.search(note, 0)
    while header:
        nmarks = len(header.group(1))
        newlevel = shuffle(truelevel, nmarks, currlevel)
        if newlevel != nmarks:
            note = note[0:header.start()] + '#' * newlevel + note[header.end()-1:]
        currlevel = newlevel
        header = header_re.search(note, header.start() + newlevel + 1)
    return note


hash_re = re.compile(r'#([^# \n].*)')    # missing space after #

def fixSpacing(note):
    note = re.sub(r'\<br\> +#', "<br>#", note, 0)   # Remove spaces before markdown headers
    while sub := hash_re.search(note):              # Add space after # where missing
        note = note[0:sub.start()] + "# " + sub.group(1) + u'\n'
    return note

# The fix applies if column 3 has more than four characters, and the row has exactly 8 columns to start.
# The fix assumes that the first four characters are valid and should have been followed by a tab.
# This output row should have 9 columns and column 3 should have four characters.
# This fixes a common problem with Gujarati tN files.
def fixID(row):
    if len(row) == 8 and len(row[3]) > 4:
        col4 = row[3][4:]
        row.insert(4, col4)
        row[3] = row[3][0:4]
    return row
 
def cleanRow(row):
    i = 0
    while i < len(row):
        row[i] = row[i].strip('" ')     # remove leading and trailing spaces and quotes  
        i += 1
    if len(row) == 8 and len(row[3]) > 4: # A common problem in Gujarati tN, where the ID column is merged with the next column.
        row = fixID(row)
    if len(row) == 9:
        row[8] = row[8].replace("rc://en/", "rc://*/")
        row[8] = fixSpacing(row[8])     # fix spacing around hash marks
        row[8] = fixHeadingLevels(row[8])
    return row

def cleanFile(path):
    bakpath = path + ".orig"
    if not os.path.isfile(bakpath):
        os.rename(path, bakpath)

    data = tsv.tsvRead(bakpath)
    for row in data:
        row = cleanRow(row)
    tsv.tsvWrite(data, path)

# Recursive routine to convert all files under the specified folder
def cleanFolder(folder):
    global nProcessed
    global max_files
    if nProcessed >= max_files:
        return
    sys.stdout.write(shortname(folder) + '\n')
    for entry in os.listdir(folder):
        path = os.path.join(folder, entry)
        if os.path.isdir(path) and entry[0] != '.':
            cleanFolder(path)
        elif filename_re.match(entry):
            cleanFile(path)
            nProcessed += 1
        if nProcessed >= max_files:
            break

# Processes all .txt files in specified directory, one at a time
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] != 'hard-coded-path':
        source_dir = sys.argv[1]

    if source_dir and os.path.isdir(source_dir):
        cleanFolder(source_dir)
        sys.stdout.write("Done. Processed " + str(nProcessed) + " files.\n")
    elif filename_re.match(source_dir) and os.path.isfile(source_dir):
        path = source_dir
        source_dir = os.path.dirname(path)
        cleanFile(path)
        sys.stdout.write("Done. Processed 1 file.\n")
    else:
        sys.stderr.write("Usage: python tsv_cleanup.py <folder>\n  Use . for current folder.\n")

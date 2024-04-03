# -*- coding: utf-8 -*-
# Renames Paratext .SFM files to our standard naming convention.
# Changes the line endings to LF, if necessary.
# Set these config values in config.ini before running this script.
#   source_dir
#   target_dir

import configreader
import os
from pathlib import Path
import shutil
import sys
import usfm_verses

# Generates our standard name for usfm file
def makeUsfmFilename(bookId):
    num = usfm_verses.verseCounts[bookId]['usfm_number']
    return num + '-' + bookId + '.usfm'

def convert(source_dir, target_dir):
    count = 0
    sourcepath = Path(source_dir)
    for path in sourcepath.glob('*.SFM'):
        bookid = path.name[2:5]
        newpath = os.path.join(target_dir, makeUsfmFilename(bookid))
        shutil.copyfile(str(path), str(newpath))
        count += 1
    if count == 0:
        sys.stderr.write(f"There are no .SFM files in {source_dir}.\n")
    return count

if __name__ == "__main__":
    config = configreader.get_config(sys.argv, 'rename_paratext_files')
    if config:
        source_dir = config['source_dir']
        target_dir = config['target_dir']

        Path(target_dir).mkdir(exist_ok=True)
        count = convert(source_dir, target_dir)
        print(f"Copied and renamed {count} files.")

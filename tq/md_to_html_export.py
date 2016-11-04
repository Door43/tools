#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  Copyright (c) 2016 unfoldingWord
#  http://creativecommons.org/licenses/MIT/
#  See LICENSE file for details.
#
#  Contributors:
#  Richard Mahn <richard_mahn@wycliffeassociates.org>
#
#  Converts a tA repo into a PDF
#
#  Usage: md_to_pdf.py -i <directory of all ta repos> -o <directory where html flies will be placed>
#

import os
import re
import sys
import codecs
import argparse
import markdown2
import time
import inspect

from glob import glob
from bs4 import BeautifulSoup

reload(sys)
sys.setdefaultencoding('utf8')

# Let's include ../general_tools as a place we can import python files from
cmd_subfolder = os.path.realpath(os.path.abspath(os.path.join(os.path.split(inspect.getfile(inspect.currentframe()))[0],"../general_tools")))
if cmd_subfolder not in sys.path:
    sys.path.insert(0, cmd_subfolder)
import get_bible_book

tqRoot = ''


def fix_content(content):
    content = re.sub(ur'A\. (.*)', ur'A. \1\n</p>\n\n<p>\n<hr/>', content)
    content = re.sub(ur'(Q\?|A\.) ', ur'<b>\1</b> ', content)
    content = re.sub(ur'>([^>]+) 0*([0-9]+) Translation Questions', ur'>\1 \2', content)
    return content


def main(inpath, outpath, version, book):
    tqRoot = inpath

    license = markdown2.markdown_path(tqRoot+'/'+'LICENSE.md')

    content = ''
    books = get_bible_book.book_order
    for b in books:
        b = b.lower()
        if book == 'all' or b == book:
            content += u'<div id="{0}" class="book">'.format(b)
            files = sorted(glob(os.path.join(tqRoot, 'content', b, '*.md')))
            for f in files:
                chapter = os.path.splitext(os.path.basename(f))[0]
                c = markdown2.markdown_path(f)
                c = u'<div id="{0}-chapter-{1}" class="chapter">'.format(b, chapter) + c + u'</div>'
                c = re.sub('<p><strong><a href="\./">Back to .*?</a></strong></p>', '', c)
                content += c
            content += u'</div>'
    content = fix_content(content)

    cover = '''<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8" />
  <link href="https://fonts.googleapis.com/css?family=Noto+Sans" rel="stylesheet">
  <link href="style.css" rel="stylesheet">
</head>
<body>
  <div style="text-align:center;padding-top:200px" class="break" id="translationQuestions">
    <img src="https://unfoldingword.org/assets/img/icon-tq.png" width="120">
    <h1 class="h1">translationQuestions</h1>
    <h3 class="h3">v'''+version+'''</h3>
  </div>
</body>
</html>
'''

    license = '''<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8" />
  <link href="https://fonts.googleapis.com/css?family=Noto+Sans" rel="stylesheet">
  <link href="style.css" rel="stylesheet">
</head>
<body>
  <div class="break">
    <span class="h1">Copyrights & Licensing</span>
'''+license+'''
    <p>
      <strong>Date:</strong> '''+time.strftime("%Y-%m-%d")+'''<br/>
      <strong>Version:</strong> '''+version+'''
    </p>
  </div>
</body>
</html>
'''

    body = u'''<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8" />
  <link href="https://fonts.googleapis.com/css?family=Noto+Sans" rel="stylesheet">
  <link href="style.css" rel="stylesheet">
  </style>
</head>
<body>
'''+content+u'''
</body>
</html>
'''

    coverFile = outpath+'/cover.html'
    f = codecs.open(coverFile, 'w', encoding='utf-8')
    f.write(cover)
    f.close()

    licenseFile = outpath+'/license.html'
    f = codecs.open(licenseFile, 'w', encoding='utf-8')
    f.write(license)
    f.close()

    bodyFile = outpath+'/{0}.html'.format(book)
    f = codecs.open(bodyFile, 'w', encoding='utf-8')
    f.write(body)
    f.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-i', '--input', dest="inpath",
        help="Directory of the tQ repo to be compiled into html", required=True)
    parser.add_argument('-o', '--output', dest="outpath", default='.',
        required=False, help="Output path of the html file")
    parser.add_argument('-v', '--version', dest="version",
        required=True, help="Version of translationQuestions")
    parser.add_argument('-b', '--book', dest="book", default='all',
        required=False, help="Bible book")

    args = parser.parse_args(sys.argv[1:])

    main(args.inpath, args.outpath, args.version, args.book)

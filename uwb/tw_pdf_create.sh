#!/usr/bin/env bash
# -*- coding: utf8 -*-
#
#  tw_pdf_create.sh - generates a PDF for translationWords, including all words from KT and Other
#
#  Copyright (c) 2015 unfoldingWord
#  http://creativecommons.org/licenses/MIT/
#  See LICENSE file for details.
#
#  Contributors:
#  Jesse Griffin <jesse@distantshores.org>
#  Richard Mahn <richard_mahn@wycliffeassociates.org>
#  Caleb Maclennan <caleb@alerque.com>

# Set script to die if any of the subprocesses exit with a fail code. This
# catches a lot of scripting mistakes that might otherwise only show up as side
# effects later in the run (or at a later time). This is especially important so
# we know out temp dir situation is sane before we get started.
set -e

# ENVIRONMENT VARIABLES:
# DEBUG - true/false -  If true, will run "set -x"
# TOOLS_DIR - Directory of the "tools" repo where scripts and templates resides. Defaults to the parent directory of this script
# WORKING_DIR - Directory where all HTML files for tN, tQ, tW, tA are collected and then a full HTML file is made before conversion to PDF, defaults to a system suggested temp location
# OUTPUT_DIR - Directory to put the PDF, defaults to the current working directory
# BASE_URL - URL for the _export/xhtmlbody to get Dokuwiki content, defaults to 'https://door43.org/_export/xhtmlbody'
# NOTES_URL - URL for getting translationNotes, defaults to $BASE_URL/en/bible/notes
# TEMPLATE - Location of the TeX template for Pandoc, defaults to "$TOOLS_DIR/general_tools/pandoc_pdf_template.tex

# Instantiate a DEBUG flag (default to false). This enables output usful durring
# script development or later DEBUGging but not normally needed durring
# production runs. It can be used by calling the script with the var set, e.g.:
#     $ DEBUG=true ./uwb/pdf_create.sh <book>
: ${DEBUG:=false}

: ${TOOLS_DIR:=$(cd $(dirname "$0")/../ && pwd)}
: ${OUTPUT_DIR:=$(pwd)}
: ${TEMPLATE:=$TOOLS_DIR/general_tools/pandoc_pdf_template.tex}

# If running in DEBUG mode, output information about every command being run
$DEBUG && set -x

# Create a temorary diretory using the system default temp directory location
# in which we can stash any files we want in an isolated namespace. It is very
# important that this dir actually exist. The set -e option should always be used
# so that if the system doesn't let us create a temp directory we won't contintue.
if [[ -z "$WORKING_DIR" ]]; then
    WORKING_DIR=$(mktemp -d -t "ubw_pdf_create.XXXXXX")
    # If _not_ in DEBUG mode, _and_ we made our own temp directory, then
    # cleanup out temp files after every run. Running in DEBUG mode will skip
    # this so that the temp files can be inspected manually
    $DEBUG || trap 'popd; rm -rf "$WORKING_DIR"' EXIT SIGHUP SIGTERM
elif [[ ! -d "$WORKING_DIR" ]]; then
    mkdir -p "$WORKING_DIR"
fi

# Change to own own temp dir but note our current dir so we can get back to it
pushd $WORKING_DIR

if [ -z "$1" ];
then
    : ${LANGUAGE:='en'}
else
    LANGUAGE=$1
fi

: ${D43_BASE_DIR:=/var/www/vhosts/door43.org/httpdocs/data/gitrepo/pages}
: ${D43_BASE_URL:=https://door43.org/_export/xhtmlbody}

: ${CL_DIR:=$LANGUAGE/legal/license}
: ${TW_DIR:=$LANGUAGE/obe}

if [ ! -e $D43_BASE_DIR ];
then
    echo "The directory $D43_BASE_DIR does not exist. Can't continue. Exiting."
    exit 1;
fi

DATE=`date +"%Y-%m-%d"`

CL_FILE="${LANGUAGE}_tw_cl.html" # Copyrights & Licensing
KT_FILE="${LANGUAGE}_tw_kt.html" # Key Terms file
OTHER_FILE="${LANGUAGE}_tw_ot.html" # Other Terms file
HTML_FILE="${LANGUAGE}_tw_all.html" # Compilation of all above HTML files
PDF_FILE="$OUTPUT_DIR/tW_${LANGUAGE^^}_$DATE.pdf" # Outputted PDF file
LINKS_FILE="${LANGUAGE}_tw_links.sed" # SED commands for links
BAD_LINKS_FILE="${LANGUAGE}_tw_bad_links.txt"

generate_term_file () {
    dir=$1
    out_file=$2

    echo "GENERATING $out_file"

    rm -f $out_file
    touch $out_file

    find $dir -type f -name "*.txt" -print | awk -vFS=/ -vOFS=/ '{ print $NF,$0 }' |
        sort -u -t / | cut -f2- -d/ |
        while read f; do
            filename=$(basename $f)
            term=${filename%%.txt}
            dir="$TW_DIR/$(basename $(dirname $f))"

            mkdir -p "$dir" # creates the dir path in $WORKING_DIR

            # If the file doesn't exit or the file is older than (-ot) the Door43 repo one, fetch it
            if [ ! -e "$dir/$term.html" ] || [ "$dir/$term.html" -ot "$D43_BASE_DIR/$dir/$term.txt" ];
            then
                wget -U 'me' "$D43_BASE_URL/$dir/$term" -O "$dir/$term.html"
            fi

            grep -v '<strong>.*&gt;&gt;<\/a><\/strong>' "$dir/$term.html" |
                    grep -v ' href="\/tag\/' >> "$out_file"

            echo "<hr/>" >> "$out_file"

            linkname=$(head -3 "$dir/$term.html" | grep -o 'id=".*"' | cut -f 2 -d '=' | tr -d '"')
            echo "s@\"[^\"]*/$dir/$term\"@\"#$linkname\"@g" >> "$LINKS_FILE"
        done

    # Quick fix for getting rid of these Bible References lists in a table, removing table tags
    sed -i -e 's/^\s*<table class="ul">/<ul>/' "$out_file"
    sed -i -e 's/^\s*<tr>//' "$out_file"
    sed -i -e 's/^\s*<td class="page"><ul>\(.*\)<\/ul><\/td>/\1/' "$out_file"
    sed -i -e 's/^\s*<\/tr>//' "$out_file"
    sed -i -e 's/^\s*<\/table>/<\/ul>/' "$out_file"

    # increase all headers by one so that the headers we add when making the HTML_FILE are the only h1 headers
    sed -i -e 's/<\(\/\)\{0,1\}h3/<\1h4/g' "$out_file"
    sed -i -e 's/<\(\/\)\{0,1\}h2/<\1h3/g' "$out_file"
    sed -i -e 's/<\(\/\)\{0,1\}h1/<\1h2/g' "$out_file"
}

# ---- MAIN EXECUTION BEGINS HERE ----- #
    rm -f $CL_FILE $KT_FILE $OTHER_FILE $HTML_FILE $LINKS_FILE $BAD_LINKS_FILE # We start fresh, only files that remain are any files retrieved with wget

    touch "$LINKS_FILE"
    touch "$BAD_LINKS_FILE"

    # ----- START GENERATE CL PAGE ----- #
    echo "GENERATING $CL_FILE"

    mkdir -p "$CL_DIR"

    # If the file doesn't exist or is older than (-ot) the file in the Door43 repo, fetch the file
    if [ ! -e "$CL_DIR/uw.html" ] || [ "$CL_DIR/uw.html" -ot "$D43_BASE_DIR/$CL_DIR/uw.txt" ];
    then
        wget -U 'me' "$D43_BASE_URL/$CL_DIR/uw" -O "$CL_DIR/uw.html"
    fi

    cat "$CL_DIR/uw.html" > "$CL_FILE"

    # increase all headers by one so that the headers we add when making the HTML_FILE are the only h1 headers
    sed -i -e 's/<\(\/\)\{0,1\}h3/<\1h4/g' "$CL_FILE"
    sed -i -e 's/<\(\/\)\{0,1\}h2/<\1h3/g' "$CL_FILE"
    sed -i -e 's/<\(\/\)\{0,1\}h1/<\1h2/g' "$CL_FILE"
    # ----- END GENERATE CL PAGES ------- #

    if ! $COMBINED_LISTS;
    then
        # ----- GENERATE KT PAGES --------- #
        generate_term_file "$D43_BASE_DIR/$TW_DIR/kt" $KT_FILE
        # ----- EMD GENERATE KT PAGES ----- #

        # ----- GENERATE OTHER PAGES --------- #
        generate_term_file "$D43_BASE_DIR/$TW_DIR/other" $OTHER_FILE
        # ----- EMD GENERATE OTHER PAGES ----- #
    else
        generate_term_file "$D43_BASE_DIR/$TW_DIR/other $D43_BASE_DIR/$TW_DIR/kt" $OTHER_FILE
    fi

    # ----- GENERATE COMPLETE HTML PAGE ----------- #
    echo "GENERATING $HTML_FILE"

    echo '<h1>Copyrights & Licensing</h1>' >> $HTML_FILE
    cat $CL_FILE >> $HTML_FILE

    if ! $COMBINED_LISTS;
    then
        echo '<h1>Key Terms</h1>' >> $HTML_FILE
        cat $KT_FILE >> $HTML_FILE

        echo '<h1>Other Terms</h1>' >> $HTML_FILE
        cat $OTHER_FILE >> $HTML_FILE
     else
        echo '<h1>translationWords</h1>' >> $HTML_FILE
        cat $OTHER_FILE >> $HTML_FILE
     fi
    # ----- END GENERATE COMPLETE HTML PAGE --------#

    # ----- START LINK FIXES AND CLEANUP ----- #
    sed -i \
        -e 's/<\/span>/<\/span> /g' \
        -e 's/jpg[?a-zA-Z=;&0-9]*"/jpg"/g' \
        -e 's/ \(src\|href\)="\// \1="https:\/\/door43.org\//g' \
        $HTML_FILE

    # Link Fixes
    sed -i -f "$LINKS_FILE" "$HTML_FILE"
    # ----- END LINK FIXES AND CLEANUP ------- #

    # ----- START GENERATE PDF FILE ----- #
    echo "GENERATING $PDF_FILE";

    TITLE='translationWords'

    # Create PDF
    pandoc \
        -S \
        --latex-engine="xelatex" \
        --template="$TEMPLATE" \
        --toc \
        --toc-depth=2 \
        -V documentclass="scrartcl" \
        -V classoption="oneside" \
        -V geometry='hmargin=2cm' \
        -V geometry='vmargin=3cm' \
        -V title="$TITLE" \
        -V date="$DATE" \
        -V mainfont="Noto Serif" \
        -V sansfont="Noto Sans" \
        -o $PDF_FILE $HTML_FILE

    echo "PDF FILE: $PDF_FILE"
    echo "Done!"

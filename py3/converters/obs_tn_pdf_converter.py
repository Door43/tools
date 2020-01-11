#!/usr/bin/env python3
#
#  Copyright (c) 2019 unfoldingWord
#  http://creativecommons.org/licenses/MIT/
#  See LICENSE file for details.
#
#  Contributors:
#  Richard Mahn <rich.mahn@unfoldingword.org>

"""
This script generates the HTML and PDF OBS SN & SQ documents
"""
import os
import re
import markdown2
from glob import glob
from bs4 import BeautifulSoup
from .pdf_converter import PdfConverter, run_converter
from ..general_tools.file_utils import write_file, load_json_object, read_file

TN_TITLES_TO_IGNORE = {
    'en': ['A Bible story from',
           'Connecting Statement',
           'Connecting Statement:',
           'General Information',
           'General Note'
           ],
    'fr': ['Information générale',
           'Termes Importants',
           'Une histoire biblique tirée de',
           'Une histoire de la Bible tirée de',
           'Une histoire de la Bible à partir',
           'Une histoire de la Bible à partir de',
           'Mots de Traduction',
           'Nota geral',
           'Déclaration de connexion',
           'Cette histoire biblique est tirée',
           'Une histoire biblique tirée de:',
           'Informations générales',
           'Information Générale'
           ]
}


class ObsTnPdfConverter(PdfConverter):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._tw_cat = None

    @property
    def tw_cat(self):
        if not self._tw_cat:
            mapping = {
                'idol': 'falsegod',
                'witness': 'testimony',
                'newcovenant': 'covenant',
                'taxcollector': 'tax',
                'believer': 'believe'
            }
            tw_cat_file = os.path.join(self.converters_dir, 'tw_cat.json')
            self._tw_cat = load_json_object(tw_cat_file)
            for chapter in self._tw_cat['chapters']:
                self._tw_cat[chapter['id']] = {}
                for frame in chapter['frames']:
                    self._tw_cat[chapter['id']][frame['id']] = []
                    for item in frame['items']:
                        term = item['id']
                        category = None
                        for c in ['kt', 'names', 'other']:
                            if os.path.exists(os.path.join(self.resources['tw'].repo_dir, 'bible', c, f'{term}.md')):
                                category = c
                                break
                        if not category and term in mapping:
                            category = None
                            for c in ['kt', 'names', 'other']:
                                if os.path.exists(os.path.join(self.resources['tw'].repo_dir, 'bible', c,
                                                               f'{mapping[term]}.md')):
                                    category = c
                                    term = mapping[term]
                                    break
                        if category:
                            self._tw_cat[chapter['id']][frame['id']].append(
                                f'rc://{self.lang_code}/tw/dict/bible/{category}/{term}')
                        if not category or term != item['id']:
                            fix = None
                            if term != item['id']:
                                fix = term
                            source_rc = f'tw_cat.json {chapter["id"]}/{frame["id"]}'
                            self.add_bad_link(source_rc, item['id'], fix)
        return self._tw_cat

    def get_body_html(self):
        self.logger.info('Generating OBS TN html...')
        tn_html = self.get_obs_tn_html()
        ta_html = self.get_ta_html()
        tw_html = self.get_tw_html()
        body_html = '\n'.join([tn_html, tw_html, ta_html])
        return body_html

    def get_obs_tn_html(self):
        obs_tn_html = f'''
<section id="obs-sn">
    <div class="resource-title-page no-header">
        <img src="images/{self.resources['obs'].logo}.png" class="logo" alt="UTN">
        <h1 class="section-header">{self.simple_title}</h1>
    </div>
'''
        obs_tn_chapter_dirs = sorted(glob(os.path.join(self.main_resource.repo_dir, 'content', '*')))
        for obs_tn_chapter_dir in obs_tn_chapter_dirs:
            if os.path.isdir(obs_tn_chapter_dir):
                chapter_num = os.path.basename(obs_tn_chapter_dir)
                chapter_id = f'obs-tn-{chapter_num}'
                soup = BeautifulSoup(
                    markdown2.markdown_path(os.path.join(self.resources['obs'].repo_dir, 'content',
                                                         f'{chapter_num}.md')), 'html.parser')
                chapter_title = soup.h1.text
                obs_tn_html += f'''
    <article id="{chapter_id}">
        <h2 class="section-header">{chapter_title}</h2>
'''
                paragraphs = soup.find_all('p')
                frames = ['']  # 0 is empty for the intro/title note
                for paragraph_idx, p in enumerate(paragraphs):  # iterate over loop [above sections]
                    if paragraph_idx % 2:
                        frames.append(p.text)
                for frame_idx, frame_html in enumerate(frames):
                    frame_num = str(frame_idx).zfill(2)
                    frame_id = f'obs-tn-{chapter_num}-{frame_num}'
                    frame_title = f'{chapter_num}:{frame_num}'
                    notes_file = os.path.join(obs_tn_chapter_dir, f'{frame_num}.md')
                    notes_html = ''
                    if os.path.isfile(notes_file):
                        notes_html = markdown2.markdown_path(notes_file)
                        notes_html = self.increase_headers(notes_html, 3)
                    if not frame_html and not notes_html:
                        continue
                    if frame_html:
                        frame_html = re.sub(r'[\n\s]+', ' ', frame_html, flags=re.MULTILINE)
                        if notes_html:
                            phrases = self.get_phrases_to_highlight(notes_html, 'h4')
                            frame_html = self.highlight_text_with_phrases(frame_html, phrases, frame_title,
                                                                          TN_TITLES_TO_IGNORE[self.lang_code])
                    # Some OBS TN languages (e.g. French) do not have Translation Words in their TN article.
                    # We need to add them ourselves from the tw_cat file
                    if notes_html and '/tw/' not in notes_html and chapter_num in self.tw_cat and \
                            frame_num in self.tw_cat[chapter_num] and len(self.tw_cat[chapter_num][frame_num]):
                        notes_html += f'''
           <h3>{self.resources['tw'].simple_title}</h3>
           <ul>
'''
                        for rc in self.tw_cat[chapter_num][frame_num]:
                            notes_html += f'''
                <li>[[{rc}]]</li>
'''
                        notes_html += '''
            </ul>
'''
                    if frame_html:
                        frame_html = f'''
            <div id="{frame_id}-text" class="frame-text">
                {frame_html}
            </div>
'''
                    if notes_html:
                        notes_html = f'''
            <div id="{frame_id}-notes" class="frame-notes">
                {notes_html}
            </div>
'''
                    obs_tn_html += f'''
        <div id="{frame_id}">
            <h3>{frame_title}</h3>
            {frame_html}
            {notes_html}
        </div>
'''
                    if frame_idx < len(frames) - 1:
                        obs_tn_html += '<hr class="frame-divider"/>\n'
                    # HANDLE RC LINKS FOR FRAME
                    frame_rc = f'rc://{self.lang_code}/obs-tn/help/{chapter_num}/{frame_num}'
                    self.resource_data[frame_rc] = {
                        'rc': frame_rc,
                        'id': frame_id,
                        'link': f'#{frame_id}',
                        'title': frame_title
                    }
                    self.get_resource_data_from_rc_links(notes_html, frame_rc)
                obs_tn_html += '''
    </article>
'''
        obs_tn_html += '''
</section>
'''
        return obs_tn_html

    def get_ta_html(self):
        self.logger.info('Generating TA html...')
        ta_html = ''
        sorted_rcs = sorted(self.resource_data.keys(), key=lambda k: self.resource_data[k]['title'].lower())
        for rc in sorted_rcs:
            if '/ta/' not in rc:
                continue
            html = self.resource_data[rc]['text']
            if html:
                title = self.resource_data[rc]['title']
                alt_title = self.resource_data[rc]['alt_title']
                if 'question' in self.resource_data[rc] and self.resource_data[rc]['question']:
                    question_box = f'''
    <div class="top-box box">
        <div class="ta-question">
            {self.translate('this_page_answers_the_question')}: <em>{self.resource_data[rc]['question']}</em>
        </div>
    </div>
'''
                else:
                    question_box = ''
                if alt_title:
                    headers = f'''
        <h2 class="section-header hidden">{alt_title}</h2>
        <h2>{title}</h2>
'''
                else:
                    headers = f'''
        <h2 class="section-header">{title}</h2>
'''
                ta_html += f'''
    <article id="{self.resource_data[rc]['id']}">
        {headers}
        {question_box}
        {html}
        {self.get_go_back_to_html(rc)}
    </article>
'''
        if ta_html:
            ta_html = f'''
<section id="ta">
    <div class="resource-title-page">
        <h1 class="section-header">{self.resources['ta'].title}</h1>
    </div>
    {ta_html}
</section>
'''
        return ta_html

    def get_tw_html(self):
        self.logger.info('Generating TW html...')
        tw_html = ''
        sorted_rcs = sorted(self.resource_data.keys(), key=lambda k: self.resource_data[k]['title'].lower())
        for rc in sorted_rcs:
            if '/tw/' not in rc:
                continue
            html = self.resource_data[rc]['text']
            if html:
                html = self.increase_headers(html)
                title = self.resource_data[rc]['title']
                alt_title = self.resource_data[rc]['alt_title']
                if alt_title:
                    headers = f'''
        <h2 class="section-header hidden">{alt_title}</h2>
        <h2>{title}</h2>
'''
                else:
                    headers = f'''
        <h2 class="section-header">{title}</h2>
'''
                tw_html += f'''
    <article id="{self.resource_data[rc]['id']}">
        {headers}
        {html}
        {self.get_go_back_to_html(rc)}
    </article>
'''
        if tw_html:
            tw_html = f'''
<section id="tw">
    <div class="resource-title-page">
        <h1 class="section-header">{self.resources['tw'].title}</h1>
    </div>
    {tw_html}
</section>
'''
        return tw_html

    def has_tn_references(self, rc):
        if rc not in self.rc_references:
            return False
        for reference in self.rc_references[rc]:
            if '/obs-tn/' in reference:
                return True
        return False

    def get_go_back_to_html(self, rc):
        if not self.has_tn_references(rc):
            return ''
        references = []
        done = {}
        for reference in self.rc_references[rc]:
            if '/obs-tn/' in reference and reference not in done:
                parts = reference[5:].split('/')
                frame_id = f'obs-tn-{parts[3]}-{parts[4]}'
                frame_title = f'{parts[3]}:{parts[4]}'
                references.append(f'<a href="#{frame_id}">{frame_title}</a>')
                done[reference] = True
        if len(references):
            references_str = '; '.join(references)
            go_back_to_html = f'''
    <p class="go-back">
        (<b>{self.translate('go_back_to')}:</b> {references_str})
    </p>
'''
        return go_back_to_html

    def get_resource_data_from_rc_links(self, text, source_rc, save_text=True):
        rcs = re.findall(r'rc://[A-Z0-9/_\*-]+', text, flags=re.IGNORECASE | re.MULTILINE)
        for orig_rc in rcs:
            parts = orig_rc[5:].split('/')
            resource = parts[1]
            path = '/'.join(parts[3:])
            rc = 'rc://' + self.lang_code + '/' + '/'.join(parts[1:])

            if resource not in ['ta', 'tw']:
                continue

            if rc not in self.rc_references:
                self.rc_references[rc] = []
            if source_rc not in self.rc_references[rc]:
                self.rc_references[rc].append(source_rc)
            title = ''
            anchor_path = path.replace('/', '-')
            anchor_id = f'{resource}-{anchor_path}'
            link = f'#{anchor_id}'
            file_path = os.path.join(self.working_dir, f'{self.lang_code}_{resource}', f'{path}.md')
            if not os.path.isfile(file_path):
                file_path = os.path.join(self.working_dir, f'{self.lang_code}_{resource}', f'{path}/01.md')
            fix = None
            if not os.path.isfile(file_path):
                if resource == 'tw':
                    for category in ['kt', 'other', 'names']:
                        path2 = re.sub(r'^bible/([^/]+)/', rf'bible/{category}/', path.lower())
                        fix = f'rc://{self.lang_code}/tw/dict/{path2}'
                        anchor_path = path2.replace('/', '-')
                        anchor_id = f'{resource}-{anchor_path}'
                        link = f'#{anchor_id}'
                        file_path = os.path.join(self.working_dir, f'{self.lang_code}_{resource}', f'{path2}.md')
                        if os.path.isfile(file_path):
                            break
                elif resource == 'ta':
                    bad_names = {
                        'figs-abstractnoun': 'translate/figs-abstractnouns'
                    }
                    if parts[3] in bad_names:
                        path2 = bad_names[parts[3]]
                    else:
                        path2 = path
                    fix = f'rc://{self.lang_code}/ta/man/{path2}'
                    anchor_path = path2.replace('/', '-')
                    anchor_id = f'{resource}-{anchor_path}'
                    link = f'#{anchor_id}'
                    file_path = os.path.join(self.working_dir, f'{self.lang_code}_{resource}', f'{path2}/01.md')

            if os.path.isfile(file_path):
                if fix:
                    self.add_bad_link(source_rc, rc, fix)
                if rc not in self.resource_data or (save_text and not self.resource_data[rc]['text']):
                    resource_html = markdown2.markdown_path(file_path)
                    alt_title = None
                    question = None
                    if resource == 'ta':
                        title_file = os.path.join(os.path.dirname(file_path), 'title.md')
                        if os.path.isfile(title_file):
                            title = read_file(title_file)
                        else:
                            title = self.get_title_from_html(resource_html)
                            resource_html = re.sub(r'\s*\n*\s*<h\d>[^<]+</h\d>\s*\n*', r'', resource_html, 1,
                                                   flags=re.IGNORECASE | re.MULTILINE)  # removes the header
                        if len(title) > 70:
                            alt_title = ' '.join(title[:70].split(' ')[:-1]) + ' ...'
                        question_file = os.path.join(os.path.dirname(file_path), 'sub-title.md')
                        if os.path.isfile(question_file):
                            question = read_file(question_file)
                        if save_text:
                            resource_html = self.fix_ta_links(resource_html, path.split('/')[0])
                    elif resource == 'tw':
                        title = self.get_title_from_html(resource_html)
                        if len(title) > 70:
                            alt_title = ','.join(title[:70].split(',')[:-1]) + ', ...'
                        if save_text:
                            resource_html = re.sub(r'\s*\n*\s*<h\d>[^<]+</h\d>\s*\n*', r'', resource_html, 1,
                                                   flags=re.IGNORECASE | re.MULTILINE)  # removes the header
                            resource_html = re.sub(r'\n*\s*\(See [^\n]*\)\s*\n*', '\n\n', resource_html,
                                                   flags=re.IGNORECASE | re.MULTILINE)  # removes the See also line
                            resource_html = self.fix_tw_links(resource_html, path.split('/')[1])
                    self.resource_data[rc] = {
                        'rc': rc,
                        'link': link,
                        'id': anchor_id,
                        'title': title,
                        'alt_title': alt_title,
                        'question': question,
                        'text': resource_html if save_text else None,
                    }
                    self.get_resource_data_from_rc_links(resource_html, rc, False)
            else:
                self.add_bad_link(source_rc, rc)
        #### THE BELOW IS TO FIND ALL RELATIVE REFERENCES (../<term> and ./<term) AS ERRORS,
        #### BUT I BELIEVE THIS IS ALLOWED - RHM
        # rcs = re.findall(r'(?<=\()\.+/[^\)]+(?=\))', text, flags=re.IGNORECASE | re.MULTILINE)
        # for rc in rcs:
        #     fix = re.sub(r'(\.\./)+(kt|names|other)/([^)]+?)(\.md)*', rf'rc://{self.lang_code}/tw/dict/bible/\2/\3', rc,
        #                  flags=re.IGNORECASE)
        #     if fix != rc:
        #         self.add_bad_link(source_rc, rc, fix)
        #     else:
        #         self.add_bad_link(source_rc, rc)
        # rcs = re.findall(r'(?<=\()\.[^ \)]+(?=\))', text, flags=re.IGNORECASE | re.MULTILINE)
        # for rc in rcs:
        #     fix = None
        #     if '/kt/' in rc or '/names/' in rc or '/other/' in rc:
        #         new_rc = re.sub(r'(\.\./)+(kt|names|other)/([^)]+?)(\.md)*',
        #                         rf'rc://{self.lang_code}/tw/dict/bible/\2/\3', rc, flags=re.IGNORECASE)
        #         if new_rc != rc:
        #             fix = new_rc
        #     self.add_bad_link(source_rc, rc, fix)

    def fix_tw_links(self, text, group):
        text = re.sub(r'href="\.\./([^/)]+?)(\.md)*"', rf'href="rc://{self.lang_code}/tw/dict/bible/{group}/\1"', text,
                      flags=re.IGNORECASE | re.MULTILINE)
        text = re.sub(r'href="\.\./([^)]+?)(\.md)*"', rf'href="rc://{self.lang_code}/tw/dict/bible/\1"', text,
                      flags=re.IGNORECASE | re.MULTILINE)
        text = re.sub(r'(\(|\[\[)(\.\./)*(kt|names|other)/([^)]+?)(\.md)*(\)|\]\])(?!\[)',
                      rf'[[rc://{self.lang_code}/tw/dict/bible/\3/\4]]', text,
                      flags=re.IGNORECASE | re.MULTILINE)
        return text

    def fix_ta_links(self, text, manual):
        text = re.sub(r'href="\.\./([^/"]+)/01\.md"', rf'href="rc://{self.lang_code}/ta/man/{manual}/\1"', text,
                      flags=re.IGNORECASE | re.MULTILINE)
        text = re.sub(r'href="\.\./\.\./([^/"]+)/([^/"]+)/01\.md"', rf'href="rc://{self.lang_code}/ta/man/\1/\2"', text,
                      flags=re.IGNORECASE | re.MULTILINE)
        text = re.sub(r'href="([^# :/"]+)"', rf'href="rc://{self.lang_code}/ta/man/{manual}/\1"', text,
                      flags=re.IGNORECASE | re.MULTILINE)
        return text

    def save_bad_links_html(self):
        bad_links = "BAD LINKS:\n"
        for source_rc in sorted(self.bad_links.keys()):
            for rc in sorted(self.bad_links[source_rc].keys()):
                source = source_rc[5:].split('/')
                parts = rc[5:].split('/')
                if source[1] == 'obs-tn':
                    if parts[1] == 'tw':
                        line = '  tW'
                    else:
                        line = '  tN'
                    line += f' {source[3].upper()} {source[4]}:{source[5]}'
                else:
                    line = f'  {source_rc}'
                line += f': BAD RC - `{rc}`'
                if self.bad_links[source_rc][rc]:
                    line += f' - change to `{self.bad_links[source_rc][rc]}`'
                bad_links += f'{line}\n'
        save_file = os.path.join(self.output_dir, f'{self.file_id}_bad_links.txt')
        write_file(save_file, bad_links)
        self.logger.info(f'BAD LINKS file can be found at {save_file}')

    def save_bad_notes(self):
        bad_notes = '<!DOCTYPE html><html lang="en-US"><head data-suburl=""><title>NON-MATCHING NOTES</title><meta charset="utf-8"></head><body><p>NON-MATCHING NOTES (i.e. not found in the frame text as written):</p><ul>'
        for cf in sorted(self.bad_notes.keys()):
            bad_notes += '<li><a href="{0}_html/{0}.html#obs-tn-{1}" title="See in the OBS tN Docs (HTML)" target="obs-tn-html">{1}</a><a href="https://git.door43.org/{6}/{2}_obs-tn/src/branch/{7}/content/{3}/{4}.md" style="text-decoration:none" target="obs-tn-git"><img src="http://www.myiconfinder.com/uploads/iconsets/16-16-65222a067a7152473c9cc51c05b85695-note.png" title="See OBS UTN note on DCS"></a><a href="https://git.door43.org/{6}/{2}_obs/src/branch/master/content/{3}.md" style="text-decoration:none" target="obs-git"><img src="https://cdn3.iconfinder.com/data/icons/linecons-free-vector-icons-pack/32/photo-16.png" title="See OBS story on DCS"></a>:<br/><i>{5}</i><br/><ul>'.format(
                self.file_id, cf, self.lang_code, cf.split('-')[0], cf.split('-')[1], self.bad_notes[cf]['text'],
                self.owner, DEFAULT_TAG)
            for note in self.bad_notes[cf]['notes']:
                for key in note.keys():
                    if note[key]:
                        bad_notes += f'<li><b><i>{key}</i></b><br/>{note[key]} (QUOTE ISSUE)</li>'
                    else:
                        bad_notes += f'<li><b><i>{key}</i></b></li>'
            bad_notes += '</ul></li>'
        bad_notes += "</u></body></html>"
        save_file = os.path.join(self.output_dir, f'{self.file_id}_bad_notes.html')
        write_file(save_file, bad_notes)
        self.logger.info(f'BAD NOTES file can be found at {save_file}')


if __name__ == '__main__':
    run_converter(['obs-tn', 'obs', 'ta', 'tw'], ObsTnPdfConverter)
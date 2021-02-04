import argparse
import json
import os
import random
from sys import exit
from typing import Optional

import requests

# CDN where the Book API is hosted.
BOOK_CDN = 'https://ereader-books-prod.chegg.com'

# Template HTML page for each section of the book.
SECTION_TEMPLATE =\
'''<!DOCTYPE html>
<html>
<meta charset="UTF-8">
<head>
  <title>{title}</title>
</head>
<body>
<div class="page hw_page hw_background">
{text}
</div>
</body>
</html>
'''

EXPORT_DIRECTORY = 'export'
IMAGE_DIRECTORY = f'{EXPORT_DIRECTORY}/images'

USER_AGENT_POOL = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.141 Safari/537.36'
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:84.0) Gecko/20100101 Firefox/84.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.2 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.141 Safari/537.36 Edg/87.0.664.75'
]


class ETextbookFetcher:
    def __init__(self, session, book_id, isbn):
        self.session: requests.Session = session
        self.id: str = book_id
        self.isbn: str = isbn
        self.base_url: str = f'{BOOK_CDN}/{isbn[-3:]}/{isbn}/{book_id}'

    def fetch_metadata(self) -> Optional[dict]:
        response = self.session.get(f'{self.base_url}/metadata.json')
        if not response:
            print(f'Fetching metadata error: {response.status_code} {response.reason}')
            return None
        return response.json()

    def fetch_toc(self) -> Optional[dict]:
        response = self.session.get(f'{self.base_url}/toc.json')
        if not response:
            print(f'Fetching TOC error: {response.status_code} {response.reason}')
            return None
        return response.json()

    def fetch_section(self, section: int, title='', download_assets=True) -> Optional[str]:
        response = self.session.get(f'{self.base_url}/sections/{section}/content')
        if not response:
            print(f'Fetching section error: {response.status_code} {response.reason}')
            return None

        text = response.text

        if download_assets:
            response = self.session.get(f'{self.base_url}/sections/{section}/metadata.json')
            if not response:
                print(f'Could not fetch metadata for section: {response.status_code} {response.reason}')
                return text

            metadata = response.json()

            for asset in metadata['assets']:
                if asset['type'] == 'image':
                    path = asset['path']
                    filename = path.rsplit('/')[-1]

                    # Relative to the HTML file.
                    new_path = f'./images/{filename}'

                    # Actual export path.
                    export_path = f'{IMAGE_DIRECTORY}/{filename}'

                    # Reroute the image href in the HTML.
                    text = text.replace(path, new_path)

                    if os.path.exists(export_path):
                        print(f'Skipping {filename}: already downloaded')
                        continue

                    with open(export_path, 'wb+') as f_asset:
                        print(f'Downloading {path}...')
                        f_asset.write(self.session.get(path).content)

        text = SECTION_TEMPLATE.format(title=title, text=text)
        return text


def initiate_session(user_agent=None):
    session = requests.Session()

    if user_agent is None:
        print('Randomly selecting a User-Agent.')

        user_agent = random.choice(USER_AGENT_POOL)

    print(f'Using User-Agent: {user_agent}')

    session.cookies.set('User-Agent', user_agent)

    with open('cookies.json', 'r') as cookies_f:
        cookies = json.load(cookies_f)

    for k, v in cookies.items():
        session.cookies.set(k, v)

    return session


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('isbn', help='ISBN number of book', type=str)
    parser.add_argument('book_id', help='UUID of the book', type=str)
    parser.add_argument('-s', '--skip-downloaded', help='Skip sections that are already downloaded',
                        action='store_true')
    parser.add_argument('-d', '--output-directory', help='The directory that will contain the exported book assets.',
                        required=False, type=str)
    parser.add_argument('-u', '--user-agent', help='Provide a user agent to use rather than a randomly selected one.',
                        required=False, type=str)
    args = parser.parse_args()

    ISBN = args.isbn
    BOOK_ID = args.book_id
    SESSION = initiate_session(args.user_agent)

    SKIP_DOWNLOADED = args.skip_downloaded

    if args.output_directory is not None:
        EXPORT_DIRECTORY = args.output_directory
        IMAGE_DIRECTORY = f'{EXPORT_DIRECTORY}/images'

    print('Book info:')
    print('\tISBN:', ISBN)
    print('\tBOOK_ID:', BOOK_ID)

    # Make necessary directories.
    if not os.path.exists(EXPORT_DIRECTORY):
        os.makedirs(EXPORT_DIRECTORY)

    if not os.path.exists(IMAGE_DIRECTORY):
        os.makedirs(IMAGE_DIRECTORY)

    book = ETextbookFetcher(SESSION, BOOK_ID, ISBN)
    book_metadata = book.fetch_metadata()

    if book_metadata is None:
        exit('Failed to fetch book metadata. Exiting...')

    length = book_metadata['length']

    toc = book.fetch_toc()

    if toc is None:
        exit('Failed to fetch book table of contents. Exiting...')

    toc = toc['toc']['tocItems']

    sections = {}

    for item in toc:
        section_index = item['sectionIndex']

        if section_index not in sections:
            sections[section_index] = item
        elif item['depth'] == 1:
            # Ensure we get only top level sections so we do not have redundant HTML files.
            sections[section_index] = item

    # Create the actual filenames of the sections.
    section_filenames = [(sections[i]['filename'], f'section_{i}.html') for i in sections]

    print(f'Total sections: {length}')

    for section in sections:
        export_filename = f'{EXPORT_DIRECTORY}/section_{section}.html'

        if SKIP_DOWNLOADED and os.path.exists(export_filename):
            print(f'Skipping Section {section}: already downloaded')
            continue

        print(f'Fetching Section {section}...')

        section_title = sections[section]['title']
        section_text = book.fetch_section(section, title=section_title)

        if section_text is None:
            print(f'Could not fetch section {section}....')
            continue

        # Replace any references to the old filenames.
        for old_fn, new_fn in section_filenames:
            section_text = section_text.replace(old_fn, new_fn)

        print(f'Exporting Section {section}...')

        with open(export_filename, 'wb+') as f:
            section_text = section_text.encode('ascii', 'xmlcharrefreplace')
            f.write(section_text)

    print('Done.')

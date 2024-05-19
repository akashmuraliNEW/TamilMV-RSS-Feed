import requests
from bs4 import BeautifulSoup
import concurrent.futures
from xml.etree import ElementTree as ET
from datetime import datetime

class Scraper:
    def __init__(self):
        self.all_links = []
        self.titles = set()  # Use set for faster lookups
        self.url = 'https://www.1tamilmv.eu/'
        self.session = requests.Session()  # Create a session for connection pooling

    def get_links(self, url):
        response = self.session.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        # Refine selectors to target relevant elements based on website structure
        a_tags = soup.find_all('a', href=lambda href: href and 'attachment.php' in href)
        return a_tags

    def scrape(self, links):
        with concurrent.futures.ProcessPoolExecutor() as executor:
            results = executor.map(self.get_links, links)
            for result in results:
                for a in result:
                    yield a.text, a['href']

    def build_xml(self, channel):
        now = datetime.now()
        for title, link in self.all_links:
            if title not in self.titles:
                self.titles.add(title)
                item = ET.SubElement(channel, 'item')
                ET.SubElement(item, 'title').text = title
                ET.SubElement(item, 'link').text = link
                ET.SubElement(item, 'pubDate').text = now.isoformat('T')

    def begin(self):
        print('Feed generation started')
        rss = ET.Element('rss', version='2.0')
        channel = ET.SubElement(rss, 'channel')
        ET.SubElement(channel, 'title').text = 'TamilMV RSS Feed'
        ET.SubElement(channel, 'description').text = 'Share and support'
        ET.SubElement(channel, 'link').text = 'https://instagram.com/mr.anonymous.wiz'

        response = self.session.get(self.url)
        content = response.content
        soup = BeautifulSoup(content, 'html.parser')

        # Refine selectors based on website structure
        links = [a['href'] for p in soup.find_all('p', style='font-size: 13.1px;') for a in p.find_all('a', href=True)]
        filtered_links = [link for link in links if 'index.php?/forums/topic/' in link]

        self.all_links = list(self.scrape(filtered_links))

        self.build_xml(channel)

        tree = ET.ElementTree(rss)
        tree.write('tamilmvRSS.xml', encoding='utf-8', xml_declaration=True)
        print('Base feed finished')

    def job(self):
        # ... (rest of the job function remains mostly unchanged)

# ... (remaining code for run_schedule, run, and setup_routes functions largely unchanged)

if __name__ == '__main__':
    scraper = Scraper()
    scraper.run()
    Thread(target=scraper.run_schedule).start()
        

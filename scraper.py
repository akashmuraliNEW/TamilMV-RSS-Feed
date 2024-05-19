import requests
from bs4 import BeautifulSoup
import torrent_parser as tp
import xml.etree.ElementTree as ET
from datetime import datetime
import concurrent.futures
import pickle
from flask import Flask, send_file, Response
import os
from threading import Thread
import logging

logging.basicConfig(level=logging.INFO)

class Scraper:
    def __init__(self):
        self.all_links = []
        self.titles = []
        self.url = os.getenv('SCRAPER_URL', 'https://www.1tamilmv.eu/')
        Thread(target=self.begin).start()
        self.app = Flask(__name__)
        self.port = int(os.environ.get("PORT", 8000))
        self.setup_routes()

    def save_list_to_file(self, file_name='rssList.txt'):
        try:
            with open(file_name, 'wb') as f:
                pickle.dump(self.all_links, f)
            logging.info("List saved to file successfully.")
        except Exception as e:
            logging.error(f"Error saving list to file: {e}")

    def load_list_from_file(self, file_name='rssList.txt'):
        try:
            with open(file_name, 'rb') as f:
                self.all_links = pickle.load(f)
            logging.info("List loaded from file successfully.")
        except Exception as e:
            logging.error(f"Error loading list from file: {e}")

    def get_links(self, url):
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        a_tags = soup.find_all('a', href=lambda href: href and 'attachment.php' in href)
        return a_tags

    def get_torrent_size(self, torrent_file_path):
        data = tp.parse_torrent_file(torrent_file_path)
        if 'files' in data['info']:
            size = sum(file['length'] for file in data['info']['files'])
        else:
            size = data['info']['length']
        return size

    def scrape(self, links):
        with concurrent.futures.ThreadPoolExecutor() as executor:
            # Using list comprehension for efficient execution
            results = list(executor.map(self.get_links, links[:30]))
            for result in results:
                for a in result:
                    yield a.text, a['href']

    def build_xml(self, channel):
        now = datetime.now()
        for x in self.all_links:
            item = ET.SubElement(channel, 'item')
            ET.SubElement(item, 'title').text = x[0]
            ET.SubElement(item, 'link').text = x[1]
            ET.SubElement(item, 'pubDate').text = now.isoformat('T')

    def begin(self):
        if os.path.exists('rssList.txt'):
            self.load_list_from_file()
            logging.info("rssList.txt loaded")
            return
        logging.info('Feed generation started')
        rss = ET.Element('rss', version='2.0')
        channel = ET.SubElement(rss, 'channel')
        ET.SubElement(channel, 'title').text = '1Tamilmv Rss feed'
        ET.SubElement(channel, 'description').text = 'Share and support'
        ET.SubElement(channel, 'link').text = 'https:/t.me/Tanujairam'
        response = requests.get(self.url)
        content = response.content
        soup = BeautifulSoup(content, 'html.parser')
        paragraphs = soup.find_all('p', style='font-size: 13.1px;')
        links = [a['href'] for p in paragraphs for a in p.find_all('a', href=True)]
        filtered_links = [link for link in links if 'index.php?/forums/topic/' in link]
        self.all_links = list(self.scrape(filtered_links))
        self.titles = [link[0] for link in self.all_links]
        self.save_list_to_file()
        self.build_xml(channel)
        tree = ET.ElementTree(rss)
        tree.write('tamilmvRSS.xml', encoding='utf-8', xml_declaration=True)
        logging.info('Base feed finished')

    def job(self):
        if not self.all_links and os.path.exists('rssList.txt'):
            self.load_list_from_file()
        logging.info('Fetching Started')
        response = requests.get(self.url)
        content = response.content
        soup = BeautifulSoup(content, 'html.parser')
        paragraphs = soup.find_all('p', style='font-size: 13.1px;')
        links = [a['href'] for p in paragraphs for a in p.find_all('a', href=True)]
        filtered_links = [link for link in links if 'index.php?/forums/topic/' in link]
        scraped = list(self.scrape(filtered_links))
        new_links = [link for link in scraped if link[0] not in self.titles]
        self.all_links = new_links + self.all_links
        if new_links:
            self.save_list_to_file()
            tree = ET.ElementTree()
            tree.parse('tamilmvRSS.xml')
            root = tree.getroot()
            channel = root.find('channel')
            now = datetime.now().isoformat()
            for item_data in reversed(new_links):
                item = ET.Element('item')
                ET.SubElement(item, 'title').text = item_data[0]
                ET.SubElement(item, 'link').text = item_data[1]
                ET.SubElement(item, 'pubDate').text = now
                channel.insert(3, item)
            tree.write('tamilmvRSS.xml', encoding='utf-8', xml_declaration=True)
            logging.info('New items added to feed')

    def run_schedule(self):
        while True:
            try:
                self.job()
            except Exception as e:
                logging.error(f"Error during scheduled job: {e}")
            sleep(1500)

    def run(self):
        logging.info(f"Server is running on port {self.port}")
        self.app.run(host='0.0.0.0', port=self.port)

    def setup_routes(self):
        @self.app.route('/')
        def serve_rss():
            return send_file('tamilmvRSS.xml')

        @self.app.route('/status')
        def start():
            return Response("Server is running", status=200)

if __name__ == '__main__':
    scraper = Scraper()
    scraper.run()
    Thread(target=scraper.run_schedule).start()

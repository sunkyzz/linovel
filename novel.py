import threading
import time
from abc import ABC, abstractmethod, abstractstaticmethod

import requests
from bs4 import BeautifulSoup


class AbstractNovel(ABC):
    """
    abstract novel class

    Attributes:
        url: The novel url
        single_thread: A bool represent whether use single thread grab novel information
        volume_name: A string represent the volume name
        volume_number: A string represent the volume number
        book_name: A string represent the book name
        author: A string represent the author
        illustrator: A string represent the illustrator
        introduction: A string represent the introduction
        chapters: A list represent the chapter
        cover_url: A string represent the cover_url
        date: A string represent the date the book last updated (As specified in ISO 8601)
        novel_information: A list contains dict which represent the novel information
    """

    _TIMEOUT = 20
    _RETRIES = 6
    _REQUEST_INTERVAL = 1.5  # seconds between requests
    _RATE_LIMIT_WAIT = 15  # base wait on HTTP 429
    _THROTTLE_LOCK = threading.Lock()
    _last_request_time = 0.0
    _HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:19.0) Gecko/20100101 Firefox/19.0'}

    def __init__(self, url, single_thread=False):
        self.url = url
        self.single_thread = single_thread
        self.volume_name = ''
        self.volume_number = ''
        self.author = ''
        self.illustrator = ''
        self.introduction = ''
        self.chapters = []
        self.cover_url = ''
        self.date = ''
        self.novel_information = []

    def __str__(self):
        return '{}:{}'.format(self.__name__, self.url)

    @abstractstaticmethod
    def check_url(url):
        """check whether the url match this website"""
        pass

    def parse_page(self, url, encoding=''):
        """
        parse page with BeautifulSoup

        Args:
            url: A string represent the url to be parsed
            encoding: A string represent the encoding of the html

        Return:
            A BeatifulSoup element
        """
        last_error = None
        for attempt in range(self._RETRIES):
            try:
                self._throttle()
                r = requests.get(url, headers=self._HEADERS, timeout=self._TIMEOUT)
                if r.status_code == 429:
                    wait = int(r.headers.get('Retry-After') or 0) or self._RATE_LIMIT_WAIT * (attempt + 1)
                    print('Rate limited (429) on {}, waiting {}s'.format(url, wait))
                    time.sleep(wait)
                    last_error = requests.HTTPError('429 Too Many Requests')
                    continue
                r.raise_for_status()
                r.encoding = 'utf-8' if not encoding else encoding
                return BeautifulSoup(r.text, 'lxml')
            except requests.RequestException as e:
                last_error = e
                print('Retry {}/{} for {}: {}'.format(attempt + 1, self._RETRIES, url, e))
                time.sleep(2 * (attempt + 1))
        raise RuntimeError('Failed to fetch {} after {} attempts: {}'.format(url, self._RETRIES, last_error))

    def _throttle(self):
        """keep a minimum interval between requests to avoid 429 from the server"""
        with self._THROTTLE_LOCK:
            now = time.monotonic()
            wait = AbstractNovel._last_request_time + self._REQUEST_INTERVAL - now
            if wait > 0:
                time.sleep(wait)
            AbstractNovel._last_request_time = time.monotonic()

    @abstractmethod
    def extract_novel_information(self):
        """extract novel information"""
        pass

    @abstractmethod
    def get_novel_information(self):
        """
        return the novel information

        Return:
            A list contains dict, dict usually has these information: volume_name, volume_number, book_name,
            author, illustrator, introduction, chapters, cover_url, date, source
        """
        pass

"""	Module for parsing XML format RSS feeds.
	
    <function 'rss_arg_parser'> creates <class 'ArgumentParser' object with following arguments: 
    url	, --version, --json, --date, --source, --verbose, --limit, --pdf, --html, --log
	
	<class 'Tree'> with methods for fetching and parsing XML document from provided url, caching news in database, converting result to json, html, pdf format.

    <class 'FeedParserException'> custom exception class for exception handling.

    <function 'logging_basicConfig'> for setting logging level for this module.

    """


import argparse
import os
import logging
import sys
import sqlite3
from urllib.request import _UrlopenRet
import xml.etree.ElementTree as ET




def rss_arg_parser():
	"""	Creates custom parser with following arguments: 
	\nurl					URL to XML format RSS feed
	\n--version			print version info
	\n--json				print result as JSON in stdout
	\n--date				outputs articles from specified date
	\n--source			outputs articles from specified source
	\n--verbose			output verbose status messages
	\n--limit				limit news topics, if provided
	\n--pdf				export result as PDF to provided destination (default=cwd)
	\n--html				export result as HTML to provided destination (default=cwd)
			"""
	parser = argparse.ArgumentParser(description='tool for parsing RSS feeds')
	parser.add_argument('url', metavar='URL', nargs='?', help='URL to XML format RSS feed')
	parser.add_argument('--version', action='store_true', help='print version info')
	parser.add_argument('--json', action='store_true', help='print result as JSON in stdout')
	parser.add_argument('--log', metavar='FILEPATH', type=str, default=None, help='sets logging level to logging.DEBUG')
	parser.add_argument('--date', type=str, nargs='?', default=None, help='outputs articles from specified date')
	parser.add_argument('--source', type=str, default=None, help='outputs articles from specified source')
	parser.add_argument('--verbose', action='store_true', help='output verbose status messages')
	parser.add_argument('--limit', help='limit news topics, if provided', type=int, nargs='?', default=-1, const=5)
	parser.add_argument('--pdf', metavar='FILEPATH', type=str, const=os.path.join(os.getcwd(), 'data/', 'cached_news.pdf'), nargs='?', help='export result as PDF to provided destination, might take time for downloading images')
	parser.add_argument('--html', metavar='FILEPATH', type=str,  const=os.path.join(os.getcwd(), 'data/', 'cached_news.html'), nargs='?', help='export result as HTML to provided destination')
	args = parser.parse_args()
	return args

def logging_basicConfig(LOGGING_LEVEL, LOG_FILEPATH):
	"""	Sets logging level according to call arguments and should be called before instantiating class Tree object
		if --log FILEPATH is specified sets logging level to INFO and creates log file in provided destination
		else sets logging level to provided LOGGING_LEVEL
	"""
	if LOG_FILEPATH is None:
		logging.basicConfig(level=LOGGING_LEVEL, encoding='utf-8')
	else:
		logging.basicConfig(level=logging.INFO, filepath=LOG_FILEPATH, encoding='utf-8')

class FeedParserException(Exception):
    """Custom Exception class for <class 'Tree'>"""


class Tree:
	"""	Contains methods for fetching and parsing XML document, processing sub-elements, setting correct working tags for different variants of tags found in different sources,

	(e.g. 
		<xml>
			<article>
				<link>...</link>
				<date>...</date>
				<title>...</title>
				<summary>...</summary>			
			</article>
		</xml>	
	or
		<xml>
			<rss>
				<item>
					<link>...</link>
					<pubDate>...</pubDate>
					<title>...</title>
					<description>...</description>			
				</item>
			</rss>
		</xml>
	where working tags are different and can't be parsed by using same 'key'.)

	Parsing starts when <class 'Tree'> object is initiated and result is an attribute - instance.list_of_articles - created as a list of 	dictionaries which contain news articles organized in key-value pairs"""


	# CONSTANTS
	URL = None
	HTML_FILEPATH = None
	PDF_FILEPATH = None
	DB_FILEPATH = None
	DB = None
	LIMIT = None
	JSON = None
	FILTER_K = None
	FILTER_V = None
	CACHE = []





	def __init__(self, url, json_, html_filepath, pdf_filepath, limit, filter_src, filter_date, 
					db_filepath=os.path.join(os.getcwd(),'data/cached_news.db'), ):
		"""		Initiates class <Tree> object, connects to provided url, 
		after fetching response from RSS feed website, calls get_xml_tree method and xml.etree.ElementTree(.Element) object is created,
		calls collect_descendant_elements and collects all child, grandchild and any depth child elements, calls remove_tag_prefixes method 
		(to cover situations where, while fetching, prefixes are concatenated in front of element tags by server, also collects all tags in a set and returns it)
		set_working_tags method iterates through collected tags and sets self.ARTICLE, self.DESCRIPTION, self.DATE, self.TITLE, self.LINK variables for parsing article elements later,
		collect_articles method is called, which iterates through list of child elements and collects only article elements,
		after that parse_article method is called for every article in collected articles, organizes articles and their sub-elements in dictionaries and appends them to Tree.CACHE.
		then prints (if --limit is specified limits number of articles) formatted collected news (or if --json specified converts to json) to stdout 
		or if --html or --pdf is specified converts cached news to corresponding format, after that inserts cached news in SQLite3 database.
		if URL was not provided fetches news from database (if --date or --source is specified filters before fetching)
		according to provided arguments prints to stdout or converts to specified format.
		"""
		logging.debug("Tree.__init__(%s, %s, %s, %s, %s, %s, %s, %s)" % 
					(url, json_, html_filepath, pdf_filepath, limit, filter_src, filter_date, db_filepath))
		Tree.URL = url
		Tree.HTML_FILEPATH = html_filepath
		Tree.PDF_FILEPATH = pdf_filepath
		Tree.DB_FILEPATH = db_filepath
		Tree.LIMIT = limit
		Tree.JSON = json_
		if filter_date is not None:
			Tree.FILTER_K = 'date'
			Tree.FILTER_V = filter_date
		elif filter_src is not None:
			Tree.FILTER_K = 'news_src' 
			Tree.FILTER_V = filter_src

		try:
			Tree.DB = Tree.db_connection(Tree.DB_FILEPATH)

			if Tree.URL is not None:
				logging.info(f"Tree object created. url: {url}")
				self.response = self.estimate_connection()
				logging.info(f"Connected to source. self.response: {self.response}")
				self.tree = self.get_xml_tree()
				logging.info(f"Element object created. self.tree = {self.tree}")
				self.elements = self.collect_descendant_elements()
				logging.info("All sub-elements in xml tree collected.")
				self.__tags = self.remove_tag_prefixes() 	#returns a set of tags found in xml tree
				self.set_working_tags()
				logging.info(f"Working tags set. \n\tself.ARTICLE = {self.ARTICLE}\n\tself.DESCRIPTION = {self.DESCRIPTION}\n\tself.TITLE = {self.TITLE}\n\tself.LINK = {self.LINK}")
				self.articles = self.collect_articles()
				logging.info("Article elements collected.")
				for article in self.articles:
					logging.info("Parsing article.")
					temp = self.parse_article(article)
					logging.info("Adding parsed article to cache.")
					Tree.cache_news(temp) # appends to Tree.CACHE
				if Tree.HTML_FILEPATH is None and Tree.PDF_FILEPATH is None:
					# loops through and prints cached articles
					logging.info("Printing news articles from Tree.CACHE. Tree.LIMIT = %s" % Tree.LIMIT)
					for article in Tree.CACHE:
						if Tree.LIMIT > 0:
							Tree.print_news(article)
							Tree.LIMIT -= 1
						elif Tree.LIMIT == 0:
							pass
						else:
							Tree.print_news(article)
				else:
					logging.info("Checking if --html or --pdf flags were set")
					if Tree.HTML_FILEPATH is not None:
						Tree.create_html(filepath=Tree.HTML_FILEPATH)
					if Tree.PDF_FILEPATH is not None:
						Tree.create_pdf()
			else: # if self.URL is None
				logging.info("URL not provided, fetching news from database")
				if Tree.FILTER_K is not None:
					Tree.db_fetch_news(Tree.DB, Tree.FILTER_K, Tree.FILTER_V)
				else:
					Tree.db_fetch_news(Tree.DB)
				if Tree.HTML_FILEPATH is None and Tree.PDF_FILEPATH is None:
					logging.info("Printing news articles from Tree.CACHE. Tree.LIMIT = %s" % Tree.LIMIT)
					for article in Tree.CACHE:
						if Tree.LIMIT > 0:
							Tree.print_news(article)
							Tree.LIMIT -= 1
						elif Tree.LIMIT == 0:
							pass
						else:
							Tree.print_news(article)
						if len(Tree.CACHE) < 1:
							break
				else:
					logging.info("Checking if --html or --pdf flags were set")
					if Tree.HTML_FILEPATH is not None:
						Tree.create_html(filepath=Tree.HTML_FILEPATH)
					if Tree.PDF_FILEPATH is not None:
						Tree.create_pdf()

		except FeedParserException as e:
			logging.CRITICAL(e)
			logging.exception(e)
			sys.exit(1)
		except Exception as e:
			logging.CRITICAL(e)
			logging.exception(e)
			sys.exit(1)
		finally:
			if Tree.DB is not None:
				logging.info("Database connection closed")
				Tree.DB.close()

	def estimate_connection() -> _UrlopenRet: # returns <Response>
		pass

	def get_xml_tree() -> ET.Element:
		pass

	def collect_descendant_elements() -> list:
		pass

	def remove_tag_prefixes() -> set:
		pass

	def set_working_tags() -> None:
		pass

	def collect_articles() -> list[ET.Element]:
		pass

	def parse_article(article: ET.Element) -> dict:
		pass

	@staticmethod
	def cache_news(dict_: dict) -> None:
		pass

	@staticmethod
	def print_news(dict_: dict) -> None:
		pass

	def create_html(filepath: str) -> None:
		pass

	def create_pdf() -> None:
		pass

	def db_fetch_news(db: sqlite3.Connection, filter_key: str, filter_value: str) -> None:
		pass

	@staticmethod
	def db_connection(filepath: str) -> sqlite3.Connection:
		pass

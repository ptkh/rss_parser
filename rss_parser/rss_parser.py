"""	Module for parsing XML format RSS feeds.
	
    <function 'rss_arg_parser'> creates <class 'ArgumentParser' object with following arguments: 
    url	, --version, --json, --date, --source, --verbose, --limit, --pdf, --html, --log
	
	<class 'Tree'> with methods for fetching and parsing XML document from provided url, caching news in database, converting result to json, html, pdf format.

    <class 'FeedParserException'> custom exception class for exception handling.

    <function 'logging_basicConfig'> for setting logging level for this module.

    """


import argparse
from http.client import HTTPResponse
import os
import logging
import re
import sys
import sqlite3
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET
from lxml import html
import pdfkit
import dateutil.parser
from datetime import date
import json



def rss_arg_parser() -> argparse.Namespace:
	"""	Creates custom parser with following arguments: 
	\nurl					URL to XML format RSS feed
	\n--version				print version info
	\n--json				print result as JSON in stdout
	\n--date				outputs articles from specified date
	\n--source				outputs articles from specified source
	\n--verbose				output verbose status messages
	\n--limit				limit news topics, if provided
	\n--pdf					export result as PDF to provided destination (default=cwd)
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
	parser.add_argument('--pdf', metavar='FILEPATH', type=str, const=os.path.join(os.path.abspath('rss_parser'), 'data/cached_news.pdf'), nargs='?', help='export result as PDF to provided destination, might take time for downloading images')
	parser.add_argument('--html', metavar='FILEPATH', type=str,  const=os.path.join(os.path.abspath('rss_parser'), 'data/cached_news.html'), nargs='?', help='export result as HTML to provided destination')
	args = parser.parse_args()
	return args

def logging_basicConfig(LOGGING_LEVEL: int, LOG_FILEPATH: str) -> None:
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
	temp_html_path = os.path.join(os.path.abspath('rss_parser'), 'data/.temp.html')
	PAGE_TITLE = None
	ARTICLE_DIVS = ''
	TODAY = date.today()

	# working tags
	ARTICLE = None
	DESCRIPTION = None
	DATE = None
	LINK = 'link'
	TITLE = 'title'
	### different tag variants for parsing different sources
	article_tags = 'item', 'article', 'entry'	
	description_tags = 'description', 'summary'
	date_tags = 'pubdate', 'pubDate', 'published', 'updated', 'date'

	# RegEx pattern for removing tag prefix
	pattern_prefix = "{.*}"
	prefix_pattern = re.compile(pattern_prefix)
	### RegEx patterns for grabbing specific tags/content
	pattern_tag = "<.+?>"    
	pattern_enclosed_by_same_tag = "^<([a-z]+) *[^/]*?>((.|\n)*)</\\1>$"
	pattern_open_end_tag = "<([a-z]+) *[^/]*?>((.|\n)*)</\\1>"
	pattern_CDATA = "<![CDATA[.*?]]>"
	pattern_p = "<p(| +[^>]*)>(.*?)</p *>"
	pattern_a = "<a *(.*)>(.*)</a>"
	pattern_href = 'href *= *"(.+?)"'
	pattern_img= 'img *= *"(.+?)"'
	# compiled patterns
	tag_pattern = re.compile(pattern_tag)
	enclosed_by_same_tag_pattern = re.compile(pattern_enclosed_by_same_tag)
	open_end_tag_pattern = re.compile(pattern_open_end_tag)
	CDATA_pattern = re.compile(pattern_CDATA)
	p_pattern = re.compile(pattern_p)
	a_pattern = re.compile(pattern_a)
	href_pattern = re.compile(pattern_href)
	img_pattern = re.compile(pattern_img)


	def __init__(self, url, json_, html_filepath, pdf_filepath, limit, filter_src, filter_date, 
					db_filepath=os.path.join(os.path.abspath('rss_parser'),'data/cached_news.db'), ):
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
				self.request = self.create_request(Tree.URL)
				self.response = self.establish_connection(self.request)
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
					self.dict_ = {}
					logging.info("Parsing article.")
					self.parse_article(article)
					logging.info("Adding parsed article to cache.")
					Tree.cache_news(self.dict_) # appends to Tree.CACHE
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
				Tree.db_fetch_news(Tree.DB, Tree.FILTER_K, Tree.FILTER_V)
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
			# logging.CRITICAL(e)
			print(str(e.args)[1:-2])
			logging.exception(e)
			sys.exit(1)
		except Exception as e:
			# logging.CRITICAL(e)
			print(str(e.args)[1:-2])
			logging.exception(e)
			sys.exit(1)
		finally:
			if Tree.URL is not None:
				while len(Tree.CACHE) > 0:
					Tree.db_insert_cached_one(Tree.DB)
			if Tree.DB is not None:
				logging.info("Database connection closed")
				Tree.DB.close()

	@staticmethod
	def create_request(url: str) -> Request:
		"""Creates an HTTP request with provided url"""
		try:			
			logging.debug("Method create_request called.")
			headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.3'} #overriding user-agent prevents server from blocking request
			request = Request(url, headers=headers)  # 	<urllib.request.Request>
			logging.info("Request created: %s" % request)
			return request        
		except Exception as e:
			logging.exception(e)
			raise FeedParserException(e)

	@staticmethod
	def establish_connection(request: Request) -> HTTPResponse:
		"""Sends request to Tree.URL and returns <http.client.HTTPResponse> object"""
		try:			
			logging.debug("Method establish_connection called.")
			response = urlopen(request)
			logging.debug("Response received: %s" %response)
			
			return response
		except Exception as e:
			logging.exception(e)
			raise FeedParserException(e)

	def get_xml_tree(self) -> ET.Element:
		"""Parses xml from <HTTPResponse>.content and returns <ElementTree.Element> object"""
		try:
			logging.debug("Method get_xml_tree called.")
			content = self.response.read()
			logging.debug("Content fetched from response: %s" % content)
			tree = ET.fromstring(content)
			logging.debug("XML Element created: %s" % tree)
			return tree
		except Exception as e:
			logging.exception(e)
			raise FeedParserException(e)

	def collect_descendant_elements(self) -> list[ET.Element]:
		"""Traverses xml tree, collects all descendant elements and returns list of <ElementTree.Element> objects"""
		try:
			logging.debug("Method collect_descendant_elements called.")
			elements = [] #list for collecting child elements
			self.feed_title = "//title not provided//"
			for element in self.tree:        #(tree ~> *child* ~>...
				logging.debug("Traversing XML tree, collecting child elements")
				if element.tag == 'channel':
					for child in element:
						if child.tag == 'title':
							logging.debug("Channel title found: %s" % child.text)
							self.feed_title = child.text
				elements.append(element) 
				for elemnt in element: #( tree ~> child ~> *grandchild* ~> ... )
					if elemnt.tag == 'channel':
						for child in elemnt:
							if child.tag == 'title':
								logging.debug("Channel title found: %s" % child.text)
								self.feed_title = child.text
					elements.append(elemnt)
					for elemt in elemnt:     #( tree ~> child ~> grandchild ~> *2Xgrandchild* ~> ... )
						if elemt.tag == 'channel':
							for child in elemt:
								if child.tag == 'title':
									logging.debug("Channel title found: %s" % child.text)
									self.feed_title = child.text
						elements.append(elemt)
						for elem in elemt:   #( tree ~> child ~> grandchild ~> 2Xgrandchild ~> *3Xgrandchild* ~> ... )
							elements.append(elem)
			logging.debug("Returning article elements: %s", elements)
			return elements
		except Exception as e:
			logging.exception(e)
			raise FeedParserException(e)

	def remove_tag_prefixes(self) -> set[str]:
		"""Loops through the list of descendant elements, checks if tags contain prefixes and if they do, cuts them out
		(e.g. "{'http://example.com/'}title" or "{'http://example.com/'}description",
		where "{http://example.com/'}" is prefix and following word is tag name, result is "title" and "description")
		While looping through elements, adds all found tags in a set and returns it."""
		try:
			logging.debug("Method remove_tag_prefixes called.")
			logging.info("Checking if xml tree tags contain prefixes")
			tags = set() #for collecting tags while iterating
			if hasattr(self.tree, 'tag'):    #checks if element has tag
				if re.search(Tree.prefix_pattern, self.tree.tag) is not None: # if tag has prefix, removes it
					logging.info('Removing tag prefix: %s' % self.tree.tag)
					self.tree.tag = re.sub(Tree.prefix_pattern, '', self.tree.tag) 
				tags.add(self.tree.tag) # adds tag to set
				for element in self.tree:
					if hasattr(element, 'tag'):
						if re.search(Tree.prefix_pattern, element.tag) is not None:
							logging.info('Removing tag prefix: %s' % element.tag)
							element.tag = re.sub(Tree.prefix_pattern, '', element.tag)
						tags.add(element.tag)
						for elmnt in element:
							if hasattr(elmnt, 'tag'):
								if re.search(Tree.prefix_pattern, elmnt.tag) is not None:
									logging.info('Removing tag prefix: %s' % element.tag)
									elmnt.tag = re.sub(Tree.prefix_pattern, '', elmnt.tag)
								tags.add(elmnt.tag)
								for elmt in elmnt:
									if hasattr(elmt, 'tag'):
										if re.search(Tree.prefix_pattern, elmt.tag) is not None:
											logging.info('Removing tag prefix: %s' % element.tag)
											elmt.tag = re.sub(Tree.prefix_pattern, '', elmt.tag)
										tags.add(elmt.tag)
										for emt in elmt:
											if hasattr(emt, 'tag'):
												if re.search(Tree.prefix_pattern, emt.tag) is not None:
													logging.info('Removing tag prefix: %s' % element.tag)
													emt.tag = re.sub(Tree.prefix_pattern, '', emt.tag)
												tags.add(emt.tag)
			return tags
		except Exception as e:
			logging.exception(e)
			raise FeedParserException(e)

	def set_working_tags(self) -> None:
		"""Iterates through collected tags and sets self.ARTICLE, self.DESCRIPTION, self.DATE variables for parsing article elements to later use them while parsing article element's sub-elements."""
		try:
			logging.info("Setting working tags")
			for tag in self.__tags:
				if self.ARTICLE != None and self.DESCRIPTION != None and self.DATE != None:
					break
				if self.ARTICLE == None and tag in Tree.article_tags:
					self.ARTICLE = tag
					logging.info("Article tag set: %s" % tag)
					continue
				elif self.DESCRIPTION == None and tag in Tree.description_tags:
					self.DESCRIPTION = tag
					logging.info("Description tag set: %s" % tag)
					continue
				elif self.DATE == None and tag in Tree.date_tags:
					self.DATE = tag
					logging.info("Date tag set: %s" % tag)
					continue
		except Exception as e:
			logging.exception(e)
			raise FeedParserException(e)
		
	def collect_articles(self) -> list[ET.Element]:
		"""Loops through list of collected descendant elements and returns list of article elements"""
		try:
			articles = [] #list for collecting item blocks
			for element in self.tree:        #(tree ~> *child* ~>...
				if element.tag == self.ARTICLE: #checks if child tag is item
					logging.info("Article element found in collected articles")
					articles.append(element)    #if true, appends item block (current ET.Element object) to items list
					continue                 #and continues iterating on the same level
				for elemnt in element:       #otherwise iterates over tags one level deeper ( tree ~> child ~> *grandchild* ~> ... )
					if elemnt.tag == self.ARTICLE:
						logging.info("Article element found in collected articles")
						articles.append(elemnt)
						continue
					for elemt in elemnt:     #( tree ~> child ~> grandchild ~> *2Xgrandchild* ~> ... )
						if elemt.tag == self.ARTICLE:
							logging.info("Article element found in collected articles")
							articles.append(elemt)
							continue
						for elem in elemt:   #( tree ~> child ~> grandchild ~> 2Xgrandchild ~> *3Xgrandchild* ~> ... )
							if elem.tag == self.ARTICLE:
								logging.info("Article element found in collected articles")
								articles.append(elem)
								continue
			return articles
		except Exception as e:
			logging.exception(e)
			raise FeedParserException(e)

	def parse_article(self, article: ET.Element) -> dict:
		"""Parses article sub-elements and organizes them in a dictionary
		(e.g. dict({'title': title_element_contents, 'link': link_element_contents, ...})
		returns dictionary"""
		try:
			for element in article:
				logging.info("Parsing article sub-element: %s" % element.tag)
				if element.text is not None:
					element.text = element.text.replace(u'\xa0', u' ') 
				if element.tag == self.TITLE:
					self.parse_title(element, self.dict_)
				elif element.tag == self.DATE:
					self.parse_date(element, self.dict_)
				elif element.tag == self.LINK:
					self.parse_link(element, self.dict_)
				elif element.tag == self.DESCRIPTION:
					if element.text is None:
						if self.DESCRIPTION == 'description' and 'summary' in self.__tags:
							self.DESCRIPTION = 'summary'
						elif self.DESCRIPTION == 'summary' and 'description' in self.__tags:
							self.DESCRIPTION = 'description'
						continue
					self.parse_description(element, self.dict_)
				elif element.tag == 'content' and 'url' in element.attrib:
					if 'news_url' in self.dict_:
						self.dict_['news_url'] = f"{self.dict_['news_url']}\n{element.attrib['url']} (content)"
					else:
						self.dict_['news_url'] = f"{element.attrib['url']} (content)"
			self.dict_['news_title'] = self.dict_['news_title'].strip()
			self.dict_['news_url'] = self.dict_['news_url'].strip()
			self.dict_['news_src'] = Tree.URL
			if 'news_description' in self.dict_:
				self.dict_['news_description'] = self.dict_['news_description'].strip()
			else:
				self.dict_['news_description'] = ''
			if 'news_date' not in self.dict_:
				self.dict_['news_date'] = Tree.TODAY
			self.dict_['date'] = str(self.dict_['news_date'])[:10]
			self.dict_['news_feed_title'] = self.feed_title
		except Exception as e:
			logging.exception(e)
			raise FeedParserException(e)

	def parse_title(self, element: ET.Element, dict_: dict) -> None:
		"""Parses title element of xml and appends text to dict_[news_title]"""
		dict_['news_title'] = element.text
		
	def parse_date(self, element: ET.Element, dict_: dict) -> None:
		"""Parses date element of xml tree and appends datetime object to dict_[news_date]"""
		dict_['news_date'] = str(dateutil.parser.parse(element.text, ignoretz=True))

	def parse_link(self, element: ET.Element, dict_: dict) -> None:
		"""Parses link element of xml tree and appends links to dict_[news_url]"""
		if 'href' in element.attrib:
			if 'news_url' in dict_:
				dict_['news_url'] = f"{dict_['news_url']}\n{element.attrib['href']} (link)"
			else:
				dict_['news_url'] = f"{element.attrib['href']} (link)"
		elif type(element.text) == str:
			if 'http' in element.text:
				if 'news_url' in dict_:
					dict_['news_url'] = f"{dict_['news_url']}\n{element.text} (link)"
				else:
					dict_['news_url'] = f"{element.text} (link)"

	def parse_description(self, element: ET.Element, dict_: dict) -> None:
		"""Parses description element of xml tree, checks if element.text contains html fragments, accordingly parses and append text content to dict_[news_description]"""
		try:
			if 'type' in element.attrib and element.attrib['type'] == 'html':
				nodes = html.fragments_fromstring(element.text)
				self.parse_html(nodes, dict_)
			elif element.text is not None:
				if re.search(self.pattern_CDATA, element.text) != None:
					element.text = element.text[8:-3].strip()
				if re.search(self.enclosed_by_same_tag_pattern, element.text) is not None:
					s, e = re.search(self.enclosed_by_same_tag_pattern, element.text).span()
					fragment = element.text[s:e]
					nodes = html.fragments_fromstring(fragment)
					self.parse_html(nodes, dict_)
				elif re.search(self.open_end_tag_pattern, element.text) is not None:
					s,e = re.search(self.open_end_tag_pattern, element.text).span()
					text = element.text[:s]
					if re.search(self.tag_pattern, text) is not None:
						nodes = html.fragments_fromstring(text)
						self.parse_html(nodes, dict_)
					else:
						if 'news_description' in dict_:
							dict_['news_description'] = f"{dict_['news_description']}\n{text}"
						else:
							dict_['news_description'] = f"{text}"
					nodes = html.fragments_fromstring(element.text[s:e])
					self.parse_html(nodes, dict_)
				else: 
					dict_['news_description'] = element.text
		except Exception as e:
			logging.exception(e)
			raise FeedParserException(e)

	@staticmethod
	def cache_news(dict_: dict) -> None:
		"""Method for appending news articles to CACHE"""
		try:
			logging.debug("Appending news article to CACHE")
			Tree.CACHE.append(dict_)
		except Exception as e:
			logging.exception(e)
			raise FeedParserException(e)

	@staticmethod
	def print_news(article: dict) -> None:
		"""Prints formatted news item, if --json specified, prints JSON representation"""
		try:
			if Tree.JSON:
				logging.info("Printing JSON representation of article to stdout")
				json_str = Tree.convert_to_json(article)
				print(f"\n{json_str}\n")
			else:
				logging.info("Printing formatted article to stdout")
				for key, value in article.items():
					if key == 'news_feed_title':
						feed_title = value
					elif key == 'news_src':
						src = value
					elif key == 'news_title':
						title = value
					elif key == 'news_date':
						date = value
					elif key == 'news_description':
						description = value
					elif key == 'news_url':
						url = value
				print(f"""			
					\n____________________________________________
					\nFeed: {feed_title}
					\nSource: {src}
					\n____________________________________________
					\nTitle: {title}
					\n____________________________________________
					\nDate: {date}
					\n{description}
					\nLinks:
					\n{url}""")
		except Exception as e:
			logging.exception(e)
			raise FeedParserException(e)

	@staticmethod
	def create_html(filepath: str) -> None:
		"""Method for creating .html document from Tree.articles_html"""
		try:
			if filepath == Tree.temp_html_path:
				logging.info("Creating html document from Tree.CACHE for converting to PDF >> %s" % Tree.temp_html_path)
			else:
				logging.info("Creating html document from Tree.CACHE >> %s" % Tree.HTML_FILEPATH)
			articles_html = Tree.to_html_string(Tree.CACHE)
			with open(filepath, 'w') as file:
				file.write(articles_html)
		except Exception as e:
			logging.exception(e)
			raise FeedParserException(e)

	@staticmethod
	def to_html_string(list_of_articles: list[dict]) -> str:
		"""	Method for processing list of articles and creating Tree.articles_html,
			also, sets Tree.PAGE_TITLE"""
		logging.debug("Converting list of articles to html string")
		try:
			feed_titles = []
			for dict_ in list_of_articles:
				feed_titles.append(dict_['news_feed_title'])
				logging.debug("Appending article div string to Tree.ARTICLE_DIVS")
				if Tree.LIMIT > 0:
					Tree.ARTICLE_DIVS += Tree.article_to_html(dict_)
					Tree.LIMIT -= 1
				elif Tree.LIMIT == 0:
					pass
				else:
					Tree.ARTICLE_DIVS += Tree.article_to_html(dict_)
			logging.debug("Setting html page title")
			for title in tuple(set(feed_titles)):
				if feed_titles.count(title) == len(feed_titles):
					Tree.PAGE_TITLE = title
					break
				else:
					if feed_titles.count(title)/len(feed_titles) >= 0.75:
						Tree.PAGE_TITLE += ', ' + title

			if Tree.PAGE_TITLE is None:
				Tree.PAGE_TITLE = Tree.TODAY

			articles_html = f'''
			<!DOCTYPE html>
				<html>
					<head>
						<title>{Tree.PAGE_TITLE}</title>
					</head>
					<body>

					{Tree.ARTICLE_DIVS}

					</body>
				</html>
			'''
			return articles_html
		except Exception as e:
			logging.exception(e)
			raise FeedParserException(e)

	@staticmethod
	def article_to_html(dict_: dict) -> str:
		"""Method for converting dict_ to html fragment - article_div"""
		logging.debug("Generating html fragment for article item")
		try:
			urls_ = dict_['news_url'].split('\n')
			img_urls = []
			imgs_html = ''
			links = []
			links_html = ''

			for url in urls_:
				if 'content' in url:
					img_urls.append(url[:-10])
				else:
					links.append(url[:-7])
			for link in links:
				links_html += f'''<a href="{link}">{link}</a>\n\t\t\t\t\t\t'''

			logging.info('Parsing image links for constructing HTML')
			for img in img_urls:
				imgs_html += f'''<img src="{img}" alt="" width="60% of window">\n\t\t\t\t\t\t'''
			div_with_feed_title = f'''
					<div>
						<h2>{dict_['news_feed_title']}</h2>
						{imgs_html}
						<p>{dict_['news_src']}</p>
						<h3>{dict_['news_title']}</h3>
						<p>{dict_['news_date']}</p>
						<p>{dict_['news_description']}</p>
						{links_html}
					</div>'''
			div_without_feed_title = f'''
					<div>
						{imgs_html}
						<p>{dict_['news_src']}</p>
						<h3>{dict_['news_title']}</h3>
						<p>{dict_['news_date']}</p>
						<p>{dict_['news_description']}</p>
						{links_html}
					</div>'''
			article_div = div_without_feed_title if dict_['news_feed_title'] in Tree.ARTICLE_DIVS else div_with_feed_title
			return article_div
		except Exception as e:
			logging.exception(e)
			raise FeedParserException(e)

	@staticmethod
	def create_pdf() -> None:
		"""Created HTML document and converts it into PDF using wkhtmltopdf, embedding images may take long time."""
		try:
			Tree.create_html(Tree.temp_html_path)
			logging.info("Created html string for converting to pdf")
			try:
				logging.info("Creating pdf document using webkit rendering engine and qt. Please wait...")
				pdfkit.from_file(input=Tree.temp_html_path, output_path=Tree.PDF_FILEPATH)
				logging.info("PDF document created: %s" % Tree.PDF_FILEPATH)
			except Exception as e:
				logging.critical("Failed to create PDF document due to exception: %s", e)
				raise FeedParserException(e)
		except Exception as e:
			logging.exception(e)
			raise FeedParserException(e)
		finally:
			if os.path.exists(Tree.temp_html_path):
				os.remove(Tree.temp_html_path)

	@staticmethod
	def db_fetch_news(database: sqlite3.Connection, filter_key: str, filter_value: str) -> None:
		"""Selects rows from db according to provided column and value and fetches them
		Returns list of dictionaries containing fetched values"""
		try:
			logging.info("Fetching news articles from database")
			if filter_key is None and filter_value is None:
				sql = f"""SELECT * FROM cached_news"""
			else:
				sql = f"""SELECT * FROM cached_news WHERE {filter_key} LIKE '%{filter_value}%'"""

			logging.info(sql)

			with database:
				cursor = database.cursor()
				cursor.execute(sql)
				data = cursor.fetchall()
			for item in data:
				dict_ = {}
				dict_['date'], dict_['news_feed_title'],dict_['news_src'], dict_['news_title'], dict_['news_date'], dict_['news_description'], dict_['news_url'] = item
				Tree.cache_news(dict_)
			
		except Exception as e:
			logging.exception(e)
			raise FeedParserException(e)

	@staticmethod
	def db_connection(filepath: str) -> sqlite3.Connection:
		"""Connects to or creates the database specified by filepath
		Creates table cached_news if it does not exist
		Returns database connection object"""
		sql = """
		CREATE TABLE IF NOT EXISTS cached_news
				(date TEXT, 
				news_feed_title TEXT,
				news_src TEXT, 
				news_title TEXT, 
				news_date TEXT, 
				news_description TEXT, 
				news_url TEXT)
		"""
		logging.info("Connecting to SQLite database")
		try:
			if os.path.isfile(filepath):
				database = sqlite3.connect(filepath)
			else:
				database = sqlite3.connect(filepath)
				with database:
					cursor = database.cursor()
					cursor.execute(sql)
				logging.info("Creating cached_news table in database: %s" % filepath)
			
			return database
		except Exception as e:
			logging.exception(e)
			raise FeedParserException(e)

	@staticmethod
	def db_insert_cached_one(database: sqlite3.Connection) -> None:
		"""Inserts first row from Tree.CACHE and pops it from the list"""
		sql = """
		INSERT INTO cached_news 
				(date, 
				news_feed_title,
				news_src, 
				news_title, 
				news_date, 
				news_description, 
				news_url)
		VALUES (?, ?, ?, ?, ?, ?, ?)
		"""
		logging.info("Inserting row from Tree.CACHE into database")
		try:
			if len(Tree.CACHE) > 0:
				temp = Tree.CACHE.pop(0)
				with database:
					cursor = database.cursor()
					check_if_exists = f"SELECT date FROM cached_news WHERE news_title LIKE ?"
					cursor.execute(check_if_exists, (temp['news_title'],))
					flag = cursor.fetchone()
					if flag is None:
						cursor.execute(sql, 
							(temp['date'], 
							temp['news_feed_title'],
							temp['news_src'], 
							temp['news_title'], 
							temp['news_date'], 
							temp['news_description'], 
							temp['news_url']),
						)
		except Exception as e:
			logging.exception(e)
			raise FeedParserException(e)

	@staticmethod
	def convert_to_json(dict_: dict) -> str:
		"""Method for converting cached news articles to json"""
		logging.info("Converting news articles to json")
		try:
			json_ = json.dumps(dict_)
			return json_
		except Exception as e:
			logging.exception(e)
			raise FeedParserException(e)
			
	def parse_html(self, nodes: list[html.HtmlElement], dict_: dict) -> None:
		"""Receives html element object, loops through sub elements and calls parsing methods on them accordingly """
		try:
			logging.info("Parsing HTML fragment")
			for node in nodes:
				if node.tag == 'p' or node.tag == 'div':
					self.parse_div_p(node, dict_)
				if node.tag == 'img':
					self.parse_img(node, dict_)
				if node.tag == 'a':
					self.parse_a(node, dict_)
				for child in node.getchildren():
					if child.tag == 'div' or child.tag == 'p':
						self.parse_div_p(child, dict_)
					elif child.tag == 'img':
						self.parse_img(child, dict_)
					elif child.tag == 'a':
						self.parse_a(child, dict_)
					elif child.tag == 'ul':
						for c in child.getchildren():
							if 'news_description' in dict_:
								dict_['news_description'] = f"{dict_['news_description']}\n{c.text}"
							else:
								dict_['news_description'] = f"{c.text}"
		except Exception as e:
			logging.exception(e)
			raise FeedParserException(e)

	def parse_div_p(self, node: html.HtmlElement, dict_: dict) -> None:
		"""Parses div or p tag of html, appends text_content to dict_[news_description] and if element has sub elements instructs to parse them"""
		try:
			if node.getchildren() == []:
				if len(node.text_content()) > 0:
					if 'news_description' in dict_:
						dict_['news_description'] = f"{dict_['news_description']}\n{node.text_content()}"
					else: 
						dict_['news_description'] = f"{node.text_content()}"
			else:
				if 'news_description' in dict_:
					dict_['news_description'] = f"{dict_['news_description']}\n{node.text_content()}"
				else: 
					dict_['news_description'] = f"{node.text_content()}"
				self.parse_html(node.getchildren(), dict_)
		except Exception as e:
			logging.exception(e)
			raise FeedParserException(e)

	def parse_img(self, node: html.HtmlElement, dict_: dict) -> None:		
		"""Parses img tag of html and appends url to dict_[news_url]"""
		try:
			if 'news_url' in dict_:
				if dict_['news_url'].find(node.attrib['src']) == -1:
					dict_['news_url'] = f"{dict_['news_url']}\n{node.attrib['src']} (content)"
			else:
				dict_['news_url'] = f"{node.attrib['src']} (content)"
		except Exception as e:
			logging.exception(e)
			raise FeedParserException(e)

	def parse_a(self, node: html.HtmlElement, dict_: dict) -> None:
		"""Parses a tag of html and appends url to dict_[news_url]"""
		try:
			href = node.attrib['href']
			if 'news_url' in dict_:
				if dict_['news_url'].find(href) == -1:
					dict_['news_url'] = f"{dict_['news_url']}\n{node.attrib['href']} (link)"
			else:
				dict_['news_url'] = f"{node.attrib['href']} (link)"
		except Exception as e:
			raise e


def main():
	VERSION = 'RSSFeedParser 0.3'
	LOGGING_LEVEL = logging.CRITICAL
	LOG_FILEPATH = None

	args = rss_arg_parser()
	if args.version:
		print(VERSION)
		sys.exit(0)

	if args.log is None:
		if args.verbose:
			LOGGING_LEVEL = logging.INFO
	else:
		LOG_FILEPATH = args.log
	logging_basicConfig(LOGGING_LEVEL, LOG_FILEPATH)

	tree = Tree(args.url, 
				limit=args.limit,
				json_=args.json, 
				html_filepath=args.html, 
				pdf_filepath=args.pdf, 
				filter_src=args.source,
				filter_date=args.date,)



if __name__ == '__main__':
	main()
	sys.exit(0)
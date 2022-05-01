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

	def __init__():
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
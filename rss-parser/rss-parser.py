"""	Module for parsing XML format RSS feeds.
	
    <function 'rss_arg_parser'> creates <class 'ArgumentParser' object with following arguments: 
    url	, --version, --json, --date, --source, --verbose, --limit, --pdf, --html, --log
	
	<class 'Tree'> with methods for fetching and parsing XML document from provided url, caching news in database, converting result to json, html, pdf format.

    <class 'FeedParserException'> custom exception class for exception handling.

    <function 'logging_basicConfig'> for setting logging level for this module.

    """


import argparse
import os



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
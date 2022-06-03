import pytest
from rss_parser.rss_parser import Tree, FeedParserException
from unittest.mock import patch, Mock, MagicMock, mock_open, call
from http.client import HTTPResponse
from urllib.request import Request
from xml.etree.ElementTree import Element, fromstring
from io import StringIO
import sqlite3
import re

sample_xml_1 = """
					<xml>
						<article>
							<link>...</link>
							<date>...</date>
							<title>...</title>
							<summary>...</summary>			
						</article>
						<article>
							<link>...</link>
							<date>...</date>
							<title>...</title>
							<summary>...</summary>			
						</article>
					</xml>
"""
sample_xml_2 = """
					<xml>
						<rss>
							<item>
								<link>...</link>
								<pubDate>...</pubDate>
								<title>...</title>
								<description>...</description>			
							</item>
							<item>
								<link>...</link>
								<pubDate>...</pubDate>
								<title>...</title>
								<description>...</description>			
							</item>
						</rss>
					</xml>
"""
sample_xml_3 = bytes("""<?xml version="1.0" encoding="UTF-8"?><rss xmlns:media="http://search.yahoo.com/mrss/" version="2.0"><channel><title>Yahoo News - Latest News &amp; Headlines</title><link>https://www.yahoo.com/news</link><description>The latest news and headlines from Yahoo! News. Get breaking news stories and in-depth coverage with videos and photos.</description><language>en-US</language><copyright>Copyright (c) 2022 Yahoo! Inc. All rights reserved</copyright><pubDate>Thu, 26 May 2022 11:25:03 -0400</pubDate><ttl>5</ttl><image><title>Yahoo News - Latest News &amp; Headlines</title><link>https://www.yahoo.com/news</link><url>http://l.yimg.com/rz/d/yahoo_news_en-US_s_f_p_168x21_news.png</url></image><item><title>Goodbye NYC: Census shows big city losses, Sunbelt gains</title><link>https://news.yahoo.com/goodbye-nyc-estimates-show-big-041338762.html</link><pubDate>2022-05-26T04:13:38Z</pubDate><source url="http://www.ap.org/">Associated Press</source><guid isPermaLink="false">goodbye-nyc-estimates-show-big-041338762.html</guid><media:content height="86" url="https://s.yimg.com/uu/api/res/1.2/IIb05PJ5FnFgcf_znrJ9AA--~B/aD0zMzYyO3c9NTA4MDthcHBpZD15dGFjaHlvbg--/https://media.zenfs.com/en/ap.org/a80fc0fc10aa694611b72746a0180856" width="130"/><media:credit role="publishing company"/></item><item><title>We may not want to admit it, but there’s truth in what the ESPN crew said about Milwaukee. So what are we going to do about it?</title><link>https://news.yahoo.com/may-not-want-admit-truth-141609705.html</link><pubDate>2022-05-26T14:16:09Z</pubDate><source url="https://www.jsonline.com">Milwaukee Journal Sentinel</source><guid isPermaLink="false">may-not-want-admit-truth-141609705.html</guid><media:content height="86" url="https://s.yimg.com/uu/api/res/1.2/QDcfByQVX6xGnQmbsfsA1g--~B/aD02Njc7dz0xMDAwO2FwcGlkPXl0YWNoeW9u/https://media.zenfs.com/en/milwaukee-journal-sentinel/342c7ea7b9b8658930d1f7d9cf801768" width="130"/><media:credit role="publishing company"/></item></channel></rss>""", encoding="utf-8")

sample_prefix_xml_1 = b'<feed xmlns="http://www.w3.org/2005/Atom" xmlns:media="http://search.yahoo.com/mrss/">\r\n\t<title>Global Issues News Headlines</title>\r\n\t<id>https://www.globalissues.org/news</id>\r\n\t<updated>2022-05-30T01:11:25-07:00</updated>\r\n\t<link href="https://www.globalissues.org/news"/>\r\n\t<link rel="self" href="https://www.globalissues.org/news/feed"/>\r\n\t<author>\r\n\t\t<name>Global Issues</name>\r\n\t</author>\r\n\t<contributor>\r\n\t\t<name>Inter Press Service</name>\r\n\t</contributor>\r\n\t<contributor>\r\n\t\t<name>UN News</name>\r\n\t</contributor>\r\n\t<icon>https://static.globalissues.org/i/globalissues.png</icon>\r\n\t<logo>https://static.globalissues.org/i/globalissues/logo-feed.jpg</logo><entry><id>https://www.globalissues.org/news/2022/05/30/30981</id><title>UN Deeply Troubled by Impending Cuts on Development Aid by Rich Nations</title><updated>2022-05-30T06:25:32-07:00</updated><link rel="alternate" type="text/html" href="https://www.globalissues.org/news/2022/05/30/30981" /><link rel="enclosure" type="image/jpg" href="https://static.globalissues.org/ips/2022/05/Secretary-General-Amina_.jpg" /><summary type="html">&lt;p&gt;&lt;img src=&quot;https://static.globalissues.org/ips/2022/05/Secretary-General-Amina_.jpg&quot; width=&quot;640&quot; alt=&quot;&quot; /&gt;&lt;/p&gt;&lt;p&gt;UNITED NATIONS, May 30 (IPS)  - The four-month-old Russian invasion of Ukraine, which has triggered a hefty increase in military spending among Western nations and a rise in humanitarian and military assistance to the beleaguered country, is now threatening to undermine the flow of Official Development Assistance (ODA) to the world\xe2\x80\x99s poorer nations.&lt;/p&gt;&lt;p&gt;&lt;a href=&quot;https://www.globalissues.org/news/2022/05/30/30981&quot;&gt;Read the full story, \xe2\x80\x9cUN Deeply Troubled by Impending Cuts on Development Aid by Rich Nations\xe2\x80\x9d, on globalissues.org&lt;/a&gt; \xe2\x86\x92&lt;/p&gt;</summary><media:thumbnail url="https://static.globalissues.org/ips/2022/05/Secretary-General-Amina_-100x100.jpg" width="100" height="100" /></entry></feed><!-- 0.0011s -->'

dummy_dict = {  'news_title': 'Default title value', 
					'news_url': 'Default url value', 
					'news_src': 'Default src value', 
					'news_description': 'Default description value', 
					'news_date': 'Default news_date value', 
					'date': 'Default date value', 
					'news_feed_title': 'Default feed_title value'}
sample_filepath = '/sample/filepath'
mock_filepath = '/mock/filepath'

@pytest.mark.parametrize(
	('input_x', ),
	(
		('https://example.com', ),
		('http://example.com', ),
		('https:', ),
	)
)
def test_create_request_success(input_x, ):
	assert type(Tree.create_request(input_x)) == Request

@pytest.mark.parametrize(
	('input_x', ),
	(
		('', ),
		('example.com', ),
		('abc://example.com', ),
		('123://example.com', ),
	)
)
def test_create_request_failure(input_x, ):
	try:
		Tree.create_request(input_x)
	except Exception as e:
		assert type(e) == FeedParserException

@patch('urllib.request.urlopen', return_value=HTTPResponse)
@pytest.mark.parametrize(
	('input_x', ),
	(
		('https://example.com', ),
		('http://example.com', ),
		('http://www.example.com', ),
	)
)
def test_establish_connection_success(mock_urlopen, input_x, ):
	mock_urlopen.return_value = HTTPResponse
	assert type(Tree.establish_connection(input_x)) == HTTPResponse
	assert mock_urlopen.called_with(input_x)

@pytest.mark.parametrize(
	('input_x', ),
	(
		('', ),
		('example.com', ),
		('abc://example.com', ),
		('123://example.com', ),
		('https://example.', ),
		('https://', ),
		('https', ),
	)
)
def test_establish_connection_failure(input_x, ):
	try:
		Tree.establish_connection(input_x)
	except Exception as e:
		assert type(e) == FeedParserException

@patch('rss_parser.rss_parser.Tree.__init__', return_value=None)
@pytest.mark.parametrize(
	('input_x', ),
	(
		(sample_xml_1, ),
		(sample_xml_2, ),
		(sample_xml_3, ),
	)
)
def test_get_xml_tree(mock_init, input_x, ):
	tree = Tree()
	tree.response = Mock()
	tree.response.read = Mock(return_value=input_x)
	xml_tree = tree.get_xml_tree()
	assert type(xml_tree) == Element

@patch('rss_parser.rss_parser.Tree.__init__', return_value=None)
@pytest.mark.parametrize(
	('input_x', ),
	(
		(sample_xml_1, ),
		(sample_xml_2, ),
		(sample_xml_3, ),
	)
)
def test_collect_descendant_elements(mock_init, input_x):
	tree = Tree()
	tree.tree = fromstring(input_x)
	elements = tree.collect_descendant_elements()
	assert type(elements) == list
	assert type(elements[0]) == Element


@patch('rss_parser.rss_parser.Tree.__init__', return_value=None)
@pytest.mark.parametrize(
	('input_x', ),
	(
		(sample_prefix_xml_1, ), # this string appends prefix to each element while parsing
	)
)
def test_remove_tag_prefixes(mock_init, input_x):
	tree = Tree()
	tree.tree = fromstring(input_x)
	tree.elements = tree.collect_descendant_elements()
	for element in tree.elements:
		if element.tag in ['channel', 'feed', 'item', 'article', 'date', 'pubdate', 'pubDate', 'published', 'link', 'title']:
			assert "{http://www.w3.org/2005/Atom}" in element.tag
	tags = tree.remove_tag_prefixes()
	for tag in tags:
		if tag in ['channel', 'feed', 'item', 'article', 'date', 'pubdate', 'pubDate', 'published', 'link', 'title']:
			assert "{http://www.w3.org/2005/Atom}" not in tag

@patch('rss_parser.rss_parser.Tree.__init__', return_value=None)
@pytest.mark.parametrize(
	('input_x', 'expected'),
	(
		(sample_xml_1, {'article': 'article', 'date': 'date', 'description': 'summary'},), 
		(sample_xml_2, {'article': 'item', 'date': 'pubDate', 'description': 'description'},), 
		(sample_xml_3, {'article': 'item', 'date': 'pubDate', 'description': 'description'},), 
		(sample_prefix_xml_1, {'article': 'entry', 'date': 'updated', 'description': 'summary'},), 
	)
)
def test_set_working_tags(mock_init, input_x, expected):
	tree = Tree()
	tree.tree = fromstring(input_x)
	tree.elements = tree.collect_descendant_elements()
	tree._Tree__tags = tree.remove_tag_prefixes()
	tree.set_working_tags()
	assert {'article': tree.ARTICLE, 'date': tree.DATE, 'description': tree.DESCRIPTION} == expected

@patch('rss_parser.rss_parser.Tree.__init__', return_value=None)
@pytest.mark.parametrize(
	('input_x', 'expected'),
	(
		(sample_xml_1, 'article', ), 
		(sample_xml_2, 'item', ), 
		(sample_xml_3, 'item', ), 
		(sample_prefix_xml_1, 'entry', ), 
	)
)
def test_collect_articles(mock_init, input_x, expected):
	tree = Tree()
	tree.tree = fromstring(input_x)
	tree.elements = tree.collect_descendant_elements()
	tree._Tree__tags = tree.remove_tag_prefixes()
	tree.set_working_tags()
	articles = tree.collect_articles()
	for article in articles:
		assert article.tag == expected

@patch('rss_parser.rss_parser.Tree.__init__', return_value=None)
@pytest.mark.parametrize(
	('input_x', ),
	(
		(sample_xml_3, ), 
		(sample_prefix_xml_1, ), 
	)
)
def test_parse_article(mock_init, input_x, ):
	tree = Tree()
	tree.tree = fromstring(input_x)
	tree.elements = tree.collect_descendant_elements()
	tree._Tree__tags = tree.remove_tag_prefixes()
	tree.set_working_tags()
	articles = tree.collect_articles()

	tree.dict_ = MagicMock()
	tree.dict_.__getitem__.side_effect = dummy_dict.__getitem__
	tree.parse_title = MagicMock()
	tree.parse_date = MagicMock()
	tree.parse_link = MagicMock()
	tree.parse_description = MagicMock()
	
	for article in articles:
		tree.parse_article(article)
		for element in article:
			if element.tag == Tree.TITLE:
				assert element in tree.parse_title.call_args[0]
			if element.tag == Tree.DATE:
				assert element in tree.parse_date.call_args[0]
			if element.tag == Tree.LINK:
				if len(tree.parse_link.call_args_list) == 1:
					assert element in tree.parse_link.call_args[0]
				elif len(tree.parse_link.call_args_list) > 1:
					arguments = []
					for call in tree.parse_link.call_args_list:
						for call_args in call[0]:
							arguments.append(call_args)
					assert element in arguments
			if element.tag == Tree.DESCRIPTION:
				assert element in tree.parse_description.call_args[0]

@patch('rss_parser.rss_parser.Tree.__init__', return_value=None)
def test_cache_news(mock_init, ):
	tree = Tree()
	tree.cache_news(dummy_dict)
	assert dummy_dict in Tree.CACHE

@patch('rss_parser.rss_parser.Tree.__init__', return_value=None)
@pytest.mark.parametrize(
	('json', 'expected'),
	(
		(True, '\n{"news_title": "Default title value", "news_url": "Default url value", "news_src": "Default src value", "news_description": "Default description value", "news_date": "Default news_date value", "date": "Default date value", "news_feed_title": "Default feed_title value"}\n\n'), 
		(False, f"""			
					\n____________________________________________
					\nFeed: {dummy_dict['news_feed_title']}
					\nSource: {dummy_dict['news_src']}
					\n____________________________________________
					\nTitle: {dummy_dict['news_title']}
					\n____________________________________________
					\nDate: {dummy_dict['news_date']}
					\n{dummy_dict['news_description']}
					\nLinks:
					\n{dummy_dict['news_url']}\n"""), 
	)
)
def test_print_news(mock_init, capsys, json, expected):
	tree = Tree()
	Tree.JSON = json
	tree.print_news(dummy_dict)
	out, err = capsys.readouterr()
	assert out == expected

@patch('rss_parser.rss_parser.Tree.__init__', return_value=None)
@patch('rss_parser.rss_parser.Tree.to_html_string', return_value='mocked html string')
@pytest.mark.parametrize(
	('input_x', ),
	(
		(sample_filepath, ),
		(mock_filepath, ),
	)
)
def test_create_html(mock_init, mock_to_html_string, input_x):
	tree = Tree()
	Tree.temp_html_path = input_x
	with patch('rss_parser.rss_parser.open', mock_open()) as mock_file:
		tree.create_html(mock_filepath)
		assert call(mock_filepath, 'w') in mock_file.mock_calls
		assert call('mocked html string') in mock_file().write.mock_calls
	
@patch('rss_parser.rss_parser.Tree.__init__', return_value=None)
@patch('rss_parser.rss_parser.Tree.article_to_html', return_value='mocked html string\n\t\t\t\t\t')
@pytest.mark.parametrize(
	('LIMIT', 'PAGE_TITLE', 'expected'),
	(
		(1, None, '''
			<!DOCTYPE html>
				<html>
					<head>
						<title>TODAY</title>
					</head>
					<body>

					mocked html string\n\t\t\t\t\t

					</body>
				</html>
			''',),
		(-1, 'sample page title', '''
			<!DOCTYPE html>
				<html>
					<head>
						<title>sample page title</title>
					</head>
					<body>

					mocked html string\n\t\t\t\t\t

					</body>
				</html>
			''',),
	)
)
def test_to_html_string(mock_init, mock_article_to_html, LIMIT, PAGE_TITLE, expected):
	tree = Tree()
	Tree.ARTICLE_DIVS = ''
	Tree.TODAY = 'TODAY'
	Tree.LIMIT = LIMIT
	dummy_dict['news_feed_title'] = PAGE_TITLE
	actual = tree.to_html_string([dummy_dict])
	assert actual == expected

@patch('rss_parser.rss_parser.Tree.__init__', return_value=None)
@pytest.mark.parametrize(
	('content', 'news_feed_title', 'expected'),
	(
		(True, True, '''
					<div>
						<h2>Default feed title</h2>
						<img src="fake-img-link.com" alt="" width="60% of window">
						<img src="fake-img-link.org" alt="" width="60% of window">\n\t\t\t\t\t\t
						<p>Default src value</p>
						<h3>Default title value</h3>
						<p>Default news_date value</p>
						<p>Default description value</p>
						<a href="sample-url.com">sample-url.com</a>\n\t\t\t\t\t\t
					</div>'''),
		(False, False, '''
					<div>
						
						<p>Default src value</p>
						<h3>Default title value</h3>
						<p>Default news_date value</p>
						<p>Default description value</p>
						<a href="sample-url.com">sample-url.com</a>
						<a href="sample-url.org">sample-url.org</a>\n\t\t\t\t\t\t
					</div>'''),
	)
)
def test_article_to_html(mock_init, content, news_feed_title, expected):
	tree = Tree()
	dummy_dict['news_feed_title'] = 'Default feed title'
	if not news_feed_title:
		Tree.ARTICLE_DIVS = dummy_dict['news_feed_title']
	if content: dummy_dict['news_url'] = 'sample-url.com (link)\nfake-img-link.com (content)\nfake-img-link.org (content)'
	else: dummy_dict['news_url'] = 'sample-url.com (link)\nsample-url.org (link)'
	actual = tree.article_to_html(dummy_dict)
	assert actual == expected

@patch('rss_parser.rss_parser.Tree.__init__', return_value=None)
@patch('rss_parser.rss_parser.Tree.create_html', )
@patch('pdfkit.from_file', )
def test_create_pdf(mock_pdfkit_from_file, mock_create_html, mock_init):
	tree = Tree()
	Tree.temp_html_path = mock_filepath
	Tree.PDF_FILEPATH = sample_filepath
	tree.create_pdf()
	assert call(mock_filepath) in mock_create_html.mock_calls
	assert call(input=mock_filepath, output_path=sample_filepath) in mock_pdfkit_from_file.mock_calls

@patch('os.path.isfile', return_value=False)
@patch('rss_parser.rss_parser.Tree.__init__', return_value=None)
@patch('sqlite3.connect')
def test_db_connection_1(mock_db, mock_init, mock_isfile):
	tree = Tree()
	db = tree.db_connection(mock_filepath)
	assert call(mock_filepath) in mock_db.mock_calls
	db.close()

@patch('rss_parser.rss_parser.Tree.__init__', return_value=None)
@patch('os.path.isfile', return_value=False)
def test_db_connection_2(mock_isfile, mock_init, ):
	tree = Tree()
	db = tree.db_connection('file::memory:?cache=shared')
	cursor = db.cursor()
	cursor.execute("SELECT name FROM sqlite_master")
	result = cursor.fetchone()
	assert 'cached_news' in result
	db.close()
			

@patch('rss_parser.rss_parser.Tree.__init__', return_value=None)
def test_db_insert_cached_one(mock_init, ):
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
	tree = Tree()
	tree.CACHE[0] = dummy_dict
	db = tree.db_connection('file::memory:?cache=shared')
	tree.db_insert_cached_one(db)
	cursor = db.cursor()
	cursor.execute("SELECT * FROM cached_news")
	result = cursor.fetchone()
	assert dummy_dict['news_title'] in result
	db.close()
	Tree.CACHE = []


@patch('rss_parser.rss_parser.Tree.__init__', return_value=None)
@patch('rss_parser.rss_parser.Tree.cache_news')
@pytest.mark.parametrize(
	('k', 'v'),
	(
		(None, None),
		('news_title', 'Default title value'),
	)
)
def test_db_fetch_news(mock_cache_news, mock_init, k, v):
	tree = Tree()
	Tree.CACHE.append(dummy_dict)
	db = tree.db_connection('file::memory:?cache=shared')
	tree.db_insert_cached_one(db)
	Tree.CACHE = []
	tree.db_fetch_news(db, k, v)
	assert call(dummy_dict) in mock_cache_news.mock_calls
	db.close()

@patch('rss_parser.rss_parser.Tree.__init__', return_value=None)
def test_cache_news(mock_init, ):
	tree = Tree()
	Tree.CACHE = []
	tree.cache_news(dummy_dict)
	assert dummy_dict in Tree.CACHE

@patch('rss_parser.rss_parser.Tree.__init__', return_value=None)
def test_parse_title(mock_init):
	tree = Tree()
	element = MagicMock()
	element.text = 'Default title value'
	temp = {}
	tree.parse_title(element, temp)
	assert temp['news_title'] == element.text
	
@patch('rss_parser.rss_parser.Tree.__init__', return_value=None)
def test_parse_title(mock_init):
	tree = Tree()
	element = MagicMock()
	element.text = 'Fri, 03 Jun 2022 05:50:03 -0400'
	temp = {}
	tree.parse_date(element, temp)
	assert temp['news_date'] == '2022-06-03 05:50:03'

@patch('rss_parser.rss_parser.Tree.__init__', return_value=None)
@pytest.mark.parametrize(
	('input_x', 'expected', ),
	(
		({'news_url': ''}, '\nhttp://example.com (link)'),
		({}, 'http://example.com (link)'),
	)
)
def test_parse_link_1(mock_init, input_x, expected):
	tree = Tree()
	element = MagicMock()
	element.attrib = {'href': 'http://example.com'}
	temp = input_x
	tree.parse_link(element, temp)
	assert temp['news_url'] == expected

@patch('rss_parser.rss_parser.Tree.__init__', return_value=None)
@pytest.mark.parametrize(
	('input_x', 'expected', ),
	(
		({'news_url': ''}, '\nhttp://example.com (link)'),
		({}, 'http://example.com (link)'),
	)
)
def test_parse_link_2(mock_init, input_x, expected):
	tree = Tree()
	element = MagicMock()
	element.text = 'http://example.com'
	temp = input_x
	tree.parse_link(element, temp)
	assert temp['news_url'] == expected

@patch('rss_parser.rss_parser.Tree.__init__', return_value=None)
@patch('rss_parser.rss_parser.Tree.parse_html')
@patch('lxml.html.fragments_fromstring', return_value='dummy string 1')
def test_parse_description_1(mock_fragments_fromstring, mock_parse_html, mock_init, ):
	tree = Tree()
	element = MagicMock()
	element.attrib = {'type': 'html'}
	element.text = 'dummy string 2'
	temp = {}
	tree.parse_description(element, temp)
	assert call('dummy string 2') in mock_fragments_fromstring.mock_calls
	assert call('dummy string 1', temp) in mock_parse_html.mock_calls

@pytest.mark.parametrize(
	('input_x', 'flag', 'dict_', ), 
	(
		('<![CDATA[<p>dummy string 2</p>]]>', None, {}),
		('<![CDATA[<ABC><p>dummy string 2</p><XYZ>]]>', None, {}),
		('<![CDATA[<img href="https://www.example.com/"><p>dummy string 2</p>]]>', 1, {}), # flag is 1 if self-closing tag is before enclosing tags
		('<![CDATA[Default description text<p>dummy string 2</p>]]>', 2, {'news_description': ''}), # flag is 2 if text with no tags is before enclosing tags
		('<![CDATA[Default description text<p>dummy string 2</p>]]>', 3, {}), # flag is 3 if 'news_description' key exists in dictionary
		('dummy string 2', 4, {}),
	)
)
@patch('rss_parser.rss_parser.Tree.__init__', return_value=None)
@patch('rss_parser.rss_parser.Tree.parse_html')
@patch('lxml.html.fragments_fromstring', return_value='dummy string 1')
def test_parse_description_2(mock_fragments_fromstring, mock_parse_html, mock_init, input_x, flag, dict_, ):
	tree = Tree()
	element = MagicMock()
	element.text = input_x 
	temp = dict_
	tree.parse_description(element, temp)
	if flag == 1:
		assert call('<img href="https://www.example.com/">') in mock_fragments_fromstring.mock_calls
	if flag == 2:
		assert temp['news_description'] == "\nDefault description text"
	if flag == 3:
		assert temp['news_description'] == "Default description text"
	if flag == 4:
		assert temp['news_description'] == "dummy string 2"
	else:
		assert call('<p>dummy string 2</p>') in mock_fragments_fromstring.mock_calls
		assert call('dummy string 1', temp) in mock_parse_html.mock_calls

@pytest.mark.parametrize(
	('flag', 'node_tag', 'child_tag', 'c_text', 'dict_'),
	(	(1, 'p', None, None, {}),
		(2, 'div', None, None, {}),
		(3, 'img', None, None, {}),
		(4, 'a', None, None, {}),
		(5, None, 'div', None, {}),
		(6, None, 'p', None, {}),
		(7, None, 'img', None, {}),
		(8, None, 'a', None, {}),
		(9, None, 'ul', 'Default description text', {'news_description': ''}),
		(10, None, 'ul', 'Default description text', {}),
		(False, None, None, 'Default description text', {}),
	)
)
@patch('rss_parser.rss_parser.Tree.__init__', return_value=None)
@patch('rss_parser.rss_parser.Tree.parse_div_p')
@patch('rss_parser.rss_parser.Tree.parse_img')
@patch('rss_parser.rss_parser.Tree.parse_a')
def test_parse_html(mock_parse_a ,mock_parse_img, mock_parse_div_p, mock_init, flag, node_tag, child_tag, c_text, dict_):
	tree = Tree()
	temp = dict_
	node = MagicMock()
	child = MagicMock()
	c = MagicMock()
	nodes = [node]
	node.getchildren.return_value = [child]
	child.getchildren.return_value = [c]
	node.tag = node_tag
	child.tag = child_tag
	c.text = c_text
	tree.parse_html(nodes, temp)
	if flag in [1,2,5,6]:
		assert len(mock_parse_div_p.mock_calls) > 0
	if flag in [3,7]:
		assert len(mock_parse_img.mock_calls) > 0
	if flag in [4,8]:
		assert len(mock_parse_a.mock_calls) > 0
	if flag == 9:
		assert len(child.getchildren.mock_calls) > 0
		assert temp['news_description'] == '\nDefault description text'
	if flag == 10:
		assert len(child.getchildren.mock_calls) > 0
		assert temp['news_description'] == 'Default description text'

@pytest.mark.parametrize(
	('getchildren', 'dict_'), 
	(
		([], {}),
		([], {'news_description': ''}),
		([MagicMock()], {}),
		([MagicMock()], {'news_description': ''}),
	)
)
@patch('rss_parser.rss_parser.Tree.__init__', return_value=None)
@patch('rss_parser.rss_parser.Tree.parse_html')
def test_parse_div_p(mock_parse_html, mock_init, getchildren, dict_, ):
	tree = Tree()
	temp = dict_
	node = MagicMock()
	node.getchildren.return_value = getchildren
	node.text_content.return_value = 'Default description text'
	if dict_ == {}:
		tree.parse_div_p(node, temp)
		assert temp['news_description'] == 'Default description text'
	else:
		tree.parse_div_p(node, temp)
		assert temp['news_description'] == '\nDefault description text'
	if len(getchildren) != 0:
		assert len(mock_parse_html.mock_calls) > 0

@pytest.mark.parametrize(
	('dict_', ), 
	(
		({}, ),
		({'news_url': ''}, ),
	),
)
@patch('rss_parser.rss_parser.Tree.__init__', return_value=None)
def test_parse_img(mock_init, dict_, ):
	tree = Tree()
	temp = dict_
	node = MagicMock()
	node.attrib.__getitem__.return_value = 'http://image-link.com/'
	if dict_ == {}:
		tree.parse_img(node, temp)
		assert temp['news_url'] == 'http://image-link.com/ (content)'
	else:
		tree.parse_img(node, temp)
		assert temp['news_url'] == '\nhttp://image-link.com/ (content)'

@pytest.mark.parametrize(
	('dict_', ), 
	(
		({}, ),
		({'news_url': ''}, ),
	),
)
@patch('rss_parser.rss_parser.Tree.__init__', return_value=None)
def test_parse_a(mock_init, dict_, ):
	tree = Tree()
	temp = dict_
	node = MagicMock()
	node.attrib.__getitem__.return_value = 'http://example.com/'
	if dict_ == {}:
		tree.parse_a(node, temp)
		assert temp['news_url'] == 'http://example.com/ (link)'
	else:
		tree.parse_a(node, temp)
		assert temp['news_url'] == '\nhttp://example.com/ (link)'




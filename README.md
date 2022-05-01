# Command line tool for parsing XML format RSS feeds.


```rss_parser -h
usage: rss_parser [-h] [--version] [--json] [--log FILEPATH] [--date [DATE]] [--source SOURCE] [--verbose] [--limit [LIMIT]] [--pdf [FILEPATH]]
                  [--html [FILEPATH]]
                  [URL]

tool for parsing RSS feeds

positional arguments:
  URL                URL to XML format RSS feed

optional arguments:
  -h, --help         show this help message and exit
  --version          print version info
  --json             print result as JSON in stdout
  --log FILEPATH     sets logging level to logging.DEBUG
  --date [DATE]      outputs articles from specified date
  --source SOURCE    outputs articles from specified source
  --verbose          output verbose status messages
  --limit [LIMIT]    limit news topics, if provided
  --pdf [FILEPATH]   export result as PDF to provided destination, might take time for downloading images
  --html [FILEPATH]  export result as HTML to provided destination
```


If [URL] is provided fetches and outputs news articles to stdout.
Before exiting articles are saved in a database and can be fetched back in [URL] is omitted:

```rss_parser https://news.yahoo.com/rss --limit 1
					
____________________________________________
					
Feed: Yahoo News - Latest News & Headlines
					
Source: https://news.yahoo.com/rss
					
____________________________________________
					
Title: Evidence mounts of GOP involvement in Trump election schemes
					
____________________________________________
					
Date: 2022-05-01 11:51:11

					

					
Links:
					
https://news.yahoo.com/evidence-mounts-gop-involvement-trump-115111526.html (link)
https://s.yimg.com/uu/api/res/1.2/P2YsUZB5orq4C22KCWHs1g--~B/aD0yOTY5O3c9NDQ1MzthcHBpZD15dGFjaHlvbg--/https://media.zenfs.com/en/ap.org/1c7ea04927bc22093ed0bd260bf2a4d6 (content)
```				


```rss_parser --limit 1
			
					
____________________________________________
					
Feed: Yahoo News - Latest News & Headlines
					
Source: https://news.yahoo.com/rss
					
____________________________________________
					
Title: Evidence mounts of GOP involvement in Trump election schemes
					
____________________________________________
					
Date: 2022-05-01 11:51:11

					

					
Links:
					
https://news.yahoo.com/evidence-mounts-gop-involvement-trump-115111526.html (link)
https://s.yimg.com/uu/api/res/1.2/P2YsUZB5orq4C22KCWHs1g--~B/aD0yOTY5O3c9NDQ1MzthcHBpZD15dGFjaHlvbg--/https://media.zenfs.com/en/ap.org/1c7ea04927bc22093ed0bd260bf2a4d6 (content)

```

if [--html] or [--pdf] is specified, corresponding file is created in provided [FILEPATH] or by default in package directory.


if [--json] is specified output is in JSON format
```rss_parser --limit 1 --json

{"date": "2022-05-01", "news_feed_title": "Yahoo News - Latest News & Headlines", "news_src": "https://news.yahoo.com/rss", "news_title": "Evidence mounts of GOP involvement in Trump election schemes", "news_date": "2022-05-01 11:51:11", "news_description": "", "news_url": "https://news.yahoo.com/evidence-mounts-gop-involvement-trump-115111526.html (link)\nhttps://s.yimg.com/uu/api/res/1.2/P2YsUZB5orq4C22KCWHs1g--~B/aD0yOTY5O3c9NDQ1MzthcHBpZD15dGFjaHlvbg--/https://media.zenfs.com/en/ap.org/1c7ea04927bc22093ed0bd260bf2a4d6 (content)"}
```
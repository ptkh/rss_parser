"""	Module for parsing XML format RSS feeds.
	
	<class 'Tree'> with methods for fetching and parsing XML document from provided url, caching news in database, converting result to json, html, pdf format.

    <class 'FeedParserException'> custom exception class for exception handling.

    <function 'logging_basicConfig'> for setting logging level for this module.

	<function 'rss_arg_parser'> creates <class 'ArgumentParser' object with following arguments: 
    url	, --version, --json, --date, --source, --verbose, --limit, --pdf, --html, --log"""
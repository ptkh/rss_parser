from setuptools import setup

setup(
   name='rss_parser',
   version='0.0.1',
   description='XML format RSS feed parser',
   author='Khachidze Paata',
   author_email='peterkhachidze@gmail.com',
   packages=['rss_parser'],  
   entry_points={
        'console_scripts': [
            'rss_parser=rss_parser.rss_parser:main'
        ]
    },
)
# you2rss
YouTube subscriptions to RSS podcast feeds and web interface

Django application that parses your subscriptions and creates RSS feeds for each of them. 
When requesting an item from the feed the item is downloaded, converted to audio only, and returned. 
Also provides a web interface for browsing your subscriptions, their videos, and 

Requires a Google API key!
Requires django, django_cron, youtube-dl and feedgen

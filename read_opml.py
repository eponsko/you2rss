#!/usr/bin/env python
import os
import requests
os.environ['DJANGO_SETTINGS_MODULE'] = 'hominem.settings'
import django
from django.utils import timezone
import json
import datetime
django.setup()
from you2rss.models import Channel, Video, Podcast, Pod
from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
import logging
import feedparser
from pprint import pprint
log = logging.getLogger(__name__)


class UpdateChannels():
    RUN_EVERY_MINS = 120
    code = 'you2rss.cron.cleanup'

    def do(self):
        log.info('Updating videos')
        try: 
            self.update_subscriptions()
        except Exception as e:
            log.error("Caught exception while updating subscriptions")
            log.error(str(e))
        try:
            self.update_all_videos()
        except Exception as e:
            log.error("Caught exception while updating videos")
            log.error(str(e))

    def update_subscriptions(self):
        log.info('running update subscriptions')
        head = {'referer': 'http://' + 'www.hominem.se'}
        payload = {'key': settings.APIKEY,
                   'part': 'snippet',
                   'channelId': 'UCvVx_jTHBKt0HW-iEkZnXTg',
                   'maxResults': '50'}
        nextpage = None
        more = True
        while more:
            try:
                r = requests.get('https://www.googleapis.com/youtube/v3/subscriptions', headers=head, params=payload)
            except requests.RequestException as e:
                log.error("Exception in requests.get when searching: " + str(e))
                return

            subscriptions = json.loads(r.text)
            if 'nextPageToken' in subscriptions:
                nextpage = subscriptions['nextPageToken']
                payload['pageToken'] = nextpage
                more = True
            else:
                nextpage = None
                more = False

            existing_subs = Channel.objects.all()
            log.info('Got ' + str(len(subscriptions['items'])) + ' subscriptions')
            for sub in subscriptions['items']:
                s = sub['snippet']
                title = s['title']
                channelId = s['resourceId']['channelId']
                publishedAt = timezone.datetime.strptime(s['publishedAt'], '%Y-%m-%dT%H:%M:%S.%fZ')
                pub = timezone.make_aware(publishedAt, timezone=None)
                description = s['description']
                thumb = s['thumbnails']['default']['url']

                channels = Channel.objects.filter(title_text=title)
                if len(channels) == 0:
                    q = Channel(channel_id=channelId, title_text=title, description_text=description, thumbnail=thumb,
                            pub_date=pub,latest_video=pub)
                    q.save()
                    log.info("Added new channel: " + title)
                else:
                    log.info("Channel " + title + "already exists")

    def update_all_videos(self):
        try:
            for channel in Channel.objects.all():
                self.update_videos(channel)

        except Exception as e:
            log.error("Caught exception when updating all videos")
            log.error(e)

    def update_videos(self, channel):
        log.info('Updating videos for channel "' + channel.title_text + '"')
        head = {'referer': 'http://' + 'www.hominem.se'}
        payload = {'key': settings.APIKEY,
                   'part': 'snippet',
                   'order': 'date',
                   'channelId': channel.channel_id,
                   'maxResults': '50'}
        nextpage = None
        more = True
        videos = channel.video_set.order_by('pub_date')
        latest = None
        numvideos = 0
        if videos:
            last_pub = videos.last().pub_date
            latest = last_pub + datetime.timedelta(0, 60)

        if latest:
            payload['publishedAfter'] = latest.isoformat()
            log.info('Latest local video from ' + str(latest) + ' in channel "' + channel.title_text + '"')
        else:
            log.info('No latest video found, new channel ' + channel.title_text)

        while more:
            try:
                r = requests.get('https://www.googleapis.com/youtube/v3/search', headers=head, params=payload)
            except requests.RequestException as e:
                log.error("Exception in requests.get when searching: " + str(e))
                return

            videos = json.loads(r.text)
            if 'error' in videos:
                log.error(videos['error'])
                log.error("request was " + r.url)
                return

            totalvideos = videos['pageInfo']['totalResults']
            numitems = 0
            if 'items' in videos:
                for item in videos['items']:
                    if 'youtube#video' in item['id']['kind']:
                        numvideos += 1
                    else:
                        numitems += 1

            log.info("Got " + str(numvideos) + " videos of " + str(totalvideos) + '. Got ' + str(numitems) + ' items.')

            if 'nextPageToken' in videos:
                nextpage = videos['nextPageToken']
                payload['pageToken'] = nextpage
                more = True
            else:
                nextpage = None
                more = False

            self.insert_videos(channel, videos, latest)

    def insert_videos(self, channel, videos, latest):
        log.info('insert_videos called :  ' + str(videos))
        try:
            for item in videos['items']:
                log.info('item in resp: ' + str(item))
                if not 'youtube#video' in item['id']['kind']:
                    continue
                videoId = item['id']['videoId']
                s = item['snippet']
                publishedAt = timezone.datetime.strptime(s['publishedAt'], '%Y-%m-%dT%H:%M:%S.%fZ')
                title = s['title']
                pub = timezone.make_aware(publishedAt, timezone=None)
                description = s['description']
                thumb = s['thumbnails']['default']['url']
                if len(channel.video_set.filter(title_text=title)) == 0:
                    v = channel.video_set.create(video_id=videoId,
                                                 title_text=title,
                                                 description_text=description,
                                                 thumbnail=thumb,
                                                 pub_date=publishedAt)
                    log.info("Created video " + str(v) + "published at " + publishedAt.isoformat())
                    v.save()
                    channel.latest_video = publishedAt
                    channel.save()
                else:
                    log.info('Video ' + title + ' already exists locally')
        except Exception as e:
            log.info("Caught exception " + str(e))

    def update_videos_for(self, channeltitle):
        channel = Channel.objects.get(title_text=channeltitle)
        if channel:
            self.update_videos(channel)

    def delete_videos_for(self, channeltitle):
        channel = Channel.objects.get(title_text=channeltitle)
        if channel:
            for video in channel.video_set.all():
                video.delete()

    def delete_all_channels(self):
        for channel in Channel.objects.all():
            channel.delete()

    def print_all_channels(self):
        for channel in Channel.objects.all():
            log.info(str(channel))

    def latest_video(self, channel):
        videos = channel.video_set.order_by('pub_date')
        if videos:
            log.info("Oldest: " + str(videos.first().pub_date) + " Latest: " + str(videos.last().pub_date))
            log.info("Setting latest video")
            channel.latest_video = videos.last().pub_date
            channel.save()

    def check_latest_in_channels(self):
        for channel in Channel.objects.all():
            self.latest_video(channel)

class UpdatePodcasts():
    RUN_EVERY_MINS = 120
    code = 'you2rss.cron.cleanup'

    def do(self):
        log.info('Updating videos')
        try: 
            self.update_subscriptions()
        except Exception as e:
            log.error("Caught exception while updating subscriptions")
            log.error(str(e))
        try:
            self.update_all_videos()
        except Exception as e:
            log.error("Caught exception while updating videos")
            log.error(str(e))

            
    def update_all_podcasts(self):
        try:
            for podcast in Podcast.objects.all():
                self.update_podcast(podcast)

        except Exception as e:
            log.error("Caught exception when updating all videos")
            log.error(e)
        
    def update_podcast(self, podcast):
        log.info('Updating pods for podcast "' + podcast.title_text + '"')
        from time import mktime
        list_of_pods = podcast.pod_set.order_by('-pub_date')
        d = feedparser.parse(podcast.rss_link)
        if d['status'] != 200:
            log.error("feedparser error: " + str(d['status']))
            return
        for n in d.entries:
            skip = False
            for existing in list_of_pods:
                if n.title  == existing.title_text:
                    skip = True
            if not skip:
                publishedAt = timezone.datetime.fromtimestamp(mktime(n.published_parsed))
                fileUrl = n.link
                for enc in n.enclosures:
                    if "audio" in enc.type:
                        fileUrl = enc.href                
                
                pod = podcast.pod_set.create(pod_id=n.id, title_text=n.title,
                                             description_text=n.description,
                                             pub_date=publishedAt,
                                             audio_link=fileUrl,
                                             http_link=n.link)
                log.info("Created pod "+ n.title + " published at " + n.published)
                pod.save()
                podcast.save()
                
                
        list_of_pods = podcast.pod_set.order_by('-pub_date')
        if len(list_of_pods) > 0:
            podcast.latest_pod = list_of_pods[0].pub_date
            podcast.save()
        
    def read_opml(self, filename):
        rssList = []
        log.info("Reading OPML: " + str(filename))
        import xml.etree.ElementTree as ET
        tree = ET.parse(filename)
        root = tree.getroot()
        for child in root:
            if 'body' in child.tag:
                for item in child:
                    if 'outline' in item.tag:
                        if 'xmlUrl' in item.attrib:
                            rssList.append(item.attrib['xmlUrl'])
        for entry in rssList:
            self.add_podcast_rssfeed(entry)
            
    def add_podcast_rssfeed(self, rssfeed):
            r = 0
            if 'you2rss' in rssfeed:
                log.error("Not adding you2rss feed to you2rss!")
                return False
            print("Adding RSS feed: " + rssfeed)                
            d = feedparser.parse(rssfeed)
            if d['status'] != 200:
                print("feedparser error: " + str(d['status']))
                return False
            else:                
                imageUrl = "" 
                if 'href' in d.feed.image:
                    imageUrl = d.feed.image['href']
                
                publishedAt = timezone.datetime(2000,12,15)

                q = Podcast(title_text=d.feed.title, description_text=d.feed.description, thumbnail=imageUrl,rss_link=rssfeed,
                            http_link=d.feed.link, pub_date=publishedAt, latest_pod=publishedAt)
                q.save()
                return q
                
    def update_podcast_deletefirst(self, podcastid):
        from time import mktime
        podcast = 0
        try:
            podcast = Podcast.objects.get(id=podcastid)
            for pod in podcast.pod_set.all():
                pod.delete()
                
            list_of_pods = podcast.pod_set.order_by('-pub_date')
            if len(list_of_pods) > 0:
                podcast.latest_pod = list_of_pods[0].pub_date
                podcast.save()

        except Exception as e:
            print("Could not find podcast ", podcastid)
            return
        print "RSS link: " + podcast.rss_link
        d = feedparser.parse(podcast.rss_link)
        if d['status'] != 200:
            print("feedparser error: " + str(d['status']))
            return
        skip = False
        for n in d.entries:
            for existing in list_of_pods:
                if n.title  == existing.title_text:
                    skip = True
            if not skip:
                publishedAt = timezone.datetime.fromtimestamp(mktime(n.published_parsed))
                fileUrl = n.link
                for enc in n.enclosures:
                    if "audio" in enc.type:
                        fileUrl = enc.href                
                
                pod = podcast.pod_set.create(pod_id=n.id, title_text=n.title,
                                             description_text=n.description,
                                             pub_date=publishedAt,
                                             audio_link=fileUrl,
                                             http_link=n.link)
                log.info("Created pod "+n.title + " published at " + n.published)
                pod.save()
                podcast.save()
            else:
                print("Not adding, already exists")
                
                
        list_of_pods = podcast.pod_set.order_by('-pub_date')
        if len(list_of_pods) > 0:
            podcast.latest_pod = list_of_pods[0].pub_date
            podcast.save()

                
if __name__ == '__main__':

    import argparse

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(title='subcommands',
                                       description='valid subcommands',
                                       help='additional help',
                                       dest='command')

    channel_parser = subparsers.add_parser('channel', help='channels help')
    podcast_parser = subparsers.add_parser('podcast', help='podcasts help')

    subpodcast_parser = podcast_parser.add_subparsers(title='podcastsubcommand',
                                                      description='valid podcast subcommands',
                                                      help='additional help',
                                                      dest='action')

    subpodcast_parser.add_parser('updateall')
    subpodcast_parser.add_parser('latest')
    subpodcast_parser.add_parser('deleteall')
    podcast_opml = subpodcast_parser.add_parser('opml')
    podcast_update = subpodcast_parser.add_parser('update')
    podcast_rss = subpodcast_parser.add_parser('rss')

    podcast_opml.add_argument('NAME', help="name of opml file to read")
    podcast_update.add_argument('NAME', help="ID of podcast to update")
    podcast_rss.add_argument('RSS', help="Add podcast RSS feed")
    
    subchannel_parser = channel_parser.add_subparsers(title='channelsubcommand',
                                                      description='valid channel subcommands',
                                                      help='additional help',
                                                      dest='action')
    subchannel_parser.add_parser('updateall')
    subchannel_parser.add_parser('latest')
    subchannel_parser.add_parser('deleteall')

    channel_update = subchannel_parser.add_parser('update')
    channel_delete = subchannel_parser.add_parser('delete')

    channel_update.add_argument('NAME', help="name of channel to update")
    channel_delete.add_argument('NAME', help="name of channel to delete")

    video_parser = subparsers.add_parser('videos', help='video help')
    video_parser.add_argument('delete')
    video_parser.add_argument('update')
    args = parser.parse_args()
    print args
    if args.command == 'channel':
        a = UpdateChannels()
        if args.action == 'updateall':
            print("Updating all channels..")
            a.update_subscriptions()
            a.update_all_videos()
        elif args.action == 'update':
            print("Updating channel '" + args.NAME + "'")
            a.update_videos_for(args.NAME)
        elif args.action == 'latest':
            print("Checking latest in channels")
            a.check_latest_in_channels()
        elif args.action == 'deleteall':
            print("delete all channels")
        elif args.action == 'delete':
            print("delete channel " + args.NAME)
        else:
            print("unknown channel command!")
    elif args.command == 'podcast':
        a = UpdatePodcasts()
        if args.action == 'updateall':
            a.update_all_podcasts()
            # a.update_subscriptions()
           # a.update_all_videos()
        elif args.action == 'latest':
            print("Checking latest in podcasts")
           # a.check_latest_in_channels()
        elif args.action == 'deleteall':
            print("delete all podcasts")            
        elif args.action == 'opml':
            a.read_opml(args.NAME)
        elif args.action == 'update':
            a.update_podcast(args.NAME)
        elif args.action == 'rss':
            podcast = a.add_podcast_rssfeed(args.RSS)
            if podcast:
                a.update_podcast(podcast)
        else:
            print("unknown podcast command!")

        #    check_latest_in_channels()
#    a.update_subscriptions()
#    a.update_all_videos()
    # update_videos_for('Veritasium')
    # delete_videos_for('quite1nteresting')
    # delete_all_channels()
    # print_all_channels()



#!/usr/bin/env python
import os
# os.environ['DJANGO_SETTINGS_MODULE'] = 'hominem.settings'
# import django
# django.setup()
from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.utils import timezone
from django_cron import CronJobBase, Schedule
from glob import glob
from models import Channel, Video
import datetime
import json
import logging
import requests

log = logging.getLogger(__name__)


class CleanUpFiles(CronJobBase):
    RUN_EVERY_MINS = 240
    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)
    code = 'you2rss.cron.cleanup'

    def do(self):
        try:
            log.info('Cleaning up downloaded files')
            files = glob(settings.STATIC_ROOT + '/files/*_out.*')
            log.info('Found ' + str(len(files)) + ' files')
            for file in files:
                log.info('Deleting ' + file)
                os.remove(file)
        except Exception as e:
            log.info(e)


class UpdateChannels(CronJobBase):
    RUN_EVERY_MINS = 120
    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)
    code = 'you2rss.cron.cleanup'

    def do(self):
        log.info('Updating videos')
        #        self.update_subscriptions()
        self.update_all_videos()

    def update_subscriptions(self):
        log.info('running update subscriptions')
        head = {'referer': 'http://' + 'www.hominem.se'}
        payload = {'key': settings.APIKEY,
                   'part': 'snippet',
                   'channelId': 'UCvVx_jTHBKt0HW-iEkZnXTg',
                   'maxResults': '50'}

        r = requests.get('https://www.googleapis.com/youtube/v3/subscriptions', headers=head, params=payload)
        subscriptions = json.loads(r.text)
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
                            pub_date=pub)
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


if __name__ == '__main__':

    import argparse

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(title='subcommands',
                                       description='valid subcommands',
                                       help='additional help',
                                       dest='command')
    channel_parser = subparsers.add_parser('channel', help='channels help')

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
    a = UpdateChannels()
    if args.command == 'channel':
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

            #    check_latest_in_channels()
    a.update_subscriptions()
    a.update_all_videos()
    # update_videos_for('Veritasium')
    # delete_videos_for('quite1nteresting')
    # delete_all_channels()
    # print_all_channels()

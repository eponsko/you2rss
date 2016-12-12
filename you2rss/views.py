import os
from concurrent.futures import ThreadPoolExecutor
import youtube_dl
from django.http import HttpResponse, FileResponse, Http404, HttpResponseRedirect
from django.template import loader
from django.urls import reverse
from django.contrib.sites.shortcuts import get_current_site
from feedgen.feed import FeedGenerator
from django.shortcuts import redirect
from django.conf import settings
import time
import mimetypes
import glob
import logging
from .models import Channel, Video

try:
    FileNotFoundError
except NameError:
    # py2
    FileNotFoundError = IOError

executor = ThreadPoolExecutor(max_workers=4)
mimetypes.init()

log = logging.getLogger(__name__)

downloaded_file = None


def my_hook(d):
    if d['status'] == 'finished':
        global downloaded_file
        downloaded_file = d['filename']
        log.info('Download of "' + downloaded_file + '" complete. Time: ' + d['_elapsed_str'] + ' size: ' + d[
            '_total_bytes_str'] + ' , converting it...')


def index(request):
    return redirect('you2rss:channels')


def listchannels(request):
    #    latest_channel_list = Channel.objects.order_by('title_text')
    latest_channel_list = Channel.objects.order_by('-latest_video')
    template = loader.get_template('you2rss/index.html')
    context = {
        'latest_channel_list': latest_channel_list,
    }
    return HttpResponse(template.render(context, request))


def listvideos(request):
    return HttpResponse('Video list')


def listvideoschannel(request, channel_id):
    channel = Channel.objects.get(channel_id=channel_id)
    video_list = channel.video_set.all()
    template = loader.get_template('you2rss/videos.html')
    context = {
        'video_list': video_list,
        'channel_title': channel.title_text,
        'channel_thumb': channel.thumbnail,
        'description': channel.description_text
    }
    return HttpResponse(template.render(context, request))


def rsschannels(request):
    return HttpResponse('combined rss feed here')


def test(request, vid):
    data = '''
    <table>
    <tr> <td>%s</td> </tr>
    <tr><td>%s</td></tr>
    <tr><td>%s</td></tr>
    <tr><td>%s</td></tr>
    </table>
    '''
    return HttpResponse(data)


def rssvideoschannel(request, channel_id):
    channel = Channel.objects.get(channel_id=channel_id)
    if not channel:
        return Http404

    videos = channel.video_set.order_by('-pub_date')
    fg = FeedGenerator()
    fg.load_extension('podcast')

    channelURL = ''.join(['http://', get_current_site(request).domain,
                          reverse('you2rss:videoperchannel', args=(channel_id,))])
    fg.id(channelURL)
    fg.title(channel.title_text)
    fg.author({'name': 'pon sko', 'email': 'john@example.de'})
    fg.link(href=channelURL, rel='alternate')
    description = channel.description_text
    if len(description) < 2:
        description = "no desc"
    fg.subtitle(description)
    fg.description(description)
    fg.language('en')
    fg.logo(logo=channel.thumbnail)
    fg.image(url=channel.thumbnail, title=channel.title_text)
    fg.podcast.itunes_image(channel.thumbnail)

    for video in videos:
        fe = fg.add_entry()
        fe.author(name=channel.title_text)
        videodesc = video.description_text
        if len(videodesc) < 2:
            videodesc = "no desc"
        fe.content(videodesc)
        fileURL = ''.join(['http://', get_current_site(request).domain,
                           reverse('you2rss:rssfile', args=(video.video_id,))])

        fe.enclosure(fileURL, '1337', 'audio/mpeg')
        fe.id(fileURL)
        fe.link(href=fileURL, rel='alternate')
        fe.podcast.itunes_image(video.thumbnail)
        fe.pubdate(video.pub_date)
        fe.published(video.pub_date)
        fe.title(video.title_text)

    rssdata = fg.rss_str(pretty=True)
    response = HttpResponse(rssdata, content_type='application/rss+xml; charset=UTF-8')
    response['Content-Length'] = len(rssdata)
    return response


def download(request, vid):
    executor.submit(startDownload, vid)
    template = loader.get_template('you2rss/started.html')
    context = {
        'vid': vid,
    }
    return HttpResponse(template.render(context, request))


def file(request, vid):
    filepath = settings.FILE_LOCATION + vid + '_out.*'
    txt = glob.glob(filepath)
    for textfile in txt:
        if os.path.exists(textfile):
            response = FileResponse(open(textfile, 'rb'))
            response['Content-Type'] = mimetypes.guess_type(textfile)[0]
            log.info(response['Content-Type'])
            response['Content-Length'] = os.path.getsize(textfile)
            return response
    return Http404


def rssfile(request, vid):
    filepath = settings.FILE_LOCATION + vid + '_out.*'
    txt = glob.glob(filepath)
    for textfile in txt:
        if os.path.exists(textfile):
            return HttpResponseRedirect('http://' + get_current_site(request).domain + '/' + textfile)
            response = FileResponse(open(textfile, 'rb'))
            response['Content-Type'] = mimetypes.guess_type(textfile)[0]
            response['Content-Length'] = os.path.getsize(textfile)
            return response
    startDownload(vid)
    txt = glob.glob(filepath)
    for textfile in txt:
        if os.path.exists(textfile):
            return HttpResponseRedirect('http://' + get_current_site(request).domain + '/' + textfile)
            response = FileResponse(open(textfile, 'rb'))
            response['Content-Type'] = mimetypes.guess_type(textfile)[0]
            response['Content-Length'] = os.path.getsize(textfile)
            return response
    return Http404


def startDownload(vid):
    v = Video.objects.get(video_id=vid)
    ydl_opts = {
        'format': 'worstaudio/worst',
        'keepvideo': 'false',
        'outtmpl': settings.FILE_LOCATION + vid + '_out.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'best'
        }],
        'logger': log,
        'progress_hooks': [my_hook],
    }

    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            url = 'http://www.youtube.com/watch/?v=' + vid
            log.info('Downloading of "' + vid + '" started')
            a = ydl.download([url])
            filepath = settings.FILE_LOCATION + vid + '_out.*'
            txt = glob.glob(filepath)

            log.info('Files found : ' + str(txt) + ' len: ' + str(len(txt)))

            if len(txt) == 1:
                log.info('Download and conversion successful')
                v.downloaded = True
                v.save()
            elif len(txt) > 1:
                # cleanup wasn't performed
                try:
                    log.info('Removing file "' + downloaded_file + '"')
                    os.remove(downloaded_file)
                except OSError:
                    log.error('Tried to delete file "' + downloaded_file + '" but failed')
                v.downloaded = True
                v.save()
            else:
                log.error('Download of "' + vid + '" failed, output file does not exist')

    except youtube_dl.DownloadError as e:
        log.error('exception downloadning: ' + str(e))
    except Exception as e:
        log.error('caught exception')
        log.error("I/O error({0}): {1}".format(e.errno, e.strerror))

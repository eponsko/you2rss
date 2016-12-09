from __future__ import unicode_literals
from django.utils.encoding import python_2_unicode_compatible
from django.db import models

# parse datetime from youtube
# datetime.datetime.strptime('2012-01-08T19:45:15.000Z', '%Y-%m-%dT%H:%M:%S.%fZ')

@python_2_unicode_compatible
# Create your models here.
class Channel(models.Model):
    channel_id = models.CharField(max_length=200)
    title_text = models.CharField(max_length=200)
    description_text = models.CharField(max_length=500)
    pub_date = models.DateTimeField('date published')
    thumbnail = models.CharField(max_length=200)
    latest_video = models.DateTimeField('latest video')
    def __str__(self):
        return self.title_text
@python_2_unicode_compatible
class Video(models.Model):
    channel = models.ForeignKey(Channel, on_delete=models.CASCADE)
    video_id = models.CharField(max_length=200)
    pub_date = models.DateTimeField('date published')
    title_text = models.CharField(max_length=200)
    description_text = models.CharField(max_length=2000)
    thumbnail = models.CharField(max_length=200)
    downloaded = models.BooleanField(default=False)
    def __str__(self):
        return self.title_text
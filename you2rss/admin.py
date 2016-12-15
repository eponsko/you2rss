from django.contrib import admin
from .models import Channel, Video
import logging

log = logging.getLogger(__name__)
# Register your models here.

def update_channel(modeladmin, request, queryset):
    log.info('admin: update_channel called ')
    for n in queryset:
        log.info("query : "+ str(n))
update_channel.short_description = "Update selected channels"

def update_latest_video(modeladmin, request, queryset):
    log.info('admin: update_latest_video called')
    for channel in queryset:
        videos = channel.video_set.order_by('-pub_date')
        if len(videos) > 0:
            if channel.latest_video != videos[0].pub_date:
                channel.latest_video = videos[0].pub_date
                log.info('Updateing latest_video to '+ str(channel.latest_video))
                channel.save()
update_latest_video.short_description = "Update latest video"

@admin.register(Channel)
class ChannelAdmin(admin.ModelAdmin):
    date_hierarchy = 'latest_video'
    ordering = ['title_text']
    list_display = ('title_text', 'latest_video',)
    actions = [update_channel, update_latest_video]

@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    date_hierarchy = 'pub_date'
    ordering = ['-pub_date']
    list_display = ('title_text', 'channel', 'pub_date',)
    list_filter = ('channel','pub_date',)

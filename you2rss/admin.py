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
        
@admin.register(Channel)
class ChannelAdmin(admin.ModelAdmin):
    date_hierarchy = 'latest_video'
    ordering = ['title_text']
    list_display = ('title_text', 'latest_video',)
    actions = [update_channel]

@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    date_hierarchy = 'pub_date'
    ordering = ['-pub_date']
    list_display = ('title_text', 'channel', 'pub_date',)
    list_filter = ('channel','pub_date',)

from django.conf.urls import url

from . import views

app_name = 'you2rss'
urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^channel$', views.listchannels, name='channels'),
    url(r'^video$', views.listvideos, name='videos'),
    url(r'^podkicker_backup\.opml$', views.generateopml, name='opml'),
    url(r'^channel/(?P<channel_id>[A-Za-z0-9_-]+)/$', views.listvideoschannel, name='videoperchannel'),
    url(r'^rss$', views.rsschannels, name='rsschannels'),
    url(r'^rss/(?P<channel_id>[A-Za-z0-9_-]+)/$', views.rssvideoschannel, name='rssvideoperchannel'),
    url(r'^download/(?P<vid>[A-Za-z0-9_-]+)/$', views.download, name='startdownload'),
    url(r'^file/(?P<vid>[A-Za-z0-9_-]+)/$', views.file, name='file'),
    url(r'^rssfile/(?P<vid>[A-Za-z0-9_-]+)/$', views.rssfile, name='rssfile'),
    url(r'^test/(?P<vid>[A-Za-z0-9_-]+)/$', views.test, name='test')

]

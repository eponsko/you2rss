from django.forms import ModelForm
from .models import Channel, Video, Podcast, Pod
class ChannelForm(ModelForm):
    class Meta:
        model = Channel
        fields = [ 'channel_id' ]


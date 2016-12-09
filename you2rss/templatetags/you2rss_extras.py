__author__ = 'eponsko'
import os
import glob
import logging
from django import template
register = template.Library()
log = logging.getLogger(__name__)

@register.filter(name='video_exists')
def video_exists(value):
    filepath = 'static/files/'+value+'_out.*'
    txt = glob.glob(filepath)
#    log.info('Files found : ' + str(txt) + ' len: ' + str(len(txt)) ) 
    if len(txt) > 0:
        return True
    return False


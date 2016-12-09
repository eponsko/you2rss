#!/bin/bash
NAME="hominem"                                     # Name of the application (*)
DJANGODIR=/var/www/hominem                         # Django project directory (*)
SOCKFILE=/run/gunicorn/gunicorn.sock               # we will communicate using this unix socket (*)
USER=www-data                                      # the user to run as (*)
GROUP=www-data                                     # the group to run as (*)
NUM_WORKERS=3                                      # how many worker processes should Gunicorn spawn (*)
DJANGO_SETTINGS_MODULE=hominem.settings            # which settings file should Django use (*)
DJANGO_WSGI_MODULE=hominem.wsgi                    # WSGI module name (*)

echo "Starting $NAME as `whoami`"

export DJANGO_SETTINGS_MODULE=$DJANGO_SETTINGS_MODULE

# Start your Django Unicorn
cd $DJANGODIR
echo "in directory $(pwd)"
exec gunicorn ${DJANGO_WSGI_MODULE} \
  --name $NAME \
  --workers $NUM_WORKERS \
  --user $USER \
  --bind=unix:$SOCKFILE \
  --pid $DJANGODIR/gunicorn.pid \
  --error-logfile=$DJANGODIR/error_logs.log \
  --log-syslog

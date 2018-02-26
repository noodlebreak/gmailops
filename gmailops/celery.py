from __future__ import absolute_import
import os
import sys

from celery import Celery
from django.conf import settings


PROJECT_ROOT = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'apps'))


# set the default Django settings module for the 'celery' program.
os.environ['DJANGO_SETTINGS_MODULE'] = 'gmailops.settings'

# import django
# django.setup()

app = Celery('gmailops', broker=settings.BROKER_URL)
app.config_from_object('django.conf:settings')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))


if __name__ == '__main__':
    app.start()

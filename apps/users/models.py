# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth.models import AbstractUser
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from jsonfield import JSONField

# Create your models here.


class User(AbstractUser):
    """
    Our custom user auth model, to hold Google OAuth creds of
    the user as well.
    """

    credentials = JSONField(default={})
    email = models.EmailField(max_length=320, blank=True, null=True, default=None)
    latest_history_id = models.CharField(max_length=30, blank=True)
    google_authorized = models.BooleanField(default=False)

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return "{}-{}".format(self.email, self.username)

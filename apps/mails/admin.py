# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.contrib import admin

from . import models


class MailAdmin(admin.ModelAdmin):
    search_fields = ['user__username', 'message_id', 'thread_id', 'labels']
    ordering = ['-date']


class UserCredentialAdmin(admin.ModelAdmin):
    search_fields = ['user__username']

admin.site.register(models.Mail, MailAdmin)

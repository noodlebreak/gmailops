# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.contrib import admin
from django.contrib.auth.models import User
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from jsonfield import JSONField


class Mail(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL)
    snippet = models.TextField(blank=True)
    attachment_id = models.TextField(blank=True)
    history_id = models.CharField(max_length=30, blank=True)
    thread_id = models.CharField(max_length=30, blank=True)
    thread_topic = models.CharField(max_length=500, blank=True)
    message_id = models.CharField(max_length=30, blank=True)
    email_from = models.TextField(blank=True)
    email_to = models.TextField(blank=True)
    email_cc = models.TextField(blank=True)
    email_bcc = models.TextField(blank=True)
    subject = models.TextField(blank=True)
    labels = models.CharField(max_length=1000, blank=True)
    date = models.DateTimeField(blank=True)
    text = models.TextField(blank=True)
    html = models.TextField(blank=True)

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = (('user', 'message_id'),)

    def __unicode__(self):
        return str(self.snippet[:15])


class Condition(models.Model):

    FC_FROM = 'email_from'
    FC_TO = 'email_to'
    FC_SUBJECT = 'subject'
    FC_MESSAGE = 'text'
    FC_DATE_RECEIVED = 'date'

    FIELD_CHOICES = (
        (FC_FROM, 'From'),
        (FC_TO, 'To'),
        (FC_SUBJECT, 'Subject'),
        (FC_MESSAGE, 'Message'),
        (FC_DATE_RECEIVED, 'Date Received'),
    )

    PC_CONTAINS = 'contains'
    PC_DOES_NOT_CONTAIN = 'does-not-contain'
    PC_EQUALS = 'equals'
    PC_DOES_NOT_EQUAL = 'does-not-equal'
    PC_LESS_THAN = 'lt'
    PC_GREATER_THAN = 'gt'

    PREDICATE_CHOICES = (
        (PC_CONTAINS, "Contains"),
        (PC_DOES_NOT_CONTAIN, "Does not contain"),
        (PC_EQUALS, "Equals"),
        (PC_DOES_NOT_EQUAL, "Does not equal"),
        (PC_LESS_THAN, "Less than"),
        (PC_GREATER_THAN, "Greater than"),
    )
    field = models.CharField(max_length=30, choices=FIELD_CHOICES)
    predicate = models.CharField(max_length=30, choices=PREDICATE_CHOICES)
    value = models.CharField(max_length=1000)

    def __unicode__(self):
        return "{}-{}-{}".format(self.get_field_display(), self.get_predicate_display(), self.value)


class Action(models.Model):
    AC_MARK_AS_READ = 'mark-read'
    AC_MARK_AS_UNREAD = 'mark-unread'
    AC_ARCHIVE = 'archive'
    AC_ADD_LABEL = 'add-label'
    ACTION_CHOICES = (
        (AC_MARK_AS_READ, 'Mark as read'),
        (AC_MARK_AS_UNREAD, 'Mark as unread'),
        (AC_MARK_AS_READ, 'Archive message'),
        (AC_ADD_LABEL, 'Add label'),
    )
    action_type = models.CharField(max_length=30, choices=ACTION_CHOICES)
    value = models.CharField(max_length=100, null=True, blank=True)  # Required only for label

    def __unicode__(self):
        return "{}-{}".format(self.get_action_type_display(), self.value)


class Rule(models.Model):
    QC_ALL = 'all'
    QC_ANY = 'any'
    QUANTIFIER_CHOICES = (
        (QC_ALL, 'All'),
        (QC_ANY, 'Any'),
    )

    name = models.CharField(max_length=100)
    predicate_quantifier = models.CharField(max_length=5, choices=QUANTIFIER_CHOICES)
    rules = models.ManyToManyField("mails.Condition")
    actions = models.ManyToManyField("mails.Action")

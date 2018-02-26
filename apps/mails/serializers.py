from django.conf import settings
from rest_framework import serializers

from . import models


class MailSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.Mail
        fields = ['id', 'user', 'snippet', 'attachment_id', 'history_id', 'thread_id', 'thread_topic',
                  'message_id', 'email_from', 'email_to', 'email_cc', 'email_bcc', 'subject', 'date']


class ConditionSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.Condition
        exclude = []


class ActionSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.Action
        exclude = []


class RuleSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.Rule
        exclude = []

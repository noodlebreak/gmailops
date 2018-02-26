import base64
import json
import os
import logging
import httplib2
from urlparse import urljoin

from googleapiclient.discovery import build
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.http import HttpResponseBadRequest
from django.http import HttpResponseRedirect
from django.views.generic import View
from django.shortcuts import render
from oauth2client.client import flow_from_clientsecrets

import google.auth.exceptions as google_auth_exceptions
import google.oauth2.credentials
import google_auth_oauthlib.flow
import googleapiclient.discovery
from rest_framework import filters as drf_filters
from rest_framework import permissions
from rest_framework import viewsets
from rest_framework.decorators import list_route
from rest_framework.response import Response

from users.models import User
from . import models
from . import serializers
from . import tasks


if settings.DEBUG:
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'


class MailViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.MailSerializer
    scopes = ['https://www.googleapis.com/auth/gmail.readonly',
              'https://www.googleapis.com/auth/gmail.send',
              'https://www.googleapis.com/auth/gmail.labels',
              'https://www.googleapis.com/auth/userinfo.email', ]
    filter_backends = (drf_filters.SearchFilter, drf_filters.DjangoFilterBackend, drf_filters.OrderingFilter)
    search_fields = ('snippet', 'subject', 'text')
    filter_fields = ('user__username', 'snippet', 'thread_id', 'thread_topic', 'subject', 'email_from',
                     'email_to', 'email_cc', 'email_bcc', 'text')
    ordering_fields = ('created', 'pk', )

    def get_queryset(self):
        qs = models.Mail.objects.filter(user=self.request.user)
        return qs

    def get_user_email(self, credentials):
        credentials = google.oauth2.credentials.Credentials(**credentials)
        user_info_service = googleapiclient.discovery.build(
            'oauth2',
            'v1',
            credentials=credentials,
            cache_discovery=False
        )
        user_info = user_info_service.userinfo().get().execute()
        return user_info.get('email')

    def run_watch(self, user_id):
        user = models.User.objects.get(pk=user_id)
        credentials = google.oauth2.credentials.Credentials(**user.credentials)
        service = googleapiclient.discovery.build('gmail', 'v1', credentials=credentials, cache_discovery=False)
        project = models.GSuiteAppCredential.objects.filter(project_name=settings.GSUITE_PROJECT_NAME).first()
        if (not project) or (project and project.topic_path):
            data = {
                'labelIds': ['INBOX', 'SENT'],
                'topicName': project.topic_path,
            }
            try:
                response = service.users().watch(userId='me', body=data).execute()
            except google_auth_exceptions.RefreshError as error:
                log_on_sentry(
                    'During watch: User remove access from app',
                    None,
                    'ERROR',
                    extra={
                        'username': user.username
                    }
                )
                return
            usercredential.latest_history_id = response["historyId"]
            usercredential.save()
        else:
            log_on_sentry(
                'Topic path not found in GSuiteAppCredential',
                None,
                'ERROR',
            )

    @list_route(methods=["get"], url_path="complete-sync")
    def complete_sync(self, request):
        tasks.pull_complete_messages(request.user.id)
        return Response({"status": True})

    @list_route(methods=["get"], url_path="partial-sync")
    def partial_sync(self, request):
        tasks.pull_partial_messages(request.user.id)
        return Response({"status": True})

    @list_route(methods=["post"], url_path="notify", permission_classes=[])
    def notify(self, request):
        data = request.data
        extra_data = data["message"]["data"]
        extra_data = json.loads(base64.b64decode(extra_data))
        email = extra_data["emailAddress"]
        history_id = extra_data["historyId"]
        usercredential = models.UserCredential.objects.filter(email=email).select_related("user").first()
        if usercredential and history_id:
            tasks.pull_partial_messages(usercredential.user.id, latest_history_id=history_id)
        return Response({"status": True})


class ConditionViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.ConditionSerializer
    queryset = models.Condition.objects.all()
    filter_backends = (drf_filters.SearchFilter, drf_filters.DjangoFilterBackend, drf_filters.OrderingFilter)
    # search_fields = ('snippet', 'subject', 'text')
    # filter_fields = ('user__username', 'snippet', 'thread_id', 'thread_topic', 'subject', 'email_from',
    #                  'email_to', 'email_cc', 'email_bcc', 'text')
    # ordering_fields = ('created', 'pk', )


class ActionViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.ActionSerializer
    queryset = models.Action.objects.all()
    filter_backends = (drf_filters.SearchFilter, drf_filters.DjangoFilterBackend, drf_filters.OrderingFilter)
    # search_fields = ('snippet', 'subject', 'text')
    # filter_fields = ('user__username', 'snippet', 'thread_id', 'thread_topic', 'subject', 'email_from',
    #                  'email_to', 'email_cc', 'email_bcc', 'text')
    # ordering_fields = ('created', 'pk', )


class RuleViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.RuleSerializer
    queryset = models.Rule.objects.all()
    filter_backends = (drf_filters.SearchFilter, drf_filters.DjangoFilterBackend, drf_filters.OrderingFilter)
    # search_fields = ('snippet', 'subject', 'text')
    # filter_fields = ('user__username', 'snippet', 'thread_id', 'thread_topic', 'subject', 'email_from',
    #                  'email_to', 'email_cc', 'email_bcc', 'text')
    # ordering_fields = ('created', 'pk', )

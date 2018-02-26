# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render
import base64
import json
import os
import logging
import httplib2
from urlparse import urljoin

import google.auth.exceptions as google_auth_exceptions
import google.oauth2.credentials
import google_auth_oauthlib.flow
import googleapiclient.discovery
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.http import HttpResponse
from django.http import HttpResponseBadRequest
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods
from django.views.generic import View
from rest_framework.response import Response


from mails import tasks
from users.models import User
from users.forms import UserForm
from . import models


if settings.DEBUG:
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'


GMAIL_SCOPES = ['https://www.googleapis.com/auth/gmail.readonly',
                'https://www.googleapis.com/auth/gmail.send',
                'https://www.googleapis.com/auth/gmail.labels',
                'https://www.googleapis.com/auth/userinfo.email', ]


def signup(request):
    if request.method == 'GET':
        form = UserForm()
        return render(request, "users/signup.html",
                      {'form': form})
    else:
        form = UserForm(request.POST or None)
        if form.is_valid():
            user = form.save()
            user.set_password(form.data['password'])
            user.save()
            return render(request, 'users/signup.html', {'ok': user})
        else:
            return render(request, "users/signup.html",
                          {'form': form})


@require_http_methods(["GET", "POST"])
def user_logout(request):
    """
    Logout user.
    """
    logout(request)
    return redirect(reverse('login'))


@require_http_methods(["GET", "POST"])
def user_login(request):
    """
    View a user sees when they login,
    or after clicking an email confirmation
    link.
    """
    if request.user and request.user.is_authenticated():
        return redirect(reverse('user-home'))
    data = request.POST
    # user_id can be either via username or email
    user_id = data.get('username', None)
    password = data.get('password', None)

    # Try to authenticate a user with given creds
    user = authenticate(username=user_id, password=password)
    if not user:
        error = "Incorrect password or username."
        print(error)
        return render(request,
                      'users/login.html',
                      dict(error=error))

    try:
        # Login user
        login(request, user)
    except:
        return render(request,
                      'users/login.html',
                      error='Something went wrong. Sorry.')
    else:
        return redirect(reverse('user-home'))


@require_http_methods(["GET"])
def user_home(request):
    """
    View a user sees if they are logged in,
    or after clicking an email confirmation
    link.
    """

    if not request.user.is_authenticated():
        return redirect(reverse('login'))

    context = {}
    errors = []

    if request.user.google_authorized:
        context['oauth_authorized'] = True
    else:
        flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
            settings.GOOGLE_OAUTH2_CLIENT_SECRETS_JSON,
            GMAIL_SCOPES,
            state=request.user.username
        )
        flow.redirect_uri = urljoin('http://' + settings.API_BASE_URL, '/google-oauth2callback/')
        authorization_url, state = flow.authorization_url(access_type='offline', include_granted_scopes='true')
        context['oauth_url'] = authorization_url

    context['errors'] = errors
    return render(
        request,
        'users/user_home.html',
        context,
    )


# @login_required
# def index(request):
#     storage = DjangoORMStorage(CredentialsModel, 'id', request.user, 'credential')
#     credential = storage.get()
#     if credential is None or credential.invalid == True:
#         FLOW.params['state'] = xsrfutil.generate_token(settings.SECRET_KEY,
#                                                        request.user)
#         authorize_url = FLOW.step1_get_authorize_url()
#         return HttpResponseRedirect(authorize_url)
#     else:
#         http = httplib2.Http()
#         http = credential.authorize(http)
#         service = build("plus", "v1", http=http)
#         activities = service.activities()
#         activitylist = activities.list(collection='public',
#                                        userId='me').execute()
#         logging.info(activitylist)

#         return render(request, 'plus/welcome.html', {
#             'activitylist': activitylist,
#         })


def google_authenticate(self, request):
    if request.user.google_authorized:
        return Response({"status": True})
    flow = google_auth_oauthlib.flow.Flow.from_client_config(
        project.app_credential,
        GMAIL_SCOPES,
        state=request.user.username
    )
    flow.redirect_uri = urljoin('https://' + settings.API_BASE_URL, '/google-oauth2callback/')
    authorization_url, state = flow.authorization_url(access_type='offline', include_granted_scopes='true')
    return Response({"status": False, "url": authorization_url})


def get_user_email(credentials):
    credentials = google.oauth2.credentials.Credentials(**credentials)
    user_info_service = googleapiclient.discovery.build(
        'oauth2',
        'v1',
        credentials=credentials,
        cache_discovery=False
    )
    user_info = user_info_service.userinfo().get().execute()
    return user_info.get('email')

def oauth2callback(request):
    error = request.GET.get("error", "")
    if error == "access_denied":
        return HttpResponse("You denied access to your Google account.")
    username = request.GET.get("state", "")
    user = User.objects.get(username=username)
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        settings.GOOGLE_OAUTH2_CLIENT_SECRETS_JSON,
        GMAIL_SCOPES,
        state=username
    )
    flow.redirect_uri = urljoin('http://' + settings.API_BASE_URL, '/google-oauth2callback/')
    authorization_response = urljoin('http://' + settings.API_BASE_URL, request.get_full_path())
    flow.fetch_token(authorization_response=authorization_response)
    credentials = flow.credentials
    credentials = {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }
    email = get_user_email(credentials)

    had_creds_previously = bool(user.credentials)

    if user.email and user.email != email:
        return HttpResponse({"error": "User tried to re-authenticate with different gmail account"}, status=400)
    else:
        user.email = email
        user.credentials = credentials
        user.google_authorized = True
        user.save()
        if not had_creds_previously:
            tasks.pull_complete_messages.delay(user.id, credentials)
        else:
            tasks.pull_partial_messages.delay(user.id, credentials=credentials)

    return HttpResponseRedirect(redirect_to='/')

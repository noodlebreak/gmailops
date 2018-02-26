import base64
import re

import google.auth.exceptions as google_auth_exceptions
import google.oauth2.credentials
import googleapiclient.discovery
import pytz
from apiclient import errors
from dateutil.parser import parse as parse_date
from django.conf import settings
from django.db.models import Q
from django.db.utils import OperationalError
from django.utils import timezone
from googleapiclient.http import BatchHttpRequest

from users.models import User
from gmailops.celery import app
from . import models


def get_text_html(payload):
    """
    Fetch encoded text and html and send then after decoding
    """

    text = ''
    html = ''
    if 'parts' in payload:
        for part in payload["parts"]:
            if 'mimeType' in part and part['mimeType'] == "text/plain" and 'data' in part['body']:
                text = base64.urlsafe_b64decode(str(part['body']['data']))
            elif 'mimeType' in part and part['mimeType'] == "text/html" and 'data' in part['body']:
                html = base64.urlsafe_b64decode(str(part['body']['data']))
        if 'parts' in payload["parts"][0]:
            for part in payload["parts"][0]["parts"]:
                if 'mimeType' in part and part['mimeType'] == "text/plain" and 'data' in part['body']:
                    text = base64.urlsafe_b64decode(str(part['body']['data']))
                elif 'mimeType' in part and part['mimeType'] == "text/html" and 'data' in part['body']:
                    html = base64.urlsafe_b64decode(str(part['body']['data']))
            if 'parts' in payload["parts"][0]["parts"][0]:
                for part in payload["parts"][0]["parts"][0]["parts"]:
                    if 'mimeType' in part and part['mimeType'] == "text/plain" and 'data' in part['body']:
                        text = base64.urlsafe_b64decode(str(part['body']['data']))
                    elif 'mimeType' in part and part['mimeType'] == "text/html" and 'data' in part['body']:
                        html = base64.urlsafe_b64decode(str(part['body']['data']))
    return (text, html)


def create_message(response, user):
    """
    Fetches the data from response and create individual message
    """

    snippet = response['snippet']
    snippet = snippet if not isinstance(snippet, unicode) else snippet.encode('unicode_escape')
    message_id = response['id']
    history_id = response['historyId']
    thread_id = response['threadId']
    headers = response['payload']['headers']
    labels = ", ".join(response['labelIds'])
    attachment_ids = []
    payload = response['payload']
    if 'parts' in payload:
        for part in payload['parts']:
            if 'attachmentId' in part['body']:
                attachment_ids.append(part['body']['attachmentId'])
    text, html = get_text_html(payload)
    email_from = ''
    email_to = ''
    email_cc = ''
    email_bcc = ''
    thread_topic = ''
    subject = ''
    date = ''
    for header in headers:
        if header['name'] == "From":
            email_from = header["value"]
            email_from = email_from if not isinstance(email_from, unicode) else email_from.encode('unicode_escape')
        elif header['name'] == "To":
            email_to = header["value"]
            email_to = email_to if not isinstance(email_to, unicode) else email_to.encode('unicode_escape')
        elif header['name'] == "CC":
            email_cc = header["value"]
            email_cc = email_cc if not isinstance(email_cc, unicode) else email_cc.encode('unicode_escape')
        elif header["name"] == "BCC":
            email_bcc = header["value"]
            email_bcc = email_bcc if not isinstance(email_bcc, unicode) else email_bcc.encode('unicode_escape')
        elif header["name"] == "Thread-Topic":
            thread_topic = header["value"]
            thread_topic = thread_topic if not isinstance(thread_topic, unicode) else thread_topic.encode(
                'unicode_escape')
        elif header['name'] == "Subject":
            subject = header["value"]
            subject = subject if not isinstance(subject, unicode) else subject.encode('unicode_escape')
        elif header['name'] == "Date":
            date = parse_date(header["value"]) if parse_date(header["value"]).tzinfo else parse_date(
                header["value"]).replace(tzinfo=pytz.utc)
    if not models.Mail.objects.filter(user=user, message_id=message_id).exists():
        try:
            obj = models.Mail(
                user=user,
                snippet=snippet,
                attachment_id=','.join(attachment_ids),
                history_id=history_id,
                thread_id=thread_id,
                thread_topic=thread_topic,
                message_id=message_id,
                email_from=email_from,
                email_to=email_to,
                email_cc=email_cc,
                email_bcc=email_bcc,
                subject=subject,
                labels=labels,
                date=date,
                text=text,
                html=html
            )
            obj.save()
        except OperationalError:
            obj = models.Mail(
                user=user,
                snippet=snippet,
                attachment_id=','.join(attachment_ids),
                history_id=history_id,
                thread_id=thread_id,
                thread_topic=thread_topic,
                message_id=message_id,
                email_from=email_from,
                email_to=email_to,
                email_cc=email_cc,
                email_bcc=email_bcc,
                subject=subject,
                labels=labels,
                date=date
            )
            obj.save()


def callback(request_id, response, exception):
    """
    Callback function for batch requests
    """

    if exception:
        pass
    else:
        user_id = request_id.split('-')[0]
        user = User.objects.get(pk=user_id)
        create_message(response, user)


@app.task
def pull_complete_messages(user_id, credentials=None):
    """
    Pull complete messages from gmail for inbox and sent labels and store then into Mail model
    """

    user = User.objects.filter(pk=user_id).first()
    if not credentials:
        credentials = user.credentials
    credentials = google.oauth2.credentials.Credentials(**credentials)
    service = googleapiclient.discovery.build('gmail', 'v1', credentials=credentials, cache_discovery=False)
    batch = BatchHttpRequest()
    user_id = user.id
    try:
        service.users().messages().list(userId='me', labelIds=['INBOX']).execute()
    # Raise when unauthorize of app by user
    except google_auth_exceptions.RefreshError as error:
        user.google_authorized = False
        user.save()
        print('Complete sync: User {} removed access from app'.format(user.username))
        return

    i = 0
    try:
        # Fetches list of messages from gmail for inbox
        response = service.users().messages().list(
            userId='me',
            labelIds=['INBOX'],
            maxResults=500
        ).execute()
        for message in response['messages']:
            print("processing message {}".format(i))
            i = i + 1
            request_id = "{}-{}".format(user_id, i)
            # Added get api of gmail to fetch messages data in batch request
            batch.add(
                service.users().messages().get(userId='me', id=message["id"]),
                callback=callback,
                request_id=request_id
            )
        batch.execute()
        while 'nextPageToken' in response:
            # Fetches list of messages from gmail for inbox
            response = service.users().messages().list(
                userId='me',
                labelIds=['INBOX'],
                pageToken=response['nextPageToken'],
                maxResults=500
            ).execute()
            for message in response['messages']:
                i = i + 1
                request_id = "{}-{}".format(user_id, i)
                # Added get api of gmail to fetch messages data in batch request
                batch.add(
                    service.users().messages().get(userId='me', id=message["id"]),
                    callback=callback,
                    request_id=request_id
                )
            batch.execute()
    # Raise when status code is greater than 300
    except errors.HttpError as error:
        pass
    try:
        # Fetches list of messages from gmail for sent
        response = service.users().messages().list(
            userId='me',
            labelIds=['SENT'],
            maxResults=500
        ).execute()
        for message in response['messages']:
            i = i + 1
            request_id = "{}-{}".format(user_id, i)
            # Added get api of gmail to fetch messages data in batch request
            batch.add(
                service.users().messages().get(userId='me', id=message["id"]),
                callback=callback,
                request_id=request_id
            )
        batch.execute()
        while 'nextPageToken' in response:
            # Fetches list of messages from gmail for sent
            response = service.users().messages().list(
                userId='me',
                labelIds=['SENT'],
                pageToken=response['nextPageToken'],
                maxResults=500
            ).execute()
            for message in response['messages']:
                i = i + 1
                request_id = "{}-{}".format(user_id, i)
                # Added get api of gmail to fetch messages data in batch request
                batch.add(
                    service.users().messages().get(userId='me', id=message["id"]),
                    callback=callback,
                    request_id=request_id
                )
            batch.execute()
    # Raise when status code is greater than 300
    except errors.HttpError as error:
        pass


@app.task
def pull_partial_messages(user_id, credentials=None, latest_history_id=None):
    """
    Pull rest of messages after complete sync from gmail for inbox and sent labels and store then into Mail model
    """

    user = User.objects.filter(pk=user_id).select_related("usercredential").first()
    usercredential = user.usercredential
    if not credentials:
        credentials = usercredential.credentials
    credentials = google.oauth2.credentials.Credentials(**credentials)
    service = googleapiclient.discovery.build('gmail', 'v1', credentials=credentials, cache_discovery=False)
    try:
        service.users().messages().list(userId='me', labelIds=['INBOX']).execute()
    # Raise when unauthorize of app by user
    except google_auth_exceptions.RefreshError as error:
        user.usercredential.authorized = False
        user.usercredential.save()
        print('Partial sync: User removed access from app')
        return
    batch = BatchHttpRequest()
    user_id = user.id
    i = 0
    if not latest_history_id:
        # Fetch latest history_id for inbox label per user
        mail = models.Mail.objects.filter(user=user, labels__contains='INBOX').order_by('-date').first()
        start_history_id = mail.history_id if mail else None
    else:
        start_history_id = usercredential.latest_history_id
    if start_history_id:
        # Fetch list of messages from history using start_history_id for inbox
        history = service.users().history().list(
            userId='me',
            startHistoryId=start_history_id,
            maxResults=500,
            labelId='INBOX'
        ).execute()
        if "history" in history:
            try:
                for message in history["history"]:
                    i = i + 1
                    request_id = "{}-{}".format(user_id, i)
                    # Added get api of gmail to fetch messages data in batch request
                    batch.add(
                        service.users().messages().get(userId='me', id=message["messages"][0]["id"]),
                        callback=callback,
                        request_id=request_id
                    )
                batch.execute()
                while 'nextPageToken' in history:
                    # Fetch list of messages from history using start_history_id for inbox
                    history = service.users().history().list(
                        userId='me',
                        startHistoryId=start_history_id,
                        maxResults=500,
                        labelId='INBOX',
                        pageToken=history['nextPageToken']
                    ).execute()
                    for message in history["history"]:
                        i = i + 1
                        request_id = "{}-{}".format(user_id, i)
                        # Added get api of gmail to fetch messages data in batch request
                        batch.add(
                            service.users().messages().get(userId='me', id=message["messages"][0]["id"]),
                            callback=callback,
                            request_id=request_id
                        )
                    batch.execute()
            # Raise when status code is greater than 300
            except errors.HttpError as error:
                pass
    if not latest_history_id:
        # Fetch latest history_id for sent label per user
        mail = models.Mail.objects.filter(user=user, labels__contains='INBOX').order_by('-date').first()
        start_history_id = mail.history_id if mail else None
    else:
        start_history_id = usercredential.latest_history_id

    if start_history_id:
        # Fetch list of messages from history using start_history_id for sent
        history = service.users().history().list(
            userId='me',
            startHistoryId=start_history_id,
            maxResults=500,
            labelId='SENT'
        ).execute()
        if "history" in history:
            try:
                for message in history["history"]:
                    i = i + 1
                    request_id = "{}-{}".format(user_id, i)
                    # Added get api of gmail to fetch messages data in batch request
                    batch.add(
                        service.users().messages().get(userId='me', id=message["messages"][0]["id"]),
                        callback=callback,
                        request_id=request_id
                    )
                batch.execute()
                while 'nextPageToken' in history:
                    # Fetch list of messages from history using start_history_id for sent
                    history = service.users().history().list(
                        userId='me',
                        startHistoryId=start_history_id,
                        maxResults=500,
                        labelId='SENT',
                        pageToken=history['nextPageToken']
                    ).execute()
                    for message in history["history"]:
                        i = i + 1
                        request_id = "{}-{}".format(user_id, i)
                        # Added get api of gmail to fetch messages data in batch request
                        batch.add(
                            service.users().messages().get(userId='me', id=message["messages"][0]["id"]),
                            callback=callback,
                            request_id=request_id
                        )
                    batch.execute()
            # Raise when status code is greater than 300
            except errors.HttpError as error:
                pass
    if latest_history_id:
        usercredential.latest_history_id = latest_history_id
        usercredential.save()


@app.task
def update_data_in_mails():
    """
    Function to update the text and html present in mail if text and html are not present
    """

    for mail in models.Mail.objects.all().select_related('user').prefetch_related('user__usercredential').iterator():
        credentials = mail.user.usercredential.credentials
        credentials = google.oauth2.credentials.Credentials(**credentials)
        service = googleapiclient.discovery.build('gmail', 'v1', credentials=credentials, cache_discovery=False)
        try:
            response = service.users().messages().get(userId='me', id=mail.message_id).execute()
            payload = response['payload']
            text, html = get_text_html(payload)
            mail.text = text
            mail.html = html
            try:
                mail.save()
            except OperationalError:
                pass
        except (google_auth_exceptions.RefreshError, errors.HttpError) as error:
            if isinstance(error, google_auth_exceptions.RefreshError):
                print('During mail update data: User removed access from app')

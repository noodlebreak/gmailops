from django.conf.urls import include, url
from rest_framework import routers

from mails import views as mail_apis

router = routers.DefaultRouter()
router.register(r'mails', mail_apis.MailViewSet, base_name='mails')
router.register(r'conditions', mail_apis.ConditionViewSet, base_name='conditions')
router.register(r'actions', mail_apis.ActionViewSet, base_name='actions')
router.register(r'rules', mail_apis.RuleViewSet, base_name='rules')

urlpatterns = [
    url(r'', include(router.urls)),
]

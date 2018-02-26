from django.conf.urls import url

from . import views
urlpatterns = [

    url(r'^signup$', views.signup, name='signup'),
    url(r'^login$', views.user_login, name='login'),
    url(r'^logout$', views.user_logout, name='logout'),
    # url(r'^/google-login/', views.google_authenticate, name='google-auth'),
    url(r'^google-oauth2callback/$', views.oauth2callback, name='google-oauth-callback'),
    url(r'^$', views.user_home, name='user-home'),
]

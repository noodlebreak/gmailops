"""gmailops URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import include, url
from django.contrib import admin
from gmailops import apiv1_urls

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    # url(r'^accounts/login/$', 'django.contrib.auth.views.login',
    # {'template_name': 'users/login.html'}),

    url(r'^api/v1/', include(apiv1_urls)),
    # url(r'^api/v1/auth/', include('accounts.urls')),
    url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    url(r'', include('users.urls')),

]

from django.conf.urls import url

from . import views

app_name = 'psnvalue'
urlpatterns = [
    url(r'^$', views.IndexView.as_view(), name='index'),
    url(r'^(?P<library_id>[0-9]+)/updatelib/$', views.updatelib, name='updatelib'),
]
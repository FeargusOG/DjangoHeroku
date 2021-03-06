from django.conf.urls import url

from . import views

app_name = 'psnvalue'
urlpatterns = [
    url(r'^$', views.IndexView.as_view(), name='index'),
    url(r'^(?P<library_id>[0-9]+)/gamelist/$', views.GameListView.as_view(), name='gamelist'),
    url(r'^(?P<library_id>[0-9]+)/updatelib/$', views.view_sync_psn_library_with_psn_store, name='updatelib'),
    url(r'^(?P<library_id>[0-9]+)/updateweightedrating/$', views.view_update_psn_weighted_ratings, name='updateweightedrating'),
    url(r'^(?P<library_id>[0-9]+)/updategamethumbs/$', views.view_update_psn_game_thumbnails, name='updategamethumbs'),
]

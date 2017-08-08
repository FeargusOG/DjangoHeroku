from . import library_manager

from django.views import generic
from django.http import HttpResponse
from django.http import Http404

from .models import Library, GameList

class IndexView(generic.ListView):
    template_name = 'psnvalue/index.html'
    context_object_name = 'library_list'

    def get_queryset(self):
        return Library.objects.all()

class GameListView(generic.ListView):
    template_name = 'psnvalue/gamelist.html'
    context_object_name = 'game_list'

    def get_queryset(self):
        return GameList.objects.filter(rating_count__gte=50, base_price__gte=1).order_by('-value_score')

def listlibs(request):
    return HttpResponse("You're at the psnvalue list.")

def updatelib(request, library_id):
    if not request.user.is_staff:
        raise Http404("You do not have access to this resource.")
    library_manager.update_library(library_id)
    return HttpResponse("You're at the psnvalue updatelib.")

def updateweightedrating(request, library_id):
    if not request.user.is_staff:
        raise Http404("You do not have access to this resource.")
    library_manager.update_weighted_rating(library_id)
    return HttpResponse("You're at the psnvalue update weighted rating.")

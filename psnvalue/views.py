from . import library_manager

from django.views import generic
from django.http import HttpResponse
from django.http import Http404

from .models import Library

class IndexView(generic.ListView):
    template_name = 'psnvalue/index.html'
    context_object_name = 'library_list'

    def get_queryset(self):
        """Return the last five published questions (not including those set to be published in the future)."""
        return Library.objects.all()

def listlibs(request):
    return HttpResponse("Hello, world. You're at the psnvalue list.")

def updatelib(request, library_id):
    if not request.user.is_staff:
        raise Http404("Not found.")
    library_manager.update_library("PS4")
    return HttpResponse("Hello, world. You're at the psnvalue updatelib.")

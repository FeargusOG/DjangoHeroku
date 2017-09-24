from django.shortcuts import render

def index(request):
    template_name = 'DjangoHerokuSite/index.html'
    return render(request, template_name, None)
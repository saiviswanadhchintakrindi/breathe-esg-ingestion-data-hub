from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse, HttpResponseRedirect

def health(request):
    return JsonResponse({"status": "ok"})

def root(request):
    return HttpResponseRedirect('/health/')

urlpatterns = [
    path('', root),
    path('health/', health),
    path('admin/', admin.site.urls),
    path('api/', include('ingestion.urls')),
]

from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from django.http import FileResponse
import os
from django.conf import settings
from django.conf.urls.static import static

def serve_template(request, template_name):
    template_path = os.path.join(settings.BASE_DIR, 'templates', template_name)
    if os.path.exists(template_path):
        return FileResponse(open(template_path, 'rb'), content_type='text/html')
    else:
        from django.http import HttpResponseNotFound
        return HttpResponseNotFound('Template not found')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/users/', include('users.urls')),
    path('templates/<str:template_name>', serve_template, name='serve_template'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

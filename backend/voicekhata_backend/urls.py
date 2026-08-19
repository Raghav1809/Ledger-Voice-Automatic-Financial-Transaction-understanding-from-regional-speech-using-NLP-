from django.contrib import admin
from django.urls import path, include, re_path
from django.views.generic import TemplateView
from django.views.static import serve
from django.conf import settings
from pathlib import Path

FRONTEND_DIR = settings.BASE_DIR.parent / 'frontend'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('authentication.urls')),
    path('api/customers/', include('customers.urls')),
    path('api/transactions/', include('transactions.urls')),
    path('api/voice/', include('voice.urls')),
    path('api/inventory/', include('inventory.urls')),
    path('api/insights/', include('insights.urls')),
    path('api/reminders/', include('reminders.urls')),
    path('api/settings/', include('settings_app.urls')),

    # Serve AngularJS static subfolders (css, js, views, webfonts) directly
    re_path(r'^(?P<path>(css|js|views|webfonts)/.*)$', serve, {'document_root': FRONTEND_DIR}),

    # Catch-all to serve AngularJS SPA index.html
    re_path(r'^.*$', TemplateView.as_view(template_name='index.html'), name='home'),
]
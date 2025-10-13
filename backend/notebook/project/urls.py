"""
URL configuration for the standalone notebook project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from django_reverse_js import views

from notebook.views import notebook_list


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', notebook_list, name='home'),
    path('notebook/', include('notebook.urls', namespace='notebook')),
    path('runner/', include('notebook.runner.urls')),

    path('reverse.js', views.urls_js, name='reverse_js'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

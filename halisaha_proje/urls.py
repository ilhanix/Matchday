"""
URL configuration for halisaha_proje project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
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
from django.contrib import admin
from django.urls import path, include
from grup_yonetimi import views as grup_views

urlpatterns = [
    path('admin/', admin.site.urls),# grup_yonetimi uygulamasının URL'lerini buraya dahil et
    path('grup/', include('grup_yonetimi.urls')),
    path('', grup_views.ana_sayfa, name='ana_sayfa'), # <<< Bütün trafiği karşılayacak
    path('hesap/', include('django.contrib.auth.urls')), # <<< BU SATIRI EKLEYİN
    path('grup/', include('grup_yonetimi.urls')),
]

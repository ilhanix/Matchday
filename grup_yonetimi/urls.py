from django.urls import path
from . import views# grup_yonetimi/views.py dosyasının en üstüne
from django.contrib.auth.views import LogoutView
# ...

urlpatterns = [
    # Gruptaki maçların listesi
    path('<int:grup_id>/maclar/', views.mac_listesi, name='mac_listesi'),
    path('cikis/', LogoutView.as_view(), name='logout'),
    # Yeni maç oluşturma ve dengeleme sayfası
    path('<int:grup_id>/mac/yeni/', views.mac_olustur_dengele, name='mac_olustur_dengele'),
    path('mac/<int:mac_id>/sil/', views.mac_sil, name='mac_sil'),
    path('mac/<int:mac_id>/skor-gir/', views.mac_sonucu_gir, name='mac_sonucu_gir'), # <<< YENİ SATIR
    path('olustur/', views.grup_olustur, name='grup_olustur'),
    path('<int:grup_id>/', views.grup_detay, name='grup_detay'), # <<< YENİ SATIR
    path('<int:grup_id>/katil/', views.grup_katil, name='grup_katil'), # <<< YENİ
    path('onay/<int:grup_oyuncu_id>/', views.grup_onayla, name='grup_onayla'),# Grup Ayrılma (Onaylı üye)
    path('<int:grup_id>/ayril/', views.grup_ayril, name='grup_ayril'), # <<< YENİ
    path('<int:grup_id>/talep-iptal/', views.grup_talep_iptal, name='grup_talep_iptal'), # <<< YENİ
    path('profil/duzenle/', views.profil_duzenle, name='profil_duzenle'),
    path('kayit/', views.kayit, name='kayit'), # <<< YENİ SATIR
    path('<int:grup_id>/mac-olustur/', views.mac_olustur, name='mac_olustur'),
    path('mac/<int:mac_id>/katilim/', views.mac_katilim_toggle, name='mac_katilim_toggle'), # <<< YENİ SATIR
    path('mac/<int:mac_id>/dengele/otomatik/', views.mac_dengele_otomatik, name='mac_dengele_otomatik'), # <<< YENİ
    path('mac/<int:mac_id>/dengele/manuel/', views.mac_dengele_manuel, name='mac_dengele_manuel'), # <<< YENİ
]
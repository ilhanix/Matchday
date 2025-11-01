# grup_yonetimi/admin.py
from django.contrib import admin
from .models import OyuncuProfili, Grup, GrupOyuncu, Mac, MacOyuncu, GrupAyarlari, MacKatilim

# Admin paneli görünümünü özelleştirebiliriz.
# Örneğin, GrupOyuncu listeleme ekranında hangi alanların görüneceğini belirtelim.
class GrupOyuncuAdmin(admin.ModelAdmin):
    # Admin listeleme ekranında görünecek alanlar
    list_display = ('oyuncu', 'grup', 'onay_durumu', 'oynadigi_mac', 'gol', 'toplam_seviye_puani')
    # Filtreleme seçenekleri
    list_filter = ('grup', 'onay_durumu')
    # Arama çubuğunda arama yapılacak alanlar
    search_fields = ('oyuncu__username', 'grup__grup_adi')


# Modelleri admin paneline kaydediyoruz
admin.site.register(OyuncuProfili)
admin.site.register(Grup)
admin.site.register(GrupOyuncu, GrupOyuncuAdmin) # Özelleştirilmiş admin sınıfını kullanıyoruz
admin.site.register(Mac) 
admin.site.register(MacOyuncu)
admin.site.register(GrupAyarlari)
admin.site.register(MacKatilim)
from django.db import models
from django.contrib.auth.models import User # Django'nun hazır kullanıcı modelini kullanıyoruz
from django.db.models import Sum
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings

# --- Mevki Seçenekleri ---
MEVKI_SECENEKLERI = (
    ('KL', 'Kaleci'),
    ('DF', 'Defans'),
    ('OS', 'Orta Saha'),
    ('FR', 'Forvet'),
    ('CY', 'Çok Yönlü'),
)

# --- 1. Kullanıcı/Oyuncu Profili Modeli ---
class OyuncuProfili(models.Model):
    # Django'nun hazır 'User' modeli ile birebir ilişki kuruyoruz (Giriş/Kayıt için)
    kullanici = models.OneToOneField(User, on_delete=models.CASCADE) 
    
    # Gerekli Profil Bilgileri
    mevkii = models.CharField(max_length=2, choices=MEVKI_SECENEKLERI, default='CY')
    profil_resmi = models.ImageField(upload_to='profil_resimleri/', null=True, blank=True)
    
    # Yönetici Tarafından Verilen Puanlar
    yetkili_puan = models.IntegerField(default=5, help_text="Yönetici tarafından verilen yetenek puanı (1-10)")
    kisilik_puani = models.IntegerField(default=5, help_text="Yönetici tarafından verilen kişilik puanı (1-10)")

    def __str__(self):
        return f"{self.kullanici.username} Profili"

# --- 2. Grup Modeli ---
class Grup(models.Model):
    grup_adi = models.CharField(max_length=100)
    grup_resmi = models.ImageField(upload_to='grup_resimleri/', null=True, blank=True)
    # Grubun yöneticisi: Bir kullanıcı (User) ile ilişkilendirildi.
    yonetici = models.ForeignKey(User, on_delete=models.CASCADE, related_name='yönettigi_gruplar')

    def __str__(self):
        return self.grup_adi

# --- 3. Grup Oyuncusu İstatistikleri Modeli (İlişki ve İstatistikler) ---
class GrupOyuncu(models.Model):
    ONAY_DURUMU = (
        ('B', 'Beklemede'),
        ('O', 'Onaylandı'),
        ('R', 'Reddedildi'),
    )

    grup = models.ForeignKey(Grup, on_delete=models.CASCADE)
    oyuncu = models.ForeignKey(User, on_delete=models.CASCADE)
    onay_durumu = models.CharField(max_length=1, choices=ONAY_DURUMU, default='B')
    
    # İstatistikler (Maç sonuçlarından ve girişlerden geliyor)
    oynadigi_mac = models.IntegerField(default=0)
    kazandigi_mac = models.IntegerField(default=0)
    kaybettigi_mac = models.IntegerField(default=0)
    berabere_mac = models.IntegerField(default=0)
    gol = models.IntegerField(default=0)
    asist = models.IntegerField(default=0)
    sari_kart = models.IntegerField(default=0)
    kirmizi_kart = models.IntegerField(default=0)

    # Dengeleme Algoritması için Toplam Puan (İhtiyaç durumunda dinamik hesaplanacak)
    toplam_seviye_puani = models.IntegerField(default=0) 
    
    class Meta:
        # Bir oyuncunun aynı gruba birden fazla kez eklenmesini engeller.
        unique_together = ('grup', 'oyuncu') 

    def __str__(self):
        return f"{self.oyuncu.username} - {self.grup.grup_adi}"
    
    # Puanlama Mantığı (Metot)
    def hesapla_seviye_puani(self):
        """
        Oyuncunun dengeleme algoritmasında kullanılacak puanını hesaplar.
        """
        try:
            ayarlar = self.grup.grup_ayarlari
            min_mac_grup = ayarlar.min_mac_grup_puani
            min_mac_genel = ayarlar.min_mac_genel_puani
        except ObjectDoesNotExist: # Özellikle kaydın yokluğunu yakalamak için
            # Eğer kayıt yoksa varsayılan değerleri kullan ve Yetkili Puanı kuralına geç
            min_mac_grup = 5
            min_mac_genel = 10
            # ... (Bu durumda doğrudan yetkili puanı mantığına atlamak daha temiz olabilir,
            #     ama şimdilik sadece değerleri ayarlayalım)
        except AttributeError:
             # Eğer "grup_ayarlari" attribute'u bulunamıyorsa (genellikle Django'nun yeniden yüklenmesiyle düzelir)
             min_mac_grup = 5
             min_mac_genel = 10
        
        # 1. Puanları Hesapla (Maç Başına Puan)
        grup_mac_puani_toplam = (self.kazandigi_mac * 3) + (self.berabere_mac * 2) + (self.kaybettigi_mac * 1)
        
        # 2. KARAR MANTIĞI
        
        if self.oynadigi_mac >= min_mac_grup:
            # GRUP İÇİ KURAL: Grupta yeterli maç oynadıysa, sadece grup içi ortalama puan kullanılır.
            if self.oynadigi_mac == 0:
                ortalama_puan = 0
            else:
                # Grup içi ortalama maç puanı (3'lük sistemde 1 ile 3 arası)
                ortalama_puan = grup_mac_puani_toplam / self.oynadigi_mac
            
            # Puanı büyük bir ölçeğe (0-30 arası gibi) taşımak için x10 yapıldı.
            return int(ortalama_puan * 10) 
            pass
        else:
            # GENEL KURAL: Grupta yeterli maç yoksa, genel performansa bakılır.
            
            # Genel maç sayısını hesapla (Oyuncunun dahil olduğu TÜM GrupOyuncu kayıtlarına bak)
            tum_gruplar = GrupOyuncu.objects.filter(oyuncu=self.oyuncu)
            genel_mac_sayisi = tum_gruplar.aggregate(Sum('oynadigi_mac'))['oynadigi_mac__sum'] or 0
            
            if genel_mac_sayisi >= min_mac_genel:
                # Genel maç sayısı yeterliyse: Genel puan ortalaması
                
                # Tüm Gruplardaki Puanları Topla
                genel_puan_toplami = sum(
                    (g.kazandigi_mac * 3) + (g.berabere_mac * 2) + (g.kaybettigi_mac * 1)
                    for g in tum_gruplar
                )
                ortalama_puan = genel_puan_toplami / genel_mac_sayisi
                return int(ortalama_puan * 10)
                pass
            else:
                # YETKİLİ PUANI KURALI: Yeterli maç yoksa, yetkili puanı kullanılır.
                profil = self.oyuncu.oyuncuprofili
                # (Yetkili Puan + Kişilik Puanı) / 20 * 3. * 10 (ölçeklendirme)
                yetkili_puani_temeli = (profil.yetkili_puan + profil.kisilik_puani) / 20 * 3 * 10
                return int(yetkili_puani_temeli)
        return 0

# GrupOyuncu modelinde toplam_seviye_puani alanını bu metottan dönen değere göre otomatik güncellemeliyiz.
# grup_yonetimi/models.py dosyanızdaki mevcut kodun devamına ekleyin

# --- 4. Maç Modeli (Organizasyon ve Skor Bilgileri) ---
class Mac(models.Model):
    # Maçın ait olduğu grup
    grup = models.ForeignKey(Grup, on_delete=models.CASCADE)
    
    # Maç Bilgileri
    tarih = models.DateField(verbose_name="Maç Tarihi")
    saat = models.TimeField(verbose_name="Maç Saati")
    yer = models.CharField(max_length=255, verbose_name="Maç Yeri")
    
    # Skorlar
    # Takım A ve Takım B isimleri dengeleme algoritması tarafından belirlenecek.
    takim_a_skor = models.IntegerField(default=0)
    takim_b_skor = models.IntegerField(default=0)
    
    # Maçın oynanıp oynanmadığı bilgisini tutar (Skor girildiyse True olur)
    oynandi_mi = models.BooleanField(default=False, verbose_name="Oynandı mı?") 
    # <<< DENGELEME ALANLARI - BUNLARI EKLEYİN >>>
    takim_a_denge_puani = models.IntegerField(default=0, help_text="Takım A'nın dengeleme için kullanılan toplam puanı.")
    takim_b_denge_puani = models.IntegerField(default=0, help_text="Takım B'nin dengeleme için kullanılan toplam puanı.")
    denge_farki = models.IntegerField(default=0, help_text="İki takım arasındaki puan farkı.")
    # <<< DENGELEME ALANLARI SONU >>>

    @property
    def denge_renk(self):
        """Denge farkına göre CSS rengini döndürür."""
        if self.denge_farki > 10:
            return 'red'
        else:
            # 10 ve altındaki farklar için yeşil/güzel
            return 'green'
    def __str__(self):
        return f"{self.grup.grup_adi} - {self.tarih} @ {self.yer}"

# grup_yonetimi/models.py (Mac modelinden sonra ekleyin)

class MacKatilim(models.Model):
    mac = models.ForeignKey(Mac, on_delete=models.CASCADE, related_name='katilimlar')
    oyuncu = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    
    # Kullanıcının katılım zamanını tutabiliriz
    katilim_zamani = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Bir oyuncu, aynı maça iki kez katılamaz (tekil kısıtlama)
        unique_together = ('mac', 'oyuncu')
        verbose_name = "Maç Katılımı"
        verbose_name_plural = "Maç Katılımları"

    def __str__(self):
        return f"{self.oyuncu.username} -> {self.mac.grup.grup_adi} Maçı"

# --- 5. Maç Oyuncu İstatistikleri Modeli (Maç Bazında Detaylar) ---
class MacOyuncu(models.Model):
    mac = models.ForeignKey(Mac, on_delete=models.CASCADE)
    oyuncu = models.ForeignKey(User, on_delete=models.CASCADE)
    
    # Oyuncunun hangi takımda oynadığı (Dengeleme sonrası atanır)
    takim = models.CharField(max_length=1, choices=[('A', 'Takım A'), ('B', 'Takım B')], blank=True, null=True) 

    # Maçta atılan gol/asist (Yönetici tarafından onaylanan değerler)
    gol = models.IntegerField(default=0)
    asist = models.IntegerField(default=0)
    sari_kart = models.IntegerField(default=0)
    kirmizi_kart = models.IntegerField(default=0)

    class Meta:
        # Aynı oyuncunun aynı maçta birden fazla olmasını engeller
        unique_together = ('mac', 'oyuncu') 

    def __str__(self):
        return f"{self.oyuncu.username} - {self.mac.grup.grup_adi} Maçı"
    # grup_yonetimi/models.py dosyasındaki mevcut kodun devamına ekleyin

# --- 6. Grup Ayarları Modeli (Algoritma Parametreleri) ---
class GrupAyarlari(models.Model):
    grup = models.OneToOneField(Grup, on_delete=models.CASCADE, primary_key=True)
    
    # Parametre 1: Oyuncunun grup puanlamasına geçişi için minimum maç sayısı
    min_mac_grup_puani = models.IntegerField(default=5, help_text="Grupta bu kadar maç oynayan oyuncu, sadece grup içi puan ortalaması ile değerlendirilir.")
    
    # Parametre 2: Oyuncunun yetkili puanından puanlamaya geçişi için minimum maç sayısı (Grup bağımsız)
    min_mac_genel_puani = models.IntegerField(default=10, help_text="Toplamda bu kadar maç oynayan oyuncu, genel puan ortalaması ile değerlendirilir.")
    
    def __str__(self):
        return f"{self.grup.grup_adi} Ayarları"
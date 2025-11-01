
# grup_yonetimi/views.py
from django.contrib.auth.models import User
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Grup, GrupOyuncu, Mac, MacOyuncu, MacKatilim
from django.contrib.auth.models import User
from .utils import find_optimal_teams # Dengeleme fonksiyonumuz
from django.contrib.auth.views import LogoutView
from django.db import transaction # Veritabanı işlemlerinde tutarlılık için
from django.core.exceptions import ObjectDoesNotExist
from django.contrib import messages
from django.views.decorators.http import require_POST
from .forms import GrupForm, GrupAyarlariForm # <<< BUNU EN ÜSTE IMPORT EDİN
from django.db.models import Q # Import'lar listesine ekleyin
from django.db import IntegrityError # Import'lara ekleyin
from .forms import KullaniciForm, OyuncuProfiliForm, OyuncuProfili # <<< EN ÜSTE IMPORT EDİN
from .forms import KayitFormu, MacOlusturFormu # Import'lar listesine ekleyin
from django.utils import timezone # EN ÜSTE EKLEYİN
from django.contrib.auth import get_user_model # EN ÜSTE EKLEYİN
User = get_user_model() # EN ÜSTE KULLANIN
# from .forms import MacKatilimFormu # Formları daha sonra ekleyeceğiz
# grup_yonetimi/views.py (mac_listesi fonksiyonunu bulun ve değiştirin)


@login_required
def mac_listesi(request, grup_id):
    grup = get_object_or_404(Grup, pk=grup_id)
    
    # Maçları tarihe göre ayırıyoruz
    bugun = timezone.localdate()
    
    # Yaklaşan ve oynanmamış maçlar
    gelecek_maclar = Mac.objects.filter(
        grup=grup, 
        oynandi_mi=False, 
        tarih__gte=bugun # Bugünkü veya sonraki maçlar
    ).order_by('tarih', 'saat')
    
    # Oynanmış veya geçmiş maçlar
    gecmis_maclar = Mac.objects.filter(
        grup=grup
    ).filter(
        Q(oynandi_mi=True) | Q(tarih__lt=bugun) # Oynandıysa VEYA tarihi eskiyse
    ).order_by('-tarih', '-saat') # tersten sırala

    # Kullanıcının katıldığı maçların ID'lerini çek
    katildigim_mac_ids = MacKatilim.objects.filter(
        mac__in=gelecek_maclar, 
        oyuncu=request.user
    ).values_list('mac_id', flat=True)

    # Her maç için katılım sayısını çekelim (template'te göstermek için)
    katilim_sayilari = {}
    for mac in gelecek_maclar:
        katilim_sayilari[mac.id] = mac.katilimlar.count()

    context = {
        'grup': grup,
        'gelecek_maclar': gelecek_maclar,
        'gecmis_maclar': gecmis_maclar,
        'katildigim_mac_ids': katildigim_mac_ids,
        'katilim_sayilari': katilim_sayilari,
        'is_yonetici': grup.yonetici == request.user,
    }
    
    return render(request, 'grup_yonetimi/mac_listesi.html', context)

# ... (mac_olustur_dengele fonksiyonu burada devam etmeli) ...
@login_required
def mac_olustur_dengele(request, grup_id):
    grup = get_object_or_404(Grup, pk=grup_id)

    # Yöneticilik Kontrolü (Sadece yönetici oluşturabilir)
    if grup.yonetici != request.user:
        return redirect('mac_listesi', grup_id=grup_id) # İzin yoksa listeye yönlendir

    # Grupta 'Onaylanmış' olan ve maça katılabilecek oyuncuları çek
    katilimcilar_qs = GrupOyuncu.objects.filter(
        grup=grup, 
        onay_durumu='O'
        # Burada maça katılacağını belirten oyuncular filtrelenecek
        # Ancak basit tutmak için şimdilik tüm onaylı oyuncuları alalım.
    )

    if request.method == 'POST':
        # 1. Puanları Hesapla
        katilimcilar = []
        for g_oyuncu in katilimcilar_qs:
            # Oyuncunun güncel puanını hesapla (models.py'de yazdığımız metot)
            puan = g_oyuncu.hesapla_seviye_puani() 
            g_oyuncu.toplam_seviye_puani = puan # GrupOyuncu modelindeki alanı güncelle
            g_oyuncu.save()
            
            katilimcilar.append({
                'oyuncu_id': g_oyuncu.oyuncu.id,
                'puan': puan,
                'mevkii': g_oyuncu.oyuncu.oyuncuprofili.mevkii
            })

        # Katılımcı sayısı kontrolü
        n = len(katilimcilar)
        if n % 2 != 0 or n < 2:
            # Hata mesajı: Oyuncu sayısı tek veya yetersiz
            return render(request, 'grup_yonetimi/mac_dengele.html', 
                          {'grup': grup, 'hata': 'Oyuncu sayısı tek veya yetersiz. Dengeleme yapılamaz.'})
        
        takim_sayisi = n // 2
        
        # 2. Optimal Dengelemeyi Yap
        # utils.py'daki fonksiyonu çağır
        # grup_yonetimi/views.py (mac_olustur_dengele fonksiyonunun POST bloğu içinde)
# ... [Optimal Dengelemeyi Yaptığımız Yer] ...
        
        # 2. Optimal Dengelemeyi Yap
        takim_a_ids, takim_b_ids, fark = find_optimal_teams(katilimcilar, takim_sayisi)

        # Kullanıcının girdiği maç tarihini ve yerini çekme
        mac_tarihi = request.POST.get('tarih') # HTML'den gelen 'tarih' name'li input
        mac_yeri = request.POST.get('yer')     # HTML'den gelen 'yer' name'li input

        # 3. Maç Objesini Oluşturma
        yeni_mac = Mac.objects.create(
            grup=grup,
            tarih=mac_tarihi,
            yer=mac_yeri,
            takim_a_denge_puani=takim_a_ids['toplam_puan'],
            takim_b_denge_puani=takim_b_ids['toplam_puan'],
            denge_farki=fark,
            # Varsayılan olarak skorlar 0-0 ve oynanmadı olarak kalacak
        )

        # 4. MacOyuncu Objelerini Oluşturma (Takımlara Oyuncuları Atama)
        
        # Takım A Oyuncuları
        for oyuncu_id in takim_a_ids['oyuncu_ids']:
            oyuncu = get_object_or_404(User, pk=oyuncu_id)
            grup_oyuncu = GrupOyuncu.objects.get(grup=grup, oyuncu=oyuncu)
            
            MacOyuncu.objects.create(
                mac=yeni_mac,
                oyuncu=oyuncu,
                # grup_oyuncu_istatistik=grup_oyuncu, # İstatistik referansı
                takim='A'
            )

        # Takım B Oyuncuları
        for oyuncu_id in takim_b_ids['oyuncu_ids']:
            oyuncu = get_object_or_404(User, pk=oyuncu_id)
            grup_oyuncu = GrupOyuncu.objects.get(grup=grup, oyuncu=oyuncu)
            
            MacOyuncu.objects.create(
                mac=yeni_mac,
                oyuncu=oyuncu,
                # grup_oyuncu_istatistik=grup_oyuncu,
                takim='B'
            )

        # 5. Başarılı Tamamlanma Sonucu Yönlendirme
        # Yeni maç listesini göstermek üzere yönlendir
        return redirect('mac_listesi', grup_id=grup.id)

# ... [mac_olustur_dengele fonksiyonunun sonu] ...

    
    # GET isteği (Sayfa görüntüleme)
    context = {
        'grup': grup,
        'oyuncular': katilimcilar_qs,
    }
    return render(request, 'grup_yonetimi/mac_dengele.html', context)

# grup_yonetimi/views.py dosyasında, diğer görünüm fonksiyonlarının yanına

@login_required
def ana_sayfa(request):
    user = request.user

    # 1. Kullanıcının MEVCUT DURUMU (ID'leri çekiyoruz)
    mevcut_durumlar = GrupOyuncu.objects.filter(oyuncu=user)
    
    # Onaylı grupların ID'leri
    onayli_grup_ids = mevcut_durumlar.filter(onay_durumu='O').values_list('grup_id', flat=True)
    
    # Bekleyen grupların ID'leri
    bekleyen_grup_ids = mevcut_durumlar.filter(onay_durumu='B').values_list('grup_id', flat=True)
    
    # Yönetilen grupların ID'leri (Yönetilen gruplar otomatik onaylı sayılır)
    yonetilen_grup_ids = Grup.objects.filter(yonetici=user).values_list('id', flat=True)

    # 2. KATEGORİLERİ OLUŞTURMA
    
    # A) ONAYLI GRUPLARIM (Yönetilenler + Onaylı Üyelikler)
    onayli_gruplarim = Grup.objects.filter(
        Q(id__in=onayli_grup_ids) | Q(id__in=yonetilen_grup_ids)
    ).distinct()

    # B) ONAY BEKLEYEN GRUPLARIM
    talep_gonderilen_gruplar = Grup.objects.filter(
        id__in=bekleyen_grup_ids
    ).distinct()

    # C) KATILABİLECEĞİM GRUPLAR
    # Tüm gruplardan: 
    # - Yönetilenleri,
    # - Onaylı olduklarımı, 
    # - Talep gönderdiklerimi çıkar.
    tum_iliskili_gruplar_ids = list(onayli_grup_ids) + list(bekleyen_grup_ids) + list(yonetilen_grup_ids)

    katilabilecegim_gruplar = Grup.objects.exclude(
        id__in=tum_iliskili_gruplar_ids
    ).distinct()

    context = {
        'onayli_gruplarim': onayli_gruplarim,
        'talep_gonderilen_gruplar': talep_gonderilen_gruplar,
        'katilabilecegim_gruplar': katilabilecegim_gruplar,
        'yonetilen_gruplar': Grup.objects.filter(yonetici=user), # Yönetilenler ayrı bir liste olarak kalsın
    }
    
    return render(request, 'grup_yonetimi/ana_sayfa.html', context)

# grup_yonetimi/views.py (Diğer fonksiyonların yanına ekleyin)


@login_required
def mac_sonucu_gir(request, mac_id):
    mac = get_object_or_404(Mac, pk=mac_id)
    grup = mac.grup

    # Yönetici Kontrolü: Sadece Grup Yöneticisi sonuç girebilir.
    if grup.yonetici != request.user:
        messages.error(request, "Yalnızca grup yöneticisi maç sonucu girebilir.")
        return redirect('mac_listesi', grup_id=grup.id)

    # Eğer skor zaten girilmişse, düzenlemeye izin verilebilir (ancak şimdilik listeye yönlendiriyoruz)
    if mac.oynandi_mi:
        # messages.info(request, "Bu maçın skoru daha önce girilmiş.")
        pass 
        
    # Maça katılan oyuncular
    mac_oyunculari = MacOyuncu.objects.filter(mac=mac).select_related('oyuncu')

    if request.method == 'POST':
        # --- Maç Sonucunu Kaydetme ve İstatistik Güncelleme MANTIĞI ---
        
        try:
            if mac.oynandi_mi:
                # <<< ÖNEMLİ DEĞİŞİKLİK BURADA: ÖNCE ESKİ VERİYİ GERİ AL! >>>
                geri_al_istatistikleri(mac)
            # 1. Skorları Çekme
            takim_a_skor = int(request.POST.get('takim_a_skor', 0))
            takim_b_skor = int(request.POST.get('takim_b_skor', 0))
            
            # 2. Maçı ve Skoru Güncelleme
            mac.takim_a_skor = takim_a_skor
            mac.takim_b_skor = takim_b_skor
            mac.oynandi_mi = True
            mac.save()
            
            # 3. İstatistikleri ve Puanları Hesaplama (Transaction kullanarak hata durumunda geri alma)
            with transaction.atomic():
                
                # MacOyuncu kayıtlarını döngüye alarak istatistikleri ve GrupOyuncu'yu güncelle
                for mac_oyuncu in mac_oyunculari:
                    oyuncu_id_str = str(mac_oyuncu.oyuncu.id)
                    
                    # Formdan gelen bireysel istatistikleri çek
                    gol = int(request.POST.get(f'gol_{oyuncu_id_str}', 0))
                    asist = int(request.POST.get(f'asist_{oyuncu_id_str}', 0))
                    sari_kart = int(request.POST.get(f'sari_{oyuncu_id_str}', 0))
                    kirmizi_kart = int(request.POST.get(f'kirmizi_{oyuncu_id_str}', 0))
                    
                    # MacOyuncu kaydını istatistiklerle güncelle (Gol/Asist onayı)
                    mac_oyuncu.gol = gol
                    mac_oyuncu.asist = asist
                    mac_oyuncu.sari_kart = sari_kart
                    mac_oyuncu.kirmizi_kart = kirmizi_kart
                    mac_oyuncu.save()

                    # GrupOyuncu İstatistiklerini Güncelleme (Oyuncunun genel grup karnesi)
                    grup_oyuncu = GrupOyuncu.objects.get(grup=grup, oyuncu=mac_oyuncu.oyuncu)
                    
                    # Maç Katılımı ve Gol/Asist güncelleme
                    grup_oyuncu.oynadigi_mac += 1
                    grup_oyuncu.gol += gol
                    grup_oyuncu.asist += asist
                    grup_oyuncu.sari_kart += sari_kart
                    grup_oyuncu.kirmizi_kart += kirmizi_kart
                    
                    # Kazanma/Berabere/Kaybetme Güncellemesi (Puanlama Mantığı)
                    if mac_oyuncu.takim == 'A':
                        kazanan_skor = takim_a_skor
                        kaybeden_skor = takim_b_skor
                    else: # Takım B
                        kazanan_skor = takim_b_skor
                        kaybeden_skor = takim_a_skor
                        
                    if kazanan_skor > kaybeden_skor:
                        grup_oyuncu.kazandigi_mac += 1  # 3 Puan
                    elif kazanan_skor == kaybeden_skor:
                        grup_oyuncu.berabere_mac += 1 # 2 Puan
                    else:
                        grup_oyuncu.kaybettigi_mac += 1 # 1 Puan
                        
                    # GrupOyuncu'nun son halini kaydet
                    grup_oyuncu.save()
                    
                messages.success(request, f"{grup.grup_adi} için maç sonucu başarıyla kaydedildi.")
                return redirect('mac_listesi', grup_id=grup.id)

        except ValueError:
            messages.error(request, "Skorlar sayısal olmalıdır.")
            pass # Hata yönetimi burada daha detaylı yapılabilir.
        except ObjectDoesNotExist:
            messages.error(request, "İlgili oyuncu veya grup kaydı bulunamadı.")
            pass
        except Exception as e:
            messages.error(request, f"Beklenmedik bir hata oluştu: {e}")
            pass

    # GET isteği (Formu Göster)
    takimlar_ve_oyunculari = [
        {'isim': 'A', 'oyuncular': mac_oyunculari.filter(takim='A')},
        {'isim': 'B', 'oyuncular': mac_oyunculari.filter(takim='B')},
    ]
    context = {
        'grup': grup,
        'mac': mac,
        'mac_oyunculari': mac_oyunculari,
        # Takımları ayırıyoruz
        # 'takim_a': mac_oyunculari.filter(takim='A'),
        # 'takim_b': mac_oyunculari.filter(takim='B'),
        'takim_listesi': takimlar_ve_oyunculari,
    }
    return render(request, 'grup_yonetimi/mac_sonucu_gir.html', context)

# grup_yonetimi/views.py (Gerekli import'lar ve Mac/Grup/GrupOyuncu modelleri tanımlı olmalı)

def geri_al_istatistikleri(mac):
    """
    Maç oynandıysa, skor ve istatistikleri ilgili GrupOyuncu kayıtlarından çıkarır.
    """
    if not mac.oynandi_mi:
        return

    grup = mac.grup
    
    # Maça katılan ve istatistiği olan oyuncular
    mac_oyunculari = MacOyuncu.objects.filter(mac=mac).select_related('oyuncu')

    for mac_oyuncu in mac_oyunculari:
        # Oyuncunun genel grup karnesi
        grup_oyuncu = GrupOyuncu.objects.get(grup=grup, oyuncu=mac_oyuncu.oyuncu)
        
        # 1. Genel Katılımı Geri Al
        grup_oyuncu.oynadigi_mac -= 1
        grup_oyuncu.gol -= mac_oyuncu.gol
        grup_oyuncu.asist -= mac_oyuncu.asist
        grup_oyuncu.sari_kart -= mac_oyuncu.sari_kart
        grup_oyuncu.kirmizi_kart -= mac_oyuncu.kirmizi_kart
        
        # 2. Kazanma/Berabere/Kaybetme İstatistiklerini Geri Al
        if mac_oyuncu.takim == 'A':
            kazanan_skor = mac.takim_a_skor
            kaybeden_skor = mac.takim_b_skor
        else: # Takım B
            kazanan_skor = mac.takim_b_skor
            kaybeden_skor = mac.takim_a_skor

        if kazanan_skor > kaybeden_skor:
            grup_oyuncu.kazandigi_mac -= 1
        elif kazanan_skor == kaybeden_skor:
            grup_oyuncu.berabere_mac -= 1
        else:
            grup_oyuncu.kaybettigi_mac -= 1

        grup_oyuncu.save()

    # Maç verilerini de temizle (oynandi_mi'yi False yapmaya gerek yok, sadece skorları sıfırla)
    # Skorlar güncelleneceği için, MacOyuncu istatistiklerini de sıfırlayalım (Yeni veriler formdan gelecek)
    MacOyuncu.objects.filter(mac=mac).update(gol=0, asist=0, sari_kart=0, kirmizi_kart=0)
    # Mac.objects.filter(pk=mac.id).update(takim_a_skor=None, takim_b_skor=None)
    # grup_yonetimi/views.py (Diğer fonksiyonların yanına ekleyin)

@login_required
@require_POST # Bu fonksiyonun sadece POST isteğiyle çalışmasını sağlar (Güvenlik için önemli)
def mac_sil(request, mac_id):
    mac = get_object_or_404(Mac, pk=mac_id)
    grup = mac.grup

    # Yönetici Kontrolü: Sadece Grup Yöneticisi maçı silebilir.
    if grup.yonetici != request.user:
        messages.error(request, "Yalnızca grup yöneticisi maç silebilir.")
        # redirect yerine, maçı listelediği sayfaya yönlendiriyoruz.
        return redirect('mac_listesi', grup_id=grup.id)

    # Oynanmış maçı silmeyi engelleme (ekstra güvenlik)
    if mac.oynandi_mi:
        messages.error(request, "Oynanmış bir maçı silemezsiniz. Lütfen önce skoru düzenleyin veya sıfırlayın.")
        return redirect('mac_listesi', grup_id=grup.id)

    # Maçı silme işlemi
    mac.delete()
    messages.success(request, f"'{mac.tarih}' tarihli maç başarıyla iptal edilip silinmiştir.")

    return redirect('mac_listesi', grup_id=grup.id)

# Not: require_POST kullanabilmek için aşağıdaki import'u eklediğinizden emin olun:
# from django.views.decorators.http import require_POST

# grup_yonetimi/views.py (Diğer fonksiyonların yanına ekleyin)


@login_required
def grup_olustur(request):
    if request.method == 'POST':
        grup_formu = GrupForm(request.POST, request.FILES)
        ayarlar_formu = GrupAyarlariForm(request.POST) # Ayarlar formu POST verisini alabilir
        
        if grup_formu.is_valid() and ayarlar_formu.is_valid():
            try:
                with transaction.atomic():
                    # 1. Grubu Oluşturma
                    yeni_grup = grup_formu.save(commit=False)
                    yeni_grup.yonetici = request.user # Yöneticisi giriş yapan kullanıcı
                    yeni_grup.save()
                    
                    # 2. Grup Ayarlarını Oluşturma
                    yeni_ayarlar = ayarlar_formu.save(commit=False)
                    yeni_ayarlar.grup = yeni_grup
                    yeni_ayarlar.save()
                    
                    # 3. Yöneticinin Kendisini Otomatik Olarak Gruba Üye Ekleme
                    GrupOyuncu.objects.create(
                        grup=yeni_grup,
                        oyuncu=request.user,
                        onay_durumu='O' # Yönetici olduğu için otomatik onaylı
                    )
                    
                    messages.success(request, f"'{yeni_grup.grup_adi}' grubu başarıyla oluşturuldu!")
                    return redirect('ana_sayfa')
                
            except Exception as e:
                messages.error(request, f"Grup oluşturulurken bir hata oluştu: {e}")
        else:
            messages.error(request, "Lütfen formu eksiksiz ve doğru doldurun.")
    
    else:
        grup_formu = GrupForm()
        ayarlar_formu = GrupAyarlariForm() # GET isteği için boş formlar

    context = {
        'grup_formu': grup_formu,
        'ayarlar_formu': ayarlar_formu,
    }
    return render(request, 'grup_yonetimi/grup_olustur.html', context)

# grup_yonetimi/views.py (Diğer fonksiyonların yanına ekleyin)


@login_required
def grup_detay(request, grup_id):
    grup = get_object_or_404(Grup, pk=grup_id)
    user = request.user
    
    # Kullanıcının grup ile olan durumunu kontrol et
    # GrupOyuncu'da kayıtlı olan kullanıcıyı ve durumunu çek
    grup_durumu = GrupOyuncu.objects.filter(grup=grup, oyuncu=user).first()
    
    bekleyen_talepler = None
    
    if grup.yonetici == user:
        # Yönetici ise, bekleyen tüm talepleri göster
        bekleyen_talepler = GrupOyuncu.objects.filter(grup=grup, onay_durumu='B')
    
    # Grup üyelerini çek (Sadece onaylanmış olanlar)
    uyeler = GrupOyuncu.objects.filter(grup=grup, onay_durumu='O').select_related('oyuncu')

    context = {
        'grup': grup,
        'grup_durumu': grup_durumu, # None, Beklemede, Onaylandı
        'bekleyen_talepler': bekleyen_talepler, # Sadece yöneticiye görünür
        'uyeler': uyeler,
        'is_yonetici': (grup.yonetici == user)
    }
    
    return render(request, 'grup_yonetimi/grup_detay.html', context)

# grup_yonetimi/views.py (Diğer fonksiyonların yanına ekleyin)


@login_required
@require_POST
def grup_katil(request, grup_id):
    grup = get_object_or_404(Grup, pk=grup_id)
    
    try:
        # GrupOyuncu kaydı oluştur (Varsayılan onay_durumu='B')
        GrupOyuncu.objects.create(
            grup=grup,
            oyuncu=request.user,
            onay_durumu='B'
        )
        messages.success(request, f"'{grup.grup_adi}' grubuna katılım talebiniz gönderildi. Yönetici onayını bekleyiniz.")
    except IntegrityError:
        messages.warning(request, "Bu gruba zaten bir talep göndermişsiniz veya üyesiniz.")

    return redirect('grup_detay', grup_id=grup.id)


@login_required
@require_POST
def grup_onayla(request, grup_oyuncu_id):
    talep = get_object_or_404(GrupOyuncu, pk=grup_oyuncu_id)
    grup = talep.grup
    
    # Yöneticilik Kontrolü
    if grup.yonetici != request.user:
        messages.error(request, "Bu işlemi yapmaya yetkiniz yok.")
        return redirect('grup_detay', grup_id=grup.id)
    
    action = request.POST.get('action')

    if action == 'onayla':
        talep.onay_durumu = 'O' # Onaylandı
        talep.save()
        messages.success(request, f"{talep.oyuncu.username} kullanıcısı gruba eklendi.")
    elif action == 'reddet':
        talep.delete() # Talebi sil
        messages.info(request, f"{talep.oyuncu.username} kullanıcısının talebi reddedildi.")
    
    return redirect('grup_detay', grup_id=grup.id)

# grup_yonetimi/views.py (Diğer fonksiyonların yanına ekleyin)

@login_required
@require_POST
def grup_ayril(request, grup_id):
    grup = get_object_or_404(Grup, pk=grup_id)
    
    # Yöneticinin ayrılmasını engelle (önce yöneticiyi devretmeli)
    if grup.yonetici == request.user:
        messages.error(request, "Grup yöneticisi olarak gruptan ayrılamazsınız. Önce yöneticiliği devretmelisiniz.")
        return redirect('ana_sayfa')
    
    try:
        # Onaylı kaydı bul ve sil
        GrupOyuncu.objects.get(grup=grup, oyuncu=request.user, onay_durumu='O').delete()
        messages.success(request, f"'{grup.grup_adi}' grubundan başarıyla ayrıldınız.")
    except GrupOyuncu.DoesNotExist:
        messages.error(request, "Bu grupta onaylı bir üyeliğiniz bulunamadı.")

    return redirect('ana_sayfa')


@login_required
@require_POST
def grup_talep_iptal(request, grup_id):
    grup = get_object_or_404(Grup, pk=grup_id)
    
    try:
        # Beklemedeki kaydı bul ve sil
        GrupOyuncu.objects.get(grup=grup, oyuncu=request.user, onay_durumu='B').delete()
        messages.success(request, f"'{grup.grup_adi}' grubuna gönderdiğiniz katılım talebi iptal edildi.")
    except GrupOyuncu.DoesNotExist:
        messages.error(request, "Bu grup için bekleyen bir talebiniz bulunamadı.")

    return redirect('ana_sayfa')

# grup_yonetimi/views.py (Diğer fonksiyonların yanına ekleyin)


@login_required
def profil_duzenle(request):
    # Eğer OyuncuProfili henüz oluşturulmamışsa (olası ilk kayıt), onu oluşturalım.
    # get_or_create, objeyi bulur veya oluşturur.
    profil, created = OyuncuProfili.objects.get_or_create(kullanici=request.user)
    
    if request.method == 'POST':
        # request.FILES, profil resmi gibi dosya yüklemeleri için önemlidir.
        kullanici_formu = KullaniciForm(request.POST, instance=request.user)
        profil_formu = OyuncuProfiliForm(request.POST, request.FILES, instance=profil)
        
        if kullanici_formu.is_valid() and profil_formu.is_valid():
            kullanici_formu.save()
            profil_formu.save()
            
            messages.success(request, 'Profiliniz başarıyla güncellendi!')
            return redirect('profil_duzenle') # Aynı sayfada kalıp başarı mesajını göster

        else:
            messages.error(request, 'Lütfen formdaki hataları düzeltin.')

    else:
        # GET isteği: Mevcut verilerle formları doldur
        kullanici_formu = KullaniciForm(instance=request.user)
        profil_formu = OyuncuProfiliForm(instance=profil)

    context = {
        'kullanici_formu': kullanici_formu,
        'profil_formu': profil_formu,
    }
    return render(request, 'grup_yonetimi/profil_duzenle.html', context)
# grup_yonetimi/views.py (Diğer fonksiyonların yanına ekleyin)


# Kayıt sayfası için giriş yapmaya gerek yok
def kayit(request):
    if request.method == 'POST':
        form = KayitFormu(request.POST)
        if form.is_valid():
            user = form.save()
            # Başarılı kayıt sonrası otomatik giriş yapmak için:
            # login(request, user) # İsteğe bağlı
            messages.success(request, 'Kaydınız başarıyla tamamlandı. Şimdi giriş yapabilirsiniz.')
            return redirect('login') # Django'nun varsayılan login URL'ine yönlendirir
        else:
            messages.error(request, 'Kayıt sırasında hatalar oluştu. Lütfen bilgilerinizi kontrol edin.')
    else:
        form = KayitFormu()

    context = {
        'form': form,
    }
    return render(request, 'grup_yonetimi/kayit.html', context)

# grup_yonetimi/views.py 
# from .forms import MacOlusturFormu # EN ÜSTE EKLEYİN

@login_required
def mac_olustur(request, grup_id):
    grup = get_object_or_404(Grup, pk=grup_id)
    
    # Sadece grup yöneticisi maç oluşturabilir
    if grup.yonetici != request.user:
        messages.error(request, "Sadece grup yöneticileri maç oluşturabilir.")
        return redirect('ana_sayfa')
    
    if request.method == 'POST':
        form = MacOlusturFormu(request.POST)
        if form.is_valid():
            mac = form.save(commit=False)
            mac.grup = grup
            mac.save()
            
            # Maç oluşturulduktan sonra yöneticiyi otomatik olarak katılımcı olarak ekleyebiliriz
            MacKatilim.objects.create(mac=mac, oyuncu=request.user)
            
            messages.success(request, f"'{grup.grup_adi}' için yeni maç başarıyla oluşturuldu.")
            return redirect('mac_listesi', grup_id=grup.id)
    else:
        form = MacOlusturFormu()
        
    context = {
        'form': form,
        'grup': grup,
    }
    return render(request, 'grup_yonetimi/mac_olustur.html', context)

# grup_yonetimi/views.py 
# from django.views.decorators.http import require_POST # EN ÜSTE EKLEYİN

@login_required
@require_POST
def mac_katilim_toggle(request, mac_id):
    mac = get_object_or_404(Mac, pk=mac_id)
    
    # 1. Kontrol: Maç Oynandı mı?
    if mac.oynandi_mi:
        messages.error(request, "Bu maç oynandığı için katılım durumu değiştirilemez.")
        return redirect('mac_listesi', grup_id=mac.grup.id)
    
    # 2. Katılım Kaydını Bul
    katilim_obj = MacKatilim.objects.filter(mac=mac, oyuncu=request.user)
    
    if katilim_obj.exists():
        # Kayıt varsa: Sil (Katılımdan Çekil)
        katilim_obj.delete()
        messages.info(request, f"'{mac.yer}' maçına katılımınız iptal edildi.")
    else:
        # Kayıt yoksa: Oluştur (Katıl)
        # Önce bu grubun üyesi olup olmadığını kontrol et
        if not GrupOyuncu.objects.filter(grup=mac.grup, oyuncu=request.user, onay_durumu='O').exists() and mac.grup.yonetici != request.user:
             messages.error(request, "Sadece grubun onaylı üyeleri bu maça katılabilir.")
             return redirect('mac_listesi', grup_id=mac.grup.id)
             
        MacKatilim.objects.create(mac=mac, oyuncu=request.user)
        messages.success(request, f"'{mac.yer}' maçına katılımınız onaylandı!")

    return redirect('mac_listesi', grup_id=mac.grup.id)

# grup_yonetimi/views.py

# Gerekli import'lar: (User, transaction, ObjectDoesNotExist, find_optimal_teams)

# Önemli not: Bu fonksiyon, GrupOyuncu modelindeki hesapla_seviye_puani metodunu kullanır.
# Bu metodun puanı hesaplayıp döndürdüğünden emin olun.

@login_required
@require_POST
def mac_dengele_otomatik(request, mac_id):
    mac = get_object_or_404(Mac, pk=mac_id)
    grup = mac.grup

    if grup.yonetici != request.user:
        messages.error(request, "Yetkiniz yok.")
        return redirect('mac_listesi', grup_id=grup.id)

    katilimcilar_qs = MacKatilim.objects.filter(mac=mac).select_related('oyuncu')
    n = katilimcilar_qs.count()

    if n % 2 != 0 or n < 2:
        messages.error(request, f"Dengeleme için çift sayıda (En az 2) katılımcı gereklidir. Mevcut: {n}")
        return redirect('mac_listesi', grup_id=grup.id)

    # 1. Oyuncu Puanlarını Hazırlama
    katilimcilar_data = []
    for katilim in katilimcilar_qs:
        # GrupOyuncu kaydını çek (Puan hesaplaması buradan yapılır)
        g_oyuncu = get_object_or_404(GrupOyuncu, grup=grup, oyuncu=katilim.oyuncu)
        puan = g_oyuncu.hesapla_seviye_puani() # <<< Puanı hesaplayan metodu çağır
        
        katilimcilar_data.append({
            'oyuncu_id': katilim.oyuncu.id,
            'puan': puan,
            'mevkii': g_oyuncu.oyuncu.oyuncuprofili.mevkii
        })

    # 2. Optimal Dengelemeyi Yap
    takim_sayisi = n // 2
    takim_a_sonucu, takim_b_sonucu, fark = find_optimal_teams(katilimcilar_data, takim_sayisi)

    # 3. Takımları MacOyuncu Kayıtlarına Atama
    try:
        with transaction.atomic():
            # Eski takım atamalarını sıfırla (Mevcutsa)
            MacOyuncu.objects.filter(mac=mac).delete() 

            # Yeni MacOyuncu kayıtlarını oluştur
            for oyuncu_id in takim_a_sonucu['oyuncu_ids']:
                oyuncu = get_object_or_404(User, pk=oyuncu_id)
                MacOyuncu.objects.create(mac=mac, oyuncu=oyuncu, takim='A')

            for oyuncu_id in takim_b_sonucu['oyuncu_ids']:
                oyuncu = get_object_or_404(User, pk=oyuncu_id)
                MacOyuncu.objects.create(mac=mac, oyuncu=oyuncu, takim='B')
            
            # Maç objesini dengeleme sonuçlarıyla güncelle
            mac.takim_a_denge_puani = takim_a_sonucu['toplam_puan']
            mac.takim_b_denge_puani = takim_b_sonucu['toplam_puan']
            mac.denge_farki = int(fark)
            mac.save()
            
            messages.success(request, f"Takımlar başarıyla dengelendi. Puan Farkı: {int(fark)}")
    
    except Exception as e:
        messages.error(request, f"Dengeleme sırasında bir hata oluştu: {e}")

    # Dengeleme sonucunu görmek için manuel sayfaya yönlendir
    return redirect('mac_dengele_manuel', mac_id=mac.id)


# grup_yonetimi/views.py

@login_required
def mac_dengele_manuel(request, mac_id):
    mac = get_object_or_404(Mac, pk=mac_id)
    grup = mac.grup
    renk = 'red' if mac.denge_farki > 10 else 'green'
    if grup.yonetici != request.user:
        messages.error(request, "Yetkiniz yok.")
        return redirect('mac_listesi', grup_id=grup.id)
    
    # 1. Oyuncu Puanlarını ve Mevcut Atamayı Çek
    katilimcilar_qs = MacKatilim.objects.filter(mac=mac).select_related('oyuncu')
    
    oyuncular_puanli = []
    for katilim in katilimcilar_qs:
        g_oyuncu = get_object_or_404(GrupOyuncu, grup=grup, oyuncu=katilim.oyuncu)
        
        # Mevcut atamayı çek (MacOyuncu'dan)
        mevcut_atama = MacOyuncu.objects.filter(mac=mac, oyuncu=katilim.oyuncu).first()
        
        oyuncular_puanli.append({
            'oyuncu': katilim.oyuncu,
            'puan': g_oyuncu.hesapla_seviye_puani(),
            'mevkii': g_oyuncu.oyuncu.oyuncuprofili.get_mevkii_display(),
            'takim': mevcut_atama.takim if mevcut_atama else None # None, A veya B
        })

    # 2. POST İsteği: Manuel Atamayı Kaydetme
    # grup_yonetimi/views.py (mac_dengele_manuel fonksiyonu içindeki POST bloğu)


# ...

    # 2. POST İsteği: Manuel Atamayı Kaydetme
    if request.method == 'POST':
        
        # Önceki atamaları temizle
        MacOyuncu.objects.filter(mac=mac).delete()
        
        takim_a_puani = 0
        takim_b_puani = 0
        
        # Formdan gelen her oyuncu atamasını döngüye al
        for key, value in request.POST.items():
            if key.startswith('atama_') and value in ['A', 'B']:
                # Anahtardan oyuncu ID'sini çıkar
                try:
                    oyuncu_id = key.split('_')[1]
                    oyuncu = get_object_or_404(User, pk=oyuncu_id)
                    g_oyuncu = get_object_or_404(GrupOyuncu, grup=grup, oyunc=oyuncu)
                    puan = g_oyuncu.hesapla_seviye_puani()

                    # Yeni MacOyuncu kaydını oluştur
                    MacOyuncu.objects.create(mac=mac, oyunc=oyuncu, takim=value)

                    # Puanları topla
                    if value == 'A':
                        takim_a_puani += puan
                    elif value == 'B':
                        takim_b_puani += puan
                        
                except Exception as e:
                    # Hata yönetimi (loglama yapılabilir)
                    print(f"Hata oluştu: {e}") 
                    
        # Maç objesindeki dengeleme puanlarını ve farkı güncelle
        mac.takim_a_denge_puani = takim_a_puani
        mac.takim_b_denge_puani = takim_b_puani
        mac.denge_farki = abs(takim_a_puani - takim_b_puani)
        mac.save()
        
        messages.success(request, "Manuel takım ataması başarıyla kaydedildi.")
        return redirect('mac_listesi', grup_id=grup.id)

    # ... (GET isteği içeriği devam ediyor) ...
    context = {
        'mac': mac,
        'grup': grup,
        'oyuncular_puanli': sorted(oyuncular_puanli, key=lambda x: x['puan'], reverse=True),
        'dengeleme_sonucu_mevcut': MacOyuncu.objects.filter(mac=mac).exists(),
        'denge_farki_renk': renk
    }
    return render(request, 'grup_yonetimi/mac_dengele_manuel.html', context)
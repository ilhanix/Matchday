# grup_yonetimi/forms.py

from django import forms
from .models import Grup, GrupAyarlari, OyuncuProfili, MEVKI_SECENEKLERI
from django.contrib.auth.models import User
# from .models import OyuncuProfili
from django.contrib.auth.forms import UserCreationForm
from django import forms
from .models import Mac

class GrupForm(forms.ModelForm):
    # Bu form ile kullanıcı sadece Grup Adı ve Resmi girecek.
    class Meta:
        model = Grup
        # KRİTİK: 'herkese_gorunur' alanını fields listesine ekleyin
        fields = ['grup_adi', 'grup_resmi', 'herkese_gorunur'] # <<< GÜNCELLENDİ
        widgets = {
            'grup_adi': forms.TextInput(attrs={'placeholder': 'Grubunuza bir isim verin'}),
        }
        
class GrupAyarlariForm(forms.ModelForm):
    # Bu form ile grup ayarlarını varsayılan değerlerle oluşturabiliriz.
    class Meta:
        model = GrupAyarlari
        fields = ['min_mac_grup_puani', 'min_mac_genel_puani']

# grup_yonetimi/forms.py (Mevcut formların altına ekleyin)

class KullaniciForm(forms.ModelForm):
    # Kullanıcı sadece kendi adını ve soyadını güncelleyebilmeli
    class Meta:
        model = User
        fields = ['first_name', 'last_name']
        
class OyuncuProfiliForm(forms.ModelForm):
    # Oyuncu mevkisini ve profil resmini güncelleyebilmeli
    class Meta:
        model = OyuncuProfili
        fields = ['mevkii', 'profil_resmi']
        # Yönetici Puanları (yetkili_puan, kisilik_puani) burada OLMAMALI, çünkü sadece yönetici değiştirebilir.
# grup_yonetimi/forms.py (Mevcut formların altına ekleyin)


class KayitFormu(UserCreationForm):
    # Kullanıcıdan ek olarak Ad ve Soyadını istiyoruz
    first_name = forms.CharField(max_length=150, required=True, label='Ad')
    last_name = forms.CharField(max_length=150, required=True, label='Soyad')
    
    # Mevki bilgisini de ilk kayıtta alabiliriz
    mevkii = forms.ChoiceField(choices=MEVKI_SECENEKLERI, label='Varsayılan Mevkii')

    class Meta(UserCreationForm.Meta):
        # User modelindeki kullanıcı adı ve şifre alanlarına ek olarak bu alanları kullan
        fields = UserCreationForm.Meta.fields + ('first_name', 'last_name', 'mevkii')
        pass
    # Kullanıcı kaydını (User ve OyuncuProfili) tek bir işlemle kaydetmek için save metodunu override ediyoruz
    def save(self, commit=True):
        # 1. User objesini kaydet (username, password, first_name, last_name)
        user = super().save(commit=False)
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        if commit:
            user.save()
            
        # 2. Oyuncu Profili objesini otomatik oluştur
        OyuncuProfili.objects.create(
            kullanici=user,
            mevkii=self.cleaned_data["mevkii"],
            # Yetkili puan ve kişilik puanı varsayılan olarak kalacak (5)
        )
        return user
# grup_yonetimi/forms.py (Mevcut formların altına ekleyin)


class MacOlusturFormu(forms.ModelForm):
    class Meta:
        model = Mac
        fields = ['tarih', 'saat', 'yer']
        
        # Gelişmiş Tarih/Saat widget'ları (isteğe bağlı ama UX için önerilir)
        widgets = {
            'tarih': forms.DateInput(attrs={'type': 'date'}),
            'saat': forms.TimeInput(attrs={'type': 'time'}),
        }

# grup_yonetimi/forms.py (Dosyanın sonuna ekleyin)

class OyuncuIstatistikFormu(forms.Form):
    # Bu form, her oyuncu için dinamik olarak oluşturulacak
    gol = forms.IntegerField(min_value=0, required=False, initial=0, label='Gol')
    asist = forms.IntegerField(min_value=0, required=False, initial=0, label='Asist')
    sari_kart = forms.IntegerField(min_value=0, required=False, initial=0, label='Sarı Kart')
    kirmizi_kart = forms.IntegerField(min_value=0, required=False, initial=0, label='Kırmızı Kart')

    def __init__(self, *args, oyuncu=None, **kwargs):
        super().__init__(*args, **kwargs)
        if oyuncu:
            # Oyuncuyu formun içinde tutuyoruz (kayıt yaparken kullanmak için)
            self.oyuncu = oyuncu 
            self.fields['oyuncu_id'] = forms.CharField(widget=forms.HiddenInput(), initial=oyuncu.id)
            self.fields['gol'].label = f"{oyuncu.username} - Gol"
            # ... diğer alanları da isme göre güncelleyebilirsiniz.
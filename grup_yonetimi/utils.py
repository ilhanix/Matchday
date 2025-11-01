# grup_yonetimi/utils.py

import itertools

def find_optimal_teams(katilimcilar_listesi, takim_sayisi):
    """
    Verilen oyuncu listesini, puan farkı en az olacak şekilde iki takıma böler.
    
    :param katilimcilar_listesi: Oyuncuların puan ve mevki bilgisini içeren listesi.
        Format: [{'oyuncu_id': 1, 'puan': 50, 'mevkii': 'KL'}, ...]
    :param takim_sayisi: Her takımdaki oyuncu sayısı (N/2).
    :return: En iyi takım A ve B listeleri.
    """
    
    # 1. Puanları Hazırlama
    oyuncu_id_map = {p['oyuncu_id']: p for p in katilimcilar_listesi}
    oyuncular = list(oyuncu_id_map.keys())
    
    toplam_puan = sum(p['puan'] for p in katilimcilar_listesi)
    en_iyi_fark = float('inf')
    en_iyi_takim_a = []

    # 2. Tüm Olası Takım A Kombinasyonlarını Dene (Optimal Çözüm)
    # nC(n/2) kombinasyonunu dener. 22 oyuncu için yaklaşık 650.000 kombinasyondur. Hızlıdır.
    for takim_a_ids in itertools.combinations(oyuncular, takim_sayisi):
        
        # 3. Takım B'yi Otomatik Belirle
        takim_b_ids = [p for p in oyuncular if p not in takim_a_ids]

        # 4. Mevki Kısıtlamasını Kontrol Et (Örn: Kaleci Dengesi)
        kaleci_a = sum(1 for p_id in takim_a_ids if oyuncu_id_map[p_id]['mevkii'] == 'KL')
        kaleci_b = sum(1 for p_id in takim_b_ids if oyuncu_id_map[p_id]['mevkii'] == 'KL')
        
        # Eğer kaleci sayısı eşit değilse, bu kombinasyonu atla.
        # Bu kısıt, maç özelinde seçilen tüm kritik mevkiler için genişletilmelidir.
        if kaleci_a != kaleci_b:
             continue 

        # 5. Puan Farkını Hesapla
        puan_a = sum(oyuncu_id_map[p_id]['puan'] for p_id in takim_a_ids)
        
        # Puan B'yi hesaplamaya gerek yok, Toplam Puan sabit.
        # puan_b = toplam_puan - puan_a
        # fark = abs(puan_a - puan_b)
        
        # Alternatif fark hesaplama (daha hızlı):
        # Eğer fark sıfıra yakınsa, puan A, toplam puanın yarısına yakındır.
        fark = abs(puan_a - (toplam_puan / 2))

        # 6. En İyi Kombinasyonu Kaydet
        if fark < en_iyi_fark:
            en_iyi_fark = fark
            en_iyi_takim_a = takim_a_ids
            # Eğer fark 0 ise, mükemmel denge bulundu ve aramayı durdurabiliriz.
            if fark == 0:
                break
    
    # En iyi Takım B'yi belirle
    en_iyi_takim_b = [p for p in oyuncular if p not in en_iyi_takim_a]
    # En iyi takım A ve B'nin toplam puanlarını tekrar hesapla
    puan_a = sum(oyuncu_id_map[p_id]['puan'] for p_id in en_iyi_takim_a)
    puan_b = sum(oyuncu_id_map[p_id]['puan'] for p_id in en_iyi_takim_b)
    
    # Sonucu Sözlük (Dictionary) olarak döndür
    return {
        'oyuncu_ids': en_iyi_takim_a,
        'toplam_puan': puan_a
    }, {
        'oyuncu_ids': en_iyi_takim_b,
        'toplam_puan': puan_b
    }, en_iyi_fark
    return en_iyi_takim_a, en_iyi_takim_b, en_iyi_fark
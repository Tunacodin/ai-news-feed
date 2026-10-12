# ai-news-feed

Trend olan denenebilir yapay zekâ araçlarını, modellerini ve GitHub repolarını bulup Tuna için "hadi deneyelim" formatında dikey video metnine çeviren hat. Odak: izleyicinin bugün deneyebileceği, ekranda görülebilen şeyler. Siyaset, yatırım, dava gibi gündem haberleri kapsam dışı (en fazla 2 öneri, sadece güçlü görseli varsa).

## Dizin

| Klasör | İçerik | Git |
|---|---|---|
| `scripts/` | Tüm Python betikleri; daima repo kökünden çalıştır (`python scripts/x.py`) | evet |
| `data/` | Otomatik veri: `NEWS.md`, `news.jsonl`, `trendler.json`, `seen.json` (news.yml yazar) | evet |
| `icerik/` | Öneriler, liste, video metinleri, gelen linkler (bot.yml yazar) | evet |
| `lab/` | Araştırılan her araç kendi klasöründe, `INDEX.md`, `SINYALLER.md` | evet (`test/` hariç) |
| `docs/` | Araştırma ve karar notları | evet |
| `assets/` | Sabit dosyalar (`fonts/`) | evet |
| `yerel/` | `ham/` (çekilen klipler), `cikti/` (kurgu sonucu), `indir/` (indirilen linkler) | asla |

## Akış

1. news.yml (saatlik cron): `scripts/fetch_news.py` haberleri `data/NEWS.md` ve `data/news.jsonl` dosyalarına ekler (her yeni haberi Telegram'a da yollar, `RAW_TELEGRAM=0` kapatır); `scripts/trendler.py` GitHub Trending, Hugging Face, Show HN ve Product Hunt trend fotoğrafını `data/trendler.json` dosyasına yazar.
2. Günlük öneri (her sabah bulut rutini, `oneri` skill'i): `scripts/adaylar.py` çıktısını damıtır, en iyi 8 denenebilir konuyu `icerik/oneriler/<tarih>.json` dosyasına yazar.
3. `scripts/bot.py` (bot.yml): önerileri Telegram'a butonlu yollar (yalnız `ONERI_TELEGRAM=1` ise; varsayılan kapalı), "Listeye al" / "Çektim" butonlarını ve yazılı numaraları işleyip `icerik/liste.json` dosyasına yazar.
4. VS Code (`video` skill'i): listedeki konuları derin araştırır, çekim planı ve okunacak metni `icerik/videolar/` altına yazar, push'lar; bot ikisini Telegram'a yollar.
5. Kurgu (`scripts/edit.py`, sadece yerel): Tuna ham klipleri `yerel/ham/<id>/` klasörüne koyar (ad sırası = kurgu sırası, örn. `1-yuz.mp4`, `2-ekran.mp4`, `3-yuz.mp4`). Sessizlikleri keser, dikeye oturtur, sesi dengeler, kelime kelime altyazı ve kapak yazısı basar; sonucu `yerel/cikti/<id>.mp4` olarak kaydeder ve `.env` varsa Telegram'a yollar.

6. Gelen linkler: Tuna izlediği videoların linkini Telegram'da bota atar; bot her linki `icerik/gelen/<id>.json` dosyasına yazar. VS Code'da `scripts/gelen.py` videoyu indirir, konuşmayı yazıya döker, kareleri çıkarır (`yerel/indir/<id>/`); `gelen` skill'i ekrandaki repo/URL'yi bulup doğrular ve bot bulunanları "Listeye al" butonlu kartla Telegram'a yollar. Instagram için `.env`: `IG_COOKIES=<cookies.txt yolu>` ya da `IG_TARAYICI=firefox` (yan hesap).

## Tetikleyiciler

- "listeyi hazırla", "videoları hazırla", "metinleri yaz" → `video` skill'ini uygula.
- "bugünün önerilerini hazırla", "damıt" → `oneri` skill'ini uygula.
- "edit et", "kurguyu yap", "videoyu kes" → `yerel/ham/<id>/` klasörünü kontrol et, `.venv/Scripts/python scripts/edit.py <id>` çalıştır, çıkan videodan 3-4 kare alıp altyazı ve kapağı kontrol et, sonucu bildir. Kurulum yoksa: `python -m venv .venv && .venv/Scripts/pip install faster-whisper` (ffmpeg PATH'te olmalı).
- "gelenleri işle" → `gelen` skill'ini uygula.
- "link botu başlat", "linkten video" → `.venv/Scripts/python scripts/link_bot.py` (ayrı Telegram botu, `.env`: `LINK_BOT_TOKEN`, `LINK_CHAT_ID`; `--kisayol` açılışta başlatır). Her URL "Izgara anlatım" şablonundan (`yerel/ham/yeni`, `.env` `LINK_SABLON` ile değişir) kopyalanan bir `yerel/ham/projeN` projesi olur (iş bitince içerikten ad alır, ör. `image-blaster`): indir, transkript, İçerik araştırması, taslak kurgu, render, mp4 Telegram'a. Telegram'da `/durum` kuyruğu gösterir.
- "metin yaz", "hook yaz", "metni güçlendir", "metni puanla" → `metin` skill'ini uygula (puan: `python scripts/metin_kontrol.py <md> --plan`).
- "kurgu seçiciyi aç", "sesleri/geçişleri seçeyim" → `python scripts/kurgu_secici.py <proje-klasörü> --ac` (varsayılan `yerel/ham/jev/hf5`); seçimler `secimler.json`, video `yerel/cikti/`.
- "içerik araştır", "rakip içerikler", "kullanıcılar ne diyor", "video planı çıkar" → `icerik-usta` skill'ini uygula (kodlama yok, sadece araştırma). Kurgu seçicideki İçerik sekmesi aynı skill'i arka planda çalıştırır: `python scripts/icerik_arastir.py <proje> "<istek>"` (ilk adımda `scripts/tara.py` ile `assets/kaynaklar.json` içindeki 49 kaynağı tarar), sonuç `<proje>/icerik/arastirma.json` (proje başına tek akış). Motor Gemini: Google girişli Antigravity CLI (`~/.gemini/bin/agy.exe`), model `ICERIK_MODEL` ile değişir (varsayılan gemini-3.8-flash-high); `ICERIK_MOTOR=claude` Claude'a döner.
- "paralel video", "sekmeleri aç" → `python scripts/kurgu_sekme.py --ac` (http://localhost:8760; her sekme ayrı proje, Claude oturumu ve önizleme). Medya panelinde videodaki ve toplanan tüm dosyalar düzeltilir; orijinal `.yedek/` klasöründe saklanır.
- "instagram'a yükle", "yayınla", "instagram analizi", "rapor çıkar", "rakipleri çek" → `python scripts/instagram.py <komut>` (kur, durum, yayinla, gonderiler, analiz, rapor, rakip, hashtag, sil, yorum). Yayınlama ve silme `--evet` olmadan kuru çalışır; `--evet`i ancak kullanıcı onayından sonra ekle. Veri `yerel/instagram/` altında kalır. Önizlemeli yayın paneli: kurgu seçicide "Instagram" düğmesi (`/instagram`).
- "liste ne durumda" → `icerik/liste.json` özetini göster (seçildi / hazır / çekildi).
- Bir araç, repo, model, site ya da teknik araştırıldığında (yapıştırılan gönderi, "araştır") → sonucu `lab/<slug>/README.md` olarak kaydet (`python scripts/lab.py yeni <slug> <link>`, sonra alanları doldur: `video` Tuna'ya uygunluk, `bana`/`alan` ve "Benim için" bölümü kullanıcının şirketi, danışmanlığı ve sunumları için değerlendirme; yeni bir eğilim varsa `lab/SINYALLER.md`'ye işle), ardından `python scripts/lab.py` ile `lab/INDEX.md`'yi yenile. Varsa mevcut klasörü güncelle, kopya açma.
- "lab ne durumda", "neleri test edeceğiz", "benim işime ne yarar" → `lab/INDEX.md` özetini göster (video tarafı ve "Benim için" tarafı ayrı).

## Kurallar

- Kod yorumları ASCII (depo düzeni). Kullanıcıya görünen Türkçe metin tam Türkçe karakterli; uzun çizgi (U+2014) yok.
- `icerik/bot_state.json` dosyasını elle düzenleme (Telegram okuma konumu burada).
- `yerel/`, `.env`, `.venv/` ve cookies dosyası asla commit edilmez (repo public).
- Video odağı: anlatım içeriği değil, izleyicinin bu teknoloji/repoyla artık ne yapabildiğini ve kazancını anlatır; kaynak videodaki proje yalnız bir örnektir (`docs/anlatim-dili.md` Odak).
- Test etmeden içerik yok: bir araç ancak `lab/<slug>/README.md` içinde `durum: test-edildi` ve test notları dolu ise video metnine girer. `lab/*/test/` yerel test çıktısıdır, commit edilmez.
- main'e hem news.yml hem bot.yml yazar: push'tan önce daima `git pull --rebase`.

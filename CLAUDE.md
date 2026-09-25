# ai-news-feed

Trend olan denenebilir yapay zekâ araçlarını, modellerini ve GitHub repolarını bulup Tuna için "hadi deneyelim" formatında dikey video metnine çeviren hat. Odak: izleyicinin bugün deneyebileceği, ekranda görülebilen şeyler. Siyaset, yatırım, dava gibi gündem haberleri kapsam dışı (en fazla 2 öneri, sadece güçlü görseli varsa).

## Akış

1. news.yml (saatlik cron): `fetch_news.py` haberleri `NEWS.md` ve `data/news.jsonl` dosyalarına ekler (ham haberi Telegram'a göndermez, `RAW_TELEGRAM=1` ile açılır); `trendler.py` GitHub Trending, Hugging Face, Show HN ve Product Hunt trend fotoğrafını `data/trendler.json` dosyasına yazar.
2. Günlük öneri (her sabah bulut rutini, `oneri` skill'i): `adaylar.py` çıktısını damıtır, en iyi 8 denenebilir konuyu `icerik/oneriler/<tarih>.json` dosyasına yazar.
3. `bot.py` (bot.yml): önerileri Telegram'a butonlu yollar, "Listeye al" / "Çektim" butonlarını ve yazılı numaraları işleyip `icerik/liste.json` dosyasına yazar.
4. VS Code (`video` skill'i): listedeki konuları derin araştırır, çekim planı ve okunacak metni `icerik/videolar/` altına yazar, push'lar; bot ikisini Telegram'a yollar.

## Tetikleyiciler

- "listeyi hazırla", "videoları hazırla", "metinleri yaz" → `video` skill'ini uygula.
- "bugünün önerilerini hazırla", "damıt" → `oneri` skill'ini uygula.
- "liste ne durumda" → `icerik/liste.json` özetini göster (seçildi / hazır / çekildi).

## Kurallar

- Kod yorumları ASCII (depo düzeni). Kullanıcıya görünen Türkçe metin tam Türkçe karakterli; uzun çizgi (U+2014) yok.
- `icerik/bot_state.json` dosyasını elle düzenleme (Telegram okuma konumu burada).
- main'e hem news.yml hem bot.yml yazar: push'tan önce daima `git pull --rebase`.

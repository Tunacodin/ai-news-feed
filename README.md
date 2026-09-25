# ai-news-feed

Trend olan denenebilir AI araclarini/repolarini/modellerini her sabah damitilmis video konu onerilerine, secilenleri de
kameradan okunacak dikey video metinlerine ceviren hat. Ayrinti: `CLAUDE.md`.

## Dosyalar
- `fetch_news.py` - haber cekme + dedup (`seen.json`), `NEWS.md` ve `data/news.jsonl` kaydi
- `trendler.py` - GitHub Trending, Hugging Face, Show HN, Product Hunt trend fotografi (`data/trendler.json`)
- `adaylar.py` - trendler + son 24 saatin haberleri, gunluk oneri adiminin girdisi
- `bot.py` - Telegram: gunluk oneriler, "Listeye al" / "Cektim" butonlari, hazir metin bildirimi
- `icerik/oneriler/` - gunluk oneriler, `icerik/liste.json` - secilen konular, `icerik/videolar/` - metinler
- `.claude/skills/oneri`, `.claude/skills/video` - Claude'un izledigi talimatlar
- `.github/workflows/news.yml` (saatlik), `bot.yml` (15 dk + icerik/ push'u)

## Kurulum
1. Telegram: `@BotFather` -> `/newbot` -> token al. Botla mesajlas, sonra
   `https://api.telegram.org/bot<TOKEN>/getUpdates` adresinden `chat.id` al.
2. Repo Settings -> Secrets and variables -> Actions -> iki secret ekle:
   `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`.
3. Ham haberleri de Telegram'a almak istersen news.yml'e `RAW_TELEGRAM: "1"` ekle.

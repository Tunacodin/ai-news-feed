# ai-news-feed

Trend olan denenebilir AI araclarini/repolarini/modellerini her sabah damitilmis video konu onerilerine, secilenleri de
kameradan okunacak dikey video metinlerine ceviren hat. Ayrinti: `CLAUDE.md`.

## Dizin
```
scripts/          Python betikleri (repo kokunden calistir: python scripts/x.py)
  fetch_news.py   haber cekme + dedup, data/NEWS.md ve data/news.jsonl kaydi
  trendler.py     GitHub Trending, Hugging Face, Show HN, Product Hunt trend fotografi
  adaylar.py      trendler + son 24 saatin haberleri, gunluk oneri adiminin girdisi
  bot.py          Telegram: oneriler, "Listeye al" / "Cektim" butonlari, hazir metin bildirimi
  edit.py         yerel kurgu: yerel/ham/<id>/ kliplerinden altyazili dikey video
  gelen.py        Telegram'a atilan linkleri indirir, yaziya doker, kare cikarir (yerel/indir/)
  lab.py          lab/ indeksi, yeni kayit, durum degisimi
data/             otomatik veri (news.yml yazar): NEWS.md, news.jsonl, trendler.json, seen.json
icerik/           oneriler/, liste.json, videolar/, gelen/ (bot.yml yazar)
lab/              arastirilan araclar, klasor basina bir arac; INDEX.md, SINYALLER.md
docs/             arastirma ve karar notlari
assets/fonts/     altyazi fontu
.claude/skills/   oneri, video, gelen: Claude'un izledigi talimatlar
.github/workflows news.yml (saatlik), bot.yml (15 dk + icerik/ push'u)
yerel/            ham/, cikti/, indir/: yerel medya, git'e girmez
```

## Kurulum
1. Telegram: `@BotFather` -> `/newbot` -> token al. Botla mesajlas, sonra
   `https://api.telegram.org/bot<TOKEN>/getUpdates` adresinden `chat.id` al.
2. Repo Settings -> Secrets and variables -> Actions -> iki secret ekle:
   `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`.
3. Telegram varsayilan olarak haber listesini alir (kapatmak: news.yml'e `RAW_TELEGRAM: "0"`). Gunluk oneri mesajlari icin bot.yml'e `ONERI_TELEGRAM: "1"` ekle.
4. Gelen linkler (yerel): `.venv/Scripts/pip install yt-dlp gallery-dl faster-whisper`. Instagram icin yan hesabin
   cerezleri `.env`'e: `IG_COOKIES=<repo disinda cookies.txt yolu>` ya da `IG_TARAYICI=firefox`.

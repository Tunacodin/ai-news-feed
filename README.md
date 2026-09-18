# ai-news-feed

Saatlik AI haber toplayicisi. GitHub Actions cron + ucretsiz RSS/Hacker News/Google News uclari.
Yeni haberler `NEWS.md`'ye eklenir ve Telegram'a gonderilir.

## Kurulum
1. Telegram: `@BotFather` -> `/newbot` -> token al. Botla mesajlas, sonra
   `https://api.telegram.org/bot<TOKEN>/getUpdates` adresinden `chat.id` al.
2. Repo Settings -> Secrets and variables -> Actions -> iki secret ekle:
   `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`.
3. Actions sekmesi -> `news` -> `Run workflow` ile ilk kez elle tetikle.

## Dosyalar
- `fetch_news.py` - haber cekme + dedup (`seen.json`) + Telegram gonderim
- `.github/workflows/news.yml` - saatlik cron (`5 * * * *`) + workflow_dispatch

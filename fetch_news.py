# Ne yapar: RSS + Hacker News + Google News'ten AI haberi ceker, gorulenleri eler,
# yenileri Telegram'a yollar ve NEWS.md'ye ekler. Sadece feedparser harici bagimlilik yok.
import json, os, urllib.request, urllib.parse, pathlib, html, feedparser

FEEDS = [
    "https://techcrunch.com/tag/artificial-intelligence/feed/",
    "https://news.google.com/rss/search?q=AI+model+launch&hl=en-US",
]
HN = "https://hn.algolia.com/api/v1/search_by_date?query=AI&tags=story&hitsPerPage=30"
TG_TOKEN, TG_CHAT = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "news-bot/1.0"})
    return urllib.request.urlopen(req, timeout=20).read()


def translate(text):
    # Once MyMemory (ucretsiz, anahtarsiz, sunucudan calisir), olmazsa Google gtx yedek.
    if not text:
        return text
    try:
        q = urllib.parse.quote(text)
        url = f"https://api.mymemory.translated.net/get?q={q}&langpair=en|tr"
        data = json.loads(get(url))
        t = data.get("responseData", {}).get("translatedText", "") or ""
        if t and "MYMEMORY WARNING" not in t.upper():
            return html.unescape(t)
    except Exception:
        pass
    try:
        q = urllib.parse.quote(text)
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=tr&dt=t&q={q}"
        data = json.loads(get(url))
        return "".join(seg[0] for seg in data[0] if seg and seg[0])
    except Exception:
        return text


def tg_send(text):
    if not (TG_TOKEN and TG_CHAT):
        return
    data = urllib.parse.urlencode({
        "chat_id": TG_CHAT, "text": text,
        "parse_mode": "HTML", "disable_web_page_preview": "true",
    }).encode()
    urllib.request.urlopen(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", data=data, timeout=20)


seen_path = pathlib.Path("seen.json")
seen = set(json.loads(seen_path.read_text())) if seen_path.exists() else set()
items = []

# Hacker News (JSON)
try:
    for h in json.loads(get(HN))["hits"]:
        if h.get("url") and h["objectID"] not in seen:
            items.append({"title": h["title"], "url": h["url"], "src": "HN"})
            seen.add(h["objectID"])
except Exception as e:
    print("HN hata:", e)

# RSS / Google News
for f in FEEDS:
    try:
        for e in feedparser.parse(get(f)).entries[:20]:
            key = e.get("id", e.get("link", ""))
            if key and key not in seen:
                items.append({"title": html.unescape(e.title), "url": e.link, "src": "RSS"})
                seen.add(key)
    except Exception as e:
        print("RSS hata:", f, e)

seen_path.write_text(json.dumps(list(seen)))

# Basliklari Turkce'ye cevir (sadece yeni haberler)
for i in items:
    i["title"] = translate(i["title"])

if items:
    with open("NEWS.md", "a", encoding="utf-8") as fp:
        fp.write("\n" + "\n".join(f"- [{i['title']}]({i['url']}) `{i['src']}`" for i in items) + "\n")
    # Telegram 4096 karakter siniri: 10'arli gruplar halinde yolla
    for k in range(0, len(items), 10):
        chunk = items[k:k + 10]
        msg = "\n\n".join(f"<b>{html.escape(i['title'])}</b>\n{i['url']} - {i['src']}" for i in chunk)
        try:
            tg_send(msg)
        except Exception as e:
            print("Telegram hata:", e)
    print(f"{len(items)} yeni haber")
else:
    print("yeni haber yok")

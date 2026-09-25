# Ne yapar: RSS + Hacker News + Google News'ten AI haberi ceker, gorulenleri eler,
# yenileri NEWS.md'ye ve data/news.jsonl'e (gunluk oneri adiminin girdisi) ekler.
# Ham haberleri Telegram'a yollamak artik istege bagli (RAW_TELEGRAM=1). Sadece feedparser harici bagimlilik yok.
import json, os, re, time, urllib.request, urllib.parse, pathlib, html, feedparser

FEEDS = [
    "https://techcrunch.com/tag/artificial-intelligence/feed/",
    "https://news.google.com/rss/search?q=AI+model+launch&hl=en-US",
    # Resmi urun bloglari: "bugun deneyebilirsin" turu yeni ozellikler buradan cikar
    "https://openai.com/news/rss.xml",
    "https://blog.google/technology/ai/rss/",
    "https://huggingface.co/blog/feed.xml",
]
HN = "https://hn.algolia.com/api/v1/search_by_date?query=AI&tags=story&hitsPerPage=30"
TG_TOKEN, TG_CHAT = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
RAW_TG = os.environ.get("RAW_TELEGRAM") == "1"  # ham akis; varsayilan kapali, yerine gunluk oneri gelir
LOG = pathlib.Path("data/news.jsonl")
KEEP_DAYS = 14


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


def tg_call(method, params):
    if not (TG_TOKEN and TG_CHAT):
        return {"ok": False, "description": "no token"}
    data = urllib.parse.urlencode(params).encode("utf-8")
    try:
        r = urllib.request.urlopen(f"https://api.telegram.org/bot{TG_TOKEN}/{method}", data=data, timeout=25).read()
        return json.loads(r)
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read())
        except Exception:
            return {"ok": False, "description": str(e)}
    except Exception as e:
        return {"ok": False, "description": str(e)}


def find_media(url, entry):
    # Once RSS medya alanlari, sonra sayfanin og:image/og:video etiketi. Bulamazsa (None, None).
    entry = entry or {}
    for key in ("media_content", "media_thumbnail"):
        for m in entry.get(key, []) or []:
            u = m.get("url")
            if u:
                return ("photo", u)
    for enc in (entry.get("enclosures", []) or []):
        u = enc.get("href") or enc.get("url")
        t = (enc.get("type") or "")
        if u and t.startswith("video"):
            return ("video", u)
        if u and t.startswith("image"):
            return ("photo", u)
    m = re.search(r'<img[^>]+src=["\']([^"\']+)', entry.get("summary", "") or "")
    if m:
        return ("photo", m.group(1))
    try:
        page = get(url).decode("utf-8", "ignore")
        v = re.search(r'property=["\']og:video(?::url)?["\'][^>]*content=["\']([^"\']+)', page) \
            or re.search(r'content=["\']([^"\']+)["\'][^>]*property=["\']og:video', page)
        if v:
            return ("video", html.unescape(v.group(1)))
        og = re.search(r'property=["\']og:image["\'][^>]*content=["\']([^"\']+)', page) \
            or re.search(r'content=["\']([^"\']+)["\'][^>]*property=["\']og:image', page) \
            or re.search(r'name=["\']twitter:image["\'][^>]*content=["\']([^"\']+)', page)
        if og:
            return ("photo", html.unescape(og.group(1)))
    except Exception:
        pass
    return (None, None)


def send_item(i):
    # Gorunurde sadece kalin baslik + saga ok butonu; ciplak link gorunmez. Gorsel/video varsa ekli.
    cap = f"<b>{html.escape(i['title'])}</b>"
    btn = json.dumps({"inline_keyboard": [[{"text": "→", "url": i["url"]}]]})
    base = {"chat_id": TG_CHAT, "parse_mode": "HTML", "reply_markup": btn}
    kind, media = find_media(i["url"], i.get("entry"))
    r = {"ok": False}
    if kind == "photo":
        r = tg_call("sendPhoto", {**base, "photo": media, "caption": cap})
    elif kind == "video":
        r = tg_call("sendVideo", {**base, "video": media, "caption": cap})
    if not r.get("ok"):
        # Medya yoksa ya da Telegram reddettiyse (gecersiz/buyuk/erisilemez) duz metne dus.
        if kind in ("photo", "video"):
            print("medya reddedildi:", r.get("description"), "|", (media or "")[:70])
        tg_call("sendMessage", {**base, "text": cap, "disable_web_page_preview": "true"})
    time.sleep(0.4)  # Telegram hiz sinirina takilmamak icin


def append_log(items, now):
    # Zaman damgali, makinece okunur kayit (adaylar.py okur). KEEP_DAYS gunden eskisi budanir.
    LOG.parent.mkdir(exist_ok=True)
    cutoff = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - KEEP_DAYS * 86400))
    old = [l for l in LOG.read_text(encoding="utf-8").splitlines() if l and json.loads(l)["ts"] >= cutoff] \
        if LOG.exists() else []
    new = [json.dumps({"ts": now, "title": i["title"], "title_en": i["title_en"], "url": i["url"],
                       "src": i["src"], "hn_id": i.get("hn_id"), "pub": i.get("pub")}, ensure_ascii=False) for i in items]
    LOG.write_text("\n".join(old + new) + "\n", encoding="utf-8")


def main():
    seen_path = pathlib.Path("seen.json")
    seen = set(json.loads(seen_path.read_text())) if seen_path.exists() else set()
    items = []

    # Hacker News (JSON)
    try:
        for h in json.loads(get(HN))["hits"]:
            if h.get("url") and h["objectID"] not in seen:
                items.append({"title": h["title"], "url": h["url"], "src": "HN", "hn_id": h["objectID"],
                              "pub": (h.get("created_at") or "")[:10]})
                seen.add(h["objectID"])
    except Exception as e:
        print("HN hata:", e)

    # RSS / Google News
    for f in FEEDS:
        try:
            for e in feedparser.parse(get(f)).entries[:20]:
                key = e.get("id", e.get("link", ""))
                if key and key not in seen:
                    pub = time.strftime("%Y-%m-%d", e.published_parsed) if e.get("published_parsed") else None
                    items.append({"title": html.unescape(e.title), "url": e.link, "src": "RSS", "entry": e, "pub": pub})
                    seen.add(key)
        except Exception as e:
            print("RSS hata:", f, e)

    seen_path.write_text(json.dumps(list(seen)))

    # Basliklari Turkce'ye cevir (sadece yeni haberler); orijinali arastirma icin saklanir
    for i in items:
        i["title_en"] = i["title"]
        i["title"] = translate(i["title"])

    if items:
        with open("NEWS.md", "a", encoding="utf-8") as fp:
            fp.write("\n" + "\n".join(f"- [{i['title']}]({i['url']}) `{i['src']}`" for i in items) + "\n")
        append_log(items, time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
        # Her habere ayri mesaj: kalin baslik + saga ok butonu + (varsa) gorsel/video.
        if RAW_TG:
            for i in items:
                send_item(i)
        print(f"{len(items)} yeni haber")
    else:
        print("yeni haber yok")


if __name__ == "__main__":
    main()

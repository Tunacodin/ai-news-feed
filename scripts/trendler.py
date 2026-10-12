# Ne yapar: "denenebilir" seylerin anlik trend fotografini data/trendler.json'a yazar:
# GitHub Trending (gunluk), Hugging Face trend modeller ve Space'ler (tarayicida denenen demolar),
# Show HN (son 36 saat), Product Hunt AI kategorisi. news.yml her calismada tazeler; gunluk oneri okur.
# Her kaynak bagimsiz: biri coken digerlerini etkilemez.
import json, re, time, html, pathlib, feedparser
from fetch_news import get

OUT = pathlib.Path("data/trendler.json")


def clean(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", s or ""))).strip()


def github():
    s = get("https://github.com/trending?since=daily").decode("utf-8", "ignore")
    out = []
    for a in re.findall(r'<article class="Box-row">(.*?)</article>', s, re.S):
        repo = re.search(r'<h2[^>]*>\s*<a[^>]*href="/([^"]+)"', a)
        if not repo:
            continue
        d = re.search(r'<p class="col-9[^"]*">(.*?)</p>', a, re.S)
        today = re.search(r"([\d,]+) stars? today", a)
        total = re.search(r'href="/[^"]+/stargazers"[^>]*>.*?</svg>\s*([\d,]+)', a, re.S)
        lang = re.search(r'itemprop="programmingLanguage">([^<]+)<', a)
        num = lambda m: int(m.group(1).replace(",", "")) if m else None
        out.append({"ad": repo.group(1), "url": f"https://github.com/{repo.group(1)}", "aciklama": clean(d.group(1) if d else ""),
                    "bugun_yildiz": num(today), "toplam_yildiz": num(total), "dil": lang.group(1) if lang else None})
    return out


def hf(kind):
    rows = json.loads(get(f"https://huggingface.co/api/{kind}?sort=trendingScore&limit=25&full=true"))
    out = []
    for x in rows:
        card = x.get("cardData") or {}
        base = "https://huggingface.co/" + ("spaces/" if kind == "spaces" else "")
        out.append({"ad": x["id"], "url": base + x["id"], "baslik": card.get("title"),
                    "aciklama": card.get("short_description"), "tur": x.get("pipeline_tag") or x.get("sdk"),
                    "begeni": x.get("likes"), "trend": x.get("trendingScore"), "olusturma": (x.get("createdAt") or "")[:10]})
    return out


def show_hn():
    since = int(time.time()) - 36 * 3600
    url = f"https://hn.algolia.com/api/v1/search?tags=show_hn&numericFilters=created_at_i>{since},points>15&hitsPerPage=40"
    hits = json.loads(get(url))["hits"]
    hits.sort(key=lambda h: -(h.get("points") or 0))
    return [{"ad": h["title"], "url": h.get("url") or f"https://news.ycombinator.com/item?id={h['objectID']}",
             "hn": f"https://news.ycombinator.com/item?id={h['objectID']}", "puan": h.get("points"),
             "yorum": h.get("num_comments")} for h in hits]


def product_hunt():
    f = feedparser.parse(get("https://www.producthunt.com/feed?category=artificial-intelligence"))
    # Ozetin sonundaki "Discussion | Link" kalibi atilir
    return [{"ad": e.title, "url": e.link, "aciklama": re.sub(r"\s*Discussion\s*\|\s*Link\s*$", "", clean(e.get("summary")))[:200],
             "tarih": (e.get("published") or "")[:10]}
            for e in sorted(f.entries, key=lambda e: e.get("published") or "", reverse=True)[:30]]


def main():
    data = {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    for key, fn in [("github", github), ("hf_space", lambda: hf("spaces")), ("hf_model", lambda: hf("models")),
                    ("show_hn", show_hn), ("product_hunt", product_hunt)]:
        try:
            data[key] = fn()
        except Exception as e:
            print(key, "hata:", e)
            data[key] = []
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print({k: len(v) for k, v in data.items() if isinstance(v, list)})


if __name__ == "__main__":
    main()

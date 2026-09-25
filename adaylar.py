# Ne yapar: gunluk oneri adimi (Claude) icin tek bir aday listesi basar:
#  1) data/trendler.json: GitHub Trending, HF Space/model, Show HN, Product Hunt (denenebilir seyler)
#  2) data/news.jsonl: son N saatin (varsayilan 26) haberleri, HN puan/yorum sayilari tazelenmis
# Kullanim: python adaylar.py [saat]. Ag hatasinda puansiz devam eder.
import json, sys, time, pathlib, urllib.request

HOURS = int(sys.argv[1]) if len(sys.argv) > 1 else 26
LOG, TREND = pathlib.Path("data/news.jsonl"), pathlib.Path("data/trendler.json")


def hn_stats(ids):
    # Algolia tek istekte coklu hikaye: tags=story,(story_1,story_2,...). 50'lik parcalar.
    out = {}
    for k in range(0, len(ids), 50):
        tags = ",".join(f"story_{i}" for i in ids[k:k + 50])
        url = f"https://hn.algolia.com/api/v1/search?tags=story,({tags})&hitsPerPage=50"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "news-bot/1.0"})
            for h in json.loads(urllib.request.urlopen(req, timeout=20).read())["hits"]:
                out[h["objectID"]] = (h.get("points") or 0, h.get("num_comments") or 0)
        except Exception as e:
            print("HN puan hatasi:", e, file=sys.stderr)
    return out


def trends():
    if not TREND.exists():
        print("# Trend fotografi yok (data/trendler.json)")
        return
    t = json.loads(TREND.read_text(encoding="utf-8"))
    print(f"# TRENDLER ({t['ts']})")
    print("## GitHub Trending (bugun yildiz / toplam)")
    for x in t.get("github", []):
        print(f"+{x['bugun_yildiz']}/{x['toplam_yildiz']} {x['dil'] or '-'} | {x['ad']} | {x['aciklama'][:140]} | {x['url']}")
    for key, name in [("hf_space", "Hugging Face Space (tarayicida denenen demo)"), ("hf_model", "Hugging Face model")]:
        print(f"## {name} (trend puani, begeni, olusturma)")
        for x in t.get(key, []):
            print(f"{x['trend']} {x['begeni']}b {x['olusturma']} {x['tur'] or '-'} | {x['ad']} | {x['baslik'] or ''} {x['aciklama'] or ''} | {x['url']}")
    print("## Show HN (son 36 saat, puan/yorum)")
    for x in t.get("show_hn", []):
        print(f"{x['puan']}p/{x['yorum']}y | {x['ad']} | {x['url']}")
    print("## Product Hunt AI")
    for x in t.get("product_hunt", []):
        print(f"{x['tarih']} | {x['ad']} | {x['aciklama'][:120]} | {x['url']}")


def news():
    cutoff = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - HOURS * 3600))
    rows = [json.loads(l) for l in LOG.read_text(encoding="utf-8").splitlines() if l.strip()]
    rows = [r for r in rows if r["ts"] >= cutoff]
    stats = hn_stats([r["hn_id"] for r in rows if r.get("hn_id")])
    for r in rows:
        r["pts"], r["cmt"] = stats.get(r.get("hn_id"), (None, None))
    # HN'de ilgi goren once, sonra en yeni. Kopya haberleri birlestirmek Claude'un isi.
    rows.sort(key=lambda r: r["ts"], reverse=True)
    rows.sort(key=lambda r: -(r["pts"] or 0))
    print(f"# HABERLER: son {HOURS} saat, {len(rows)} adet (yayin tarihi, kaynak, HN puan/yorum, baslik, url)")
    for r in rows:
        score = f"{r['pts']}p/{r['cmt']}y" if r["pts"] is not None else "-"
        print(f"{r.get('pub') or r['ts'][:10]} {r['src']:3} {score:>9} | {r.get('title_en') or r['title']} | {r['url']}")


if __name__ == "__main__":
    trends()
    print()
    news()

# Instagram Graph API (Facebook Login yolu), sadece yerel.
# Kurulum: .env -> META_APP_ID, META_APP_SECRET, kisa omurlu kullanici token'i ile:
#   python scripts/instagram.py kur <kisa_token>
# Sonra .env'e IG_TOKEN (suresiz sayfa token'i) ve IG_USER_ID yazilir.
# Komutlar: kur, durum, yayinla, gonderiler, analiz, rapor, rakip, hashtag, sil, yorum, otodm
# Veriler yerel/instagram/ altina yazilir (repo public; analiz verisi commit edilmez).
import argparse, datetime, html, json, os, pathlib, re, socket, sys, time, urllib.error, urllib.parse, urllib.request
KOK = pathlib.Path(__file__).resolve().parent.parent


def env():
    # .env from repo root, so the editor server works from any cwd
    d = {}
    p = KOK / ".env"
    if p.exists():
        for l in p.read_text(encoding="utf-8").splitlines():
            if "=" in l and not l.strip().startswith("#"):
                k, v = l.split("=", 1)
                d.setdefault(k.strip(), v.strip().strip('"'))
    # GitHub Actions passes secrets as env vars (no .env there)
    for k in ("IG_TOKEN", "IG_USER_ID", "IG_KULLANICI"):
        if os.environ.get(k):
            d[k] = os.environ[k].strip()
    return d

SURUM = "v25.0"
GRAPH = f"https://graph.facebook.com/{SURUM}"
RUPLOAD = f"https://rupload.facebook.com/ig-api-upload/{SURUM}"
KLASOR = KOK / "yerel" / "instagram"
REELS_METRIK = ("views,reach,likes,comments,shares,saved,total_interactions,"
                "ig_reels_avg_watch_time,ig_reels_video_view_total_time,reels_skip_rate")
HESAP_METRIK = ("reach,views,accounts_engaged,total_interactions,likes,comments,shares,saves,"
                "profile_views,profile_links_taps,follows_and_unfollows")


class HataIG(Exception):
    pass


def istek(yol, params=None, yontem="GET", url=None, veri=None, basliklar=None):
    params = dict(params or {})
    adres = url or (yol if yol.startswith("http") else f"{GRAPH}/{yol.lstrip('/')}")
    govde = veri
    if yontem in ("GET", "DELETE") or veri is not None:
        if params:
            adres += ("&" if "?" in adres else "?") + urllib.parse.urlencode(params)
    else:
        govde = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(adres, data=govde, method=yontem, headers=basliklar or {})
    try:
        return json.loads(urllib.request.urlopen(req, timeout=300).read() or b"{}")
    except urllib.error.HTTPError as e:
        try:
            h = json.loads(e.read()).get("error", {})
        except Exception:
            h = {}
        raise HataIG(f"{e.code} {h.get('type', '')} ({h.get('code', '')}/{h.get('error_subcode', '')}): "
                     f"{h.get('error_user_msg') or h.get('message', e.reason)}") from None


def ayar():
    e = env()
    tok, uid = e.get("IG_TOKEN"), e.get("IG_USER_ID")
    if not (tok and uid):
        sys.exit("IG_TOKEN ve IG_USER_ID yok. Once: python scripts/instagram.py kur <kisa_token>")
    return tok, uid


def env_yaz(degerler):
    p = KOK / ".env"
    satirlar = p.read_text(encoding="utf-8").splitlines() if p.exists() else []
    kalan = dict(degerler)
    for i, l in enumerate(satirlar):
        k = l.split("=", 1)[0].strip()
        if k in kalan:
            satirlar[i] = f"{k}={kalan.pop(k)}"
    satirlar += [f"{k}={v}" for k, v in kalan.items()]
    p.write_text("\n".join(satirlar) + "\n", encoding="utf-8")


def kaydet(ad, veri):
    KLASOR.mkdir(parents=True, exist_ok=True)
    (KLASOR / ad).write_text(json.dumps(veri, ensure_ascii=False, indent=1), encoding="utf-8")


# ---------- kur / durum ----------

def kur(a):
    e = env()
    app, sir = e.get("META_APP_ID"), e.get("META_APP_SECRET")
    if not (app and sir):
        sys.exit(".env'e META_APP_ID ve META_APP_SECRET ekle (Meta uygulamasi > Ayarlar > Temel).")
    uzun = istek("oauth/access_token", {"grant_type": "fb_exchange_token", "client_id": app,
                                         "client_secret": sir, "fb_exchange_token": a.token})["access_token"]
    sayfalar = istek("me/accounts", {"fields": "name,access_token,instagram_business_account{id,username}",
                                     "access_token": uzun}).get("data", [])
    bagli = [s for s in sayfalar if s.get("instagram_business_account")]
    if not bagli:
        sys.exit("Instagram'a bagli Facebook Sayfasi bulunamadi. Sayfa izni verildi mi, hesap sayfaya bagli mi?")
    if a.sayfa:
        bagli = [s for s in bagli if a.sayfa.lower() in s["name"].lower()] or bagli
    s = bagli[0]
    ig = s["instagram_business_account"]
    # Uzun omurlu kullanici token'indan alinan sayfa token'i suresizdir.
    env_yaz({"IG_TOKEN": s["access_token"], "IG_USER_ID": ig["id"], "IG_KULLANICI": ig.get("username", "")})
    print(f"Baglandi: @{ig.get('username')} (sayfa: {s['name']}). .env guncellendi.")
    if len(bagli) > 1:
        print("Diger sayfalar:", ", ".join(x["name"] for x in bagli[1:]), "(secmek icin --sayfa)")


def durum(a):
    tok, uid = ayar()
    e = env()
    h = istek(uid, {"fields": "username,name,followers_count,follows_count,media_count", "access_token": tok})
    print(f"@{h['username']}  takipci {h.get('followers_count')}  gonderi {h.get('media_count')}")
    if e.get("META_APP_ID") and e.get("META_APP_SECRET"):
        d = istek("debug_token", {"input_token": tok,
                                  "access_token": f"{e['META_APP_ID']}|{e['META_APP_SECRET']}"}).get("data", {})
        bitis = d.get("expires_at") or 0
        print("Token:", "suresiz" if not bitis else datetime.datetime.fromtimestamp(bitis).isoformat(),
              "| izinler:", ", ".join(d.get("scopes", [])))


# ---------- yayinla ----------

def reel_yayinla(video, aciklama="", kapak_ms=None, ortak=None, akisa=True, deneme=False, ses_adi=None, ilerleme=print):
    # local mp4 -> resumable upload -> wait FINISHED -> publish; returns {"id", "permalink"}
    tok, uid = ayar()
    video = pathlib.Path(video)
    if not video.is_file():
        raise HataIG(f"video yok: {video}")
    if len(aciklama) > 2200:
        raise HataIG(f"açıklama {len(aciklama)} karakter, sınır 2200")
    p = {"media_type": "REELS", "upload_type": "resumable", "caption": aciklama,
         "share_to_feed": "true" if akisa else "false", "access_token": tok}
    if kapak_ms is not None:
        p["thumb_offset"] = str(int(kapak_ms))
    if ortak:
        p["collaborators"] = json.dumps([o.lstrip("@") for o in ortak][:3])
    if deneme:
        p["trial_params"] = json.dumps({"graduation_strategy": "SS_PERFORMANCE"})
    if ses_adi:
        p["audio_name"] = ses_adi[:100]
    ilerleme("Konteyner açılıyor")
    kap = istek(f"{uid}/media", p, "POST")["id"]
    veri = video.read_bytes()
    ilerleme(f"Video yükleniyor ({len(veri) // 1024 // 1024} MB)")
    r = istek("", url=f"{RUPLOAD}/{kap}", yontem="POST", veri=veri,
              basliklar={"Authorization": f"OAuth {tok}", "offset": "0", "file_size": str(len(veri))})
    if not r.get("success"):
        raise HataIG(f"yükleme başarısız: {r}")
    ilerleme("Instagram videoyu işliyor")
    for _ in range(90):
        s = istek(kap, {"fields": "status_code,status", "access_token": tok})
        if s.get("status_code") == "FINISHED":
            break
        if s.get("status_code") in ("ERROR", "EXPIRED"):
            raise HataIG(f"işleme hatası: {s.get('status')}")
        time.sleep(10)
    else:
        raise HataIG(f"zaman aşımı; konteyner {kap} 24 saat geçerli")
    ilerleme("Yayınlanıyor")
    mid = istek(f"{uid}/media_publish", {"creation_id": kap, "access_token": tok}, "POST")["id"]
    m = istek(mid, {"fields": "permalink", "access_token": tok})
    KLASOR.mkdir(parents=True, exist_ok=True)
    with (KLASOR / "yayinlar.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps({"id": mid, "permalink": m.get("permalink"), "video": video.name, "aciklama": aciklama,
                            "zaman": datetime.datetime.now().isoformat(timespec="seconds")}, ensure_ascii=False) + "\n")
    return {"id": mid, "permalink": m.get("permalink")}


def yayinla(a):
    _, uid = ayar()
    video = pathlib.Path(a.video)
    if not video.exists():
        sys.exit(f"Video yok: {video}")
    aciklama = pathlib.Path(a.aciklama_dosya).read_text(encoding="utf-8") if a.aciklama_dosya else (a.aciklama or "")
    print(f"Hedef: @{env().get('IG_KULLANICI', uid)}  video: {video.name} ({video.stat().st_size // 1024 // 1024} MB)")
    print("Aciklama:", (aciklama[:200] + "...") if len(aciklama) > 200 else aciklama or "(bos)")
    if not a.evet:
        print("\nKuru calisma: hicbir sey yuklenmedi. Yayinlamak icin --evet ekle.")
        return
    r = reel_yayinla(video, aciklama, a.kapak_ms, a.ortak, not a.akisa_koyma, a.deneme, a.ses_adi)
    print(f"Yayinlandi: {r['permalink']} (id {r['id']})")


# ---------- editor paneli (kurgu_secici.py /instagram) ----------

TASLAK = KLASOR / "taslaklar.json"
PANEL = {"durum": "bos", "adim": "", "sonuc": None, "hata": None}
_HESAP = {"t": 0, "v": None}


def panel_hesap():
    if time.time() - _HESAP["t"] > 600:
        try:
            tok, uid = ayar()
            _HESAP["v"] = istek(uid, {"fields": "username,name,profile_picture_url,followers_count,media_count", "access_token": tok})
        except (HataIG, SystemExit) as ex:
            _HESAP["v"] = {"hata": str(ex)}
        _HESAP["t"] = time.time()
    return _HESAP["v"]


def panel_taslaklar():
    return json.loads(TASLAK.read_text(encoding="utf-8")) if TASLAK.exists() else {}


def panel_taslak_kaydet(ad, t):
    d = panel_taslaklar()
    d[pathlib.Path(ad).name] = {k: t.get(k) for k in ("aciklama", "kapak_ms", "ses_adi", "akisa", "ortak", "deneme")}
    KLASOR.mkdir(parents=True, exist_ok=True)
    TASLAK.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")


def panel_yayinlar():
    f = KLASOR / "yayinlar.jsonl"
    return [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()] if f.exists() else []


def panel_yayinla(video, t):
    # background job for the editor; state in PANEL
    if PANEL["durum"] == "calisiyor":
        return False
    PANEL.update(durum="calisiyor", adim="Başlıyor", sonuc=None, hata=None)

    def is_():
        try:
            r = reel_yayinla(video, str(t.get("aciklama") or ""), t.get("kapak_ms"), t.get("ortak") or None,
                             t.get("akisa", True), bool(t.get("deneme")), t.get("ses_adi") or None,
                             ilerleme=lambda m: PANEL.update(adim=m))
            PANEL.update(durum="bitti", sonuc=r, adim="Yayınlandı")
        except Exception as ex:
            PANEL.update(durum="hata", hata=str(ex), adim="")
    import threading
    threading.Thread(target=is_, daemon=True).start()
    return True


_META = {}  # gun -> {"t", "v"}; editor Meta tab, 10 min cache


def panel_meta(gun=30, yenile=False):
    # channel + per-post insights for the editor's Meta tab
    gun = max(1, min(int(gun), 30))  # API: max 30 days per request
    c = _META.get(gun)
    if c and not yenile and time.time() - c["t"] < 600:
        return c["v"]
    try:
        tok, uid = ayar()
        h = istek(uid, {"fields": "username,name,profile_picture_url,followers_count,follows_count,media_count",
                        "access_token": tok})
        medya = medya_listesi(tok, uid, 50, ",thumbnail_url,media_url")
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(8) as ex:
            ic = ex.map(lambda m: medya_icgoru(tok, m), medya)
            kanal = ex.submit(hesap_icgoru, tok, uid, gun)
            onceki = ex.submit(hesap_icgoru, tok, uid, gun, gun)  # same-length window right before
            gunluk = ex.submit(gunluk_erisim, tok, uid, gun)
            kitle = {b: ex.submit(kitle_dagilim, tok, uid, b) for b in ("age", "gender", "city", "country")}
            for m, i in zip(medya, ic):
                m["icgoru"] = i
            v = {"zaman": datetime.datetime.now().isoformat(timespec="seconds"), "hesap": h,
                 "kanal": {"gun": gun, **kanal.result()}, "onceki": onceki.result(), "gunluk": gunluk.result(),
                 "kitle": {b: f.result() for b, f in kitle.items()}, "medya": medya}
    except (HataIG, SystemExit) as ex:
        return {"hata": str(ex)}
    _META[gun] = {"t": time.time(), "v": v}
    return v


# ---------- analiz ----------

def medya_listesi(tok, uid, n, ek=""):
    alan = "id,caption,media_type,media_product_type,permalink,timestamp,like_count,comments_count" + ek
    out, url = [], None
    params = {"fields": alan, "limit": min(n, 50), "access_token": tok}
    while len(out) < n:
        r = istek(url or f"{uid}/media", None if url else params)
        out += r.get("data", [])
        url = r.get("paging", {}).get("next")
        if not url:
            break
    return out[:n]


def medya_icgoru(tok, m):
    metrik = REELS_METRIK if m.get("media_product_type") == "REELS" else "reach,likes,comments,shares,saved,total_interactions,views"
    try:
        r = istek(f"{m['id']}/insights", {"metric": metrik, "access_token": tok})
        return {x["name"]: (x.get("values") or [{}])[0].get("value", x.get("total_value", {}).get("value"))
                for x in r.get("data", [])}
    except HataIG as ex:
        return {"hata": str(ex)}


def gonderiler(a):
    tok, uid = ayar()
    for m in medya_listesi(tok, uid, a.n):
        bas = (m.get("caption") or "").split("\n")[0][:60]
        print(f"{m['timestamp'][:10]}  {m['id']}  {m.get('media_product_type', ''):6}  "
              f"begeni {m.get('like_count', '-'):>5}  yorum {m.get('comments_count', '-'):>4}  {bas}")


def gunluk_erisim(tok, uid, gun):
    # daily reach series for the Meta tab chart; end_time's date is the (Pacific) day itself
    bitis = int(time.time())
    try:
        r = istek(f"{uid}/insights", {"metric": "reach", "period": "day", "since": bitis - gun * 86400,
                                      "until": bitis, "access_token": tok})
        d = (r.get("data") or [{}])[0].get("values", [])
        return [{"t": x["end_time"], "v": x.get("value", 0)} for x in d]
    except HataIG:
        return []


def kitle_dagilim(tok, uid, kirilim):
    # follower demographics; Meta returns nothing below 100 followers
    try:
        r = istek(f"{uid}/insights", {"metric": "follower_demographics", "period": "lifetime",
                                      "metric_type": "total_value", "breakdown": kirilim, "access_token": tok})
        b = ((r.get("data") or [{}])[0].get("total_value") or {}).get("breakdowns") or [{}]
        s = [{"ad": x["dimension_values"][0], "v": x["value"]} for x in b[0].get("results", [])]
        return sorted(s, key=lambda x: -x["v"])[:8]
    except (HataIG, KeyError, IndexError):
        return []


def hesap_icgoru(tok, uid, gun, kaydir=0):
    bitis = int(time.time()) - kaydir * 86400
    p = {"metric": HESAP_METRIK, "period": "day", "metric_type": "total_value",
         "since": bitis - gun * 86400, "until": bitis, "access_token": tok}
    try:
        r = istek(f"{uid}/insights", p)
        return {x["name"]: x.get("total_value", {}).get("value") for x in r.get("data", [])}
    except HataIG as ex:
        return {"hata": str(ex)}


def analiz(a):
    tok, uid = ayar()
    h = istek(uid, {"fields": "username,followers_count,follows_count,media_count", "access_token": tok})
    medya = medya_listesi(tok, uid, a.n)
    for i, m in enumerate(medya, 1):
        m["icgoru"] = medya_icgoru(tok, m)
        print(f"\r{i}/{len(medya)} gonderi", end="", flush=True)
    print()
    gun = min(a.gun, 30)  # API: tek istekte en fazla 30 gun
    veri = {"zaman": datetime.datetime.now().isoformat(timespec="seconds"), "hesap": h,
            "hesap_icgoru": {"gun": gun, **hesap_icgoru(tok, uid, gun)}, "medya": medya}
    ad = f"analiz-{datetime.date.today()}.json"
    kaydet(ad, veri)
    print(f"Kaydedildi: {KLASOR / ad}")
    return veri


# ---------- rapor ----------

def _yuzde(x, y):
    return f"%{100 * x / y:.1f}" if x and y else "-"


def rapor(a):
    dosyalar = sorted(KLASOR.glob("analiz-*.json"))
    if a.yenile or not dosyalar:
        veri = analiz(a)
    else:
        veri = json.loads(dosyalar[-1].read_text(encoding="utf-8"))
    h, hi = veri["hesap"], veri["hesap_icgoru"]
    satir = []
    reels = [m for m in veri["medya"] if m.get("media_product_type") == "REELS" and "hata" not in m.get("icgoru", {})]
    reels.sort(key=lambda m: m["icgoru"].get("views") or 0, reverse=True)
    for m in reels:
        g = m["icgoru"]
        izl = g.get("views") or 0
        ort = g.get("ig_reels_avg_watch_time")
        satir.append(
            f"<tr><td>{m['timestamp'][:10]}</td><td><a href='{html.escape(m['permalink'])}'>"
            f"{html.escape((m.get('caption') or '(açıklamasız)').split(chr(10))[0][:70])}</a></td>"
            f"<td class=s>{izl:,}</td><td class=s>{g.get('reach') or 0:,}</td>"
            f"<td class=s>{_yuzde((g.get('saved') or 0) + (g.get('shares') or 0), izl)}</td>"
            f"<td class=s>{g.get('reels_skip_rate') if g.get('reels_skip_rate') is not None else '-'}</td>"
            f"<td class=s>{f'{ort / 1000:.1f} sn' if ort else '-'}</td></tr>")
    toplam = sum(m["icgoru"].get("views") or 0 for m in reels)
    ozet = [("Takipçi", f"{h.get('followers_count', 0):,}"), ("Reel sayısı (analiz)", str(len(reels))),
            ("Toplam izlenme", f"{toplam:,}"), ("Reel başına izlenme", f"{toplam // len(reels):,}" if reels else "-"),
            (f"Son {hi.get('gun')} gün erişim", f"{hi.get('reach') or '-'}"),
            (f"Son {hi.get('gun')} gün profil ziyareti", f"{hi.get('profile_views') or '-'}")]
    tarih = veri["zaman"][:10]
    sayfa = f"""<!doctype html><html lang=tr><meta charset=utf-8><title>Instagram raporu {tarih}</title>
<style>body{{font:15px/1.5 Inter,system-ui,sans-serif;background:#F7F8F7;color:#17201F;max-width:1040px;margin:40px auto;padding:0 24px}}
h1{{font-size:24px;margin:0}}.alt{{color:#596563;margin:4px 0 28px}}table{{border-collapse:collapse;width:100%;background:#fff}}
th,td{{border-bottom:1px solid #D9DEDD;padding:8px 10px;text-align:left}}th{{font-size:12px;color:#596563;text-transform:uppercase}}
.s{{text-align:right;font-variant-numeric:tabular-nums}}a{{color:#17201F}}h2{{font-size:16px;margin:32px 0 10px}}</style>
<h1>Instagram raporu: @{html.escape(h.get('username', ''))}</h1><p class=alt>Veri tarihi {tarih}. Kaydetme+paylaşım oranı izlenmeye göre; atlama oranı ilk 3 saniyede kaydıranların yüzdesi.</p>
<table>{''.join(f'<tr><td>{k}</td><td class=s>{v}</td></tr>' for k, v in ozet)}</table>
<h2>Reel'ler (izlenmeye göre)</h2><table><tr><th>Tarih</th><th>Gönderi</th><th class=s>İzlenme</th><th class=s>Erişim</th>
<th class=s>Kaydet+paylaş</th><th class=s>Atlama %</th><th class=s>Ort. izleme</th></tr>{''.join(satir)}</table></html>"""
    yol = KLASOR / f"rapor-{tarih}.html"
    yol.write_text(sayfa, encoding="utf-8")
    print(f"Rapor: {yol.resolve()}")


# ---------- trend / rakip ----------

def rakip(a):
    tok, uid = ayar()
    sonuc = []
    for k in a.kullanici:
        k = k.lstrip("@")
        alan = (f"business_discovery.username({k}){{username,followers_count,media_count,"
                f"media.limit({a.n}){{caption,media_product_type,like_count,comments_count,view_count,permalink,timestamp}}}}")
        try:
            b = istek(uid, {"fields": alan, "access_token": tok})["business_discovery"]
        except HataIG as ex:
            print(f"@{k}: {ex}")
            continue
        sonuc.append(b)
        print(f"\n@{b['username']}  takipci {b.get('followers_count'):,}  gonderi {b.get('media_count')}")
        for m in sorted(b.get("media", {}).get("data", []), key=lambda m: m.get("view_count") or m.get("like_count") or 0, reverse=True):
            print(f"  {m['timestamp'][:10]}  izl {m.get('view_count', '-'):>8}  beg {m.get('like_count', '-'):>6}  "
                  f"{(m.get('caption') or '').splitlines()[0][:60] if m.get('caption') else ''}  {m['permalink']}")
    kaydet(f"rakip-{datetime.date.today()}.json", sonuc)


def hashtag(a):
    tok, uid = ayar()
    hid = istek("ig_hashtag_search", {"user_id": uid, "q": a.etiket.lstrip("#"), "access_token": tok})["data"][0]["id"]
    alan = "caption,media_type,like_count,comments_count,permalink,timestamp"
    r = istek(f"{hid}/{'recent_media' if a.yeni else 'top_media'}", {"user_id": uid, "fields": alan, "limit": 50, "access_token": tok})
    veri = r.get("data", [])
    kaydet(f"hashtag-{a.etiket.lstrip('#')}-{datetime.date.today()}.json", veri)
    for m in veri:
        print(f"{m.get('timestamp', '')[:10]}  beg {m.get('like_count', '-'):>6}  yor {m.get('comments_count', '-'):>4}  {m['permalink']}")


# ---------- yonetim ----------

def sil(a):
    tok, _ = ayar()
    m = istek(a.id, {"fields": "permalink,caption,timestamp", "access_token": tok})
    print(f"{m['timestamp'][:10]}  {m['permalink']}\n{(m.get('caption') or '')[:200]}")
    if not a.evet:
        print("\nKuru calisma: silinmedi. Silmek icin --evet ekle (geri alinamaz).")
        return
    print("Silindi." if istek(a.id, {"access_token": tok}, "DELETE").get("success") else "Silinemedi.")


def yorum(a):
    tok, _ = ayar()
    r = istek(a.id, {"comment_enabled": "true" if a.durum == "ac" else "false", "access_token": tok}, "POST")
    print("Tamam." if r.get("success") else r)


# ---------- otodm: "yorumlara X yaz" -> private reply DM ----------
# Rules in yerel/instagram/otodm.json (on GitHub Actions written from the OTODM_JSON secret, otodm.yml): {"acik": true, "kurallar": {"claude": {"mesaj": "...", "yanit": ["..."]}}}
# A post joins automatically when its caption has "Yorumlara <KELIME> yaz" and a rule exists for KELIME,
# or when its media id is listed in the rule's "medya".
# Needs instagram_manage_comments + instagram_manage_messages (+ "Allow access to messages" in the IG app).
# Private replies: one per comment, only within 7 days of the comment, so polling catches up after downtime.
OTODM = KLASOR / "otodm.json"
OTODM_DURUM = KLASOR / "otodm_durum.json"
OTODM_LOG = KLASOR / "otodm.log"
CTA_DESEN = re.compile(r"yorum(?:lar)?a\s+([^\s,.!:;✅]+)\s+yaz", re.I)


def _kucuk(s):
    return (s or "").replace("İ", "i").replace("I", "ı").casefold()


def _sik(w):
    return re.sub(r"(.)\1+", r"\1", w)  # collapse repeated letters


def _json(p, varsayilan):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return varsayilan


def _tum(yol, params, sayfa=10):
    r = istek(yol, params)
    out = r.get("data", [])
    while sayfa > 1 and r.get("paging", {}).get("next"):
        r, sayfa = istek("", url=r["paging"]["next"]), sayfa - 1
        out += r.get("data", [])
    return out


def otodm_tur(kuru=False, log=print):
    tok, uid = ayar()
    kurallar = {_kucuk(k): v for k, v in _json(OTODM, {}).get("kurallar", {}).items()}
    if not kurallar:
        return 0
    ben = _kucuk(env().get("IG_KULLANICI"))
    durum = _json(OTODM_DURUM, {"islenen": {}})
    # "baslangic" (unix ts) in otodm.json: comments older than this are never touched
    sinir, n = max(time.time() - 7 * 86400 + 600, _json(OTODM, {}).get("baslangic", 0)), 0
    # rule key is a name; the comment keyword is "kelime" (default: the key), so two posts can share
    # one keyword with different messages. "medya": ["<media id>"] binds a post to a rule explicitly.
    bagli = {mid: k for k, v in kurallar.items() for mid in v.get("medya", [])}
    for m in istek(f"{uid}/media", {"fields": "id,caption", "limit": 15, "access_token": tok}).get("data", []):
        ad = bagli.get(m["id"])
        if not ad:
            # caption CTA only picks a rule that is not bound to specific posts, and only if unambiguous
            k = CTA_DESEN.search(m.get("caption") or "")
            adaylar = [a for a, v in kurallar.items() if k and not v.get("medya")
                       and _kucuk(v.get("kelime", a)) == _kucuk(k.group(1))]
            if len(adaylar) > 1:
                log(f"{m['id']}: '{k.group(1)}' birden cok kurala uyuyor, kurala medya ekle")
            ad = adaylar[0] if len(adaylar) == 1 else None
        kural = kurallar.get(ad)
        if not kural:
            continue
        kelime = _kucuk(kural.get("kelime", ad))
        for y in _tum(f"{m['id']}/comments", {"fields": "id,text,timestamp,username,replies{username}", "limit": 50, "access_token": tok}):
            if y["id"] in durum["islenen"] or _kucuk(y.get("username")) == ben:
                continue
            # stateless guard: we already answered this comment (state cache lost, or another runner)
            if any(_kucuk(r.get("username")) == ben for r in y.get("replies", {}).get("data", [])):
                continue
            if datetime.datetime.strptime(y["timestamp"], "%Y-%m-%dT%H:%M:%S%z").timestamp() < sinir:
                continue
            # tolerant match: "Klippp" -> "klip"; rule "esler": ["clip"] adds aliases
            hedef = {_sik(x) for x in [kelime] + [_kucuk(e) for e in kural.get("esler", [])]}
            if not hedef & {_sik(w) for w in re.findall(r"\w+", _kucuk(y.get("text")))}:
                continue
            log(f"@{y.get('username')} -> {kelime}: {(y.get('text') or '')[:60]}" + (" (kuru)" if kuru else ""))
            if kuru:
                continue
            try:
                istek("me/messages", {"recipient": json.dumps({"comment_id": y["id"]}),
                                      "message": json.dumps({"text": kural["mesaj"]}, ensure_ascii=False),
                                      "access_token": tok}, "POST")
                sonuc = int(time.time())
            except HataIG as ex:
                if re.search(r"\((3|10|190|200)/", str(ex)):
                    raise  # missing permission / token: stop, do not burn comments
                log(f"  DM gitmedi: {ex}")
                sonuc = -1
            yan = kural.get("yanit") or []
            if sonuc > 0 and yan:
                try:
                    istek(f"{y['id']}/replies", {"message": yan[n % len(yan)], "access_token": tok}, "POST")
                except HataIG as ex:
                    log(f"  yorum yaniti gitmedi: {ex}")
            durum["islenen"][y["id"]] = sonuc
            OTODM_DURUM.write_text(json.dumps(durum, ensure_ascii=False, indent=1), encoding="utf-8")
            n += 1
            time.sleep(2)
    return n


def otodm_dongu(aralik=60, log=None):
    # runs on GitHub Actions now; the local editor poller only with OTODM_YEREL=1 (avoid double DMs)
    if env().get("OTODM_YEREL") != "1":
        return
    # one poller per machine: several editor servers may start this, the port bind picks one
    kilit = socket.socket()
    try:
        kilit.bind(("127.0.0.1", 8798))
    except OSError:
        return
    KLASOR.mkdir(parents=True, exist_ok=True)

    def yaz(s):
        with OTODM_LOG.open("a", encoding="utf-8") as f:
            f.write(f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S}  {s}\n")
    log = log or yaz
    while True:
        bekle = aralik
        if _json(OTODM, {}).get("acik"):
            try:
                otodm_tur(log=log)
            except HataIG as ex:
                log(f"durdu: {ex}")
                bekle = 900
            except Exception as ex:  # network etc.; keep the loop alive
                log(f"hata: {ex!r}")
                bekle = 300
        time.sleep(bekle)


def otodm(a):
    KLASOR.mkdir(parents=True, exist_ok=True)
    if a.dongu:
        print(f"Her {a.dongu} sn yorumlar taranıyor (Ctrl+C ile dur). Kayıt: {OTODM_LOG}")
        return otodm_dongu(a.dongu, log=print)
    if not (a.kuru or _json(OTODM, {}).get("acik")):
        return print("otodm kapalı (otodm.json: acik false).")
    print(f"{otodm_tur(kuru=a.kuru)} yorum işlendi.")


def main():
    ap = argparse.ArgumentParser(description="Instagram Graph API (yerel)")
    alt = ap.add_subparsers(dest="komut", required=True)
    k = alt.add_parser("kur", help="kisa token -> suresiz sayfa token'i, .env'e yazar")
    k.add_argument("token")
    k.add_argument("--sayfa", help="birden fazla sayfa varsa ad parcasi")
    alt.add_parser("durum")
    y = alt.add_parser("yayinla", help="yerel mp4'u Reel olarak yayinlar (--evet olmadan kuru calisma)")
    y.add_argument("video")
    y.add_argument("--aciklama")
    y.add_argument("--aciklama-dosya")
    y.add_argument("--kapak-ms", type=int, help="kapak karesi, milisaniye")
    y.add_argument("--ortak", nargs="*", help="en fazla 3 ortak kullanici adi")
    y.add_argument("--akisa-koyma", action="store_true", help="sadece Reels sekmesinde gorunsun")
    y.add_argument("--deneme", action="store_true", help="deneme reel'i (takipci olmayanlara once gosterilir)")
    y.add_argument("--ses-adi", help="orijinal sesin adi (bir kez verilebilir)")
    y.add_argument("--evet", action="store_true")
    g = alt.add_parser("gonderiler")
    g.add_argument("--n", type=int, default=25)
    for ad in ("analiz", "rapor"):
        p = alt.add_parser(ad)
        p.add_argument("--n", type=int, default=50, help="son kac gonderi")
        p.add_argument("--gun", type=int, default=30, help="hesap ozeti icin gun (en fazla 30)")
        if ad == "rapor":
            p.add_argument("--yenile", action="store_true", help="once yeni analiz cek")
    r = alt.add_parser("rakip", help="herkese acik Isletme/Icerik Ureticisi hesaplari")
    r.add_argument("kullanici", nargs="+")
    r.add_argument("--n", type=int, default=12)
    h = alt.add_parser("hashtag", help="App Review (Instagram Public Content Access) gerekir")
    h.add_argument("etiket")
    h.add_argument("--yeni", action="store_true", help="en iyi yerine son 24 saat")
    s = alt.add_parser("sil")
    s.add_argument("id")
    s.add_argument("--evet", action="store_true")
    yo = alt.add_parser("yorum", help="yorumlari ac/kapat")
    yo.add_argument("id")
    yo.add_argument("durum", choices=["ac", "kapat"])
    od = alt.add_parser("otodm", help="'Yorumlara X yaz' yorumlarina DM gonderir (yerel/instagram/otodm.json)")
    od.add_argument("--kuru", action="store_true", help="gondermeden kimlere gidecegini listele")
    od.add_argument("--dongu", type=int, metavar="SN", help="surekli calis, SN saniyede bir tara")
    a = ap.parse_args()
    try:
        globals()[a.komut](a)
    except HataIG as ex:
        sys.exit(f"Instagram API hatasi: {ex}")


if __name__ == "__main__":
    main()

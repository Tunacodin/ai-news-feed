# Ne yapar: Telegram tarafini yonetir (GitHub Actions'ta bot.yml ile calisir):
#  1) getUpdates ile "Listeye al" / "Cektim" butonlarini ve yazili komutlari (1 3 5, /liste) isler
#  2) icerik/oneriler/*.json icinden henuz gonderilmemis gunluk onerileri butonlu mesajla yollar
#  3) icerik/liste.json'da durumu "hazir" olup bildirilmemis video metinlerini yollar
# Her adim tekrar calistirmaya dayanikli; durum icerik/bot_state.json'da tutulur.
import json, re, time, pathlib, html
from fetch_news import tg_call, TG_CHAT

ROOT = pathlib.Path("icerik")
STATE, LISTE = ROOT / "bot_state.json", ROOT / "liste.json"
REPO_URL = "https://github.com/Tunacodin/ai-news-feed/blob/main/"
AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]


def load(p, default):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def save(p, data):
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def esc(s):
    return html.escape(s or "", quote=False)


def tarih_tr(t):
    y, m, d = t.split("-")
    return f"{int(d)} {AYLAR[int(m) - 1]}"


def send(text, buttons=None):
    p = {"chat_id": TG_CHAT, "parse_mode": "HTML", "text": text[:4096], "disable_web_page_preview": "true"}
    if buttons:
        p["reply_markup"] = json.dumps({"inline_keyboard": buttons})
    r = tg_call("sendMessage", p)
    if not r.get("ok"):
        print("sendMessage hata:", r.get("description"))
    time.sleep(0.4)  # Telegram hiz siniri
    return r


def ozet(liste):
    say = lambda d: sum(1 for x in liste if x["durum"] == d)
    return f"Liste: {say('secildi')} seçildi · {say('hazir')} hazır · {say('cekildi')} çekildi"


def pitch(o):
    etiket = " · ".join(esc(o[k]) for k in ("tur", "zorluk", "maliyet") if o.get(k))
    ekran = f"<b>Ekranda:</b> {esc(o['demo_ani'])}\n" if o.get("demo_ani") else ""
    return (f"<b>{o['no']}. {esc(o['baslik'])}</b>\n<i>“{esc(o.get('hook'))}”</i>\n\n{esc(o.get('ozet'))}\n\n"
            f"{ekran}<b>Neden tutar:</b> {esc(o.get('neden'))}\n<b>Fikrim:</b> {esc(o.get('fikir'))}\n"
            f"{etiket + ' · ' if etiket else ''}Potansiyel {o.get('puan', '?')}/10 · {esc(o.get('dogrulama'))}")


def pick(tarih, no, liste):
    # Oneriyi listeye kopyalar (VS Code adimi tek dosyadan calissin diye). (oneri, yeni_mi) doner.
    iid = f"{tarih}-{no}"
    var = next((x for x in liste if x["id"] == iid), None)
    if var:
        return var, False
    o = next((x for x in load(ROOT / "oneriler" / f"{tarih}.json", {}).get("oneriler", []) if x["no"] == no), None)
    if not o:
        return None, False
    liste.append({**o, "id": iid, "durum": "secildi", "secildi": now(), "dosya": None, "bildirildi": False})
    return o, True


def set_button(msg, data, label):
    # Basilan butonu etikete cevirir (ornek: "Listede ✓"); diger butonlar (Kaynak) kalir.
    rows = [[({"text": label, "callback_data": "noop"} if b.get("callback_data") == data else b) for b in row]
            for row in (msg.get("reply_markup") or {}).get("inline_keyboard", [])]
    tg_call("editMessageReplyMarkup", {"chat_id": msg["chat"]["id"], "message_id": msg["message_id"],
                                       "reply_markup": json.dumps({"inline_keyboard": rows})})


def on_callback(cq, liste):
    msg, data = cq.get("message") or {}, cq.get("data", "")
    if str(msg.get("chat", {}).get("id")) != str(TG_CHAT):
        return
    kind, _, rest = data.partition(":")
    note = None
    if kind == "al":
        tarih, no = rest.rsplit(":", 1)
        o, yeni = pick(tarih, int(no), liste)
        if o:
            note = "Listeye alındı" if yeni else "Zaten listede"
            set_button(msg, data, "Listede ✓")
    elif kind == "cek":
        x = next((x for x in liste if x["id"] == rest), None)
        if x:
            x["durum"], x["cekildi"] = "cekildi", now()
            note = "Çekildi olarak işaretlendi"
            set_button(msg, data, "Çekildi ✓")
    # Gecikmeli islendiginde Telegram "query too old" der; zararsiz, yok sayilir.
    tg_call("answerCallbackQuery", {"callback_query_id": cq["id"], "text": note or ""})


def liste_mesaji(liste):
    blok = lambda d, n=None: "\n".join(f"• {esc(x['baslik'])}" for x in [x for x in liste if x["durum"] == d][-(n or 99):]) or "• yok"
    return (f"<b>Video listesi</b>\n\n<b>Seçildi (metin bekliyor)</b>\n{blok('secildi')}\n\n"
            f"<b>Hazır (çekilecek)</b>\n{blok('hazir')}\n\n<b>Son çekilenler</b>\n{blok('cekildi', 5)}")


def on_message(m, state, liste):
    if str(m.get("chat", {}).get("id")) != str(TG_CHAT):
        return
    text = (m.get("text") or "").strip()
    if text.startswith("/liste"):
        send(liste_mesaji(liste))
    elif re.fullmatch(r"[\d\s,]+", text) and state.get("son_oneri"):
        alinan, zaten, yok = [], [], []
        for no in dict.fromkeys(int(n) for n in re.findall(r"\d+", text)):
            o, yeni = pick(state["son_oneri"], no, liste)
            (yok if not o else alinan if yeni else zaten).append(str(no))
        parca = [(f"Listeye alındı: {', '.join(alinan)}", alinan), (f"Zaten listede: {', '.join(zaten)}", zaten),
                 (f"Bugünün önerilerinde yok: {', '.join(yok)}", yok)]
        send(". ".join(t for t, v in parca if v))
    else:
        send("Numaraları yaz (örn: 1 3 5) ya da önerideki <b>Listeye al</b>'a bas. Liste için: /liste")


def poll(state, liste):
    r = tg_call("getUpdates", {"offset": state["offset"], "timeout": 0,
                               "allowed_updates": json.dumps(["message", "callback_query"])})
    if not r.get("ok"):
        print("getUpdates:", r.get("description"))
        return
    for u in r["result"]:
        state["offset"] = u["update_id"] + 1
        if "callback_query" in u:
            on_callback(u["callback_query"], liste)
        elif "message" in u:
            on_message(u["message"], state, liste)


def send_digests(state, liste):
    for f in sorted((ROOT / "oneriler").glob("*.json")):
        tarih = f.stem
        if tarih in state["gonderilen"]:
            continue
        d = load(f, {})
        onr = d.get("oneriler", [])
        head = (f"<b>Günün önerileri · {tarih_tr(tarih)}</b>\n{len(onr)} konu. Beğendiğinde <b>Listeye al</b>'a bas "
                f"ya da numaraları yaz (örn: 1 3 5).\n{ozet(liste)}")
        if d.get("not"):
            head += f"\n\n<i>{esc(d['not'])}</i>"
        if not send(head).get("ok"):
            return  # token yok ya da Telegram hatasi: gonderilmedi say, sonraki calismada tekrar dene
        for o in onr:
            btn = [{"text": "Listeye al", "callback_data": f"al:{tarih}:{o['no']}"}]
            if o.get("dene_url"):
                btn.append({"text": "Dene →", "url": o["dene_url"]})
            elif o.get("kaynaklar"):
                btn.append({"text": "Kaynak →", "url": o["kaynaklar"][0]})
            send(pitch(o), [btn])
        state["gonderilen"].append(tarih)
        state["son_oneri"] = max(tarih, state.get("son_oneri") or "")


def bolum(dosya, ad):
    # Video dosyasinin "## <ad>" bolumu; **kalin** isaretleri Telegram HTML'ine cevrilir.
    s = pathlib.Path(dosya).read_text(encoding="utf-8")
    m = re.search(rf"^## {ad}\s*\n(.*?)(?=^## |\Z)", s, re.S | re.M)
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", esc(m.group(1).strip() if m else ""))


def notify_ready(liste):
    # Iki mesaj (Telegram 4096 karakter siniri): once cekim plani, sonra butonlu okunacak metin.
    for x in liste:
        if x["durum"] != "hazir" or x.get("bildirildi") or not x.get("dosya") or not pathlib.Path(x["dosya"]).exists():
            continue
        plan = bolum(x["dosya"], "Çekim planı")
        if plan:
            send(f"<b>Çekim planı:</b> {esc(x['baslik'])}\n\n{plan}")
        r = send(f"<b>Okunacak metin:</b> {esc(x['baslik'])}\n\n{bolum(x['dosya'], 'Okunacak metin')}",
                 [[{"text": "Dosyayı aç →", "url": REPO_URL + x["dosya"]},
                   {"text": "Çektim", "callback_data": f"cek:{x['id']}"}]])
        if r.get("ok"):
            x["bildirildi"] = True


def main():
    (ROOT / "oneriler").mkdir(parents=True, exist_ok=True)
    state = load(STATE, {"offset": 0, "gonderilen": [], "son_oneri": None})
    liste = load(LISTE, [])
    poll(state, liste)
    send_digests(state, liste)
    notify_ready(liste)
    save(STATE, state)
    save(LISTE, liste)


if __name__ == "__main__":
    main()

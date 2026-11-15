#!/usr/bin/env python3
"""UNIT-01 LINE bot: stock-update broadcast (Flex 1) + product card (Flex 2).

Every round sends ONE request containing 2 messages, so the product card
always lands directly under the stock card.

Usage
  python3 send.py --due                 # send the slot due now (run from cron at 09:00 / 13:00 / 19:00)
  python3 send.py --slot 1116-0900      # send one specific slot now
  python3 send.py --test 1116-0900      # push that slot only to LINE_TEST_USER_ID (no broadcast)
  python3 send.py --validate            # ask LINE to validate every slot's messages (sends nothing)
  python3 send.py --preview             # write rendered JSON for every slot into ./preview/
  python3 send.py --list                # show the schedule and what has been sent

Environment
  LINE_CHANNEL_ACCESS_TOKEN   required for --due/--slot/--test/--validate
  LINE_TEST_USER_ID           required for --test (your own LINE userId)
"""
import argparse, datetime as dt, json, os, sys, uuid, urllib.request, urllib.error
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
CFG_PATH = os.path.join(HERE, "config", "campaign.json")
API = "https://api.line.me/v2/bot/message"
DUE_WINDOW_MIN = 180  # wide window: GitHub Actions cron can lag; slots are 4h apart so no overlap


def load():
    with open(CFG_PATH, encoding="utf-8") as f:
        return json.load(f)


def save(cfg):
    tmp = CFG_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    os.replace(tmp, CFG_PATH)


def ampm(t):
    h, m = map(int, t.split(":"))
    return f"{(h % 12) or 12:02d}:{m:02d} {'AM' if h < 12 else 'PM'}"


# ---------- Flex 1: stock card (Stock C · HUD compact) ----------
def stock_flex(cfg, slot):
    total, sold = int(cfg["total"]), int(slot["sold"])
    if not 0 <= sold <= total:
        raise ValueError(f"slot {slot['id']}: sold={sold} must be 0..{total}")
    remain, pct = total - sold, max(1, round(sold / total * 100)) if sold else 0
    bar_fill = [{"type": "box", "layout": "vertical", "contents": [], "width": f"{pct}%",
                 "height": "8px", "backgroundColor": "#111111"}] if pct else []
    body = [
        {"type": "text", "text": "STOCK UPDATE", "size": "xxs", "color": "#555555"},
        {"type": "box", "layout": "horizontal", "alignItems": "flex-end", "contents": [
            {"type": "text", "flex": 0, "contents": [
                {"type": "span", "text": str(sold), "size": "3xl", "weight": "bold", "color": "#111111"},
                {"type": "span", "text": f" / {total}", "size": "md", "color": "#777777"}]},
            {"type": "text", "align": "end", "gravity": "bottom", "contents": [
                {"type": "span", "text": "REMAIN ", "size": "xxs", "color": "#555555"},
                {"type": "span", "text": str(remain), "size": "lg", "weight": "bold", "color": "#111111"}]},
        ]},
        {"type": "box", "layout": "horizontal", "alignItems": "center", "spacing": "xs", "contents": [
            {"type": "text", "text": "[", "flex": 0, "size": "xs", "color": "#111111"},
            {"type": "box", "layout": "vertical", "height": "8px", "backgroundColor": "#DCDCD8",
             "contents": bar_fill},
            {"type": "text", "text": "]", "flex": 0, "size": "xs", "color": "#111111"},
        ]},
    ]
    if cfg.get("access_code"):
        body += [
            {"type": "separator", "margin": "md", "color": "#BDBDB8"},
            {"type": "box", "layout": "horizontal", "margin": "md", "contents": [
                {"type": "text", "text": "<<< ACCESS CODE", "size": "xxs", "color": "#555555", "gravity": "center"},
                {"type": "text", "text": f"[ {cfg['access_code']} ]", "align": "end", "size": "sm",
                 "weight": "bold", "color": "#111111"}]},
        ]
    bubble = {
        "type": "bubble", "size": "kilo",
        "header": {"type": "box", "layout": "horizontal", "backgroundColor": "#111111",
                   "paddingAll": "10px", "paddingStart": "14px", "paddingEnd": "14px", "contents": [
                       {"type": "text", "text": "INVITE ONLY", "size": "xxs", "weight": "bold", "color": "#FFFFFF"},
                       {"type": "text", "text": ampm(slot["time"]), "size": "xxs", "weight": "bold",
                        "color": "#FFFFFF", "align": "end"}]},
        "body": {"type": "box", "layout": "vertical", "spacing": "sm", "paddingAll": "14px", "contents": body},
    }
    return {"type": "flex", "altText": f"Stock update {ampm(slot['time'])} · {sold}/{total} · Remain {remain}",
            "contents": bubble}


# ---------- Flex 2: product card A / B / C ----------
def product_flex(cfg, slot):
    v = slot.get("product_card", "A")
    url = cfg["get_access_url"]
    img = f"{cfg['image_base_url'].rstrip('/')}/{cfg['images'][v]}"
    dark = v == "B"
    fg, sub, bg = ("#FFFFFF", "#D9D9D9", "#0B0B0B") if dark else ("#111111", "#666666", "#FFFFFF")
    title_row = {"type": "box", "layout": "horizontal", "contents": [
        {"type": "text", "text": cfg["product_name"], "weight": "bold", "size": "lg", "color": fg, "flex": 3},
        {"type": "text", "text": f"฿{cfg['price']}", "weight": "bold", "size": "md", "color": fg,
         "align": "end", "gravity": "bottom", "flex": 2}]}
    if v == "A":
        chips = [{"type": "box", "layout": "vertical", "flex": 0, "cornerRadius": "999px", "borderWidth": "1px",
                  "borderColor": "#CFCFCB", "paddingTop": "2px", "paddingBottom": "2px", "paddingStart": "8px",
                  "paddingEnd": "8px", "contents": [{"type": "text", "text": f, "size": "xxs", "color": fg}]}
                 for f in cfg["features"]]
        body = [title_row,
                {"type": "box", "layout": "vertical", "spacing": "xs", "contents": [
                    {"type": "box", "layout": "horizontal", "spacing": "xs", "contents": chips[i:i + 2] +
                     [{"type": "filler"}]} for i in range(0, len(chips), 2)]}]
    elif v == "B":
        body = [{"type": "text", "text": "INVITATION ONLY", "size": "xxs", "color": "#BDBDBD"},
                title_row,
                {"type": "text", "text": " · ".join(cfg["features"]), "size": "xxs", "color": sub, "wrap": True}]
    else:
        labels = ["Cut", "Edge", "Finish", "Fabric"]
        rows = []
        for lab, f in zip(labels, cfg["features"]):
            rows += [{"type": "separator", "color": "#E2E2DE"},
                     {"type": "box", "layout": "horizontal", "paddingTop": "6px", "paddingBottom": "6px", "contents": [
                         {"type": "text", "text": lab, "size": "xs", "color": sub},
                         {"type": "text", "text": f, "size": "xs", "color": fg, "align": "end"}]}]
        rows.append({"type": "separator", "color": "#E2E2DE"})
        body = [title_row, {"type": "box", "layout": "vertical", "contents": rows}]
    bubble = {
        "type": "bubble", "size": "kilo",
        "styles": {"body": {"backgroundColor": bg}, "footer": {"backgroundColor": bg}},
        "hero": {"type": "image", "url": img, "size": "full", "aspectRatio": "4:3", "aspectMode": "cover",
                 "action": {"type": "uri", "label": "GET ACCESS", "uri": url}},
        "body": {"type": "box", "layout": "vertical", "spacing": "md", "paddingAll": "14px", "contents": body},
        "footer": {"type": "box", "layout": "vertical", "paddingAll": "14px", "paddingTop": "0px", "contents": [
            {"type": "button", "height": "md",
             "style": "secondary" if dark else "primary",
             "color": "#FFFFFF" if dark else "#111111",
             "action": {"type": "uri", "label": "GET ACCESS", "uri": url}}]},
    }
    return {"type": "flex", "altText": f"{cfg['product_name']} · ฿{cfg['price']} · GET ACCESS", "contents": bubble}


def messages(cfg, slot):
    return [stock_flex(cfg, slot), product_flex(cfg, slot)]


# ---------- LINE API ----------
def call(path, payload, retry_key=None):
    token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
    if not token:
        sys.exit("Set LINE_CHANNEL_ACCESS_TOKEN first.")
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    if retry_key:
        headers["X-Line-Retry-Key"] = retry_key
    req = urllib.request.Request(f"{API}/{path}", data=json.dumps(payload).encode(), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read().decode() or "{}"
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def find(cfg, slot_id):
    for s in cfg["slots"]:
        if s["id"] == slot_id:
            return s
    sys.exit(f"No slot {slot_id}. Run --list.")


def send_slot(cfg, slot):
    if slot.get("sent"):
        print(f"{slot['id']} already sent at {slot.get('sent_at')}, skipping."); return
    # Stable retry key per slot: if the request is retried, LINE will not deliver it twice.
    key = str(uuid.uuid5(uuid.NAMESPACE_URL, f"unit01/{slot['id']}"))
    payload = {"messages": messages(cfg, slot)}
    if cfg.get("send_mode") == "broadcast":
        code, body = call("broadcast", payload, key)
    else:
        sys.exit("Only send_mode=broadcast is supported.")
    print(slot["id"], code, body)
    if code == 200 or (code == 409 and "already" in body.lower()):
        slot["sent"] = True
        slot["sent_at"] = dt.datetime.now(ZoneInfo(cfg["timezone"])).isoformat(timespec="seconds")
        save(cfg)
    else:
        sys.exit(1)


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--due", action="store_true")
    g.add_argument("--slot")
    g.add_argument("--test")
    g.add_argument("--validate", action="store_true")
    g.add_argument("--preview", action="store_true")
    g.add_argument("--list", action="store_true")
    a = ap.parse_args()
    cfg = load()
    tz = ZoneInfo(cfg["timezone"])

    if a.list:
        for s in cfg["slots"]:
            print(f"{s['id']}  {s['date']} {s['time']}  {s['sold']:>3}/{cfg['total']}  card {s['product_card']}  "
                  f"{'SENT ' + s.get('sent_at', '') if s.get('sent') else 'pending'}")
    elif a.preview:
        out = os.path.join(HERE, "preview"); os.makedirs(out, exist_ok=True)
        for s in cfg["slots"]:
            m = messages(cfg, s)
            for i, msg in enumerate(m, 1):
                with open(os.path.join(out, f"{s['id']}_msg{i}.json"), "w", encoding="utf-8") as f:
                    json.dump(msg["contents"], f, ensure_ascii=False, indent=2)
        print(f"Wrote {len(cfg['slots']) * 2} files to {out} (paste any into LINE Flex Message Simulator).")
    elif a.validate:
        bad = 0
        for s in cfg["slots"]:
            code, body = call("validate/broadcast", {"messages": messages(cfg, s)})
            print(s["id"], "OK" if code == 200 else f"ERROR {code} {body}")
            bad += code != 200
        sys.exit(1 if bad else 0)
    elif a.test:
        uid = os.environ.get("LINE_TEST_USER_ID") or sys.exit("Set LINE_TEST_USER_ID first.")
        code, body = call("push", {"to": uid, "messages": messages(cfg, find(cfg, a.test))})
        print("test push", code, body)
    elif a.slot:
        send_slot(cfg, find(cfg, a.slot))
    elif a.due:
        now = dt.datetime.now(tz)
        for s in cfg["slots"]:
            at = dt.datetime.fromisoformat(f"{s['date']}T{s['time']}").replace(tzinfo=tz)
            if at <= now < at + dt.timedelta(minutes=DUE_WINDOW_MIN) and not s.get("sent"):
                send_slot(cfg, s); return
        print(f"{now:%Y-%m-%d %H:%M} nothing due.")


if __name__ == "__main__":
    main()

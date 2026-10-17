#!/usr/bin/env python3
"""Polite, resumable collector for NDERF experiences (private working copy only).

Run on YOUR computer (the cloud sandbox cannot reach the site):
    py scripts\\ingest_nderf.py --contact "https://www.myparallax.org" --archive-pages 2 --limit 200
Spread over all years (about 10 random accounts per archive page, reproducible):
    py scripts\\ingest_nderf.py --contact "https://www.myparallax.org" --archive-pages 0 --per-page 10 --limit 0

What it does
  1. Reads the archive list, picks the newest N archive pages, collects links to experience pages.
  2. Downloads each experience page, one request per --delay seconds (default 2.0).
  3. Saves the page text to narrative_corpus_private/nderf/raw/<id>.txt   (NEVER commit or publish; ignored by git)
  4. Writes narrative_corpus_private/nderf/index.jsonl with id, type, retrieved_at, text hash, flags.
  5. Writes numbered batches narrative_corpus_private/nderf/batches/batch_001.txt ... for coding.
     Records that mention suicide are flagged and kept OUT of the batches until reviewed by a human.

Rules (narrative_corpus/SOURCES.md):
  * identified user agent, slow rate, stops on HTTP 403/429/503 (never works around a refusal)
  * no names stored in index.jsonl (the first name that appears in the URL is not copied)
  * nothing here is published; only derived codes and statistics are
Standard library only. Resumable: already downloaded ids are skipped.
"""
import argparse, hashlib, html, json, os, random, re, sys, time, datetime
import urllib.request, urllib.error, urllib.parse
from html.parser import HTMLParser

EXP_RE = re.compile(r'''href=["']([^"']*(?:/Experiences/[^"']+\.htm|search\.nderf\.org/experience/\d+)[^"']*)["']''', re.I)
ARCH_RE = re.compile(r'''href=["']([^"']*\b2_\d+(?:_\d+)?\.html)["']''', re.I)
ID_RE = re.compile(r'(\d{3,7})(?:\.htm)?/?$')
TYPE_RE = re.compile(r'_([a-z]{2,10})_\d+\.htm$', re.I)
SUICIDE_RE = re.compile(r'suicid|killed myself|kill myself|end my life|took my own life', re.I)


class TextOut(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts = []; self.skip = 0
    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"): self.skip += 1
        if tag in ("p", "br", "div", "tr", "li", "h1", "h2", "h3", "h4"): self.parts.append("\n")
    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript") and self.skip: self.skip -= 1
    def handle_data(self, d):
        if not self.skip: self.parts.append(d)


def to_text(raw_html):
    p = TextOut(); p.feed(raw_html)
    t = html.unescape("".join(p.parts))
    lines = [re.sub(r"[ \t ]+", " ", l).strip() for l in t.splitlines()]
    out, blank = [], 0
    for l in lines:
        if not l:
            blank += 1
            if blank > 1: continue
        else:
            blank = 0
        out.append(l)
    return "\n".join(out).strip()


class Stop(Exception):
    pass


def clean_url(url):
    """Percent-encode non-ASCII characters (some experience URLs contain accented letters)."""
    p = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit((p.scheme, p.netloc.encode("idna").decode("ascii"),
                                    urllib.parse.quote(p.path, safe="/%:@!$&'()*+,;=~-._"),
                                    urllib.parse.quote(p.query, safe="=&%+"), ""))


def fetch(url, ua, timeout=30):
    url = clean_url(url)
    req = urllib.request.Request(url, headers={"User-Agent": ua, "Accept": "text/html"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = r.read()
            enc = r.headers.get_content_charset()
    except urllib.error.HTTPError as e:
        if e.code in (401, 403, 429, 503):
            raise Stop("HTTP %d from %s: the site is refusing or limiting access. Stopping; do not retry around it." % (e.code, url))
        if e.code == 404:
            return None
        raise
    return decode_bytes(data, enc)


def decode_bytes(data, header_enc):
    """Header charset, else <meta charset>, else UTF-8, else Windows-1252."""
    enc = header_enc
    if not enc:
        m = re.search(rb"charset=[\"']?([A-Za-z0-9_-]+)", data[:4096], re.I)
        enc = m.group(1).decode("ascii") if m else None
    for e in ([enc] if enc else []) + ["utf-8", "cp1252"]:
        try:
            return data.decode(e)
        except (UnicodeDecodeError, LookupError):
            continue
    return data.decode("utf-8", errors="replace")


def absolute(base, href):
    return urllib.request.urljoin(base, href)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="https://www.nderf.org")
    ap.add_argument("--out", default=os.path.join("narrative_corpus_private", "nderf"))
    ap.add_argument("--contact", required=True, help="URL or address that identifies you in the user agent")
    ap.add_argument("--archive-pages", type=int, default=2, help="how many archive pages to read (newest first); 0 = all pages")
    ap.add_argument("--per-page", type=int, default=0, help="take at most this many random accounts per archive page (0 = all); spreads the sample across years")
    ap.add_argument("--seed", type=int, default=2026, help="random seed for --per-page (keeps the sample reproducible)")
    ap.add_argument("--batches", action="store_true", help="also write text batches for manual reading (not needed for parse_nderf.py)")
    ap.add_argument("--limit", type=int, default=200)
    ap.add_argument("--delay", type=float, default=2.0, help="seconds between requests (min 1.0)")
    ap.add_argument("--batch-size", type=int, default=10)
    ap.add_argument("--dry-run", action="store_true", help="list what would be fetched; download nothing but the lists")
    a = ap.parse_args()
    delay = max(a.delay, 1.0)
    ua = "ParallaxResearchBot/0.1 (non-commercial research on aggregate statistics; +%s)" % a.contact
    base = a.base.rstrip("/")
    raw_dir = os.path.join(a.out, "raw"); batch_dir = os.path.join(a.out, "batches")
    os.makedirs(raw_dir, exist_ok=True); os.makedirs(batch_dir, exist_ok=True)
    index_path = os.path.join(a.out, "index.jsonl")

    try:
        listing = fetch(base + "/Archives/archivelist.htm", ua)
        if not listing: sys.exit("archive list not found")
        pages = []
        for h in ARCH_RE.findall(listing):
            u = absolute(base + "/Archives/archivelist.htm", h)
            if u not in pages: pages.append(u)
        take = pages if a.archive_pages == 0 else pages[:a.archive_pages]
        print("archive pages found: %d (reading %d, newest first as listed)" % (len(pages), len(take)))
        if not pages: sys.exit("no archive links found: the page layout may have changed")

        rng = random.Random(a.seed)
        links, period_of = [], {}
        for pg in take:
            time.sleep(delay)
            body = fetch(pg, ua)
            if not body: print("  missing:", pg); continue
            page_links = []
            for h in EXP_RE.findall(body):
                u = absolute(pg, h)
                if u not in page_links and u not in links: page_links.append(u)
            tot = len(page_links)
            if a.per_page and tot > a.per_page:
                page_links = rng.sample(page_links, a.per_page)
            pm = re.search(r"2_(?:\d+_)?(\d{4})\.html", pg)
            for u in page_links:
                links.append(u); period_of[u] = pm.group(1) if pm else None
            print("  %s -> %d links (using %d)" % (pg, tot, len(page_links)))
        print("experience links collected: %d" % len(links))
        if not links: sys.exit("no experience links found on the archive pages: layout differs; nothing was downloaded")
        if a.limit and len(links) > a.limit:
            if a.per_page:
                links = rng.sample(links, a.limit)
            else:
                links = links[:a.limit]
        if a.dry_run:
            for u in links[:10]: print("  would fetch:", u)
            print("dry run: stopping here"); return

        have = set()
        if os.path.exists(index_path):
            with open(index_path, encoding="utf-8") as fh:
                for line in fh:
                    try: have.add(json.loads(line)["id"])
                    except Exception: pass

        new = 0
        with open(index_path, "a", encoding="utf-8", newline="\n") as idx:
            for u in links:
                m = ID_RE.search(u.split("?")[0])
                if not m: print("  no id in", u); continue
                rid = "nderf-" + m.group(1)
                if rid in have: continue
                time.sleep(delay)
                try:
                    body = fetch(u, ua)
                except Stop:
                    raise
                except Exception as exc:  # one bad page must not end the run
                    print("  skipped (%s): %s" % (type(exc).__name__, u)); continue
                if not body: print("  404:", u); continue
                text = to_text(body)
                tm = TYPE_RE.search(u)
                with open(os.path.join(raw_dir, rid + ".txt"), "w", encoding="utf-8", newline="\n") as fh:
                    fh.write(text)
                rec = {"id": rid, "type": (tm.group(1).lower() if tm else "unknown"),
                       "retrieved_at": datetime.date.today().isoformat(),
                       "text_hash": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                       "chars": len(text), "flag_suicide": bool(SUICIDE_RE.search(text)),
                       "archive_year": period_of.get(u)}
                idx.write(json.dumps(rec) + "\n"); idx.flush(); have.add(rid); new += 1
                if new % 20 == 0: print("  downloaded %d" % new)
        print("new pages downloaded: %d" % new)
    except Stop as e:
        print("STOPPED:", e); print("Partial results are kept. Contact the site before continuing.")

    # batches (optional; excluding flagged records)
    recs = []
    if os.path.exists(index_path):
        with open(index_path, encoding="utf-8") as fh:
            for line in fh:
                try: recs.append(json.loads(line))
                except Exception: pass
    ok = [r for r in recs if not r["flag_suicide"]]
    flagged = len(recs) - len(ok)
    if not a.batches:
        print("records: %d (held back from batches if --batches is used: %d)" % (len(recs), flagged))
        return
    for f in os.listdir(batch_dir):
        if f.startswith("batch_"): os.remove(os.path.join(batch_dir, f))
    for i in range(0, len(ok), a.batch_size):
        chunk = ok[i:i + a.batch_size]
        with open(os.path.join(batch_dir, "batch_%03d.txt" % (i // a.batch_size + 1)), "w", encoding="utf-8", newline="\n") as fh:
            for r in chunk:
                with open(os.path.join(raw_dir, r["id"] + ".txt"), encoding="utf-8") as src:
                    fh.write("### %s | type=%s\n%s\n\n" % (r["id"], r["type"], src.read()))
    print("records: %d, in batches: %d, held back (suicide keyword): %d" % (len(recs), len(ok), flagged))
    print("batches in:", batch_dir)


if __name__ == "__main__":
    main()

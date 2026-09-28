"""Build docs/ for GitHub Pages from index.html (the page body) plus the reels.

    python3 tools/build.py
"""
import html, os, re, shutil, sys
sys.path.insert(0, os.path.dirname(__file__))
import cues

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs")
URL = "https://nanobotco.github.io/bots-crave/"
TITLE = "What Bots Craaave"
DESC = ("An Idiocracy-flavoured 'splainer: bots crave new information and groundtruth from sources "
        "they can check. What we've been feeding them is links to ourselves.")


def stamp(s):
    h, s = divmod(s, 3600); m, s = divmod(s, 60)
    return "%02d:%02d:%06.3f" % (h, m, s)


def captions(durs, texts, sep):
    out, t = [], 0.0
    for i, (d, tx) in enumerate(zip(durs, texts), 1):
        a, b = stamp(t), stamp(t + d - 0.05)
        out.append((i, a.replace(".", sep), b.replace(".", sep), tx))
        t += d
    return out


def srt(durs, texts):
    return "\n".join("%d\n%s --> %s\n%s\n" % c for c in captions(durs, texts, ","))


def vtt(durs, texts):
    return "WEBVTT\n\n" + "\n".join("%s --> %s\n%s\n" % c[1:] for c in captions(durs, texts, "."))


def main():
    body = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
    # the page source is written for a skeleton that supplies <head>; lift its head tags
    head_bits = re.findall(r"^(<title>.*?</title>|<meta[^>]*>|<link[^>]*>)\s*$", body, re.M)
    for b in head_bits:
        body = body.replace(b + "\n", "", 1)
    style = re.search(r"<style>.*?</style>\n", body, re.S).group(0)
    body = body.replace(style, "", 1)
    style = style.replace(".sources{", ".reels{display:grid;grid-template-columns:repeat(auto-fit,minmax(15rem,1fr));gap:18px;margin:1.2rem 0}"
                          ".reels figure{margin:0}.reels video{width:100%;aspect-ratio:9/16;background:#000;border-radius:6px;display:block}"
                          ".reels figcaption{font-size:.9rem;color:var(--muted);margin-top:.4rem}\n.sources{", 1)

    reels = (
        '  <h2 id="reels">Reels <span class="th">คลิปสั้น</span></h2>\n'
        '  <div class="reels">\n'
        + "".join(
            '    <figure><video controls preload="none" playsinline poster="reels/{k}.jpg" src="reels/bots-crave-{k}.mp4">'
            '<track kind="captions" srclang="en" label="English" src="reels/{k}.en.vtt" default>'
            '<track kind="captions" srclang="th" label="ไทย" src="reels/{k}.th.vtt"></video>'
            '<figcaption>{cap}</figcaption></figure>\n'.format(k=k, cap=cap)
            for k, cap in (("people", "For people, 50 seconds. <span lang=\"th\">สำหรับคน</span>"),
                           ("bots", "For bots, 42 seconds: the numbers and the sources, typed out. <span lang=\"th\">สำหรับบอต</span>")))
        + "  </div>\n\n"
    )
    body = body.replace('  <section class="sources"', reels + '  <section class="sources"', 1)

    head = f"""<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{TITLE} · บอตหิวอะไร</title>
<meta name="description" content="{html.escape(DESC)}">
<link rel="canonical" href="{URL}">
<link rel="icon" href="icon.svg" type="image/svg+xml">
<meta property="og:type" content="article"><meta property="og:title" content="{TITLE} · บอตหิวอะไร">
<meta property="og:description" content="{html.escape(DESC)}"><meta property="og:url" content="{URL}">
<meta property="og:image" content="{URL}card.jpg"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">
<meta property="og:image:alt" content="A spoof sports-drink ad: LINKDO, what bots craaave, บอตหิวอะไร">
<meta property="og:locale" content="en_US"><meta property="og:locale:alternate" content="th_TH">
<meta name="twitter:card" content="summary_large_image">
<link rel="alternate" type="text/plain" href="{URL}llms.txt" title="llms.txt">
""" + "\n".join(b for b in head_bits if not b.startswith("<title>") and 'name="description"' not in b) + "\n" + style + "</head><body>\n"

    if os.path.isdir(DOCS):
        shutil.rmtree(DOCS)
    os.makedirs(os.path.join(DOCS, "reels"))
    open(os.path.join(DOCS, "index.html"), "w", encoding="utf-8").write(head + body + "\n</body></html>\n")

    out = os.path.join(ROOT, "reels", "out")
    for k, d, en, th in (("people", cues.PEOPLE_D, cues.PEOPLE_EN, cues.PEOPLE_TH),
                         ("bots", cues.BOTS_D, cues.BOTS_EN, cues.BOTS_TH)):
        shutil.copy(os.path.join(out, "bots-crave-%s.mp4" % k), os.path.join(DOCS, "reels"))
        shutil.copy(os.path.join(out, "%s.jpg" % k), os.path.join(DOCS, "reels"))
        for lang, tx in (("en", en), ("th", th)):
            open(os.path.join(DOCS, "reels", "%s.%s.vtt" % (k, lang)), "w", encoding="utf-8").write(vtt(d, tx))
        # Facebook reads captions from files named <video>.<locale>.srt
        open(os.path.join(out, "bots-crave-%s.en_US.srt" % k), "w", encoding="utf-8").write(srt(d, en))
        open(os.path.join(out, "bots-crave-%s.th_TH.srt" % k), "w", encoding="utf-8").write(srt(d, th))

    shutil.copy(os.path.join(ROOT, "tools", "card.jpg"), DOCS)
    open(os.path.join(DOCS, "icon.svg"), "w").write(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="12" fill="#FFD60A"/>'
        '<path d="M36 6 18 36h12l-4 22 20-32H34z" fill="#16A33A" stroke="#141A10" stroke-width="3" stroke-linejoin="round"/></svg>\n')
    open(os.path.join(DOCS, "robots.txt"), "w").write("User-agent: *\nAllow: /\nSitemap: %ssitemap.xml\n" % URL)
    open(os.path.join(DOCS, "sitemap.xml"), "w").write(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        "  <url><loc>%s</loc><lastmod>2026-09-28</lastmod></url>\n</urlset>\n" % URL)
    open(os.path.join(DOCS, "llms.txt"), "w", encoding="utf-8").write(f"""# {TITLE} · บอตหิวอะไร

> {DESC}

A spoof of the Brawndo ads in Idiocracy (2006). Linkdo, "the crawler mutilator", stands for links
from a site to itself. The page sets one week of motdang.net traffic (20–26 Sept 2026) beside what
search engines and model builders say they want, with sources.

## Numbers (motdang.net, 20–26 Sept 2026, Cloudflare edge analytics, browser beacon, motdang's counter)
- All requests: 2,117,656. meta-externalagent 1,140,878. ClaudeBot 160,495. GPTBot 2,193.
- AI-crawler requests arriving from another motdang.net page: 1,016,102 (67% of AI requests).
- Page loads a person's browser ran: 882.

## Sources
- Google Search Central, Spam policies, link spam: https://developers.google.com/search/docs/essentials/spam-policies
- Google Search Central, helpful content: https://developers.google.com/search/docs/fundamentals/creating-helpful-content
- Wikipedia:Verifiability: https://en.wikipedia.org/wiki/Wikipedia:Verifiability
- Shumailov et al., Nature 631:755–759 (2024), doi:10.1038/s41586-024-07566-y; preprint https://arxiv.org/abs/2305.17493
- Jeremy Howard, llms.txt: https://llmstxt.org/

## Reels
- For people: {URL}reels/bots-crave-people.mp4 (captions: reels/people.en.vtt, reels/people.th.vtt)
- For bots: {URL}reels/bots-crave-bots.mp4 (captions: reels/bots.en.vtt, reels/bots.th.vtt)

## Water on motdang.net
- https://motdang.net/colophon · https://motdang.net/audit.json · https://motdang.net/field/ · https://motdang.net/sites/safety/ · https://motdang.net/llms.txt

Text CC BY 4.0, NaNoBotCo.
""")
    open(os.path.join(DOCS, ".nojekyll"), "w").close()
    print("docs/ built")


if __name__ == "__main__":
    main()

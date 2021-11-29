import re
import ssl
import urllib.request as urllib2
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup as soup, SoupStrainer


def remove_last_trail(url):
    """ Remove last / string from input url and return """
    if url[-1] == "/":
        return url[:-1]
    return url


def check_is_main_page(url):
    for s in url[::-1]:
        if s == "/":
            return False
        if s == "#":
            return True

    return False


def fetch_all_links_from_website(website, blacklist):
    """
    Find all ahref links from website and return them all as list without duplicates.
    This is for getting brands, phone numbers and mails.
    """
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        req = urllib2.Request(website, headers={"User-Agent": "Mozilla/5.0"})
        response = urllib2.urlopen(req, context=ctx)
        content = response.read()
    except Exception:
        return []

    # Check if page has refresh redirect url
    redirect_re = re.compile("<meta[^>]*?url=(.*?)[\"']", re.IGNORECASE)
    match = redirect_re.search(str(content))
    if match:
        url = urljoin(website, match.groups()[0].strip())
        website = url
    else:
        website = response.url
    response.close()

    website = remove_last_trail(website)
    page_links = []
    domain = urlparse(website).netloc

    for link in soup(content, "html.parser", parse_only=SoupStrainer("a")):
        if link.has_attr("href"):
            try:
                href = remove_last_trail(urljoin(website, link["href"]))
            except Exception:
                continue
            if domain in href:
                if blacklist and any(keyword in href for keyword in blacklist):
                    continue
                if check_is_main_page(href):
                    continue
                page_links.append(href)

    page_links = list(set(page_links))
    page_links.insert(0, website)

    return page_links

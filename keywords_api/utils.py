import re
import ssl
import instaloader
import urllib.request as urllib2
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup as soup, SoupStrainer
from bs4.element import Comment


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


def clean_html(raw_html):
    """
    Get raw html as parameter and returns as cleaned text.
    """
    clean_reg = re.compile("<.*?>")
    clean_text = re.sub(clean_reg, "", raw_html)
    return clean_text


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

    partner_link = ''

    for link in soup(content, "html.parser", parse_only=SoupStrainer("a")):
        partner_link = ''
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
                if href.split('/')[-1].startswith('tel:'):
                    continue
                if not href.startswith('http'):
                    continue
                if href not in page_links:
                    if '/partner' in href:
                        partner_link = href
                    else:
                        page_links.append(href)

    page_links.insert(0, website)
    if partner_link:
        page_links.insert(1, partner_link)

    return page_links


def tag_visible(element):
    if element.parent.name in ['style', 'script', 'head', 'title', 'meta', '[document]']:
        return False
    if isinstance(element, Comment):
        return False
    return True


def get_most_frequent(array):
    """
    Get the most duplicated element from array and return.
    """
    array = [
        item.strip() for item in ", ".join(array).split(",") if item.strip() != ""
    ]
    try:
        result = max(set(array), key=array.count)
    except Exception:
        result = ""

    return result


IgLoadoader = instaloader.Instaloader()
IgLoadoader.login("jose.prtlopez", "hero1113")


def get_ig_data(doctor_list):
    """
    Get detailed Instagram information using instaloader library
     and return as Dictionary.
    """
    ig_biography = ""
    ig_website = ""
    hashtags_list = []
    likes_and_comments_counts = []
    followers = []
    followees = []

    for doctor in doctor_list:
        try:
            doctor = doctor.split("/")[3]
        except Exception:
            continue

        try:
            profile = instaloader.Profile.from_username(
                IgLoadoader.context, doctor
            )
        except Exception:
            continue

        if not ig_biography:
            ig_biography = profile.biography
        if not ig_website:
            ig_website = profile.external_url

        followers.append(int(profile.followers))
        followees.append(int(profile.followees))

        posts = profile.get_posts()
        for post in posts:
            likes_and_comments_counts.append((post.likes, post.comments))
            hashtags_list.append(", ".join(post.caption_hashtags))

    if len(likes_and_comments_counts) > 0:
        avg_number_likes = sum([iter[0] for iter in likes_and_comments_counts]) / len(
            likes_and_comments_counts
        )
        avg_number_comments = sum(
            [iter[1] for iter in likes_and_comments_counts]
        ) / len(likes_and_comments_counts)
    else:
        avg_number_likes = 0
        avg_number_comments = 0

    unique_hashtags_list = list(
        set([h.strip() for h in ", ".join(hashtags_list).split(",")])
    )

    data_ig = {
        "IG_BIOGRAPHY": ig_biography,
        "IG_BIOGRAPHY_WEBSITE": ig_website,
        "IG_FOLLOWERS": sum(followers),
        "IG_FOLLOWS": sum(followees),
        "IG_POSTS": len(likes_and_comments_counts),
        "IG_HASHTAGS": ", ".join(list(filter(None, unique_hashtags_list))),
        "IG_MOST_USED_HASHTAG": get_most_frequent(hashtags_list),
        "IG_AVG_LIKES": int(avg_number_likes),
        "IG_AVG_COMMENTS": int(avg_number_comments),
        "IG_URL": doctor_list[0],
    }

    return data_ig

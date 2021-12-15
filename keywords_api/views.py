from rest_framework.views import APIView, status
from rest_framework.response import Response
import ssl
import urllib
import requests
import urllib.request as urllib2
from urllib.parse import urlparse
from bs4 import BeautifulSoup, SoupStrainer
from usp.tree import sitemap_tree_for_homepage

from .utils import fetch_all_links_from_website, clean_html, tag_visible


ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


class KeywordsAPIView(APIView):
    def get(self, request, *args, **kwargs):
        origin_keywords = request.query_params.get('keywords')
        websites = request.query_params.get('websites')
        blacklist = request.query_params.get('blacklist')

        if not origin_keywords or not websites:
            return Response(
                data={"error": "Need to specify keywords and websites"},
                status=status.HTTP_400_BAD_REQUEST
            )

        result = []
        websites = websites.split(',')
        origin_keywords = origin_keywords.split(',')
        if blacklist:
            blacklist = blacklist.split(',')

        # for website in websites:
        #     if website.startswith('http'):
        #         domain = urlparse(website).netloc
        #     else:
        #         domain = website
        #     domain = domain.replace("www.", "")
        #     if domain.endswith('/'):
        #         domain = domain[:-1]
        #
        #     keywords = origin_keywords.copy()
        #     for keyword in keywords:
        #         text = f'site:{domain} "{keyword}"'
        #         text = urllib.parse.quote_plus(text)
        #         search_url = 'https://google.com/search?q=' + text
        #         # search_term = f'https://www.google.com/search?q=site:{domain} "{keyword}"'
        #
        #         headers = {
        #             'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
        #                           'Chrome/67.0.3396.99 Safari/537.36',
        #         }
        #         response = requests.get(search_url, headers=headers)
        #         try:
        #             soup = BeautifulSoup(response.text, "html.parser")
        #             for element in soup.select('.tF2Cxc'):
        #                 link = element.select_one('.yuRUbf a')['href']
        #                 if domain in link:
        #                     if not blacklist or (blacklist and not any(word in link for word in blacklist)):
        #                         result.append(
        #                             {
        #                                 "keyword": keyword,
        #                                 "main_url": domain,
        #                                 "first_found_at": link
        #                             }
        #                         )
        #                         break
        #
        #         except Exception as e:
        #             continue

        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/67.0.3396.99 Safari/537.36',
            'Content-Type': 'text/html; charset=utf-8',
        }
        for website in websites:
            keywords = origin_keywords.copy()
            if website.startswith('http'):
                domain = urlparse(website).netloc
            else:
                domain = website
                website = f'http://{website}'
            domain = domain.replace("www.", "")
            if domain.endswith('/'):
                domain = domain[:-1]

            tree = sitemap_tree_for_homepage(website)
            page_links = [link.url for link in tree.all_pages()]
            page_links = list(set(page_links))
            page_links.insert(0, website)

            if len(page_links) <= 1:
                page_links = fetch_all_links_from_website(website, blacklist)

            for page_link in page_links:
                if blacklist and any(keyword in page_link for keyword in blacklist):
                    continue
                if len(keywords) == 0:
                    break
                try:
                    req = urllib2.Request(
                        page_link, headers=headers
                    )
                    response = urllib2.urlopen(req, context=ctx)
                    content = response.read()
                    content = content.decode().replace('­', '')
                    word_list = ""
                    try:
                        content_html = BeautifulSoup(content, "html.parser")
                        texts = content_html.findAll(text=True)
                        visible_texts = filter(tag_visible, texts)
                        word_list += u" ".join(t.strip() for t in visible_texts)
                    except Exception as e:
                        continue
                    response.close()
                except Exception as e:
                    continue

                for keyword in keywords:
                    if keyword.lower() in word_list.lower():
                        result.append(
                            {
                                "keyword": keyword,
                                "main_url": domain,
                                "first_found_at": page_link
                            }
                        )
                        keywords.remove(keyword)

        return Response(data=result, status=status.HTTP_200_OK)

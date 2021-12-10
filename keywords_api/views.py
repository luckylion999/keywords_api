from rest_framework.views import APIView, status
from rest_framework.response import Response
import ssl
import urllib
import requests
import urllib.request as urllib2
from urllib.parse import urlparse
from bs4 import BeautifulSoup, SoupStrainer

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

        for website in websites:
            keywords = origin_keywords.copy()
            page_links = fetch_all_links_from_website(website, blacklist)

            for page_link in page_links:
                if len(keywords) == 0:
                    break
                try:
                    req = urllib2.Request(
                        page_link, headers={"User-Agent": "Mozilla/5.0"}
                    )
                    response = urllib2.urlopen(req, context=ctx)
                    content = response.read()
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
                                "main_url": urlparse(website).netloc,
                                "first_found_at": page_link
                            }
                        )
                        keywords.remove(keyword)

        return Response(data=result, status=status.HTTP_200_OK)

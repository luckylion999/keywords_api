from rest_framework.views import APIView, status
from rest_framework.response import Response
import ssl
import urllib
import requests
import urllib.request as urllib2
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup, SoupStrainer
from usp.tree import sitemap_tree_for_homepage
from html_to_etree import parse_html_bytes
from scrapy.http import HtmlResponse

from .utils import (
    fetch_all_links_from_website,
    tag_visible,
    get_ig_data,
    find_links_tree,
    get_social_link
)


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
                    try:
                        content = content.decode().replace('­', '')
                    except:
                        pass
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


class IGDataAPIView(APIView):
    def get(self, request, *args, **kwargs):
        ig_list = request.query_params.get('ig_list')

        if not ig_list:
            return Response(
                data={"error": "Need to specify IG urls"},
                status=status.HTTP_400_BAD_REQUEST
            )

        ig_list = ig_list.split(',')
        result = []
        for ig_url in ig_list:
            result.append(get_ig_data([ig_url]))

        return Response(data=result, status=status.HTTP_200_OK)


class FetchSocialAccountsAPIView(APIView):
    def get(self, request, *args, **kwargs):
        websites = request.query_params.get('websites')

        if not websites:
            return Response(
                data={"error": "Need to specify websites"},
                status=status.HTTP_400_BAD_REQUEST
            )

        websites = websites.split(',')
        result = []
        for website in websites:
            if not website.startswith('http'):
                website = f'http://{website}'
            try:
                res = requests.get(website, verify=False)
            except:
                result.append(
                    {
                        'website': website,
                        'instagram_accounts': None,
                        'youtube_accounts': None,
                        'linkedin_accounts': None,
                        'twitter_accounts': None,
                        'facebook_accounts': None,
                        'pinterest_accounts': None,
                        'tiktok_accounts': None,
                    }
                )
                continue

            try:
                tree = parse_html_bytes(res.content, res.headers.get("content-type"))
                social_data = list(set(find_links_tree(tree)))
                instagram_accounts = get_social_link(social_data, "instagram.com")
                youtube_accounts = get_social_link(social_data, "youtube.com")
                linkedin_accounts = get_social_link(social_data, "linkedin.com")
                twitter_accounts = get_social_link(social_data, "twitter.com")
                facebook_accounts = get_social_link(social_data, "facebook.com")
                pinterest_accounts = get_social_link(social_data, "pinterest.com")
                tiktok_accounts = get_social_link(social_data, "tiktok.com")
            except Exception:
                instagram_accounts = None
                youtube_accounts = None
                linkedin_accounts = None
                twitter_accounts = None
                facebook_accounts = None
                pinterest_accounts = None
                tiktok_accounts = None

            result.append(
                {
                    'website': website,
                    'instagram_accounts': instagram_accounts,
                    'youtube_accounts': youtube_accounts,
                    'linkedin_accounts': linkedin_accounts,
                    'twitter_accounts': twitter_accounts,
                    'facebook_accounts': facebook_accounts,
                    'pinterest_accounts': pinterest_accounts,
                    'tiktok_accounts': tiktok_accounts
                }
            )

        return Response(data=result, status=status.HTTP_200_OK)


class LogoAPIView(APIView):
    def get(self, request, *args, **kwargs):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/75.0.3770.100 Safari/537.36'
        }

        websites = request.query_params.get('websites')

        if not websites:
            return Response(
                data={"error": "Need to specify websites"},
                status=status.HTTP_400_BAD_REQUEST
            )

        websites = websites.split(',')
        result = []

        for website in websites:
            try:
                if not website.startswith('http'):
                    website = f'http://{website}'
                response = requests.get(website, headers=headers, verify=False)
                try:
                    response = HtmlResponse(url=response.url, body=response.text, encoding='utf-8')
                    logo = response.xpath('//img[contains(@src, "logo")]/@src').extract_first()
                    if not logo:
                        logo = response.xpath('//img[contains(@data-orig-src, "logo")]/@src').extract_first()
                    if not logo:
                        logo = response.xpath('//img[contains(@data-src, "logo")]/@src').extract_first()
                    if not logo:
                        logo = response.xpath('//img[contains(@class, "logo")]/@src').extract_first()
                    if not logo:
                        logo = response.xpath('//*[contains(@class, "logo")]//img/@src').extract_first()
                    if not logo:
                        logo = response.xpath('//*[contains(@id, "logo")]//img/@src').extract_first()
                    if not logo:
                        logo = response.xpath('//*[contains(@class, "navbar-brand")]//img/@src').extract_first()

                    result.append(
                        {
                            'website': website,
                            'logo': urljoin(response.url, logo) if logo else ''
                        }
                    )

                except Exception as e:
                    result.append(
                        {
                            'website': website,
                            'logo': ''
                        }
                    )
                    continue

            except Exception as e:
                result.append(
                    {
                        'website': website,
                        'logo': ''
                    }
                )
                continue

        return Response(data=result, status=status.HTTP_200_OK)


class GTMGAFBAPIView(APIView):
    def get(self, request, *args, **kwargs):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/75.0.3770.100 Safari/537.36'
        }

        websites = request.query_params.get('websites')

        if not websites:
            return Response(
                data={"error": "Need to specify websites"},
                status=status.HTTP_400_BAD_REQUEST
            )

        websites = websites.split(',')
        result = []

        for website in websites:
            data = {
                'Website': website,
                'GOOGLE_TAG_MANAGER': 'NO',
                'GOOGLE_ANALYTICS': 'NO',
                'FACEBOOK_PIXELS': 'NO'
            }
            try:
                if not website.startswith('http'):
                    website = f'http://{website}'
                response = requests.get(website, headers=headers, verify=False)
                content = response.text
                if 'googletagmanager.com' in content:
                    data['GOOGLE_TAG_MANAGER'] = 'YES'
                if 'google-analytics.com' in content:
                    data['GOOGLE_ANALYTICS'] = 'YES'
                if 'connect.facebook.net' in content:
                    data['FACEBOOK_PIXELS'] = 'YES'
            except Exception as e:
                pass

            result.append(data)

        return Response(data=result, status=status.HTTP_200_OK)

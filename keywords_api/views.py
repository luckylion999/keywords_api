from rest_framework.views import APIView, status
from rest_framework.response import Response
import ssl
import urllib.request as urllib2

from .utils import fetch_all_links_from_website


ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


class KeywordsAPIView(APIView):
    def get(self, request, *args, **kwargs):
        keywords = request.query_params.get('keywords')
        websites = request.query_params.get('websites')
        blacklist = request.query_params.get('blacklist')

        if not keywords or not websites:
            return Response(
                data={"error": "Need to specify keywords and websites"},
                status=status.HTTP_400_BAD_REQUEST
            )

        result = []
        websites = websites.split(',')
        keywords = keywords.split(',')
        for website in websites:
            page_links = fetch_all_links_from_website(website, blacklist)

            for page_link in page_links:
                try:
                    req = urllib2.Request(
                        page_link, headers={"User-Agent": "Mozilla/5.0"}
                    )
                    response = urllib2.urlopen(req, context=ctx)
                    content = str(response.read())
                    response.close()
                except Exception:
                    continue

                for keyword in keywords:
                    if keyword in content:
                        result.append(
                            {
                                "keyword": keyword,
                                "main_url": website,
                                "first_found_at": page_link
                            }
                        )
                        keywords.remove(keyword)

        return Response(data=result, status=status.HTTP_200_OK)

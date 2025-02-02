#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import re
from typing import Optional

import requests
from praw.models import Submission

from bdfr.exceptions import SiteDownloaderError
from bdfr.resource import Resource
from bdfr.site_authenticator import SiteAuthenticator
from bdfr.site_downloaders.base_downloader import BaseDownloader


class Redgifs(BaseDownloader):
    def __init__(self, post: Submission):
        super().__init__(post)

    def find_resources(self, authenticator: Optional[SiteAuthenticator] = None) -> list[Resource]:
        media_urls = self._get_link(self.post.url)
        return [Resource(self.post, m, Resource.retry_download(m), None) for m in media_urls]

    @staticmethod
    def _get_id(url: str) -> str:
        try:
            if url.endswith("/"):
                url = url.removesuffix("/")
            redgif_id = re.match(r".*/(.*?)(?:#.*|\?.*|\..{0,})?$", url).group(1).lower()
            if redgif_id.endswith("-mobile"):
                redgif_id = redgif_id.removesuffix("-mobile")
        except AttributeError:
            raise SiteDownloaderError(f"Could not extract Redgifs ID from {url}")
        return redgif_id

    @staticmethod
    def _get_link(url: str) -> set[str]:
        redgif_id = Redgifs._get_id(url)

        auth_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJpc3MiOiJhdXRoLXNlcnZpY2UiLCJpYXQiOjE3Mzg1MjQ2OTksImF1ZCI6Imh0dHBzOi8vYXBpLnJlZGdpZnMuY29tIiwiYXpwIjoiMTgyM2MzMWY3ZDMtNzQ1YS02NTg5LTAwMDUtZDhlOGZlMGE0NGMyIiwiZXhwIjoxNzM4NjExMDk5LCJzdWIiOiJjbGllbnQvMTgyM2MzMWY3ZDMtNzQ1YS02NTg5LTAwMDUtZDhlOGZlMGE0NGMyIiwic2NvcGVzIjoicmVhZCIsInZhbGlkX2FkZHIiOiI3MS4xOTMuMTUwLjAiLCJ2YWxpZF9hZ2VudCI6Ik1vemlsbGEvNS4wIChXaW5kb3dzIE5UIDEwLjA7IFdpbjY0OyB4NjQpIEFwcGxlV2ViS2l0LzUzNy4zNiAoS0hUTUwsIGxpa2UgR2Vja28pIENocm9tZS8xMzEuMC4wLjAgU2FmYXJpLzUzNy4zNiIsInJhdGUiOi0xLCJodHRwczovL3JlZGdpZnMuY29tL3Nlc3Npb24taWQiOiIyNDI3MjY5MTg4NzE0NTQ0NDAifQ.pG7zC1RqWOJGn0CmkYfXM1a_mCSa3xpsdrlJtHDD7JJ7q3MlJMYRZqglqNBR8Ukp92wwRfRN_IhpeNYYVy6UQgpT23Rfd-eWnekobMvB8KR-n1lpuVW2SzRfRgdS9boFmKhQi2jzZkIOSBEh3kO5YMHcP0Njdf_XlfFheHcE8eV6wqpi2NTMTPD_GOb3lHX5R681k1Tz8SbouwDJLTyM8ddUobC-4PU2OpqzVRK0wwIRyc_JhTLWcjZB_Xr8-i4qnR6WdcRCsQeolWiXuL4Q3YZyYiPfIhW8dj9Qpxt2MjfGgduVfd7RCJv4IR6Qq0RwRMseuUIYF9ndJl3vyAPC1w"

        headers = {
            "referer": "https://www.redgifs.com/",
            "origin": "https://www.redgifs.com",
            "content-type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        }

        content = Redgifs.retrieve_url(f"https://api.redgifs.com/v2/gifs/{redgif_id}", headers=headers)

        if content is None:
            raise SiteDownloaderError("Could not read the page source")

        try:
            response_json = json.loads(content.text)
        except json.JSONDecodeError as e:
            raise SiteDownloaderError(f"Received data was not valid JSON: {e}")

        out = set()
        try:
            if response_json["gif"]["type"] == 1:  # type 1 is a video
                if requests.get(response_json["gif"]["urls"]["hd"], headers=headers).ok:
                    out.add(response_json["gif"]["urls"]["hd"])
                else:
                    out.add(response_json["gif"]["urls"]["sd"])
            elif response_json["gif"]["type"] == 2:  # type 2 is an image
                if response_json["gif"]["gallery"]:
                    content = Redgifs.retrieve_url(
                        f'https://api.redgifs.com/v2/gallery/{response_json["gif"]["gallery"]}'
                    )
                    response_json = json.loads(content.text)
                    out = {p["urls"]["hd"] for p in response_json["gifs"]}
                else:
                    out.add(response_json["gif"]["urls"]["hd"])
            else:
                raise KeyError
        except (KeyError, AttributeError):
            raise SiteDownloaderError("Failed to find JSON data in page")

        # Update subdomain if old one is returned
        out = {re.sub("thumbs2", "thumbs3", link) for link in out}
        out = {re.sub("thumbs3", "thumbs4", link) for link in out}
        return out

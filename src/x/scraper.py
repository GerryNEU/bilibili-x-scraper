from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator

import httpx

from src.x.exceptions import CrawlerAuthError, CrawlerFetchError


logger = logging.getLogger(__name__)

_GQL = "/i/api/graphql"
_OP_USER = "1VOOyvKkiI3FMmkeDNxM9A/UserByScreenName"
_OP_TWEETS = "HeWHY26ItCfUmm1e6ITjeA/UserTweets"

# Feature flags required by X's GraphQL API (sourced from web app)
_FEATURES = {
    "articles_preview_enabled": False,
    "c9s_tweet_anatomy_moderator_badge_enabled": True,
    "communities_web_enable_tweet_community_results_fetch": True,
    "creator_subscriptions_quote_tweet_preview_enabled": False,
    "creator_subscriptions_tweet_preview_api_enabled": True,
    "freedom_of_speech_not_reach_fetch_enabled": True,
    "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
    "longform_notetweets_consumption_enabled": True,
    "longform_notetweets_inline_media_enabled": True,
    "longform_notetweets_rich_text_read_enabled": True,
    "responsive_web_edit_tweet_api_enabled": True,
    "responsive_web_enhance_cards_enabled": False,
    "responsive_web_graphql_exclude_directive_enabled": True,
    "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
    "responsive_web_graphql_timeline_navigation_enabled": True,
    "responsive_web_media_download_video_enabled": False,
    "responsive_web_twitter_article_tweet_consumption_enabled": True,
    "rweb_tipjar_consumption_enabled": True,
    "rweb_video_timestamps_enabled": True,
    "standardized_nudges_misinfo": True,
    "tweet_awards_web_tipping_enabled": False,
    "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
    "tweet_with_visibility_results_prefer_gql_media_interstitial_enabled": False,
    "tweetypie_unmention_optimization_enabled": True,
    "verified_phone_label_enabled": False,
    "view_counts_everywhere_api_enabled": True,
    "responsive_web_grok_analyze_button_fetch_trends_enabled": False,
    "premium_content_api_read_enabled": False,
    "profile_label_improvements_pcf_label_in_post_enabled": False,
    "responsive_web_grok_share_attachment_enabled": False,
    "responsive_web_grok_analyze_post_followups_enabled": False,
    "responsive_web_grok_image_annotation_enabled": False,
    "responsive_web_grok_analysis_button_from_backend": False,
    "responsive_web_jetfuel_frame": False,
    "rweb_video_screen_enabled": True,
    "responsive_web_grok_show_grok_translated_post": True,
}

_USER_FEATURES = {
    "highlights_tweets_tab_ui_enabled": True,
    "hidden_profile_likes_enabled": True,
    "hidden_profile_subscriptions_enabled": True,
    "subscriptions_verification_info_verified_since_enabled": True,
    "subscriptions_verification_info_is_identity_verified_enabled": False,
    "responsive_web_twitter_article_notes_tab_enabled": False,
    "subscriptions_feature_can_gift_premium": False,
}


def _params(variables: dict, features: dict) -> dict:
    return {
        "variables": json.dumps(variables, separators=(",", ":")),
        "features": json.dumps(features, separators=(",", ":")),
    }


async def scrape_posts(
    client: httpx.AsyncClient,
    username: str,
    last_post_id: str | None,
) -> AsyncIterator[dict]:
    user_id = await _get_user_id(client, username)
    async for raw in _iter_timeline(client, user_id, username, last_post_id):
        yield raw


async def _get_user_id(client: httpx.AsyncClient, username: str) -> str:
    variables = {"screen_name": username, "withSafetyModeUserFields": True}
    features = {**_FEATURES, **_USER_FEATURES}
    resp = await client.get(f"{_GQL}/{_OP_USER}", params=_params(variables, features))

    if resp.status_code == 401:
        raise CrawlerAuthError("X credentials are invalid or expired")
    if resp.status_code != 200:
        raise CrawlerFetchError(
            f"Failed to look up X user @{username}: HTTP {resp.status_code} — {resp.text[:300]}"
        )

    data = resp.json()
    try:
        return str(data["data"]["user"]["result"]["rest_id"])
    except (KeyError, TypeError) as exc:
        raise CrawlerFetchError(f"X user @{username} not found in response") from exc


async def _iter_timeline(
    client: httpx.AsyncClient,
    user_id: str,
    username: str,
    stop_at: str | None,
) -> AsyncIterator[dict]:
    cursor: str | None = None

    while True:
        variables: dict = {
            "userId": user_id,
            "count": 40,
            "includePromotedContent": True,
            "withQuickPromoteEligibilityTweetFields": True,
            "withVoice": True,
            "withV2Timeline": True,
        }
        if cursor:
            variables["cursor"] = cursor

        resp = await client.get(f"{_GQL}/{_OP_TWEETS}", params=_params(variables, _FEATURES))

        if resp.status_code == 401:
            raise CrawlerAuthError("X credentials are invalid or expired")
        if resp.status_code != 200:
            raise CrawlerFetchError(
                f"Failed to fetch X timeline for @{username}: HTTP {resp.status_code}"
            )

        entries, next_cursor = _parse_timeline_entries(resp.json())

        for tweet in entries:
            tweet_id = str(tweet.get("id", ""))
            if stop_at and tweet_id == stop_at:
                return
            raw = _tweet_to_raw(tweet, username)
            if raw:
                yield raw

        if not next_cursor or not entries:
            break
        cursor = next_cursor
        await asyncio.sleep(1.0)


def _parse_timeline_entries(data: dict) -> tuple[list[dict], str | None]:
    tweets: list[dict] = []
    cursor: str | None = None

    try:
        result = data["data"]["user"]["result"]
        # GraphQL may return "timeline" or "timeline_v2" depending on client flags
        tl_root = result.get("timeline_v2") or result.get("timeline") or {}
        instructions = tl_root["timeline"]["instructions"]
    except (KeyError, TypeError):
        return tweets, cursor

    for instruction in instructions:
        if instruction.get("type") != "TimelineAddEntries":
            continue
        for entry in instruction.get("entries", []):
            entry_id = entry.get("entryId", "")
            content = entry.get("content", {})

            if entry_id.startswith("cursor-bottom"):
                cursor = content.get("value")
                continue
            if entry_id.startswith("cursor-") or entry_id.startswith("messageprompt"):
                continue

            tweet_result = (
                content.get("itemContent", {}).get("tweet_results", {}).get("result", {})
            )
            if tweet_result.get("__typename") == "TweetWithVisibilityResults":
                tweet_result = tweet_result.get("tweet", {})

            legacy = tweet_result.get("legacy", {})
            rest_id = tweet_result.get("rest_id", "")
            if not legacy or not rest_id:
                continue

            user_legacy = (
                tweet_result.get("core", {})
                .get("user_results", {})
                .get("result", {})
                .get("legacy", {})
            )
            tweets.append(
                {**legacy, "id": rest_id, "author_name": user_legacy.get("name", "")}
            )

    return tweets, cursor


def _tweet_to_raw(tweet: dict, username: str) -> dict | None:
    tweet_id = str(tweet.get("id", ""))
    if not tweet_id:
        return None
    text = tweet.get("full_text") or tweet.get("text") or ""
    return {
        "id": tweet_id,
        "text": text,
        "created_at": tweet.get("created_at", ""),
        "media_urls": _extract_media_urls(tweet),
        "url": f"https://x.com/{username}/status/{tweet_id}",
        "author_name": tweet.get("author_name", username),
    }


def _extract_media_urls(tweet: dict) -> list[str]:
    entities = tweet.get("extended_entities") or tweet.get("entities") or {}
    media_list = entities.get("media") or []
    urls: list[str] = []
    for media in media_list:
        media_type = media.get("type", "")
        if media_type == "photo":
            urls.append(media["media_url_https"])
        elif media_type in ("video", "animated_gif"):
            variants = media.get("video_info", {}).get("variants", [])
            best = max(
                (v for v in variants if v.get("content_type") == "video/mp4"),
                key=lambda v: v.get("bitrate", 0),
                default=None,
            )
            if best:
                urls.append(best["url"])
    return urls

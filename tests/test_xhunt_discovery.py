from __future__ import annotations

import json

from twitter_ops_agent.discovery.xhunt import XHuntScoutAgent, XHuntTrendClient, parse_hot_tweets


SAMPLE_HTML = r"""
<!DOCTYPE html>
<html>
  <body>
    <script>
      self.__next_f.push([1,"da:[\"$\",\"li\",\"2030000000000000001\",{\"children\":[\"$\",\"a\",null,{\"href\":\"https://twitter.com/ai_writer/status/2030000000000000001\",\"target\":\"_blank\",\"rel\":\"noopener noreferrer\",\"children\":[[\"$\",\"div\",null,{\"children\":[\"$\",\"p\",null,{\"children\":\"Anthropic builder notes\"}]}],[\"$\",\"$L14\",null,{\"content\":\"Anthropic agent workflows are getting much cheaper for developers.\",\"children\":[\"$\",\"p\",null,{\"children\":\"Anthropic agent workflows are getting much cheaper for developers.\"}]}],[\"$\",\"div\",null,{\"children\":[[\"$\",\"span\",null,{\"title\":\"Views\",\"children\":[\"$\",\"span\",null,{\"children\":\"12,345\"}]}],[\"$\",\"span\",null,{\"title\":\"Likes\",\"children\":[\"$\",\"span\",null,{\"children\":\"456\"}]}],[\"$\",\"span\",null,{\"title\":\"Retweets\",\"children\":[\"$\",\"span\",null,{\"children\":\"78\"}]}]]}],[\"$\",\"div\",null,{\"children\":[\"$\",\"$Le1\",null,{\"value\":0.82,\"locale\":\"en\",\"className\":\"text-xs\"}]}]]}]}]\n"]);
      self.__next_f.push([1,"db:[\"$\",\"li\",\"2030000000000000002\",{\"children\":[\"$\",\"a\",null,{\"href\":\"https://twitter.com/market_watch/status/2030000000000000002\",\"target\":\"_blank\",\"rel\":\"noopener noreferrer\",\"children\":[[\"$\",\"div\",null,{\"children\":[\"$\",\"p\",null,{\"children\":\"Macro market check\"}]}],[\"$\",\"$L14\",null,{\"content\":\"Completely unrelated macro thread with low engagement.\",\"children\":[\"$\",\"p\",null,{\"children\":\"Completely unrelated macro thread with low engagement.\"}]}],[\"$\",\"div\",null,{\"children\":[[\"$\",\"span\",null,{\"title\":\"Views\",\"children\":[\"$\",\"span\",null,{\"children\":\"500\"}]}],[\"$\",\"span\",null,{\"title\":\"Likes\",\"children\":[\"$\",\"span\",null,{\"children\":\"3\"}]}],[\"$\",\"span\",null,{\"title\":\"Retweets\",\"children\":[\"$\",\"span\",null,{\"children\":\"1\"}]}]]}],[\"$\",\"div\",null,{\"children\":[\"$\",\"$Le1\",null,{\"value\":0.12,\"locale\":\"en\",\"className\":\"text-xs\"}]}]]}]}]\n"]);
      self.__next_f.push([1,"dc:[\"$\",\"li\",\"2030000000000000001\",{\"children\":[\"$\",\"a\",null,{\"href\":\"https://twitter.com/ai_writer/status/2030000000000000001\",\"target\":\"_blank\",\"rel\":\"noopener noreferrer\",\"children\":[[\"$\",\"div\",null,{\"children\":[\"$\",\"p\",null,{\"children\":\"Anthropic builder notes\"}]}],[\"$\",\"$L14\",null,{\"content\":\"Anthropic agent workflows are getting much cheaper for developers.\",\"children\":[\"$\",\"p\",null,{\"children\":\"Anthropic agent workflows are getting much cheaper for developers.\"}]}],[\"$\",\"div\",null,{\"children\":[[\"$\",\"span\",null,{\"title\":\"Views\",\"children\":[\"$\",\"span\",null,{\"children\":\"12,300\"}]}],[\"$\",\"span\",null,{\"title\":\"Likes\",\"children\":[\"$\",\"span\",null,{\"children\":\"450\"}]}],[\"$\",\"span\",null,{\"title\":\"Retweets\",\"children\":[\"$\",\"span\",null,{\"children\":\"77\"}]}]]}],[\"$\",\"div\",null,{\"children\":[\"$\",\"$Le1\",null,{\"value\":0.80,\"locale\":\"en\",\"className\":\"text-xs\"}]}]]}]}]\n"]);
    </script>
  </body>
</html>
"""

GLOBAL_SAMPLE_HTML = r"""
<!DOCTYPE html>
<html>
  <body>
    <script>
      self.__next_f.push([1,"ga:[\"$\",\"li\",\"2030000000000000001\",{\"children\":[\"$\",\"a\",null,{\"href\":\"https://twitter.com/ai_writer/status/2030000000000000001\",\"target\":\"_blank\",\"rel\":\"noopener noreferrer\",\"children\":[[\"$\",\"div\",null,{\"children\":[\"$\",\"p\",null,{\"children\":\"Anthropic builder notes\"}]}],[\"$\",\"$L14\",null,{\"content\":\"Anthropic agent workflows are getting much cheaper for developers.\",\"children\":[\"$\",\"p\",null,{\"children\":\"Anthropic agent workflows are getting much cheaper for developers.\"}]}],[\"$\",\"div\",null,{\"children\":[[\"$\",\"span\",null,{\"title\":\"Views\",\"children\":[\"$\",\"span\",null,{\"children\":\"12,345\"}]}],[\"$\",\"span\",null,{\"title\":\"Likes\",\"children\":[\"$\",\"span\",null,{\"children\":\"456\"}]}],[\"$\",\"span\",null,{\"title\":\"Retweets\",\"children\":[\"$\",\"span\",null,{\"children\":\"78\"}]}]]}],[\"$\",\"div\",null,{\"children\":[\"$\",\"$Le1\",null,{\"value\":0.82,\"locale\":\"en\",\"className\":\"text-xs\"}]}]]}]}]\n"]);
      self.__next_f.push([1,"gb:[\"$\",\"li\",\"2030000000000000003\",{\"children\":[\"$\",\"a\",null,{\"href\":\"https://twitter.com/global_builder/status/2030000000000000003\",\"target\":\"_blank\",\"rel\":\"noopener noreferrer\",\"children\":[[\"$\",\"div\",null,{\"children\":[\"$\",\"p\",null,{\"children\":\"OpenAI roadmap thread\"}]}],[\"$\",\"$L14\",null,{\"content\":\"OpenAI tooling changes are forcing builders to rethink distribution.\",\"children\":[\"$\",\"p\",null,{\"children\":\"OpenAI tooling changes are forcing builders to rethink distribution.\"}]}],[\"$\",\"div\",null,{\"children\":[[\"$\",\"span\",null,{\"title\":\"Views\",\"children\":[\"$\",\"span\",null,{\"children\":\"31,000\"}]}],[\"$\",\"span\",null,{\"title\":\"Likes\",\"children\":[\"$\",\"span\",null,{\"children\":\"920\"}]}],[\"$\",\"span\",null,{\"title\":\"Retweets\",\"children\":[\"$\",\"span\",null,{\"children\":\"140\"}]}]]}],[\"$\",\"div\",null,{\"children\":[\"$\",\"$Le1\",null,{\"value\":0.91,\"locale\":\"en\",\"className\":\"text-xs\"}]}]]}]}]\n"]);
    </script>
  </body>
</html>
"""


def test_parse_hot_tweets_extracts_ranked_items_from_public_page():
    items = parse_hot_tweets(SAMPLE_HTML)

    assert [item.tweet_id for item in items] == ["2030000000000000001", "2030000000000000002"]
    assert items[0].url == "https://twitter.com/ai_writer/status/2030000000000000001"
    assert items[0].author_handle == "ai_writer"
    assert items[0].text == "Anthropic agent workflows are getting much cheaper for developers."
    assert items[0].views == 12345
    assert items[0].likes == 456
    assert items[0].retweets == 78
    assert items[0].heat == 0.82


def test_xhunt_scout_agent_filters_and_tracks_seen_state():
    client = XHuntTrendClient(
        html_loader=lambda **_: SAMPLE_HTML,
    )
    scout = XHuntScoutAgent(
        client=client,
        group="global",
        hours=4,
        limit=10,
        min_views=1000,
        min_likes=10,
        state_size=5,
    )

    report = scout.fetch_since(last_seen=json.dumps(["already-seen"]))

    assert [seed.tweet_id for seed in report.seeds] == ["2030000000000000001"]
    assert report.seeds[0].track == "AI"
    assert report.seeds[0].source_kind == "tweet"
    assert report.seeds[0].velocity_hint > 0
    assert json.loads(report.next_seen_state) == [
        "2030000000000000001",
        "2030000000000000002",
        "already-seen",
    ]


def test_xhunt_scout_agent_merges_cn_and_global_groups_with_shared_24h_top15_defaults():
    calls: list[tuple[str, int]] = []

    client = XHuntTrendClient(
        html_loader=lambda **kwargs: _load_group_html(kwargs, calls),
    )
    scout = XHuntScoutAgent(
        client=client,
        groups=("cn", "global"),
        hours=24,
        limit=15,
        min_views=1000,
        min_likes=10,
        state_size=10,
    )

    report = scout.fetch_since(last_seen=None)

    assert calls == [("cn", 24), ("global", 24)]
    assert [seed.tweet_id for seed in report.seeds] == ["2030000000000000001", "2030000000000000003"]
    assert [seed.query for seed in report.seeds] == ["cn", "global"]
    assert json.loads(report.next_seen_state) == [
        "2030000000000000001",
        "2030000000000000002",
        "2030000000000000003",
    ]


def _load_group_html(kwargs, calls: list[tuple[str, int]]) -> str:
    group = kwargs["group"]
    hours = kwargs["hours"]
    calls.append((group, hours))
    if group == "cn":
        return SAMPLE_HTML
    if group == "global":
        return GLOBAL_SAMPLE_HTML
    raise AssertionError(group)

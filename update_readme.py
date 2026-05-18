import json
import os
import urllib.request

USER = "qiz-li"

QUERY = """
query($login: String!, $cursor: String) {
  user(login: $login) {
    repositories(
      first: 100
      after: $cursor
      isFork: false
      ownerAffiliations: OWNER
    ) {
      pageInfo { hasNextPage endCursor }
      nodes {
        languages(first: 20, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
  }
}
"""


def graphql(token, query, variables):
    data = json.dumps({"query": query, "variables": variables}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=data,
        headers={
            "Authorization": f"bearer {token}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def fetch_languages(token):
    langs = {}
    cursor = None

    while True:
        result = graphql(token, QUERY, {"login": USER, "cursor": cursor})
        repos = result["data"]["user"]["repositories"]

        for repo in repos["nodes"]:
            for edge in repo["languages"]["edges"]:
                name = edge["node"]["name"]
                color = edge["node"]["color"]
                langs.setdefault(name, {"bytes": 0, "color": color})
                langs[name]["bytes"] += edge["size"]

        if not repos["pageInfo"]["hasNextPage"]:
            break
        cursor = repos["pageInfo"]["endCursor"]

    return langs


def build_output(langs):
    total = sum(v["bytes"] for v in langs.values())
    sorted_langs = sorted(langs.items(), key=lambda x: x[1]["bytes"], reverse=True)
    filtered = [(l, d, d["bytes"] / total * 100) for l, d in sorted_langs if d["bytes"] / total >= 0.01]

    yaml = "``` yaml\nTop languages:\n"
    bar = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 6" height="6">\n'
        "  <defs>\n"
        '    <linearGradient id="gradient" x1="0%" y1="0%" x2="100%" y2="0%">\n'
    )

    start = 0
    for lang, data, percent in filtered:
        yaml += f"  - {lang} {int(percent)}%\n"

        color = data["color"] or "#ccc"
        bar += f'        <stop offset="{start}%" stop-color="{color}" />\n'
        bar += f'        <stop offset="{start + percent}%" stop-color="{color}" />\n'
        start += percent

    yaml += f"```\n\n[![Languages bar](bar.svg)](https://github.com/search?q=user%3A{USER}&type=code)\n"
    bar += "    </linearGradient>\n  </defs>\n"
    bar += '  <rect x="0" y="0" width="100%" height="6px" fill="url(#gradient)" rx="1.5" />\n'
    bar += "</svg>"

    return yaml, bar


if __name__ == "__main__":
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("Error: GITHUB_TOKEN environment variable is required.")
        exit(1)

    langs = fetch_languages(token)
    if not langs:
        print("Error: No language data found.")
        exit(1)

    yaml, bar = build_output(langs)

    with open("README.md", "w") as f:
        f.write(yaml)
    with open("bar.svg", "w") as f:
        f.write(bar)

    print(f"Updated with {len(langs)} languages from user '{USER}'.")

import os
import requests
import re


def get_projects(token, username):
    url = f"https://api.github.com/users/{username}/repos?per_page=100&sort=updated"
    headers = {"Authorization": f"token {token}"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    cards = []
    for repo in response.json():
        # Only include repos with Pages, excluding the main index repo itself
        if repo.get("has_pages") and repo["name"] != f"{username}.github.io":
            name = repo["name"].replace("-", " ").title()
            link = f"https://{username}.github.io/{repo['name']}/"
            desc = repo["description"] or "No description provided."
            lang = repo["language"] or "Web"

            card = f"""
            <a href="{link}" class="card">
                <h3>{name}</h3>
                <p>{desc}</p>
                <span class="tag">{lang}</span>
            </a>"""
            cards.append(card)
    return cards


def update_html(cards):
    with open("index.html", "r", encoding="utf-8") as f:
        content = f.read()

    start_marker = ""
    end_marker = ""

    new_content = re.sub(
        f"{start_marker}.*?{end_marker}",
        f"{start_marker}\n{''.join(cards)}\n{end_marker}",
        content,
        flags=re.DOTALL,
    )

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(new_content)


if __name__ == "__main__":
    gh_token = os.getenv("GH_TOKEN")
    gh_repo = os.getenv("GITHUB_REPOSITORY")
    owner = gh_repo.split("/")[0]

    project_list = get_projects(gh_token, owner)
    update_html(project_list)

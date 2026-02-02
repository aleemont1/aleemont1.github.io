import os
import re

import requests


def get_projects(token, username):
    # Fetch repositories sorted by update time
    url = f"https://api.github.com/users/{username}/repos?per_page=100&sort=updated"
    headers = {"Authorization": f"token {token}"}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except Exception as e:
        print(f"Error fetching repos: {e}")
        return []

    cards = []
    for repo in response.json():
        # Logic: Has Pages enabled AND is not the main portfolio repo itself
        if (
            repo.get("has_pages")
            and repo["name"].lower() != f"{username}.github.io".lower()
        ):
            name = repo["name"].replace("-", " ").title()
            link = f"https://{username}.github.io/{repo['name']}/"
            desc = repo["description"] or "No description provided."
            lang = repo["language"] or "Project"

            # Create HTML Card
            card = f"""
            <a href="{link}" class="card">
                <h3>{name}</h3>
                <p>{desc}</p>
                <span class="tag">{lang}</span>
            </a>"""
            cards.append(card)
    return cards


def update_html(cards):
    file_path = "index.html"
    if not os.path.exists(file_path):
        print("index.html not found!")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Markers
    start_marker = ""
    end_marker = ""

    # Create the new content block including markers to ensure they stay for next time
    new_block = f"{start_marker}\n" + "\n".join(cards) + f"\n{end_marker}"

    # Regex to find EVERYTHING between start and end markers (inclusive)
    # and replace it with the new block
    pattern = re.compile(
        f"{re.escape(start_marker)}.*?{re.escape(end_marker)}", re.DOTALL
    )

    if not pattern.search(content):
        print("Markers not found in index.html. Initialization failed.")
        return

    new_content = pattern.sub(new_block, content)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print("Index updated successfully.")


if __name__ == "__main__":
    gh_token = os.getenv("GH_TOKEN")
    gh_repo = os.getenv("GITHUB_REPOSITORY")

    if gh_token and gh_repo:
        owner = gh_repo.split("/")[0]
        project_list = get_projects(gh_token, owner)
        update_html(project_list)
    else:
        print("Missing environment variables (GH_TOKEN or GITHUB_REPOSITORY)")

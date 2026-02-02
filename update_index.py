import os
import re

import requests

# This template is used if index.html is missing, corrupt, or missing markers
DEFAULT_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Alessandro Monticelli - Portfolio</title>
    <style>
        :root { --bg: #0d1117; --card-bg: #161b22; --text: #c9d1d9; --accent: #58a6ff; --border: #30363d; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; background: var(--bg); color: var(--text); padding: 40px 20px; margin: 0; line-height: 1.6; }
        .container { max-width: 1000px; margin: 0 auto; }
        .header { text-align: center; margin-bottom: 50px; }
        .header h1 { margin-bottom: 10px; color: var(--accent); }
        .header p { color: #8b949e; font-style: italic; }
        section { margin-bottom: 60px; }
        h2 { border-bottom: 1px solid var(--border); padding-bottom: 10px; margin-bottom: 30px; text-align: center; color: #fff; }
        .stats-grid { display: flex; flex-direction: column; align-items: center; gap: 20px; }
        .stats-grid img { width: 100%; max-width: 800px; height: auto; border-radius: 6px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }
        .card { background: var(--card-bg); border: 1px solid var(--border); border-radius: 6px; padding: 20px; text-decoration: none; color: inherit; transition: border-color 0.3s, transform 0.2s; display: flex; flex-direction: column; }
        .card:hover { border-color: var(--accent); transform: translateY(-2px); }
        .card h3 { margin: 0 0 10px 0; color: var(--accent); }
        .card p { font-size: 0.9em; color: #8b949e; margin-bottom: 15px; flex-grow: 1; }
        .tag { font-size: 0.8em; background: #21262d; padding: 4px 8px; border-radius: 12px; border: 1px solid var(--border); align-self: flex-start; color: var(--accent); }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Alessandro Monticelli</h1>
            <p>Embedded Software Engineer | Computer Engineering MSc</p>
        </div>
        <section>
            <h2>GitHub Activity & Stats</h2>
            <div class="stats-grid">
                <img src="https://raw.githubusercontent.com/aleemont1/aleemont1/main/images/contribs.svg" alt="GitHub Contributions" />
                <img src="https://raw.githubusercontent.com/aleemont1/aleemont1/main/images/userstats.svg" alt="GitHub Statistics" />
            </div>
        </section>
        <section>
            <h2>My Projects</h2>
            <div class="grid">
</div>
        </section>
    </div>
</body>
</html>"""


def get_projects(token, username):
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
        if (
            repo.get("has_pages")
            and repo["name"].lower() != f"{username}.github.io".lower()
        ):
            name = repo["name"].replace("-", " ").title()
            link = f"https://{username}.github.io/{repo['name']}/"
            desc = repo["description"] or "No description provided."
            lang = repo["language"] or "Project"

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

    # Read existing file or use template if missing/corrupt
    content = ""
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

    start_marker = ""
    end_marker = ""

    # Critical Check: If file is corrupted (missing markers), reset it completely
    if start_marker not in content or end_marker not in content:
        print("File corrupted or markers missing. Resetting to default template.")
        content = DEFAULT_TEMPLATE

    # Construct the replacement block
    # We purposefully include newlines to keep source code readable
    new_block = f"{start_marker}\n" + "\n".join(cards) + f"\n{end_marker}"

    # Safe Regex Replacement
    pattern = re.compile(
        f"{re.escape(start_marker)}.*?{re.escape(end_marker)}", re.DOTALL
    )
    new_content = pattern.sub(new_block, content)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print("Index updated successfully.")


if __name__ == "__main__":
    gh_token = os.getenv("GH_TOKEN")
    gh_repo = os.getenv("GITHUB_REPOSITORY")

    if gh_token and gh_repo:
        owner = gh_repo.split("/")[0]
        projects = get_projects(gh_token, owner)
        update_html(projects)
    else:
        print("Missing environment variables.")

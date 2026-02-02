#!/bin/bash

# ==============================================================================
# Portfolio Project Initializer
#
# This script automates the creation of the folder structure and files required
# for the GitHub Pages portfolio generator.
#
# Usage:
#   chmod +x init_portfolio.sh
#   ./init_portfolio.sh
# ==============================================================================

# Exit immediately if a command exits with a non-zero status
set -e

# 1. Define Color Codes for Output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}[INFO] Starting Project Initialization...${NC}"

# 2. Create Directory Structure
echo -e "${BLUE}[INFO] Creating directories...${NC}"
mkdir -p .github/workflows
mkdir -p src
mkdir -p tests

# 3. Create __init__.py files to make directories Python packages
touch src/__init__.py
touch tests/__init__.py

# 4. Create src/portfolio_generator.py
echo -e "${BLUE}[INFO] Writing src/portfolio_generator.py...${NC}"
cat << 'EOF' > src/portfolio_generator.py
import requests
import sys
import logging
from typing import List, Dict, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class PortfolioGenerator:
    """
    Handles the retrieval of GitHub repositories and the generation of 
    a static HTML portfolio.
    """

    def __init__(self, username: str, token: Optional[str] = None):
        """
        Initialize the generator.

        Args:
            username (str): GitHub username to target.
            token (str, optional): GitHub Personal Access Token for higher rate limits.
        """
        self.username = username
        self.api_url = f"https://api.github.com/users/{username}/repos"
        self.headers = {"Accept": "application/vnd.github.v3+json"}
        if token:
            self.headers["Authorization"] = f"token {token}"

    def fetch_repos(self) -> List[Dict]:
        """
        Fetches all public repositories for the user that have GitHub Pages enabled.

        Returns:
            List[Dict]: A list of repository data dictionaries.
        """
        logging.info(f"Fetching repositories for user: {self.username}")
        repos = []
        page = 1
        
        try:
            while True:
                # GitHub API is paginated
                response = requests.get(
                    f"{self.api_url}?per_page=100&page={page}", 
                    headers=self.headers
                )
                response.raise_for_status()
                
                data = response.json()
                if not data:
                    break
                
                # Filter logic: Must have GitHub Pages enabled and not be a fork 
                valid_repos = [
                    r for r in data 
                    if r.get("has_pages") and not r.get("fork")
                ]
                repos.extend(valid_repos)
                page += 1
                
            logging.info(f"Found {len(repos)} repositories with GitHub Pages enabled.")
            return repos

        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching repositories: {e}")
            sys.exit(1)

    def _generate_card_html(self, repo: Dict) -> str:
        """
        Generates the HTML string for a single repository card.
        """
        name = repo.get("name", "Unknown")
        description = repo.get("description") or "No description provided."
        topics = repo.get("topics", [])

        # Create tags HTML
        tags_html = "".join(
            [f'<span class="tag">{topic}</span>' for topic in topics]
        )
        
        # GitHub Pages URL Logic
        pages_url = f"https://{self.username}.github.io/{name}"

        return f"""
            <a href="{pages_url}" target="_blank" class="card">
                <h3>{name}</h3>
                <p>{description}</p>
                <div style="display: flex; flex-wrap: wrap; gap: 5px;">
                    {tags_html}
                </div>
            </a>
        """

    def render(self, template_content: str, repos: List[Dict]) -> str:
        """
        Injects the repository cards into the HTML template.
        """
        logging.info("Generating HTML cards...")
        cards_html = "\n".join([self._generate_card_html(repo) for repo in repos])
        
        try:
            output = template_content.format(
                USERNAME=self.username,
                projects_grid=cards_html
            )
            return output
        except KeyError as e:
            logging.error(f"Template formatting error. Missing key: {e}")
            sys.exit(1)

def main():
    import os
    
    # Configuration
    USERNAME = os.getenv("GITHUB_ACTOR")
    if not USERNAME:
        logging.error("GITHUB_ACTOR environment variable not found.")
        sys.exit(1)

    TOKEN = os.getenv("GITHUB_TOKEN")

    # Paths
    TEMPLATE_PATH = "template.html"
    OUTPUT_PATH = "index.html"

    # Execution
    generator = PortfolioGenerator(USERNAME, TOKEN)
    repos = generator.fetch_repos()
    
    try:
        with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
            template = f.read()
        
        final_html = generator.render(template, repos)
        
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            f.write(final_html)
            
        logging.info(f"Successfully generated {OUTPUT_PATH}")

    except FileNotFoundError:
        logging.error(f"Could not find {TEMPLATE_PATH}")
        sys.exit(1)

if __name__ == "__main__":
    main()
EOF

# 5. Create tests/test_generator.py
echo -e "${BLUE}[INFO] Writing tests/test_generator.py...${NC}"
cat << 'EOF' > tests/test_generator.py
import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Ensure we can import the source module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.portfolio_generator import PortfolioGenerator

class TestPortfolioGenerator(unittest.TestCase):

    def setUp(self):
        self.username = "testuser"
        self.generator = PortfolioGenerator(self.username)
        
        self.sample_template = """
        <html>
            <body>
                <h1>{USERNAME}</h1>
                <div class="grid">
{projects_grid}
                </div>
            </body>
        </html>
        """

    @patch('src.portfolio_generator.requests.get')
    def test_fetch_repos_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "name": "repo-with-pages",
                "has_pages": True,
                "description": "A test repo",
                "topics": ["python", "web"],
                "html_url": "https://github.com/testuser/repo-with-pages"
            }
        ]
        mock_get.return_value = mock_response

        repos = self.generator.fetch_repos()
        self.assertEqual(len(repos), 1)
        self.assertEqual(repos[0]['name'], "repo-with-pages")

    def test_generate_html_card(self):
        repo_data = {
            "name": "MyProject",
            "description": "A cool project",
            "html_url": "https://github.com/user/MyProject",
            "topics": ["ai", "ml"]
        }
        html = self.generator._generate_card_html(repo_data)
        self.assertIn("MyProject", html)
        self.assertIn("ai", html)

    def test_render_full_page(self):
        repos = [{
            "name": "Demo",
            "description": "Desc",
            "html_url": "http://url",
            "topics": []
        }]
        final_html = self.generator.render(template_content=self.sample_template, repos=repos)
        self.assertIn("Demo", final_html)
        self.assertIn("testuser", final_html)

if __name__ == '__main__':
    unittest.main()
EOF

# 6. Create template.html
# Note: CSS uses {{ }} to avoid conflict with Python .format()
echo -e "${BLUE}[INFO] Writing template.html...${NC}"
cat << 'EOF' > template.html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Alessandro Monticelli - Portfolio</title>
    <style>
        :root {{ --bg: #0d1117; --card-bg: #161b22; --text: #c9d1d9; --accent: #58a6ff; --border: #30363d; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; background: var(--bg); color: var(--text); padding: 40px 20px; margin: 0; line-height: 1.6; }}
        .container {{ max-width: 1000px; margin: 0 auto; }}
        .header {{ text-align: center; margin-bottom: 50px; }}
        .header h1 {{ margin-bottom: 10px; color: var(--accent); }}
        .header p {{ color: #8b949e; font-style: italic; }}
        section {{ margin-bottom: 60px; }}
        h2 {{ border-bottom: 1px solid var(--border); padding-bottom: 10px; margin-bottom: 30px; text-align: center; color: #fff; }}
        
        .stats-grid {{ display: flex; flex-direction: column; align-items: center; gap: 20px; }}
        .stats-grid img {{ width: 100%; max-width: 800px; height: auto; border-radius: 6px; }}
        
        .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }}
        .card {{ background: var(--card-bg); border: 1px solid var(--border); border-radius: 6px; padding: 20px; text-decoration: none; color: inherit; transition: border-color 0.3s, transform 0.2s; display: flex; flex-direction: column; }}
        .card:hover {{ border-color: var(--accent); transform: translateY(-2px); }}
        .card h3 {{ margin: 0 0 10px 0; color: var(--accent); }}
        .card p {{ font-size: 0.9em; color: #8b949e; margin-bottom: 15px; flex-grow: 1; }}
        .tag {{ font-size: 0.8em; background: #21262d; padding: 4px 8px; border-radius: 12px; border: 1px solid var(--border); align-self: flex-start; color: var(--accent); }}
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
                <img src="https://raw.githubusercontent.com/{USERNAME}/{USERNAME}/main/images/contribs.svg" alt="GitHub Contributions" />
                <img src="https://raw.githubusercontent.com/{USERNAME}/{USERNAME}/main/images/userstats.svg" alt="GitHub Statistics" />
            </div>
        </section>
        
        <section>
            <h2>My Projects</h2>
            <div class="grid">
{projects_grid}
            </div>
        </section>
    </div>
</body>
</html>
EOF

# 7. Create .github/workflows/update_portfolio.yml
echo -e "${BLUE}[INFO] Writing .github/workflows/update_portfolio.yml...${NC}"
cat << 'EOF' > .github/workflows/update_portfolio.yml
name: Update Portfolio

on:
  schedule:
    - cron: '0 0 * * *'
  workflow_dispatch:
  push:
    paths:
      - 'src/**'
      - 'template.html'
      - '.github/workflows/update_portfolio.yml'

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    
    permissions:
      contents: write

    steps:
      - name: Checkout Code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'

      - name: Install Dependencies
        run: |
          python -m pip install --upgrade pip
          pip install requests

      - name: Run Tests
        run: |
          python -m unittest discover tests

      - name: Generate Portfolio
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          GITHUB_ACTOR: ${{ github.repository_owner }}
        run: |
          python src/portfolio_generator.py

      - name: Commit and Push Changes
        uses: stefanzweifel/git-auto-commit-action@v5
        with:
          commit_message: "chore: update portfolio index.html [skip ci]"
          file_pattern: index.html
EOF

# 8. Create a placeholder .gitignore if it doesn't exist
if [ ! -f .gitignore ]; then
    echo -e "${BLUE}[INFO] Creating .gitignore...${NC}"
    echo "__pycache__/" > .gitignore
    echo "*.pyc" >> .gitignore
    echo ".DS_Store" >> .gitignore
fi

echo -e "${GREEN}[SUCCESS] Project structure initialized successfully!${NC}"
echo -e "You can now push this to GitHub to activate the Action."
echo -e "To test locally: python -m unittest discover tests"

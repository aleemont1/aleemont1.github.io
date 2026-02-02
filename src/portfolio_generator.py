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

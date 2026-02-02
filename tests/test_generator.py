import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Ensure we can import the source module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.portfolio_generator import PortfolioGenerator


class TestPortfolioGenerator(unittest.TestCase):

    def setUp(self):
        self.username = "aleemont1"
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

    @patch("src.portfolio_generator.requests.get")
    def test_fetch_repos_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "name": "repo-with-pages",
                "has_pages": True,
                "description": "A test repo",
                "topics": ["python", "web"],
                "html_url": "https://github.com/testuser/repo-with-pages",
            }
        ]
        mock_get.return_value = mock_response

        repos = self.generator.fetch_repos()
        self.assertEqual(len(repos), 1)
        self.assertEqual(repos[0]["name"], "repo-with-pages")

    def test_generate_html_card(self):
        repo_data = {
            "name": "MyProject",
            "description": "A cool project",
            "html_url": "https://github.com/user/MyProject",
            "topics": ["ai", "ml"],
        }
        html = self.generator._generate_card_html(repo_data)
        self.assertIn("MyProject", html)
        self.assertIn("ai", html)

    def test_render_full_page(self):
        repos = [
            {
                "name": "Demo",
                "description": "Desc",
                "html_url": "http://url",
                "topics": [],
            }
        ]
        final_html = self.generator.render(
            template_content=self.sample_template, repos=repos
        )
        self.assertIn("Demo", final_html)
        self.assertIn("testuser", final_html)


if __name__ == "__main__":
    unittest.main()

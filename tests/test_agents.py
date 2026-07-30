"""
Tests for analytics agents.
"""

from unittest.mock import MagicMock

import pytest

from snowflake_analytics_agents import (
    CorrectorAgent,
    DocumenterAgent,
    ReviewerAgent,
    WriterAgent,
)
from snowflake_analytics_agents.config import AgentConfig, Config, SnowflakeConfig


@pytest.fixture
def mock_config():
    """Create a mock configuration for testing."""
    snowflake_cfg = SnowflakeConfig(
        account="test_account",
        user="test_user",
        password="test_password",
        database="test_db",
        warehouse="test_wh",
    )
    agent_cfg = AgentConfig(timeout=60, max_retries=1, debug=True)
    return Config(snowflake=snowflake_cfg, agents=agent_cfg, extra={})


@pytest.fixture
def mock_client():
    """Create a mock Snowflake client."""
    mock = MagicMock()
    mock.test_connection.return_value = True
    mock.execute_query.return_value = [("test", 1)]
    return mock


class TestWriterAgent:
    """Tests for WriterAgent."""

    def test_init(self, mock_config, mock_client):
        """Test WriterAgent initialization."""
        agent = WriterAgent(mock_config, client=mock_client)
        assert agent.name == "WriterAgent"
        assert agent.config == mock_config

    def test_generate_sql_query(self, mock_config, mock_client):
        """Test SQL query generation."""
        agent = WriterAgent(mock_config, client=mock_client)
        code = agent.generate_query(description="Count users by region", query_type="sql")
        assert isinstance(code, str)
        assert "Generated query" in code

    def test_generate_python_code(self, mock_config, mock_client):
        """Test Python code generation."""
        agent = WriterAgent(mock_config, client=mock_client)
        code = agent.generate_query(description="Process daily revenue", query_type="python")
        assert isinstance(code, str)
        assert "Generated Python" in code

    def test_execute(self, mock_config, mock_client):
        """Test execute method."""
        agent = WriterAgent(mock_config, client=mock_client)
        result = agent.execute("Test query", query_type="sql")
        assert isinstance(result, str)


class TestReviewerAgent:
    """Tests for ReviewerAgent."""

    def test_init(self, mock_config, mock_client):
        """Test ReviewerAgent initialization."""
        agent = ReviewerAgent(mock_config, client=mock_client)
        assert agent.name == "ReviewerAgent"

    def test_review_code(self, mock_config, mock_client):
        """Test code review."""
        agent = ReviewerAgent(mock_config, client=mock_client)
        results = agent.review_code(code="SELECT * FROM users;", code_type="sql")
        assert isinstance(results, dict)
        assert "issues" in results
        assert "warnings" in results
        assert "suggestions" in results
        assert "score" in results

    def test_execute(self, mock_config, mock_client):
        """Test execute method."""
        agent = ReviewerAgent(mock_config, client=mock_client)
        result = agent.execute("SELECT 1;", code_type="sql")
        assert isinstance(result, dict)


class TestCorrectorAgent:
    """Tests for CorrectorAgent."""

    def test_init(self, mock_config, mock_client):
        """Test CorrectorAgent initialization."""
        agent = CorrectorAgent(mock_config, client=mock_client)
        assert agent.name == "CorrectorAgent"

    def test_fix_code(self, mock_config, mock_client):
        """Test code correction."""
        agent = CorrectorAgent(mock_config, client=mock_client)
        code = agent.fix_code(
            code="SELECT * FROM users",
            error_message="Syntax error: missing semicolon",
            code_type="sql",
        )
        assert isinstance(code, str)

    def test_execute(self, mock_config, mock_client):
        """Test execute method."""
        agent = CorrectorAgent(mock_config, client=mock_client)
        result = agent.execute("SELECT * FROM users;")
        assert isinstance(result, str)


class TestDocumenterAgent:
    """Tests for DocumenterAgent."""

    def test_init(self, mock_config, mock_client):
        """Test DocumenterAgent initialization."""
        agent = DocumenterAgent(mock_config, client=mock_client)
        assert agent.name == "DocumenterAgent"

    def test_generate_markdown_docs(self, mock_config, mock_client):
        """Test markdown documentation generation."""
        agent = DocumenterAgent(mock_config, client=mock_client)
        doc = agent.generate_documentation(
            code="SELECT COUNT(*) FROM users;", code_type="sql", format="markdown"
        )
        assert isinstance(doc, str)
        assert "Documentation" in doc or "TODO" in doc

    def test_generate_html_docs(self, mock_config, mock_client):
        """Test HTML documentation generation."""
        agent = DocumenterAgent(mock_config, client=mock_client)
        doc = agent.generate_documentation(
            code="SELECT * FROM orders;", code_type="sql", format="html"
        )
        assert isinstance(doc, str)

    def test_execute(self, mock_config, mock_client):
        """Test execute method."""
        agent = DocumenterAgent(mock_config, client=mock_client)
        result = agent.execute("SELECT 1;", code_type="sql", format="markdown")
        assert isinstance(result, str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

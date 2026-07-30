"""
Entry point for the snowflake-analytics-agents package.
Runs the CLI when the package is executed as a module: python -m snowflake_analytics_agents
"""

from .cli import main

if __name__ == "__main__":
    main()

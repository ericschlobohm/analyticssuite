from __future__ import annotations

import logging


def setup_logging(
    level: str = "INFO",
    log_file: str | None = None,
) -> logging.Logger:
    """
    Configure logging for the application.

    Args:
        level: Logging level ("DEBUG", "INFO", "WARNING", "ERROR")
        log_file: Optional file to write logs to

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger("snowflake_analytics_agents")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Console handler
    console_handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def parse_table_reference(table_ref: str) -> dict[str, str]:
    """
    Parse a Snowflake table reference into components.

    Supports formats:
    - "table"
    - "schema.table"
    - "database.schema.table"

    Args:
        table_ref: Table reference string

    Returns:
        Dict with 'database', 'schema', and 'table' keys
    """
    parts = table_ref.split(".")
    if len(parts) == 1:
        return {"table": parts[0], "schema": None, "database": None}
    elif len(parts) == 2:
        return {"table": parts[1], "schema": parts[0], "database": None}
    elif len(parts) == 3:
        return {"table": parts[2], "schema": parts[1], "database": parts[0]}
    else:
        raise ValueError(f"Invalid table reference: {table_ref}")


def format_table_reference(
    table: str,
    schema: str | None = None,
    database: str | None = None,
) -> str:
    """
    Format table reference components into a full reference.

    Args:
        table: Table name
        schema: Optional schema name
        database: Optional database name

    Returns:
        Formatted table reference
    """
    parts = []
    if database:
        parts.append(database)
    if schema:
        parts.append(schema)
    parts.append(table)
    return ".".join(parts)


def validate_sql(sql: str) -> bool:
    """
    Perform basic SQL validation (syntax check).

    Args:
        sql: SQL query string

    Returns:
        True if SQL appears valid, False otherwise
    """
    # Basic validation - check for common issues
    sql = sql.strip()
    if not sql:
        return False

    # Check for SQL keywords
    keywords = ["SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "ALTER"]
    return any(sql.upper().startswith(kw) for kw in keywords)


def truncate_string(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate a string to a maximum length.

    Args:
        text: Text to truncate
        max_length: Maximum length (excluding suffix)
        suffix: Suffix to add if truncated

    Returns:
        Truncated string
    """
    if len(text) <= max_length:
        return text
    return text[:max_length] + suffix


def format_results(
    results: list[tuple],
    columns: list[str] | None = None,
    max_rows: int = 10,
) -> str:
    """
    Format query results as a readable string.

    Args:
        results: List of result tuples
        columns: Optional list of column names
        max_rows: Maximum number of rows to display

    Returns:
        Formatted results string
    """
    if not results:
        return "No results"

    lines = []

    # Add header
    if columns:
        lines.append(" | ".join(columns))
        lines.append("-" * 50)

    # Add rows
    for i, row in enumerate(results[:max_rows]):
        lines.append(" | ".join(str(v) if v is not None else "NULL" for v in row))

    # Add truncation message if needed
    if len(results) > max_rows:
        lines.append(f"... ({len(results) - max_rows} more rows)")

    return "\n".join(lines)

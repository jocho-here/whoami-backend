from typing import List

from databases import Database

from whoami_back.utils.config import DB_DSN

database = Database(str(DB_DSN))


def to_where_clause(conditions: List) -> str:
    """
    ["cond1", "cond2", "cond3"] -> "cond1 AND cond2 AND cond3"
    """
    return " AND ".join(conditions)


def to_csv(columns) -> str:
    """
    ["key1", "key2", "key3"] -> "key1, key2, key3"
    """
    return ", ".join(columns)


def to_ref_csv(columns) -> str:
    """
    ["key1", "key2", "key3"] -> ":key1, :key2, :key3"
    """
    return ", ".join([f":{column}" for column in columns])


def to_set_statement(columns, *, update_update_at: bool = True) -> str:
    """
    ["key1", "key2", "key3"] -> "key1 = :key1, key2 = :key2, key3 = :key3"
    """
    set_columns = [f"{column} = :{column}" for column in columns]
    set_columns.append("updated_at = NOW()")

    return ", ".join(set_columns)

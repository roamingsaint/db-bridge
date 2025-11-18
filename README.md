# db-bridge

A minimal, flexible Python SQL connector for MySQL, SQLite, and PostgreSQL—just pass native SQL queries as strings, with optional INI profile configuration.

---

## Table of Contents

1. [Installation](#installation)  
2. [Quick Start](#quick-start)  
3. [Configuration](#configuration)  
   - [Custom Config Override](#custom-config-override)  
   - [INI Profiles (`~/.db_bridge.cfg`)](#ini-profiles-db_bridgecfg)  
4. [Usage Examples](#usage-examples)  
   - [Simple Queries](#simple-queries)  
   - [Parameterized Queries (Safe)](#parameterized-queries-safe)  
   - [Multiple Profiles](#multiple-profiles)  
   - [Handling NULL values](#handling-null-values)  
   - [Advanced Helpers](#advanced-helpers)  
5. [Testing](#testing)  
6. [Contributing](#contributing)  
7. [License](#license)

---

## Installation

Install from PyPI:

```bash
pip install db-bridge
```

For colorful output (needs `colorfulPyPrint`):

```bash
pip install db-bridge[color]
```

For local development:

```bash
git clone https://github.com/YourUsername/db-bridge.git
cd db-bridge
pip install -e .
```

---

## Quick Start

```python
from db_bridge.db_utils import run_sql
from db_bridge.config   import load_config

# Inspect your default config (INI default)
print(load_config())

# Simple SELECT (uses default profile)
rows = run_sql("SELECT id, name FROM users")
for row in rows:
    print(row)

# INSERT example
new_id = run_sql(
    "INSERT INTO users (name,email) VALUES (%s,%s)",
    params=("Alice","alice@example.com"),
)
print(f"Inserted row ID: {new_id}")
```

---

## Configuration

### Custom Config Override

If you ever need to point at a different INI file (for CI, Docker, or testing), set:

```bash
export DB_BRIDGE_CONFIG=/path/to/alternate_db_bridge.cfg
```

That file will be used **only if it exists**; otherwise `~/.db_bridge.cfg` is loaded as usual.

---

### INI Profiles (`~/.db_bridge.cfg`)

For multiple databases (MySQL, SQLite, PostgreSQL, or multiple instances of any), define profiles in:

```ini
[DEFAULT]
active = dev_db

[dev_db]
driver   = mysql
host     = localhost
port     = 3306
database = mydb_dev
user     = devuser
password = devpass

[prod_db]
driver   = mysql
host     = prod.db.example.com
port     = 3306
database = mydb_prod
user     = produser
password = prodpass

[sqlite_local]
driver   = sqlite
database = /full/path/to/local.db

[postgres_analytics]
driver   = postgres
host     = pg.example.com
port     = 5432
database = analytics
user     = pguser
password = pgpass
```

- **Default** profile is the one named by `[DEFAULT] active`.  
- Callers can override at runtime with the `profile` parameter (see below).  

---

## Usage Examples

### Simple Queries

```python
# returns list of dicts by default
users = run_sql("SELECT id, username FROM users")
# as tuples
users_tuples = run_sql("SELECT id, username FROM users", as_dict=False)
```

### Parameterized Queries (Safe)

```python
# Always prefer parameterized queries to avoid SQL injection
email = "bob@example.com"
rows = run_sql(
    "SELECT id,name FROM users WHERE email = %s",
    params=(email,),
)
```

### Multiple Profiles

Use the default profile:

```python
run_sql("SELECT * FROM my_table")
```

Explicitly target another INI profile:

```python
# MySQL production
run_sql("SELECT * FROM orders", profile="prod_db")

# SQLite local
run_sql("SELECT * FROM items", profile="sqlite_local")

# PostgreSQL analytics
run_sql("SELECT count(*) FROM events", profile="postgres_analytics")
```

Or supply a custom creds dict directly:

```python
creds = {"driver":"sqlite","database":"/tmp/test.db"}
run_sql("SELECT * FROM foo", db_creds=creds)
```

### Handling NULL values

When you pass raw SQL without parameters, you can convert Python `None` → SQL `NULL`:

```python
# None in SQL literal becomes NULL
rows = run_sql(
    "SELECT * FROM orders WHERE shipped_date = None",
    none_to_null=True
)
```

### Advanced Helpers

```python
from db_bridge.db_utils import get_column_values, get_column_values_regexp

# Fetch single or multiple columns, prompt if multiple matches
val = get_column_values(
    "email", "status",
    table_name="users",
    unique_column_name="username",
    unique_column_value="alice",
    primary_key="id",
    as_tuple=False,
    error_if_missing=True
)
print(val)

# Fetch rows matching a regex pattern
matches = get_column_values_regexp(
    "id", "username",
    table_name="users",
    unique_column_name="username",
    unique_column_regexp="^a.*"
)
for m in matches:
    print(m)
```

---

## Testing

Run the test suite with pytest:

```bash
pytest tests/
```

---

## Contributing

Contributions welcome! Please open issues or pull requests.  
Follow existing style and add tests for new features.

---

## License

MIT License © 2025 Kanad Rishiraj (RoamingSaint)

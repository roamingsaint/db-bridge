# db-bridge

![PyPI Version](https://img.shields.io/pypi/v/db-bridge.svg)
![License](https://img.shields.io/pypi/l/db-bridge.svg)

A minimal, flexible Python SQL connector for MySQL—just pass native SQL queries as strings, with optional 12‑factor env or INI profile configuration.

---

## Table of Contents

1. [Installation](#installation)  
2. [Quick Start](#quick-start)  
3. [Configuration](#configuration)  
   - [Environment Variables (`.env`)](#environment-variables-env)  
   - [INI Profile (`~/.dbbridge.cfg`)](#ini-profile-~dbbridgecfg)  
4. [Usage Examples](#usage-examples)  
   - [Simple Queries](#simple-queries)  
   - [Parameterized Queries (Safe)](#parameterized-queries-safe)  
   - [Handling NULL values](#handling-null-values)  
   - [Advanced Helpers](#advanced-helpers)  
5. [Testing](#testing)  
6. [Contributing](#contributing)  
7. [License](#license)

---

## Installation

Install the latest release from PyPI:

```bash
pip install db-bridge
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
from db_bridge import run_sql, load_config

# Optionally inspect loaded config
print(load_config())

# Execute a simple SELECT
rows = run_sql("SELECT id, name FROM users")
for row in rows:
    print(row)

# Execute an INSERT
new_id = run_sql("INSERT INTO users (name,email) VALUES ('Alice','alice@example.com')")
print(f"Inserted row ID: {new_id}")
```

---

## Configuration

### Environment Variables (`.env`)

Create a file named `.env` in your project root:

```dotenv
DB_HOST=localhost
DB_PORT=3306
DB_NAME=mydb
DB_USER=myuser
DB_PASS=mypassword
# Optional: switch profile when multiple in INI
# DBBRIDGE_PROFILE=prod
```

The package will load `.env` automatically if `python-dotenv` is installed.

---

### INI Profile (`~/.dbbridge.cfg`)

For multiple database profiles, create `~/.dbridge.cfg`:

```ini
[DEFAULT]
active = dev

[dev]
host = localhost
port = 3306
name = mydb_dev
user = devuser
password = devpass

[prod]
host = prod.db.example.com
port = 3306
name = mydb_prod
user = produser
password = prodpass
```

Switch profiles via:

```bash
export DBBRIDGE_PROFILE=prod
```

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

### Handling NULL values

When calling raw SQL without params, you can enable automatic `None`→`NULL` cleanup:

```python
# passing Python None in SQL literal, none_to_null=True will convert to NULL
rows = run_sql("SELECT * FROM orders WHERE shipped_date = None", none_to_null=True)
```

### Advanced Helpers

```python
from db_bridge.db_utils import get_column_values, get_column_values_regexp

# Fetch single or multiple columns, prompt if multiple matches
val = get_column_values(
    "email","status",
    table_name="users",
    unique_column_name="username",
    unique_column_value="alice",
    primary_key="id",
    as_tuple=False
)
print(val)

# Fetch rows matching a regex pattern
matches = get_column_values_regexp(
    "id","username",
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
Make sure to follow the existing style and add tests for new features.

---

## License

MIT License © 2025 Kanad Rishiraj (RoamingSaint)

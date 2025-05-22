# DBbridge

**Effortless MySQL connectivity in Python, with flexible configuration via environment variables or INI profiles.**

DBbridge is a lightweight Python library that provides:
- **Zero boilerplate:** Run SQL queries with a single function call.
- **12-factor config:** First-class support for environment variables (.env) and optional INI fallback (~/.dbbridge.cfg).
- **Multi-profile:** Store multiple database connections in one config and switch via an environment variable.
- **Extensible:** Easily add support for other databases in the future.

## Installation

```bash
pip install dbbridge
```

## Quickstart

1. **Configure**  
   - **Env vars:** Create a `.env` in your project root:

     ```env
     DB_HOST=localhost
     DB_NAME=mydb
     DB_USER=myuser
     DB_PASS=mypassword
     ```

   - **INI file:** Or edit `~/.dbbridge.cfg`:

     ```ini
     [DEFAULT]
     active = mysql

     [mysql]
     host = localhost
     port = 3306
     name = mydb
     user = myuser
     password = mypassword
     ```

2. **Use in your Python code**:

    ```python
    from dbbridge import run_sql

    rows = run_sql("SELECT * FROM users")
    for row in rows:
        print(row)
    ```

## Configuration

- **Environment variables:** `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASS`, optional `DB_PORT`.
- **INI profiles:** `~/.dbbridge.cfg` with `[DEFAULT] active = profile` and sections for each DB.

## Contributing

Contributions are welcome! Please open issues or pull requests on GitHub.

## License

This project is licensed under the MIT License.

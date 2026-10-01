# AGENTS.md

## Language

- Code comments, docstrings, identifiers, log messages and exception messages are written in English.
- Commit messages, pull request titles and descriptions are written in English.
- The bot talks to the user in Russian. All user-facing copy lives in `src/me_hub/bot/texts.py`;
  no other source file may contain Cyrillic (ruff `RUF001` is disabled only for `texts.py` and tests).

## Checks

Run before every commit:

```bash
uv run ruff format && uv run ruff check && uv run mypy && uv run pytest
```

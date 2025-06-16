# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Docker Development Environment
- `docker compose up -d` - Start development environment (LNbits on port 5002)
- `docker compose logs -f` - View container logs
- `docker compose down` - Stop development environment
- `docker compose exec lnurlp-lnbits-dev bash` - Access container shell

### Code Quality
- `make format` - Format all code (Python with black/ruff, JS with prettier)
- `make check` - Run all checks (mypy, pyright, linting)
- `make test` - Run pytest tests
- `make pre-commit` - Run pre-commit hooks

### Individual Tools
- `poetry run black .` - Format Python code
- `poetry run ruff check . --fix` - Lint Python with fixes
- `poetry run mypy .` - Type check Python
- `poetry run pyright` - Additional type checking
- `poetry run pytest` - Run tests

## Architecture Overview

LNURLp is an LNbits extension for creating static Lightning payment links. Key architectural points:

### Backend Structure
- **models.py**: Pydantic models define PayLink, CreatePayLinkData, and settings schemas
- **crud.py**: Database operations using LNbits' abstraction layer
- **views_lnurl.py**: LNURL protocol endpoints handle payment flow
- **views_api.py**: REST API for link management
- **tasks.py**: Background payment processing with webhook support
- **nostr/**: Nostr zaps integration module

### Frontend
- **static/js/index.js**: Vue.js 3 + Quasar UI application
- Templates use Jinja2 with LNbits base templates

### Key Flows
1. Payment links store configuration in database with unique IDs
2. LNURL endpoints generate invoices dynamically based on link settings
3. Webhooks notify external services of payments
4. Nostr integration enables zaps through NIP-57 events

### Database Schema
Pay links table includes: wallet, description, amount settings, currency, webhooks, success messages, and Nostr metadata. Uses LNbits migration system.

## Extension Integration

This follows LNbits extension patterns:
- Registered via __init__.py blueprint
- Uses LNbits database, wallet, and settings abstractions
- Integrates with LNbits authentication and UI framework
- Supports multi-wallet functionality
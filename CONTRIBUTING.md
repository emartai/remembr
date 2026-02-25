# Contributing to Remembr

Thank you for your interest in contributing to Remembr! This document provides guidelines and instructions for contributing.

---

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Getting Started](#getting-started)
3. [Development Setup](#development-setup)
4. [Making Changes](#making-changes)
5. [Testing](#testing)
6. [Submitting Changes](#submitting-changes)
7. [Code Style](#code-style)
8. [Documentation](#documentation)
9. [Community](#community)

---

## Code of Conduct

### Our Pledge

We are committed to providing a welcoming and inclusive environment for all contributors, regardless of experience level, gender, gender identity and expression, sexual orientation, disability, personal appearance, body size, race, ethnicity, age, religion, or nationality.

### Our Standards

**Positive behaviors:**
- Using welcoming and inclusive language
- Being respectful of differing viewpoints
- Gracefully accepting constructive criticism
- Focusing on what is best for the community
- Showing empathy towards other community members

**Unacceptable behaviors:**
- Trolling, insulting/derogatory comments, and personal attacks
- Public or private harassment
- Publishing others' private information without permission
- Other conduct which could reasonably be considered inappropriate

---

## Getting Started

### Ways to Contribute

- **Report bugs** - Found a bug? Open an issue
- **Suggest features** - Have an idea? Start a discussion
- **Fix issues** - Pick an issue and submit a PR
- **Improve docs** - Documentation can always be better
- **Write tests** - Help us improve test coverage
- **Create adapters** - Add support for new AI frameworks

### Before You Start

1. **Check existing issues** - Someone might already be working on it
2. **Open an issue first** - For major changes, discuss the approach
3. **Read the docs** - Familiarize yourself with the architecture
4. **Set up your environment** - Follow the development setup guide

---

## Development Setup

### Prerequisites

- **Python 3.11+**
- **Node.js 18+** (for TypeScript SDK)
- **PostgreSQL 15+** with pgvector extension
- **Redis 7+**
- **Git**

### Clone the Repository

```bash
git clone https://github.com/emartai/remembr.git
cd remembr
```

### Set Up Python Environment

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r server/requirements.txt
pip install -e sdk/python

# Install development dependencies
pip install pytest pytest-asyncio pytest-cov black ruff mypy
```

### Set Up Database

```bash
# Start PostgreSQL and Redis with Docker
docker-compose up -d postgres redis

# Run migrations
cd server
alembic upgrade head
```

### Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your settings
# Required:
# - DATABASE_URL
# - REDIS_URL
# - JWT_SECRET
# - JINA_API_KEY (for embeddings)
```

### Start Development Server

```bash
cd server
uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`

### Verify Setup

```bash
# Run health check
curl http://localhost:8000/api/v1/health

# Run tests
pytest tests/ -v
```

---

## Making Changes

### Branching Strategy

We use **Git Flow** branching model:

- `main` - Production-ready code
- `develop` - Integration branch for features
- `feature/*` - New features
- `bugfix/*` - Bug fixes
- `hotfix/*` - Urgent production fixes

### Creating a Feature Branch

```bash
# Update develop branch
git checkout develop
git pull origin develop

# Create feature branch
git checkout -b feature/your-feature-name

# Make your changes
# ...

# Commit your changes
git add .
git commit -m "feat: add your feature description"

# Push to your fork
git push origin feature/your-feature-name
```

### Commit Message Convention

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation changes
- `style` - Code style changes (formatting, etc.)
- `refactor` - Code refactoring
- `test` - Adding or updating tests
- `chore` - Maintenance tasks

**Examples:**
```bash
feat(adapters): add support for Haystack framework
fix(auth): resolve JWT token expiration issue
docs(api): update search endpoint documentation
test(memory): add integration tests for hybrid search
```

---

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_memory_api.py

# Run with coverage
pytest --cov=app --cov-report=html

# Run end-to-end tests
pytest tests/e2e/ -v

# Run adapter tests
python test_8_adapters_final.py
```

### Writing Tests

**Unit Test Example:**
```python
import pytest
from app.services.memory_service import MemoryService

@pytest.mark.asyncio
async def test_store_memory(memory_service, test_session):
    """Test storing a memory episode"""
    result = await memory_service.store(
        session_id=test_session.id,
        content="Test memory",
        role="user"
    )
    
    assert result.episode_id is not None
    assert result.token_count > 0
```

**Integration Test Example:**
```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_memory_api(client: AsyncClient, auth_headers):
    """Test memory API endpoint"""
    response = await client.post(
        "/api/v1/memory",
        json={
            "content": "Test memory",
            "role": "user",
            "session_id": "test-session-id"
        },
        headers=auth_headers
    )
    
    assert response.status_code == 201
    assert "episode_id" in response.json()["data"]
```

### Test Coverage Goals

- **Unit tests**: > 80% coverage
- **Integration tests**: All API endpoints
- **E2E tests**: Critical user flows
- **Adapter tests**: All 8 framework adapters

---

## Submitting Changes

### Pull Request Process

1. **Update your branch**
   ```bash
   git checkout develop
   git pull origin develop
   git checkout feature/your-feature
   git rebase develop
   ```

2. **Run tests and linting**
   ```bash
   pytest
   black .
   ruff check .
   mypy app/
   ```

3. **Push your changes**
   ```bash
   git push origin feature/your-feature
   ```

4. **Create Pull Request**
   - Go to GitHub and create a PR from your branch to `develop`
   - Fill out the PR template
   - Link related issues
   - Request review from maintainers

### Pull Request Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] All tests passing
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No new warnings
- [ ] Tests added for new functionality

## Related Issues
Closes #123
```

### Review Process

1. **Automated checks** - CI/CD runs tests and linting
2. **Code review** - Maintainer reviews code
3. **Feedback** - Address review comments
4. **Approval** - Maintainer approves PR
5. **Merge** - PR merged to develop

---

## Code Style

### Python Style Guide

We follow **PEP 8** with some modifications:

```python
# Use Black for formatting
black .

# Use Ruff for linting
ruff check .

# Use mypy for type checking
mypy app/
```

**Key conventions:**
- Line length: 100 characters
- Use type hints for function signatures
- Use docstrings for public functions
- Use f-strings for string formatting
- Use async/await for I/O operations

**Example:**
```python
from typing import Optional
from uuid import UUID

async def get_session(
    session_id: UUID,
    user_id: UUID,
    include_messages: bool = False
) -> Optional[Session]:
    """
    Retrieve a session by ID.
    
    Args:
        session_id: The session UUID
        user_id: The user UUID for authorization
        include_messages: Whether to include messages
        
    Returns:
        Session object if found, None otherwise
        
    Raises:
        UnauthorizedError: If user doesn't own session
    """
    # Implementation
    pass
```

### TypeScript Style Guide

```typescript
// Use Prettier for formatting
npm run format

// Use ESLint for linting
npm run lint
```

**Key conventions:**
- Use TypeScript strict mode
- Use interfaces for object shapes
- Use async/await for promises
- Use const for immutable values
- Use descriptive variable names

---

## Documentation

### Documentation Standards

- **Code comments** - Explain why, not what
- **Docstrings** - All public functions and classes
- **API docs** - Update OpenAPI spec for API changes
- **User docs** - Update markdown docs in `docs/`
- **Architecture docs** - Update ARCHITECTURE.md for major changes

### Documentation Structure

```
docs/
├── quickstart.md          # Getting started guide
├── api-reference.md       # Complete API documentation
├── concepts.md            # Core concepts and architecture
├── security.md            # Security and compliance
├── self-hosted.md         # Self-hosting guide
└── adapters/              # Framework adapter guides
    ├── langchain.md
    ├── langgraph.md
    └── ...
```

### Writing Documentation

**Good documentation:**
- Clear and concise
- Includes code examples
- Explains the "why" not just the "how"
- Uses proper formatting (headers, lists, code blocks)
- Includes diagrams where helpful

**Example:**
```markdown
## Hybrid Search

Remembr uses hybrid search to combine semantic and symbolic retrieval:

1. **Semantic search** - Uses Jina embeddings for similarity
2. **Metadata filtering** - Filters by session, role, tags, time
3. **Ranking** - Combines scores for final results

### Example

\`\`\`python
results = await client.search(
    query="What are user preferences?",
    session_id="session-123",
    tags=["preference"],
    limit=10
)
\`\`\`

This searches for semantically similar memories tagged with "preference" in session-123.
```

---

## Community

### Getting Help

- **GitHub Issues** - Report bugs or request features
- **GitHub Discussions** - Ask questions or share ideas
- **Email** - [nwangumaemmanuel29@gmail.com](mailto:nwangumaemmanuel29@gmail.com)

### Reporting Bugs

**Good bug reports include:**
1. **Description** - What happened vs what you expected
2. **Steps to reproduce** - Minimal steps to reproduce the issue
3. **Environment** - OS, Python version, dependencies
4. **Logs** - Relevant error messages or stack traces
5. **Screenshots** - If applicable

**Bug report template:**
```markdown
## Description
Brief description of the bug

## Steps to Reproduce
1. Step 1
2. Step 2
3. Step 3

## Expected Behavior
What should happen

## Actual Behavior
What actually happened

## Environment
- OS: Windows 11
- Python: 3.11.5
- Remembr: 1.0.0

## Logs
```
Error logs here
```

## Additional Context
Any other relevant information
```

### Suggesting Features

**Good feature requests include:**
1. **Problem statement** - What problem does this solve?
2. **Proposed solution** - How should it work?
3. **Alternatives** - What other solutions did you consider?
4. **Use cases** - Real-world examples

---

## Recognition

Contributors will be recognized in:
- **CHANGELOG.md** - Listed in release notes
- **README.md** - Added to contributors section
- **GitHub** - Contributor badge on profile

---

## License

By contributing to Remembr, you agree that your contributions will be licensed under the MIT License.

---

## Questions?

If you have questions about contributing, feel free to:
- Open a GitHub Discussion
- Email [nwangumaemmanuel29@gmail.com](mailto:nwangumaemmanuel29@gmail.com)
- Check existing issues and PRs

Thank you for contributing to Remembr! 🎉

---

**Last Updated**: February 25, 2026  
**Maintainer**: [Emmanuel Nwanguma](https://linkedin.com/in/nwangumaemmanuel)

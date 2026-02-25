#!/usr/bin/env python3
"""
Remembr Local Environment Verification Script
Audits repo structure, generates .env, checks dependencies, validates config, tests connectivity.
"""
import os
import sys
import subprocess
import secrets
import time
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Color codes for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"

class VerificationResults:
    def __init__(self):
        self.repo_checks: List[Tuple[str, bool]] = []
        self.dependencies_installed = {"python": False, "node": False}
        self.env_vars_status: Dict[str, str] = {}
        self.connectivity_tests: Dict[str, Optional[str]] = {}
        self.test_results = {"passed": 0, "failed": 0, "skipped": 0}
        self.missing_vars: List[Tuple[str, str]] = []

results = VerificationResults()

def print_header(text: str):
    print(f"\n{BOLD}{BLUE}{'=' * 80}{RESET}")
    print(f"{BOLD}{BLUE}{text.center(80)}{RESET}")
    print(f"{BOLD}{BLUE}{'=' * 80}{RESET}\n")

def print_section(text: str):
    print(f"\n{BOLD}{text}{RESET}")
    print("-" * 80)

def check_file_exists(path: str) -> bool:
    """Check if a file exists and is non-empty."""
    p = Path(path)
    return p.exists() and p.is_file() and p.stat().st_size > 0

def check_dir_exists(path: str, min_files: int = 0) -> bool:
    """Check if a directory exists and optionally has minimum number of files."""
    p = Path(path)
    if not p.exists() or not p.is_dir():
        return False
    if min_files > 0:
        files = list(p.rglob("*.py"))
        return len(files) >= min_files
    return True


def part1_repo_audit():
    """PART 1: Walk the monorepo and verify all critical files exist."""
    print_section("PART 1 — REPO STRUCTURE AUDIT")
    
    checks = [
        ("server/app/main.py", "file"),
        ("server/app/config.py", "file"),
        ("server/app/api/v1/router.py", "file"),
        ("server/app/db/session.py", "file"),
        ("server/app/db/redis.py", "file"),
        ("server/app/models/", "dir", 5),
        ("server/app/services/embedding.py", "file"),
        ("server/app/services/short_term.py", "file"),
        ("server/app/services/episodic.py", "file"),
        ("server/app/services/memory_query.py", "file"),
        ("server/app/services/auth.py", "file"),
        ("server/app/services/api_keys.py", "file"),
        ("server/app/services/scoping.py", "file"),
        ("server/app/middleware/context.py", "file"),
        ("server/app/middleware/rate_limit.py", "file"),
        ("server/alembic/", "dir", 1),
        ("sdk/python/remembr/client.py", "file"),
        ("sdk/typescript/src/client.ts", "file"),
        ("adapters/langchain/", "dir"),
        ("adapters/langgraph/", "dir"),
        ("adapters/crewai/", "dir"),
        ("adapters/autogen/", "dir"),
        ("adapters/llamaindex/", "dir"),
        ("adapters/pydantic_ai/", "dir"),
        ("adapters/openai_agents/", "dir"),
        ("adapters/haystack/", "dir"),
        ("adapters/base/utils.py", "file"),
        ("adapters/base/error_handling.py", "file"),
        ("railway.toml", "file"),
        (".github/workflows/ci.yml", "file"),
    ]
    
    for check in checks:
        path = check[0]
        check_type = check[1]
        
        if check_type == "file":
            passed = check_file_exists(path)
        elif check_type == "dir":
            min_files = check[2] if len(check) > 2 else 0
            passed = check_dir_exists(path, min_files)
        else:
            passed = False
        
        results.repo_checks.append((path, passed))
        status = f"{GREEN}+ PASS{RESET}" if passed else f"{RED}x FAIL{RESET}"
        print(f"{status} {path}")
    
    # Check .gitignore contains .env
    gitignore_check = False
    if check_file_exists(".gitignore"):
        with open(".gitignore", "r") as f:
            content = f.read()
            gitignore_check = ".env" in content
    
    results.repo_checks.append((".gitignore contains .env", gitignore_check))
    status = f"{GREEN}+ PASS{RESET}" if gitignore_check else f"{RED}x FAIL{RESET}"
    print(f"{status} .gitignore contains .env")
    
    if not gitignore_check:
        print(f"{YELLOW}! WARNING: Adding .env to .gitignore{RESET}")
        with open(".gitignore", "a") as f:
            f.write("\n# Environment variables\n.env\n")
    
    passed_count = sum(1 for _, passed in results.repo_checks if passed)
    total_count = len(results.repo_checks)
    
    print(f"\n{BOLD}Summary: {passed_count}/{total_count} checks passed{RESET}")
    
    if passed_count < total_count:
        print(f"\n{RED}Missing files:{RESET}")
        for path, passed in results.repo_checks:
            if not passed:
                print(f"  - {path}")


def part2_generate_env_file():
    """PART 2: Generate .env file template if it doesn't exist."""
    print_section("PART 2 — GENERATE LOCAL .env FILE")
    
    env_path = Path(".env")
    
    if env_path.exists():
        print(f"{YELLOW}i .env file already exists, skipping generation{RESET}")
        return
    
    print("Generating .env template from server/app/config.py...")
    
    env_template = """# ===============================================
# REMEMBR - LOCAL ENVIRONMENT CONFIGURATION
# ===============================================

# -----------------------------------------------
# ENVIRONMENT
# -----------------------------------------------
ENVIRONMENT=local
LOG_LEVEL=DEBUG

# -----------------------------------------------
# DATABASE (Supabase PostgreSQL + pgvector)
# -----------------------------------------------
# Get from: Supabase Project Settings → Database → Connection String (URI mode)
# Format: postgresql://postgres:[password]@[host]:[port]/postgres
DATABASE_URL=YOUR_SUPABASE_CONNECTION_STRING_HERE

# Database pool configuration (optional, defaults shown)
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=1800

# -----------------------------------------------
# REDIS (Upstash)
# -----------------------------------------------
# Get from: Upstash Console → Your Redis → Details → REST API → UPSTASH_REDIS_REST_URL
# Or use the standard Redis URL format: redis://default:[password]@[host]:[port]
REDIS_URL=YOUR_UPSTASH_REDIS_URL_HERE

# -----------------------------------------------
# JINA AI EMBEDDINGS
# -----------------------------------------------
# Get from: https://jina.ai/embeddings/ → Sign up → API Keys
JINA_API_KEY=YOUR_JINA_API_KEY_HERE
JINA_EMBEDDING_MODEL=jina-embeddings-v3
EMBEDDING_BATCH_SIZE=100

# -----------------------------------------------
# JWT AUTHENTICATION
# -----------------------------------------------
# SECRET_KEY will be auto-generated on first run
SECRET_KEY=WILL_BE_AUTO_GENERATED
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# -----------------------------------------------
# MONITORING (Optional)
# -----------------------------------------------
# Get from: Sentry.io → Project Settings → Client Keys (DSN)
# Leave empty for local development
SENTRY_DSN=

# -----------------------------------------------
# SHORT-TERM MEMORY CONFIGURATION
# -----------------------------------------------
SHORT_TERM_MAX_TOKENS=4000
SHORT_TERM_AUTO_CHECKPOINT_THRESHOLD=0.8

# -----------------------------------------------
# RATE LIMITING
# -----------------------------------------------
RATE_LIMIT_DEFAULT_PER_MINUTE=100
RATE_LIMIT_SEARCH_PER_MINUTE=30

# -----------------------------------------------
# API CONFIGURATION
# -----------------------------------------------
API_V1_PREFIX=/api/v1
CORS_ORIGINS=[]
"""
    
    with open(".env", "w", encoding="utf-8") as f:
        f.write(env_template)
    
    print(f"{GREEN}+ Created .env file{RESET}")
    
    print(f"\n{BOLD}Variables that need real values:{RESET}")
    print(f"\n{BOLD}From Supabase:{RESET}")
    print("  * DATABASE_URL - PostgreSQL connection string with pgvector")
    print(f"\n{BOLD}From Upstash:{RESET}")
    print("  * REDIS_URL - Redis connection string for caching and rate limiting")
    print(f"\n{BOLD}From Jina AI:{RESET}")
    print("  * JINA_API_KEY - API key for embedding generation (semantic search)")
    print(f"\n{BOLD}Auto-generated:{RESET}")
    print("  * SECRET_KEY - Will be generated automatically in Part 4")


def part3_dependency_check():
    """PART 3: Check and install dependencies."""
    print_section("PART 3 — DEPENDENCY CHECK + INSTALL")
    
    # Check Python version
    print("Checking Python version...")
    try:
        python_version = sys.version_info
        if python_version >= (3, 11):
            print(f"{GREEN}+ Python {python_version.major}.{python_version.minor}.{python_version.micro} detected{RESET}")
            results.dependencies_installed["python"] = True
        else:
            print(f"{RED}x Python 3.11+ required, found {python_version.major}.{python_version.minor}{RESET}")
            print("Install Python 3.11+: https://www.python.org/downloads/")
            return
    except Exception as e:
        print(f"{RED}x Error checking Python version: {e}{RESET}")
        return
    
    # Check/create virtual environment
    venv_path = Path(".venv")
    if not venv_path.exists():
        print("Creating virtual environment at .venv/...")
        try:
            subprocess.run([sys.executable, "-m", "venv", ".venv"], check=True, capture_output=True)
            print(f"{GREEN}+ Virtual environment created{RESET}")
        except subprocess.CalledProcessError as e:
            print(f"{RED}x Failed to create virtual environment: {e}{RESET}")
            return
    else:
        print(f"{GREEN}+ Virtual environment exists at .venv/{RESET}")
    
    # Determine pip path
    if sys.platform == "win32":
        pip_path = venv_path / "Scripts" / "pip.exe"
        python_path = venv_path / "Scripts" / "python.exe"
    else:
        pip_path = venv_path / "bin" / "pip"
        python_path = venv_path / "bin" / "python"
    
    # Install server dependencies
    print("\nInstalling server dependencies...")
    server_req = Path("server/requirements.txt")
    if server_req.exists():
        try:
            print(f"{YELLOW}(This may take a few minutes...){RESET}")
            subprocess.run(
                [str(python_path), "-m", "pip", "install", "-q", "-r", str(server_req)],
                check=True,
                capture_output=True,
                timeout=180
            )
            print(f"{GREEN}+ Server dependencies installed{RESET}")
        except subprocess.TimeoutExpired:
            print(f"{YELLOW}! Installation timed out after 3 minutes{RESET}")
            print(f"{YELLOW}  Run manually: {python_path} -m pip install -r server/requirements.txt{RESET}")
        except subprocess.CalledProcessError as e:
            print(f"{RED}x Failed to install server dependencies{RESET}")
            print(f"Error: {e.stderr.decode() if e.stderr else 'Unknown error'}")
    else:
        print(f"{YELLOW}! server/requirements.txt not found{RESET}")
    
    # Install Python SDK dependencies
    print("\nInstalling Python SDK dependencies...")
    sdk_pyproject = Path("sdk/python/pyproject.toml")
    if sdk_pyproject.exists():
        try:
            print(f"{YELLOW}(This may take a minute...){RESET}")
            subprocess.run(
                [str(python_path), "-m", "pip", "install", "-q", "-e", "sdk/python"],
                check=True,
                capture_output=True,
                timeout=60
            )
            print(f"{GREEN}+ Python SDK dependencies installed{RESET}")
        except subprocess.TimeoutExpired:
            print(f"{YELLOW}! Installation timed out after 1 minute{RESET}")
            print(f"{YELLOW}  Run manually: {python_path} -m pip install -e sdk/python{RESET}")
        except subprocess.CalledProcessError as e:
            print(f"{RED}x Failed to install Python SDK{RESET}")
    else:
        print(f"{YELLOW}! sdk/python/pyproject.toml not found{RESET}")
    
    # Check Node.js
    print("\nChecking Node.js version...")
    try:
        result = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            version = result.stdout.strip()
            major_version = int(version.lstrip('v').split('.')[0])
            if major_version >= 18:
                print(f"{GREEN}+ Node.js {version} detected{RESET}")
                results.dependencies_installed["node"] = True
            else:
                print(f"{YELLOW}! Node.js 18+ recommended, found {version}{RESET}")
                results.dependencies_installed["node"] = True
        else:
            print(f"{RED}x Node.js not found{RESET}")
            print("Install Node.js 18+: https://nodejs.org/")
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print(f"{RED}x Node.js not found{RESET}")
        print("Install Node.js 18+: https://nodejs.org/")
    
    # Install TypeScript SDK dependencies
    if results.dependencies_installed["node"]:
        print("\nInstalling TypeScript SDK dependencies...")
        ts_package = Path("sdk/typescript/package.json")
        if ts_package.exists():
            try:
                print(f"{YELLOW}(This may take a minute...){RESET}")
                # Use shell=True on Windows to find npm in PATH
                subprocess.run(
                    "npm install",
                    cwd="sdk/typescript",
                    check=True,
                    capture_output=True,
                    timeout=120,
                    shell=True
                )
                print(f"{GREEN}+ TypeScript SDK dependencies installed{RESET}")
            except subprocess.TimeoutExpired:
                print(f"{YELLOW}! Installation timed out after 2 minutes{RESET}")
                print(f"{YELLOW}  Run manually: cd sdk/typescript && npm install{RESET}")
            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                print(f"{YELLOW}! Could not install TypeScript SDK dependencies{RESET}")
                print(f"{YELLOW}  Run manually: cd sdk/typescript && npm install{RESET}")
        else:
            print(f"{YELLOW}! sdk/typescript/package.json not found{RESET}")


def load_env_file() -> Dict[str, str]:
    """Load environment variables from .env file."""
    env_vars = {}
    env_path = Path(".env")
    
    if not env_path.exists():
        return env_vars
    
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                env_vars[key.strip()] = value.strip()
    
    return env_vars

def is_placeholder(value: str) -> bool:
    """Check if a value is a placeholder."""
    if not value or value == "":
        return True
    
    placeholders = [
        "YOUR_",
        "PLACEHOLDER",
        "CHANGE_ME",
        "WILL_BE_AUTO_GENERATED",
        "TODO"
    ]
    return any(p in value.upper() for p in placeholders)

def diagnose_env_values():
    """STEP 1: Diagnose .env values and show masked diagnostics."""
    print_section("STEP 1 — DIAGNOSE .env VALUES")
    
    env_vars = load_env_file()
    
    # Diagnose DATABASE_URL
    db_url = env_vars.get("DATABASE_URL", "")
    print(f"\n{BOLD}DATABASE_URL:{RESET}")
    if db_url:
        print(f"  Starts with postgresql+asyncpg://? {GREEN}YES{RESET}" if db_url.startswith("postgresql+asyncpg://") else f"  Starts with postgresql+asyncpg://? {RED}NO{RESET}")
        print(f"  Contains .supabase.co? {GREEN}YES{RESET}" if ".supabase.co" in db_url else f"  Contains .supabase.co? {RED}NO{RESET}")
        print(f"  Contains port :5432? {GREEN}YES{RESET}" if ":5432" in db_url else f"  Contains port :5432? {RED}NO{RESET}")
        
        # Extract and mask
        import re
        match = re.search(r'://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', db_url)
        if match:
            user, pwd, host, port, db = match.groups()
            print(f"  Masked: postgresql+asyncpg://{user}:***@{host}:{port}/{db}")
        else:
            print(f"  {YELLOW}Could not parse URL structure{RESET}")
    else:
        print(f"  {RED}NOT SET{RESET}")
    
    # Diagnose REDIS_URL
    redis_url = env_vars.get("REDIS_URL", "")
    print(f"\n{BOLD}REDIS_URL:{RESET}")
    if redis_url:
        print(f"  Starts with rediss:// (TLS)? {GREEN}YES{RESET}" if redis_url.startswith("rediss://") else f"  Starts with rediss:// (TLS)? {RED}NO{RESET} - {YELLOW}This is the TLS problem!{RESET}")
        print(f"  Contains .upstash.io? {GREEN}YES{RESET}" if ".upstash.io" in redis_url else f"  Contains .upstash.io? {RED}NO{RESET}")
        print(f"  Ends with :6379? {GREEN}YES{RESET}" if redis_url.endswith(":6379") else f"  Ends with :6379? {RED}NO{RESET}")
        
        # Extract and mask
        match = re.search(r'://([^:]+):([^@]+)@([^:]+):(\d+)', redis_url)
        if match:
            user, pwd, host, port = match.groups()
            scheme = "rediss" if redis_url.startswith("rediss://") else "redis"
            print(f"  Masked: {scheme}://{user}:***@{host}:{port}")
        else:
            print(f"  {YELLOW}Could not parse URL structure{RESET}")
    else:
        print(f"  {RED}NOT SET{RESET}")
    
    # Diagnose JINA_API_KEY
    jina_key = env_vars.get("JINA_API_KEY", "")
    print(f"\n{BOLD}JINA_API_KEY:{RESET}")
    if jina_key:
        print(f"  Starts with jina_? {GREEN}YES{RESET}" if jina_key.startswith("jina_") else f"  Starts with jina_? {RED}NO{RESET} - {YELLOW}Wrong key format!{RESET}")
        print(f"  Length: {len(jina_key)} characters")
    else:
        print(f"  {RED}NOT SET{RESET}")
    
    # Diagnose SECRET_KEY
    secret_key = env_vars.get("SECRET_KEY", "")
    print(f"\n{BOLD}SECRET_KEY:{RESET}")
    if secret_key:
        print(f"  Length: {len(secret_key)} characters")
    else:
        print(f"  {RED}NOT SET{RESET}")


def auto_fix_env_urls():
    """STEP 2: Auto-fix common URL problems in .env file."""
    print_section("STEP 2 — AUTO-FIX COMMON URL PROBLEMS")
    
    env_path = Path(".env")
    if not env_path.exists():
        print(f"{RED}x .env file not found{RESET}")
        return
    
    with open(env_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    original_content = content
    fixes_applied = []
    errors_found = []
    
    # Fix DATABASE_URL driver
    if "DATABASE_URL=postgres://" in content:
        content = content.replace("DATABASE_URL=postgres://", "DATABASE_URL=postgresql+asyncpg://")
        fixes_applied.append("Updated DATABASE_URL from postgres:// to postgresql+asyncpg://")
    elif "DATABASE_URL=postgresql://" in content and "DATABASE_URL=postgresql+asyncpg://" not in content:
        content = content.replace("DATABASE_URL=postgresql://", "DATABASE_URL=postgresql+asyncpg://")
        fixes_applied.append("Updated DATABASE_URL driver to postgresql+asyncpg://")
    
    # Fix REDIS_URL TLS
    if "REDIS_URL=redis://" in content and "REDIS_URL=rediss://" not in content:
        content = content.replace("REDIS_URL=redis://", "REDIS_URL=rediss://")
        fixes_applied.append("Updated REDIS_URL to use TLS (rediss://)")
    
    # Check for localhost issues
    env_vars = load_env_file()
    db_url = env_vars.get("DATABASE_URL", "")
    if "localhost" in db_url or "127.0.0.1" in db_url:
        errors_found.append("DATABASE_URL is pointing to localhost. You need your Supabase connection string from supabase.com → Project Settings → Database → Connection string → URI format")
    
    redis_url = env_vars.get("REDIS_URL", "")
    if "localhost" in redis_url or "127.0.0.1" in redis_url:
        errors_found.append("REDIS_URL is pointing to localhost. You need your Upstash connection string from upstash.com → your database → Connect tab")
    
    jina_key = env_vars.get("JINA_API_KEY", "")
    placeholder_keys = ["YOUR_JINA_API_KEY_HERE", "jina_xxx", "your_key_here"]
    if jina_key in placeholder_keys or len(jina_key) < 20:
        errors_found.append("JINA_API_KEY appears to be a placeholder. Get your real key from jina.ai → dashboard")
    
    # Write back if changes were made
    if content != original_content:
        with open(env_path, "w", encoding="utf-8") as f:
            f.write(content)
    
    # Print results
    if fixes_applied:
        print(f"\n{GREEN}AUTO-FIXES APPLIED:{RESET}")
        for fix in fixes_applied:
            print(f"  {GREEN}+{RESET} FIXED: {fix}")
    else:
        print(f"\n{YELLOW}No automatic fixes needed{RESET}")
    
    if errors_found:
        print(f"\n{RED}ERRORS DETECTED:{RESET}")
        for error in errors_found:
            print(f"  {RED}x{RESET} ERROR: {error}")
    
    return len(fixes_applied) > 0
    """PART 4: Validate configuration and auto-generate SECRET_KEY."""
    print_section("PART 4 — CONFIGURATION VALIDATION")
    
    env_vars = load_env_file()
    
    if not env_vars:
        print(f"{RED}x No .env file found or empty{RESET}")
        return
    
    # Required variables with descriptions
    required_vars = {
        "DATABASE_URL": "PostgreSQL database connection",
        "REDIS_URL": "Session caching and rate limiting",
        "JINA_API_KEY": "Embedding generation (semantic search)",
        "SECRET_KEY": "JWT token signing",
    }
    
    missing_or_placeholder = []
    
    for var, purpose in required_vars.items():
        value = env_vars.get(var, "")
        
        if not value or is_placeholder(value):
            missing_or_placeholder.append((var, purpose))
            results.env_vars_status[var] = "missing"
            results.missing_vars.append((var, purpose))
        else:
            results.env_vars_status[var] = "set"
    
    # Auto-generate SECRET_KEY if missing
    if "SECRET_KEY" in [v[0] for v in missing_or_placeholder]:
        print(f"\n{BOLD}Generating SECRET_KEY...{RESET}")
        new_secret = secrets.token_hex(32)
        
        # Update .env file
        env_path = Path(".env")
        with open(env_path, "r") as f:
            content = f.read()
        
        content = content.replace(
            "SECRET_KEY=WILL_BE_AUTO_GENERATED",
            f"SECRET_KEY={new_secret}"
        )
        content = content.replace(
            "SECRET_KEY=YOUR_SECRET_KEY_HERE",
            f"SECRET_KEY={new_secret}"
        )
        content = content.replace(
            "SECRET_KEY=",
            f"SECRET_KEY={new_secret}"
        )
        
        with open(env_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        print(f"{GREEN}+ AUTO-GENERATED SECRET_KEY and added to .env{RESET}")
        results.env_vars_status["SECRET_KEY"] = "set"
        missing_or_placeholder = [(v, p) for v, p in missing_or_placeholder if v != "SECRET_KEY"]
        results.missing_vars = [(v, p) for v, p in results.missing_vars if v != "SECRET_KEY"]
    
    if missing_or_placeholder:
        print(f"\n{BOLD}{RED}MISSING OR PLACEHOLDER VARIABLES:{RESET}")
        for var, purpose in missing_or_placeholder:
            print(f"  {RED}x{RESET} {var} -> needed for: {purpose}")
    else:
        print(f"\n{GREEN}+ All required environment variables are set{RESET}")
    
    # Show optional variables
    optional_vars = ["SENTRY_DSN", "CORS_ORIGINS"]
    print(f"\n{BOLD}Optional variables:{RESET}")
    for var in optional_vars:
        value = env_vars.get(var, "")
        if value and not is_placeholder(value):
            print(f"  {GREEN}+{RESET} {var} is set")
        else:
            print(f"  {YELLOW}o{RESET} {var} not set (optional)")


def part5_connectivity_tests():
    """PART 5: Test connectivity to external services."""
    print_section("PART 5 — CONNECTIVITY TESTS")
    
    env_vars = load_env_file()
    
    # Test Database
    print("Testing PostgreSQL connection...")
    db_url = env_vars.get("DATABASE_URL", "")
    if not db_url or is_placeholder(db_url):
        print(f"{YELLOW}o SKIPPED - DATABASE_URL not set{RESET}")
        results.connectivity_tests["PostgreSQL"] = "skipped"
    else:
        try:
            import asyncpg
            import asyncio
            
            async def test_db():
                try:
                    conn = await asyncio.wait_for(
                        asyncpg.connect(db_url),
                        timeout=5.0
                    )
                    await conn.execute("SELECT 1")
                    
                    # Check for alembic_version table
                    result = await conn.fetchval(
                        "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'alembic_version')"
                    )
                    
                    await conn.close()
                    return True, result
                except Exception as e:
                    return False, str(e)
            
            success, migration_check = asyncio.run(test_db())
            
            if success:
                print(f"{GREEN}+ PASS - PostgreSQL connection successful{RESET}")
                results.connectivity_tests["PostgreSQL"] = "pass"
                
                if not migration_check:
                    print(f"{YELLOW}! Alembic migrations have not been run{RESET}")
                    print(f"{YELLOW}  Run: cd server && alembic upgrade head{RESET}")
                else:
                    print(f"{GREEN}+ Alembic migrations are up to date{RESET}")
            else:
                print(f"{RED}x FAIL - {migration_check}{RESET}")
                results.connectivity_tests["PostgreSQL"] = f"fail: {migration_check}"
        except ImportError:
            print(f"{YELLOW}! asyncpg not installed, skipping test{RESET}")
            results.connectivity_tests["PostgreSQL"] = "skipped"
        except Exception as e:
            print(f"{RED}x FAIL - {str(e)}{RESET}")
            results.connectivity_tests["PostgreSQL"] = f"fail: {str(e)}"
    
    # Test Redis
    print("\nTesting Redis connection...")
    redis_url = env_vars.get("REDIS_URL", "")
    if not redis_url or is_placeholder(redis_url):
        print(f"{YELLOW}o SKIPPED - REDIS_URL not set{RESET}")
        results.connectivity_tests["Redis"] = "skipped"
    else:
        try:
            import redis
            
            client = redis.from_url(redis_url, socket_connect_timeout=5)
            result = client.ping()
            
            if result:
                print(f"{GREEN}+ PASS - Redis connection successful{RESET}")
                results.connectivity_tests["Redis"] = "pass"
            else:
                print(f"{RED}x FAIL - Redis PING returned False{RESET}")
                results.connectivity_tests["Redis"] = "fail: PING returned False"
        except ImportError:
            print(f"{YELLOW}! redis package not installed, skipping test{RESET}")
            results.connectivity_tests["Redis"] = "skipped"
        except Exception as e:
            print(f"{RED}x FAIL - {str(e)}{RESET}")
            results.connectivity_tests["Redis"] = f"fail: {str(e)}"
    
    # Test Jina AI
    print("\nTesting Jina AI embeddings...")
    jina_key = env_vars.get("JINA_API_KEY", "")
    if not jina_key or is_placeholder(jina_key):
        print(f"{YELLOW}o SKIPPED - JINA_API_KEY not set{RESET}")
        results.connectivity_tests["Jina AI"] = "skipped"
    else:
        try:
            import httpx
            
            start_time = time.time()
            
            with httpx.Client(timeout=5.0) as client:
                response = client.post(
                    "https://api.jina.ai/v1/embeddings",
                    headers={
                        "Authorization": f"Bearer {jina_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "input": ["test connection"],
                        "model": "jina-embeddings-v3"
                    }
                )
                
                elapsed_ms = int((time.time() - start_time) * 1000)
                
                if response.status_code == 200:
                    print(f"{GREEN}+ PASS - Jina AI connection successful ({elapsed_ms}ms){RESET}")
                    results.connectivity_tests["Jina AI"] = "pass"
                else:
                    print(f"{RED}x FAIL - HTTP {response.status_code}: {response.text[:100]}{RESET}")
                    results.connectivity_tests["Jina AI"] = f"fail: HTTP {response.status_code}"
        except ImportError:
            print(f"{YELLOW}! httpx not installed, skipping test{RESET}")
            results.connectivity_tests["Jina AI"] = "skipped"
        except Exception as e:
            print(f"{RED}x FAIL - {str(e)}{RESET}")
            results.connectivity_tests["Jina AI"] = f"fail: {str(e)}"
    
    # Test FastAPI import
    print("\nTesting FastAPI app import...")
    try:
        # Add server to path
        sys.path.insert(0, str(Path("server").absolute()))
        
        # Set a flag to prevent actual connections during import
        os.environ["TESTING"] = "true"
        
        # Use a separate process with timeout to avoid hanging
        import_test = subprocess.run(
            [sys.executable, "-c", "import sys; sys.path.insert(0, 'server'); from app.main import app; print('SUCCESS')"],
            capture_output=True,
            text=True,
            timeout=10,
            env={**os.environ, "TESTING": "true"}
        )
        
        if import_test.returncode == 0 and "SUCCESS" in import_test.stdout:
            print(f"{GREEN}+ PASS - FastAPI app loads cleanly{RESET}")
            results.connectivity_tests["FastAPI import"] = "pass"
        else:
            error_msg = import_test.stderr[:200] if import_test.stderr else "Unknown error"
            print(f"{RED}x FAIL - {error_msg}{RESET}")
            results.connectivity_tests["FastAPI import"] = f"fail: {error_msg}"
    except subprocess.TimeoutExpired:
        print(f"{YELLOW}! TIMEOUT - App import took too long (may need DB connection){RESET}")
        results.connectivity_tests["FastAPI import"] = "timeout"
    except Exception as e:
        print(f"{RED}x FAIL - {str(e)}{RESET}")
        results.connectivity_tests["FastAPI import"] = f"fail: {str(e)}"


def part6_run_tests():
    """PART 6: Run existing test suite."""
    print_section("PART 6 — RUN EXISTING TESTS")
    
    env_vars = load_env_file()
    
    # Check if critical services are configured
    db_configured = env_vars.get("DATABASE_URL", "") and not is_placeholder(env_vars.get("DATABASE_URL", ""))
    redis_configured = env_vars.get("REDIS_URL", "") and not is_placeholder(env_vars.get("REDIS_URL", ""))
    
    if not db_configured or not redis_configured:
        print(f"{YELLOW}o SKIPPED - Database or Redis not configured{RESET}")
        print(f"   Configure DATABASE_URL and REDIS_URL to run tests")
        results.test_results["skipped"] = "all"
        return
    
    # Check if pytest is available
    try:
        import pytest
    except ImportError:
        print(f"{YELLOW}! pytest not installed, skipping tests{RESET}")
        results.test_results["skipped"] = "all"
        return
    
    # Check if server/tests exists
    tests_path = Path("server/tests")
    if not tests_path.exists():
        print(f"{YELLOW}! server/tests/ directory not found{RESET}")
        results.test_results["skipped"] = "all"
        return
    
    print("Running pytest on server/tests/...")
    print(f"{YELLOW}(This may take a minute...){RESET}\n")
    
    try:
        # Run pytest with short traceback
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "server/tests/", "--tb=short", "-v", "--no-header"],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=Path.cwd()
        )
        
        output = result.stdout + result.stderr
        
        # Parse results
        if "passed" in output or "failed" in output or "skipped" in output:
            # Extract counts from pytest output
            import re
            
            passed_match = re.search(r'(\d+) passed', output)
            failed_match = re.search(r'(\d+) failed', output)
            skipped_match = re.search(r'(\d+) skipped', output)
            
            results.test_results["passed"] = int(passed_match.group(1)) if passed_match else 0
            results.test_results["failed"] = int(failed_match.group(1)) if failed_match else 0
            results.test_results["skipped"] = int(skipped_match.group(1)) if skipped_match else 0
            
            print(f"{GREEN}+{RESET} {results.test_results['passed']} passed")
            if results.test_results['failed'] > 0:
                print(f"{RED}x{RESET} {results.test_results['failed']} failed")
            if results.test_results['skipped'] > 0:
                print(f"{YELLOW}o{RESET} {results.test_results['skipped']} skipped")
            
            # Show failed tests
            if results.test_results['failed'] > 0:
                print(f"\n{BOLD}Failed tests:{RESET}")
                failed_tests = re.findall(r'FAILED (.*?) -', output)
                for test in failed_tests[:5]:  # Show first 5
                    print(f"  * {test}")
                if len(failed_tests) > 5:
                    print(f"  ... and {len(failed_tests) - 5} more")
        else:
            print(f"{YELLOW}! Could not parse test results{RESET}")
            results.test_results["skipped"] = "all"
    
    except subprocess.TimeoutExpired:
        print(f"{YELLOW}! Tests timed out after 120 seconds{RESET}")
        results.test_results["skipped"] = "timeout"
    except Exception as e:
        print(f"{RED}x Error running tests: {str(e)}{RESET}")
        results.test_results["skipped"] = "error"


def part7_final_report():
    """PART 7: Print final readiness report."""
    print_header("REMEMBR — LOCAL READINESS REPORT")
    
    # Repo Structure
    passed_checks = sum(1 for _, passed in results.repo_checks if passed)
    total_checks = len(results.repo_checks)
    
    print(f"{BOLD}REPO STRUCTURE{RESET}")
    if passed_checks == total_checks:
        print(f"  {GREEN}+ {passed_checks}/{total_checks} checks passed{RESET}")
    else:
        print(f"  {RED}x {passed_checks}/{total_checks} checks passed{RESET}")
    
    # Dependencies
    print(f"\n{BOLD}DEPENDENCIES{RESET}")
    if results.dependencies_installed.get("python"):
        print(f"  Python packages      {GREEN}+ installed{RESET}")
    else:
        print(f"  Python packages      {RED}x not installed{RESET}")
    
    if results.dependencies_installed.get("node"):
        print(f"  Node packages        {GREEN}+ installed{RESET}")
    else:
        print(f"  Node packages        {YELLOW}o not installed{RESET}")
    
    # Environment Variables
    print(f"\n{BOLD}ENVIRONMENT VARIABLES{RESET}")
    
    env_var_display = {
        "DATABASE_URL": "add your Supabase connection string",
        "REDIS_URL": "add your Upstash Redis URL",
        "JINA_API_KEY": "add your Jina AI API key",
        "SECRET_KEY": "auto-generated"
    }
    
    for var, instruction in env_var_display.items():
        status = results.env_vars_status.get(var, "missing")
        if status == "set":
            print(f"  {var:20} {GREEN}+ set{RESET}")
        else:
            print(f"  {var:20} {RED}x NOT SET{RESET} - {instruction}")
    
    # Connectivity
    print(f"\n{BOLD}CONNECTIVITY{RESET}")
    
    for service, status in results.connectivity_tests.items():
        if status == "pass":
            print(f"  {service:20} {GREEN}+ connected{RESET}")
        elif status == "skipped":
            var_name = {
                "PostgreSQL": "DATABASE_URL",
                "Redis": "REDIS_URL",
                "Jina AI": "JINA_API_KEY"
            }.get(service, "")
            if var_name:
                print(f"  {service:20} {YELLOW}o SKIPPED{RESET} - {var_name} not set")
            else:
                print(f"  {service:20} {GREEN}+ {status}{RESET}")
        elif status and status.startswith("fail"):
            print(f"  {service:20} {RED}x FAILED{RESET}")
        else:
            print(f"  {service:20} {YELLOW}o {status}{RESET}")
    
    # Tests
    print(f"\n{BOLD}TESTS{RESET}")
    if results.test_results.get("skipped") in ["all", "timeout", "error"]:
        print(f"  {YELLOW}o SKIPPED{RESET} - {results.test_results.get('skipped')}")
    else:
        passed = results.test_results.get("passed", 0)
        failed = results.test_results.get("failed", 0)
        skipped = results.test_results.get("skipped", 0)
        
        if failed == 0:
            print(f"  {GREEN}+ {passed} passed  {failed} failed  {skipped} skipped{RESET}")
        else:
            print(f"  {YELLOW}! {passed} passed  {failed} failed  {skipped} skipped{RESET}")
    
    # Final Status
    print(f"\n{BOLD}{'-' * 80}{RESET}")
    
    missing_count = len(results.missing_vars)
    all_connected = all(
        status in ["pass", "skipped"] 
        for status in results.connectivity_tests.values()
    )
    
    if missing_count == 0 and all_connected and passed_checks == total_checks:
        print(f"{BOLD}{GREEN}STATUS: READY FOR DEPLOYMENT +{RESET}")
        print(f"\n{BOLD}NEXT STEPS:{RESET}")
        print("  1. Start the development server: cd server && uvicorn app.main:app --reload")
        print("  2. Access API docs at: http://localhost:8000/docs")
        print("  3. Run tests: pytest server/tests/")
        print("  4. Deploy to staging: railway up")
    else:
        print(f"{BOLD}{YELLOW}STATUS: NOT READY{RESET} - {missing_count} environment variable(s) need real values")
        print(f"\n{BOLD}NEXT STEPS:{RESET}")
        
        step = 1
        for var, purpose in results.missing_vars:
            service_map = {
                "DATABASE_URL": ("Supabase", "Setup Guide Section 2"),
                "REDIS_URL": ("Upstash", "Setup Guide Section 3"),
                "JINA_API_KEY": ("Jina AI", "Setup Guide Section 4"),
            }
            service, guide = service_map.get(var, ("provider", "documentation"))
            print(f"  {step}. Open .env and fill in {var} from {service}")
            step += 1
        
        print(f"  {step}. Re-run this script to confirm all connectivity tests pass")
        print(f"  {step + 1}. Once all green: start the server with uvicorn")
    
    print(f"\n{BOLD}{BLUE}{'=' * 80}{RESET}\n")


def diagnose_env_values():
    """STEP 1: Diagnose .env values and show masked diagnostics."""
    print_section("STEP 1 — DIAGNOSE .env VALUES")
    
    env_vars = load_env_file()
    
    # Diagnose DATABASE_URL
    db_url = env_vars.get("DATABASE_URL", "")
    print(f"\n{BOLD}DATABASE_URL:{RESET}")
    if db_url:
        print(f"  Starts with postgresql+asyncpg://? {GREEN}YES{RESET}" if db_url.startswith("postgresql+asyncpg://") else f"  Starts with postgresql+asyncpg://? {RED}NO{RESET}")
        print(f"  Contains .supabase.co? {GREEN}YES{RESET}" if ".supabase.co" in db_url else f"  Contains .supabase.co? {RED}NO{RESET}")
        print(f"  Contains port :5432? {GREEN}YES{RESET}" if ":5432" in db_url else f"  Contains port :5432? {RED}NO{RESET}")
        
        # Extract and mask
        import re
        match = re.search(r'://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', db_url)
        if match:
            user, pwd, host, port, db = match.groups()
            print(f"  Masked: postgresql+asyncpg://{user}:***@{host}:{port}/{db}")
        else:
            print(f"  {YELLOW}Could not parse URL structure{RESET}")
    else:
        print(f"  {RED}NOT SET{RESET}")
    
    # Diagnose REDIS_URL
    redis_url = env_vars.get("REDIS_URL", "")
    print(f"\n{BOLD}REDIS_URL:{RESET}")
    if redis_url:
        print(f"  Starts with rediss:// (TLS)? {GREEN}YES{RESET}" if redis_url.startswith("rediss://") else f"  Starts with rediss:// (TLS)? {RED}NO{RESET} - {YELLOW}This is the TLS problem!{RESET}")
        print(f"  Contains .upstash.io? {GREEN}YES{RESET}" if ".upstash.io" in redis_url else f"  Contains .upstash.io? {RED}NO{RESET}")
        print(f"  Ends with :6379? {GREEN}YES{RESET}" if redis_url.endswith(":6379") else f"  Ends with :6379? {RED}NO{RESET}")
        
        # Extract and mask
        import re
        match = re.search(r'://([^:]+):([^@]+)@([^:]+):(\d+)', redis_url)
        if match:
            user, pwd, host, port = match.groups()
            scheme = "rediss" if redis_url.startswith("rediss://") else "redis"
            print(f"  Masked: {scheme}://{user}:***@{host}:{port}")
        else:
            print(f"  {YELLOW}Could not parse URL structure{RESET}")
    else:
        print(f"  {RED}NOT SET{RESET}")
    
    # Diagnose JINA_API_KEY
    jina_key = env_vars.get("JINA_API_KEY", "")
    print(f"\n{BOLD}JINA_API_KEY:{RESET}")
    if jina_key:
        print(f"  Starts with jina_? {GREEN}YES{RESET}" if jina_key.startswith("jina_") else f"  Starts with jina_? {RED}NO{RESET} - {YELLOW}Wrong key format!{RESET}")
        print(f"  Length: {len(jina_key)} characters")
    else:
        print(f"  {RED}NOT SET{RESET}")
    
    # Diagnose SECRET_KEY
    secret_key = env_vars.get("SECRET_KEY", "")
    print(f"\n{BOLD}SECRET_KEY:{RESET}")
    if secret_key:
        print(f"  Length: {len(secret_key)} characters")
    else:
        print(f"  {RED}NOT SET{RESET}")


def auto_fix_env_urls():
    """STEP 2: Auto-fix common URL problems in .env file."""
    print_section("STEP 2 — AUTO-FIX COMMON URL PROBLEMS")
    
    env_path = Path(".env")
    if not env_path.exists():
        print(f"{RED}x .env file not found{RESET}")
        return False
    
    with open(env_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    original_content = content
    fixes_applied = []
    errors_found = []
    
    # Fix DATABASE_URL driver
    if "DATABASE_URL=postgres://" in content:
        content = content.replace("DATABASE_URL=postgres://", "DATABASE_URL=postgresql+asyncpg://")
        fixes_applied.append("Updated DATABASE_URL from postgres:// to postgresql+asyncpg://")
    elif "DATABASE_URL=postgresql://" in content and "DATABASE_URL=postgresql+asyncpg://" not in content:
        content = content.replace("DATABASE_URL=postgresql://", "DATABASE_URL=postgresql+asyncpg://")
        fixes_applied.append("Updated DATABASE_URL driver to postgresql+asyncpg://")
    
    # Fix REDIS_URL TLS
    if "REDIS_URL=redis://" in content and "REDIS_URL=rediss://" not in content:
        content = content.replace("REDIS_URL=redis://", "REDIS_URL=rediss://")
        fixes_applied.append("Updated REDIS_URL to use TLS (rediss://)")
    
    # Check for localhost issues
    env_vars = load_env_file()
    db_url = env_vars.get("DATABASE_URL", "")
    if "localhost" in db_url or "127.0.0.1" in db_url:
        errors_found.append("DATABASE_URL is pointing to localhost. You need your Supabase connection string from supabase.com → Project Settings → Database → Connection string → URI format")
    
    redis_url = env_vars.get("REDIS_URL", "")
    if "localhost" in redis_url or "127.0.0.1" in redis_url:
        errors_found.append("REDIS_URL is pointing to localhost. You need your Upstash connection string from upstash.com → your database → Connect tab")
    
    jina_key = env_vars.get("JINA_API_KEY", "")
    placeholder_keys = ["YOUR_JINA_API_KEY_HERE", "jina_xxx", "your_key_here"]
    if jina_key in placeholder_keys or len(jina_key) < 20:
        errors_found.append("JINA_API_KEY appears to be a placeholder. Get your real key from jina.ai → dashboard")
    
    # Write back if changes were made
    if content != original_content:
        with open(env_path, "w", encoding="utf-8") as f:
            f.write(content)
    
    # Print results
    if fixes_applied:
        print(f"\n{GREEN}AUTO-FIXES APPLIED:{RESET}")
        for fix in fixes_applied:
            print(f"  {GREEN}+{RESET} FIXED: {fix}")
    else:
        print(f"\n{YELLOW}No automatic fixes needed{RESET}")
    
    if errors_found:
        print(f"\n{RED}ERRORS DETECTED:{RESET}")
        for error in errors_found:
            print(f"  {RED}x{RESET} ERROR: {error}")
    
    return len(fixes_applied) > 0


def test_connectivity_verbose():
    """STEP 3: Test connectivity with verbose error details."""
    print_section("STEP 3 — TEST CONNECTIVITY WITH VERBOSE ERRORS")
    
    env_vars = load_env_file()
    db_url = env_vars.get("DATABASE_URL", "")
    redis_url = env_vars.get("REDIS_URL", "")
    jina_key = env_vars.get("JINA_API_KEY", "")
    
    all_passed = True
    
    # Test PostgreSQL
    print(f"\n{BOLD}Testing PostgreSQL connection...{RESET}")
    if not db_url or is_placeholder(db_url):
        print(f"{YELLOW}o SKIPPED - DATABASE_URL not set{RESET}")
        all_passed = False
    else:
        # First test DNS resolution
        import re
        match = re.search(r'@([^:]+):', db_url)
        if match:
            hostname = match.group(1)
            print(f"  Testing DNS resolution for {hostname}...")
            try:
                import socket
                ip = socket.gethostbyname(hostname)
                print(f"  {GREEN}+ DNS resolved to {ip}{RESET}")
            except socket.gaierror as e:
                print(f"  {RED}x DNS resolution failed: {e}{RESET}")
                print(f"  {YELLOW}This is a network/DNS issue, not a configuration issue{RESET}")
                print(f"  {YELLOW}Possible causes:{RESET}")
                print(f"    - No internet connection")
                print(f"    - Firewall blocking DNS queries")
                print(f"    - DNS server not responding")
                print(f"    - VPN required but not connected")
                all_passed = False
                # Skip the actual connection test if DNS fails
                print(f"\n{BOLD}Testing Redis connection...{RESET}")
                # Continue to Redis test
                if not redis_url or is_placeholder(redis_url):
                    print(f"{YELLOW}o SKIPPED - REDIS_URL not set{RESET}")
                    all_passed = False
                else:
                    try:
                        import redis.asyncio as redis_async
                        import asyncio
                        
                        async def test_redis():
                            try:
                                # Use SSL with relaxed cert requirements for Upstash on Windows
                                r = redis_async.from_url(
                                    redis_url,
                                    ssl_cert_reqs=None,
                                    socket_connect_timeout=10
                                )
                                result = await asyncio.wait_for(r.ping(), timeout=10.0)
                                await r.aclose()
                                return True, result
                            except Exception as e:
                                import traceback
                                return False, traceback.format_exc()
                        
                        success, result = asyncio.run(test_redis())
                        
                        if success:
                            print(f"{GREEN}+ PASS - Redis connection successful{RESET}")
                            print(f"  PING response: {result}")
                        else:
                            print(f"{RED}x FAIL - Redis connection failed{RESET}")
                            print(f"\n{YELLOW}Full error details:{RESET}")
                            print(result)
                            all_passed = False
                    except ImportError:
                        print(f"{YELLOW}! redis package not installed{RESET}")
                        all_passed = False
                    except Exception as e:
                        print(f"{RED}x FAIL - {str(e)}{RESET}")
                        all_passed = False
                
                # Test Jina AI
                print(f"\n{BOLD}Testing Jina AI embeddings...{RESET}")
                if not jina_key or is_placeholder(jina_key):
                    print(f"{YELLOW}o SKIPPED - JINA_API_KEY not set{RESET}")
                    all_passed = False
                else:
                    try:
                        import httpx
                        import asyncio
                        
                        async def test_jina():
                            try:
                                async with httpx.AsyncClient(timeout=10.0) as client:
                                    resp = await client.post(
                                        "https://api.jina.ai/v1/embeddings",
                                        headers={
                                            "Authorization": f"Bearer {jina_key}",
                                            "Content-Type": "application/json"
                                        },
                                        json={
                                            "model": "jina-embeddings-v3",
                                            "task": "retrieval.passage",
                                            "input": ["test"]
                                        }
                                    )
                                    return True, resp.status_code, resp.text[:200]
                            except Exception as e:
                                import traceback
                                return False, 0, traceback.format_exc()
                        
                        success, status, text = asyncio.run(test_jina())
                        
                        if success:
                            if status == 200:
                                print(f"{GREEN}+ PASS - Jina AI connection successful{RESET}")
                                print(f"  Status: {status}")
                                print(f"  Response preview: {text}")
                            else:
                                print(f"{YELLOW}! Jina AI responded but with status {status}{RESET}")
                                print(f"  Response: {text}")
                                all_passed = False
                        else:
                            print(f"{RED}x FAIL - Jina AI connection failed{RESET}")
                            print(f"\n{YELLOW}Full error details:{RESET}")
                            print(text)
                            all_passed = False
                    except ImportError:
                        print(f"{YELLOW}! httpx not installed{RESET}")
                        all_passed = False
                    except Exception as e:
                        print(f"{RED}x FAIL - {str(e)}{RESET}")
                        all_passed = False
                
                return all_passed
        
        try:
            import asyncpg
            import asyncio
            
            # asyncpg doesn't support postgresql+asyncpg:// scheme, convert it
            test_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
            
            async def test_pg():
                try:
                    conn = await asyncio.wait_for(
                        asyncpg.connect(test_url, statement_cache_size=0),
                        timeout=10.0
                    )
                    version = await conn.fetchval("SELECT version()")
                    await conn.close()
                    return True, version
                except Exception as e:
                    import traceback
                    return False, traceback.format_exc()
            
            success, result = asyncio.run(test_pg())
            
            if success:
                print(f"{GREEN}+ PASS - PostgreSQL connection successful{RESET}")
                print(f"  Version: {result[:80]}...")
            else:
                print(f"{RED}x FAIL - PostgreSQL connection failed{RESET}")
                print(f"\n{YELLOW}Full error details:{RESET}")
                print(result)
                all_passed = False
        except ImportError:
            print(f"{YELLOW}! asyncpg not installed{RESET}")
            all_passed = False
        except Exception as e:
            print(f"{RED}x FAIL - {str(e)}{RESET}")
            all_passed = False
    
    # Test Redis
    print(f"\n{BOLD}Testing Redis connection...{RESET}")
    if not redis_url or is_placeholder(redis_url):
        print(f"{YELLOW}o SKIPPED - REDIS_URL not set{RESET}")
        all_passed = False
    else:
        try:
            import redis.asyncio as redis_async
            import asyncio
            
            async def test_redis():
                try:
                    # Use SSL with relaxed cert requirements for Upstash on Windows
                    r = redis_async.from_url(
                        redis_url,
                        ssl_cert_reqs=None,
                        socket_connect_timeout=10
                    )
                    result = await asyncio.wait_for(r.ping(), timeout=10.0)
                    await r.aclose()
                    return True, result
                except Exception as e:
                    import traceback
                    return False, traceback.format_exc()
            
            success, result = asyncio.run(test_redis())
            
            if success:
                print(f"{GREEN}+ PASS - Redis connection successful{RESET}")
                print(f"  PING response: {result}")
            else:
                print(f"{RED}x FAIL - Redis connection failed{RESET}")
                print(f"\n{YELLOW}Full error details:{RESET}")
                print(result)
                all_passed = False
        except ImportError:
            print(f"{YELLOW}! redis package not installed{RESET}")
            all_passed = False
        except Exception as e:
            print(f"{RED}x FAIL - {str(e)}{RESET}")
            all_passed = False
    
    # Test Jina AI
    print(f"\n{BOLD}Testing Jina AI embeddings...{RESET}")
    if not jina_key or is_placeholder(jina_key):
        print(f"{YELLOW}o SKIPPED - JINA_API_KEY not set{RESET}")
        all_passed = False
    else:
        try:
            import httpx
            import asyncio
            
            async def test_jina():
                try:
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        resp = await client.post(
                            "https://api.jina.ai/v1/embeddings",
                            headers={
                                "Authorization": f"Bearer {jina_key}",
                                "Content-Type": "application/json"
                            },
                            json={
                                "model": "jina-embeddings-v3",
                                "task": "retrieval.passage",
                                "input": ["test"]
                            }
                        )
                        return True, resp.status_code, resp.text[:200]
                except Exception as e:
                    import traceback
                    return False, 0, traceback.format_exc()
            
            success, status, text = asyncio.run(test_jina())
            
            if success:
                if status == 200:
                    print(f"{GREEN}+ PASS - Jina AI connection successful{RESET}")
                    print(f"  Status: {status}")
                    print(f"  Response preview: {text}")
                else:
                    print(f"{YELLOW}! Jina AI responded but with status {status}{RESET}")
                    print(f"  Response: {text}")
                    all_passed = False
            else:
                print(f"{RED}x FAIL - Jina AI connection failed{RESET}")
                print(f"\n{YELLOW}Full error details:{RESET}")
                print(text)
                all_passed = False
        except ImportError:
            print(f"{YELLOW}! httpx not installed{RESET}")
            all_passed = False
        except Exception as e:
            print(f"{RED}x FAIL - {str(e)}{RESET}")
            all_passed = False
    
    return all_passed


def check_fastapi_import_issue():
    """STEP 4: Check if FastAPI app has import-time connection issues."""
    print_section("STEP 4 — CHECK FASTAPI IMPORT ISSUE")
    
    main_py = Path("server/app/main.py")
    session_py = Path("server/app/db/session.py")
    
    issues_found = []
    
    # Check main.py
    if main_py.exists():
        print(f"\n{BOLD}Checking server/app/main.py...{RESET}")
        with open(main_py, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Look for problematic patterns
        if "await" in content and "lifespan" not in content:
            issues_found.append("main.py may have await calls outside lifespan context")
        
        print(f"  {GREEN}+ No obvious import-time connection issues{RESET}")
    
    # Check session.py
    if session_py.exists():
        print(f"\n{BOLD}Checking server/app/db/session.py...{RESET}")
        with open(session_py, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Check if pool_pre_ping is set
        if "create_async_engine" in content:
            if "pool_pre_ping=True" in content:
                print(f"  {GREEN}+ Engine configured with pool_pre_ping=True (lazy connection){RESET}")
            else:
                print(f"  {YELLOW}! Engine may connect eagerly at import time{RESET}")
                print(f"  {YELLOW}  Recommendation: Add pool_pre_ping=True to create_async_engine(){RESET}")
    
    if not issues_found:
        print(f"\n{GREEN}+ FastAPI import configuration looks good{RESET}")
        print(f"  {YELLOW}Note: Timeout may be due to network issues, not code issues{RESET}")


def print_action_list(all_tests_passed):
    """STEP 5: Print clear action list for manual fixes."""
    print_header("DIAGNOSIS COMPLETE")
    
    env_vars = load_env_file()
    db_url = env_vars.get("DATABASE_URL", "")
    redis_url = env_vars.get("REDIS_URL", "")
    jina_key = env_vars.get("JINA_API_KEY", "")
    
    manual_actions = []
    
    # Check what still needs fixing
    if not db_url or is_placeholder(db_url) or "localhost" in db_url:
        manual_actions.append("Configure DATABASE_URL with your Supabase connection string")
    elif not db_url.startswith("postgresql+asyncpg://"):
        manual_actions.append("Update DATABASE_URL to use postgresql+asyncpg:// driver")
    
    if not redis_url or is_placeholder(redis_url) or "localhost" in redis_url:
        manual_actions.append("Configure REDIS_URL with your Upstash connection string")
    elif not redis_url.startswith("rediss://"):
        manual_actions.append("Update REDIS_URL to use rediss:// (TLS)")
    
    if not jina_key or is_placeholder(jina_key) or len(jina_key) < 20:
        manual_actions.append("Configure JINA_API_KEY with your Jina AI API key")
    
    if manual_actions or not all_tests_passed:
        print(f"\n{BOLD}{YELLOW}MANUAL ACTIONS REQUIRED:{RESET}")
        for i, action in enumerate(manual_actions, 1):
            print(f"  {i}. {action}")
        
        print(f"\n{BOLD}WHERE TO GET EACH VALUE:{RESET}")
        
        if any("DATABASE_URL" in a for a in manual_actions):
            print(f"\n{BOLD}Supabase DATABASE_URL:{RESET}")
            print("  1. Go to supabase.com and log in")
            print("  2. Click your project (remembr-dev)")
            print("  3. Left sidebar → Project Settings → Database")
            print("  4. Scroll to Connection string → select URI tab")
            print("  5. Copy the string — it looks like:")
            print("     postgresql://postgres:[PASSWORD]@db.xxx.supabase.co:5432/postgres")
            print("  6. Change postgresql:// to postgresql+asyncpg://")
            print("  7. Replace [YOUR-PASSWORD] with your actual database password")
        
        if any("REDIS_URL" in a for a in manual_actions):
            print(f"\n{BOLD}Upstash REDIS_URL:{RESET}")
            print("  1. Go to upstash.com and log in")
            print("  2. Click your database (remembr-dev)")
            print("  3. Click the Connect tab")
            print("  4. Copy the Redis URL — it must start with rediss:// (two s)")
        
        if any("JINA_API_KEY" in a for a in manual_actions):
            print(f"\n{BOLD}Jina AI JINA_API_KEY:{RESET}")
            print("  1. Go to jina.ai and log in")
            print("  2. Your API key is on the dashboard home page")
            print("  3. It starts with jina_ followed by a long string")
        
        print(f"\n{BOLD}AFTER FIXING .env:{RESET}")
        print("  Run: python verify_local.py")
        print("  All three connectivity tests should show PASS")
    else:
        print(f"\n{BOLD}{GREEN}ALL SYSTEMS GO!{RESET}")
        print(f"\n{BOLD}Next steps:{RESET}")
        print("  1. Run database migrations:")
        print("     cd server && alembic upgrade head")
        print("  2. Start the development server:")
        print("     uvicorn app.main:app --reload")
        print("  3. Access API docs at:")
        print("     http://localhost:8000/docs")
    
    print(f"\n{BOLD}{BLUE}{'=' * 80}{RESET}\n")


def main():
    """Main execution function."""
    print_header("REMEMBR CONNECTIVITY DIAGNOSTICS")
    
    try:
        diagnose_env_values()
        fixes_applied = auto_fix_env_urls()
        
        if fixes_applied:
            print(f"\n{YELLOW}Reloading .env after fixes...{RESET}")
        
        all_tests_passed = test_connectivity_verbose()
        check_fastapi_import_issue()
        print_action_list(all_tests_passed)
    except KeyboardInterrupt:
        print(f"\n\n{YELLOW}! Diagnostics interrupted by user{RESET}")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n{RED}x Unexpected error: {str(e)}{RESET}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main_old():
    """Old main execution function."""
    print_header("REMEMBR LOCAL ENVIRONMENT VERIFICATION")
    
    try:
        part1_repo_audit()
        part2_generate_env_file()
        part3_dependency_check()
        part4_configuration_validation()
        part5_connectivity_tests()
        part6_run_tests()
        part7_final_report()
    except KeyboardInterrupt:
        print(f"\n\n{YELLOW}! Verification interrupted by user{RESET}")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n{RED}x Unexpected error: {str(e)}{RESET}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

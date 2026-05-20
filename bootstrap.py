#!/usr/bin/env python
"""Bootstrap script to install dependencies and run the system."""

import subprocess
import sys
import os
from pathlib import Path


def install_deps():
    """Install dependencies."""
    print("=" * 60)
    print("Installing Dependencies")
    print("=" * 60)

    # Core packages that don't require build tools
    core_packages = [
        "pydantic>=2.0",
        "structlog>=21.0",
        "networkx>=3.0",
        "fastapi>=0.100",
        "uvicorn>=0.20",
        "pytest>=7.0",
        "pytest-asyncio>=0.21",
        "httpx>=0.24",
        "mkdocs>=1.5",
        "mkdocs-material>=9.0",
        "streamlit>=1.0",
        "sqlalchemy>=2.0",
        "langgraph>=0.0.1",
    ]

    for package in core_packages:
        print(f"\nInstalling {package}...")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", package, "-q"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(f"  Warning: {package} installation had issues")
            print(f"  {result.stderr}")
        else:
            print(f"  ✓ Installed")

    print("\n" + "=" * 60)
    print("Dependency installation complete (some packages may have failed)")
    print("=" * 60)


def run_tests():
    """Run test suite."""
    print("\n" + "=" * 60)
    print("Running Tests")
    print("=" * 60)

    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"],
        cwd=str(Path(__file__).parent),
    )

    return result.returncode == 0


def run_eval():
    """Run evaluation mode."""
    print("\n" + "=" * 60)
    print("Running Evaluation Mode (5 test queries)")
    print("=" * 60)

    result = subprocess.run(
        [sys.executable, "main.py", "--mode", "eval", "--num-queries", "5"],
        cwd=str(Path(__file__).parent),
    )

    return result.returncode == 0


def main():
    """Main bootstrap function."""
    parser_actions = {
        "install": install_deps,
        "test": run_tests,
        "eval": run_eval,
    }

    if len(sys.argv) > 1 and sys.argv[1] in parser_actions:
        action = sys.argv[1]
        parser_actions[action]()
    else:
        print("Usage: python bootstrap.py [install|test|eval]")
        print("\n  install - Install dependencies")
        print("  test    - Run test suite")
        print("  eval    - Run evaluation mode")


if __name__ == "__main__":
    main()

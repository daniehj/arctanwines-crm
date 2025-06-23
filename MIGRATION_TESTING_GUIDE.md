# Migration Testing Guide

## Overview

This guide covers the automatic migration testing system that ensures database changes are tested locally before committing to the repository. The system uses pre-commit hooks to automatically detect model changes and run migration tests with realistic Norwegian wine import data.

## íº€ Quick Setup

### 1. Install Pre-commit Hooks

```bash
# Run the setup script
python scripts/setup_pre_commit.py

# Or manually:
pip install pre-commit
pre-commit install
```

### 2. Verify Setup

```bash
# Test that everything works
pre-commit run --all-files
```

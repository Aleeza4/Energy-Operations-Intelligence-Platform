# EOIP Working Rules

> These rules must be followed throughout the project.

---

# Development Workflow

Every task follows this order:

1. Check Project Dashboard
2. Check Phase Tracker
3. Check File Registry
4. Verify the next file in the roadmap
5. Implement ONE production file
6. Implement its corresponding test file
7. Run Ruff
8. Run Black
9. Run Pytest
10. Update File Registry
11. Update Phase Tracker
12. Update Dashboard
13. Update Session Log
14. Commit to Git

---

# Coding Rules

✓ One production file at a time.

✓ Every production file has one corresponding test file.

✓ Never skip tests.

✓ Never skip formatting.

✓ Never create duplicate files.

✓ Never create duplicate functions.

✓ Never create duplicate classes.

✓ Never move to the next file until the current one passes:
- Ruff
- Black
- Pytest

---

# Documentation Rules

Every completed feature requires updating:

- Project Dashboard
- Phase Tracker
- File Registry
- Session Log

---

# Git Rules

Every completed milestone should be committed.

Commit message format:

Phase X - Module - Description

Example:

Phase 2 - Events - Complete scheduler implementation

---

# Before Starting Any Work

Always answer these questions:

1. What phase am I in?
2. What module am I in?
3. What is the current file?
4. Does the file already exist?
5. What is the next file according to the roadmap?

If any answer is unknown, stop and update the project management documents first.

---

# Definition of Done

A file is complete only if:

- Code implemented
- Unit tests implemented
- Ruff passed
- Black passed
- Pytest passed
- Documentation updated
- Git committed

Only then can the next file begin.
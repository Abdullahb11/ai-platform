---
name: Imported dependency snapshots
description: Environment behavior to remember when running projects imported from zip files.
---

Imported Node projects can contain a `node_modules` snapshot with stripped executable bits and missing platform-specific optional packages. Restore executable bits for local package binaries and reinstall the versions already declared by the project before diagnosing application code.

**Why:** A build can fail before TypeScript or Vite evaluates the project, producing misleading setup errors unrelated to the source.

**How to apply:** When an imported Node app reports permission errors for package binaries or missing native bindings, repair the dependency installation first without adding unrelated libraries.
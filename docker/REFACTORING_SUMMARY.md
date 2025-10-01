# Refactoring Summary: Environment & Command Naming

## Changes Made

### 1. File Structure Simplification
**Before**:
- `.env.dev`, `.env.prod`, `.secrets.dev`, `.secrets.prod` (4 files, duplicated data)

**After**:
- `.env.dev`, `.env.prod` (2 files, single source of truth)

**Rationale**: No need to duplicate the same data from Doppler into separate "secrets" files. The `.env.*` files serve both purposes.

### 2. Command Naming Clarity
**Before**:
- `make dev` (unclear: local or remote?)
- `make test-deploy` (unclear: which environment?)

**After**:
- `make dev-local` (clearly local dev)
- `make dev-local-detached` (local dev in background)
- `make prod-local` (local prod testing)
- `make dev-deploy` (deploy dev to remote via act)
- `make prod-deploy` (deploy prod to remote via act)

**Naming Convention**:
- `*-local`: Runs containers on your machine
- `*-deploy`: Tests deployment to remote EC2 via act
- `*-detached`: Runs in background

### 3. Script Naming
**Before**:
- `scripts/load-env-and-run.sh` (unclear what it runs)

**After**:
- `scripts/docker-compose-with-env.sh` (clear: runs docker compose with env vars)

**Rationale**: Name describes exactly what the script does.

### 4. Remote Environment Consistency
**Before**:
- Remote used generic `.env` file

**After**:
- Remote uses `.env.dev` or `.env.prod` (same names as local)

**Rationale**: No difference between local and remote - same file names, same structure.

### 5. Auto-Update Strategy
**Before**:
- Manual `sync-secrets` needed before every run

**After**:
- Every local run automatically updates `.env.dev` or `.env.prod` from Doppler
- `sync-secrets` only needed for act testing

**Rationale**: Reduces manual steps, ensures secrets are always fresh.

## File Mapping

### Local Development
```
make dev-local → Doppler (dev_personal) → .env.dev → docker-compose (dev overlay)
make prod-local → Doppler (prd) → .env.prod → docker-compose (prod overlay)
```

### Remote Deployment Testing
```
make dev-deploy → .env.dev → act → GitHub Actions → .env.dev on remote
make prod-deploy → .env.prod → act → GitHub Actions → .env.prod on remote
```

### Actual Deployment (CI/CD)
```
GitHub Actions → GitHub Secrets → .env.dev or .env.prod on remote
```

## Benefits

1. **Less Duplication**: 2 files instead of 4
2. **Clear Commands**: Naming makes intent obvious
3. **Consistent**: Same file names local and remote
4. **Automatic**: Secrets update on every run
5. **Centralized**: Makefile is the command hub
6. **Debuggable**: Files persist for inspection

## Migration Guide

If you have old commands:
- `make dev` → `make dev-local`
- `make dev-detached` → `make dev-local-detached`
- `make test-deploy` → `make dev-deploy`
- `make test-deploy-prod` → `make prod-deploy`

Old files to remove:
- `.secrets.dev` (no longer used)
- `.secrets.prod` (no longer used)
- `scripts/load-env-and-run.sh` (renamed to `docker-compose-with-env.sh`)

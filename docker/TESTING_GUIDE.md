# Testing Guide

## Quick Testing Commands

### 1. Local Development (Daily Use)
```bash
# Start dev environment locally
make dev-local-detached

# Check health
make health

# View logs
make logs

# Stop
make stop
```

### 2. Local Production Testing
```bash
# Test with production config locally
make prod-local-detached

# Check health
make health

# View logs
make logs

# Stop
make stop
```

### 3. Test Remote Deployment (Dev)
```bash
# Sync secrets first (updates .env.dev)
make sync-secrets

# Test dev deployment to remote with act
make dev-deploy
```

### 4. Test Remote Deployment (Prod)
```bash
# Sync secrets first (updates .env.prod)
make sync-secrets

# Test prod deployment to remote with act
make prod-deploy
```

## Environment Files

After running commands, you'll have:
- `.env.dev` - Dev secrets (from Doppler dev_personal)
- `.env.prod` - Prod secrets (from Doppler prd)

These files:
- Are updated automatically on every local run
- Persist between runs for inspection
- Are used by act for remote deployment testing
- Have the same names on local and remote (consistent)

**No separate "secrets" files** - the `.env.*` files serve both purposes.

## Command Naming

- **`*-local`**: Runs on your machine (dev-local, prod-local)
- **`*-deploy`**: Tests deployment to remote via act (dev-deploy, prod-deploy)
- **`*-detached`**: Runs in background

## Troubleshooting

### Containers won't start
```bash
# Clean everything and try again
make clean
make dev-local-detached
```

### Check specific service logs
```bash
make logs-miner
make logs-classifier
make logs-migrate
```

### Shell into container
```bash
make shell-miner
make shell-classifier
```

### Check container status
```bash
make ps
```

### Manual health check
```bash
curl http://localhost:8000/health  # Miner
curl http://localhost:8001/health  # Classifier
```

### Inspect environment files
```bash
cat .env.dev     # Dev config
cat .env.prod    # Prod config
```

## Best Practices

1. **Local development**: Use `make dev-local-detached` for daily work
2. **Before deployment**: Run `make dev-deploy` to test the full deployment flow
3. **Check logs**: Always check `make logs` after starting services
4. **Health checks**: Use `make health` to verify services are running
5. **Clean slate**: Use `make clean` when switching between dev/prod or debugging

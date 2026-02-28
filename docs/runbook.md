# SeshOps On-Call Runbook

## Quick Reference

| Service    | Port | Health            | Logs                             |
| ---------- | ---- | ----------------- | -------------------------------- |
| API        | 8000 | `GET /health`     | `docker logs seshops-api`        |
| Postgres   | 5432 | `pg_isready`      | `docker logs seshops-db`         |
| Grafana    | 3000 | `GET /api/health` | `docker logs seshops-grafana`    |
| Prometheus | 9090 | `GET /-/healthy`  | `docker logs seshops-prometheus` |

---

## 1. Health Check

```bash
curl -s http://localhost:8000/health | python3 -m json.tool
```

Expected response:

```json
{
  "status": "healthy",
  "components": {
    "api": "healthy",
    "database": "healthy",
    "llm": "healthy"
  }
}
```

**If `status` is `degraded`**, check which component is `unhealthy`.

---

## 2. Common Failure Modes

### Database Unreachable

**Symptoms:** `/health` returns `database: unhealthy`, API returns 500s.

```bash
# Check Postgres
docker exec seshops-db pg_isready -U seshops

# Restart
docker compose restart db

# Check connection from API container
docker exec seshops-api python -c "from app.models.engine import engine; print(engine.url)"
```

### LLM Circuit Breaker Open

**Symptoms:** `/health` returns `llm: unhealthy`, triage returns `RuntimeError: circuit breaker is open`.

The circuit auto-resets after 60 seconds. If persistent:

```bash
# Check API key validity
curl https://api.openai.com/v1/models -H "Authorization: Bearer $OPENAI_API_KEY"

# Check logs for the root cause
docker logs seshops-api 2>&1 | grep "circuit_opened"
```

### Triage Timeout (504)

**Symptoms:** Triage requests hang and return 504 after 120s.

```bash
# Check if LLM is responding
docker logs seshops-api 2>&1 | grep "seshops_llm_call"

# Check rate limits
docker logs seshops-api 2>&1 | grep "RateLimitError"
```

### Authentication Errors

**Symptoms:** Users get 401/403 on protected endpoints.

```bash
# Verify JWT secret is set
docker exec seshops-api env | grep JWT_SECRET_KEY

# Check token format
echo "$TOKEN" | cut -d. -f2 | base64 -d 2>/dev/null | python3 -m json.tool
```

---

## 3. Common Operations

### Restart API

```bash
docker compose restart api
```

### View Structured Logs

```bash
# Recent errors
docker logs seshops-api 2>&1 | grep "\[error\]" | tail -20

# Triage requests
docker logs seshops-api 2>&1 | grep "seshops_triage" | tail -20
```

### Rotate JWT Secret

1. Generate a new secret: `openssl rand -hex 64`
2. Set `JWT_SECRET_KEY` in `.env.production`
3. Restart: `docker compose restart api`
4. **Note:** All existing tokens will be invalidated immediately.

### Check Metrics

- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3000` (default: admin/admin — **change in production**)
- Key metrics:
  - `seshops_triage_requests_total` — triage volume
  - `seshops_request_duration_seconds` — latency
  - `seshops_request_count` — overall traffic

---

## 4. Escalation

If you cannot resolve the issue:

1. Check the ADRs in `docs/adr/` for design context.
2. Check `CONTRIBUTING.md` for architecture overview.
3. Review recent git history: `git log --oneline -20`

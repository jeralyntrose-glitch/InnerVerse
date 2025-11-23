# 📋 Migration Checklist

Use this checklist to migrate from the old `main.py` to the new refactored structure.

---

## ✅ Phase 1: Setup & Verification (Day 1)

### Environment Setup

- [ ] **Copy environment template**
  ```bash
  cp .env.example .env
  ```

- [ ] **Fill in your API keys in `.env`**
  - [ ] OPENAI_API_KEY
  - [ ] ANTHROPIC_API_KEY
  - [ ] PINECONE_API_KEY
  - [ ] DATABASE_URL
  - [ ] CSRF_SECRET_KEY (generate new one)

- [ ] **Generate CSRF secret**
  ```bash
  python -c "import secrets; print(secrets.token_urlsafe(32))"
  ```

- [ ] **Install dependencies**
  ```bash
  pip install -e ".[dev]"
  ```

### Database Setup

- [ ] **Backup existing database**
  ```bash
  pg_dump $OLD_DATABASE_URL > backup_$(date +%Y%m%d).sql
  ```

- [ ] **Run migrations**
  ```bash
  alembic upgrade head
  ```

- [ ] **Verify tables created**
  ```bash
  psql $DATABASE_URL -c "\dt"
  ```

### Test New Application

- [ ] **Start new application**
  ```bash
  python app.py
  ```

- [ ] **Test health check**
  ```bash
  curl http://localhost:5000/health
  ```

- [ ] **Browse to app**
  - Open http://localhost:5000
  - Test basic navigation

- [ ] **Check API docs**
  - Open http://localhost:5000/docs

---

## ✅ Phase 2: Verify Core Functionality (Day 1-2)

### Test Existing Routes

- [ ] **Chat functionality**
  - [ ] Test chat interface loads
  - [ ] Send a test message
  - [ ] Verify response received

- [ ] **Learning paths**
  - [ ] View courses list
  - [ ] Open a course
  - [ ] View a lesson

- [ ] **Health & monitoring**
  - [ ] Health check returns 200
  - [ ] Usage statistics accessible
  - [ ] No error messages in logs

### Check Logs

- [ ] **Verify structured logging works**
  ```bash
  # Should see formatted logs, not print statements
  tail -f logs/innerverse.log  # if LOG_FILE is set
  ```

- [ ] **Check for errors**
  ```bash
  # Look for ERROR or CRITICAL level logs
  grep -i error logs/innerverse.log
  ```

---

## ✅ Phase 3: Docker Setup (Day 2-3)

### Docker Testing

- [ ] **Build Docker image**
  ```bash
  docker-compose build
  ```

- [ ] **Start with Docker**
  ```bash
  docker-compose up -d
  ```

- [ ] **Check container health**
  ```bash
  docker-compose ps
  ```

- [ ] **Test application via Docker**
  - [ ] http://localhost:5000/health
  - [ ] http://localhost:5000/docs

- [ ] **Check logs**
  ```bash
  docker-compose logs -f app
  ```

- [ ] **Verify database connectivity**
  ```bash
  docker-compose exec app python -c "from src.core.database import get_db_connection; print('OK')"
  ```

---

## ✅ Phase 4: Migrate Custom Code (Week 1)

If you have custom routes in `main_legacy.py`:

### Identify Custom Routes

- [ ] **List your custom endpoints**
  ```bash
  grep "@app\." main_legacy.py | grep -v "^#"
  ```

- [ ] **Document which routes need migration**
  - Write down each custom route
  - Note what it does
  - Check if it already exists in new structure

### Migrate Routes

For each custom route:

- [ ] **Create appropriate route file**
  - Document routes → `src/api/document_routes.py`
  - YouTube routes → `src/api/youtube_routes.py`
  - etc.

- [ ] **Update imports** to use new structure
  ```python
  # Old:
  from main import something
  
  # New:
  from src.core.config import get_settings
  from src.core.database import get_db_cursor
  from src.api.dependencies import get_pinecone_index
  ```

- [ ] **Use dependency injection**
  ```python
  from fastapi import Depends
  from src.api.dependencies import get_db
  
  @router.get("/route")
  async def handler(db=Depends(get_db)):
      ...
  ```

- [ ] **Update exception handling**
  ```python
  from src.core.exceptions import ResourceNotFoundError
  
  if not found:
      raise ResourceNotFoundError(
          message="Resource not found",
          resource_id=resource_id
      )
  ```

- [ ] **Add to app.py**
  ```python
  from src.api.your_routes import router as your_router
  app.include_router(your_router)
  ```

- [ ] **Test migrated route**

---

## ✅ Phase 5: Testing (Week 1-2)

### Write Tests

- [ ] **Add tests for custom routes**
  ```python
  # tests/test_api/test_your_routes.py
  def test_your_endpoint(client):
      response = client.get("/your/endpoint")
      assert response.status_code == 200
  ```

- [ ] **Run test suite**
  ```bash
  pytest
  ```

- [ ] **Check coverage**
  ```bash
  pytest --cov=src --cov-report=html
  open htmlcov/index.html
  ```

- [ ] **Fix failing tests**

### Integration Testing

- [ ] **Test complete user flows**
  - [ ] User signup/login (if applicable)
  - [ ] Upload document
  - [ ] Create course
  - [ ] Complete lesson
  - [ ] Chat with AI

- [ ] **Test error scenarios**
  - [ ] Invalid input
  - [ ] Missing data
  - [ ] Network errors

---

## ✅ Phase 6: CI/CD Setup (Week 2)

### GitHub Actions

- [ ] **Push code to GitHub**
  ```bash
  git add .
  git commit -m "refactor: migrate to new structure"
  git push origin main
  ```

- [ ] **Check GitHub Actions run**
  - Go to your repo → Actions tab
  - Verify CI pipeline runs
  - Fix any failing checks

- [ ] **Setup branch protection** (optional)
  - Require PR reviews
  - Require CI to pass
  - Require up-to-date branches

### Secrets Configuration

- [ ] **Add secrets to GitHub**
  - Go to repo Settings → Secrets and variables → Actions
  - Add production environment secrets:
    - OPENAI_API_KEY
    - ANTHROPIC_API_KEY
    - PINECONE_API_KEY
    - DATABASE_URL (for deployment)

---

## ✅ Phase 7: Deployment (Week 2-3)

### Pre-Deployment

- [ ] **Review security settings**
  - [ ] ENVIRONMENT=production
  - [ ] DEBUG=false
  - [ ] COOKIE_SECURE=true
  - [ ] ALLOWED_ORIGINS set correctly
  - [ ] Strong CSRF_SECRET_KEY

- [ ] **Test production build locally**
  ```bash
  ENVIRONMENT=production python app.py
  ```

- [ ] **Run security scan**
  ```bash
  bandit -r src/
  ```

### Deploy

- [ ] **Choose deployment platform**
  - [ ] AWS ECS
  - [ ] Google Cloud Run
  - [ ] Azure Container Apps
  - [ ] DigitalOcean App Platform
  - [ ] Heroku
  - [ ] Your own server

- [ ] **Configure production database**
  - [ ] Create production PostgreSQL instance
  - [ ] Run migrations: `alembic upgrade head`
  - [ ] Backup strategy configured

- [ ] **Deploy application**
  - Follow your platform's deployment guide
  - Use the Dockerfile we created

- [ ] **Configure DNS** (if applicable)

- [ ] **Setup SSL/TLS certificates**

### Post-Deployment

- [ ] **Test production deployment**
  - [ ] Health check accessible
  - [ ] API endpoints work
  - [ ] Frontend loads
  - [ ] No errors in logs

- [ ] **Setup monitoring**
  - [ ] Error tracking (Sentry)
  - [ ] APM (Datadog, New Relic)
  - [ ] Uptime monitoring (UptimeRobot)

- [ ] **Setup alerts**
  - [ ] Error rate threshold
  - [ ] Response time threshold
  - [ ] Disk space
  - [ ] Memory usage

---

## ✅ Phase 8: Cleanup & Documentation (Week 3-4)

### Code Cleanup

- [ ] **Remove `main_legacy.py`** (after verifying everything works)
  ```bash
  git rm main_legacy.py
  git commit -m "chore: remove legacy main.py"
  ```

- [ ] **Remove any old/unused files**

- [ ] **Update documentation**
  - [ ] Update README if needed
  - [ ] Document any custom setup
  - [ ] Create architecture diagrams (optional)

### Team Onboarding

- [ ] **Share REFACTORING_SUMMARY.md** with team

- [ ] **Conduct code review session**
  - Walk through new structure
  - Explain dependency injection
  - Show how to add new routes
  - Demonstrate testing

- [ ] **Update development wiki/docs**

---

## ✅ Phase 9: Optimization (Ongoing)

### Performance

- [ ] **Profile application**
  ```bash
  pip install py-spy
  py-spy record -o profile.svg -- python app.py
  ```

- [ ] **Optimize slow endpoints**

- [ ] **Add caching** where appropriate
  - Use Redis for session data
  - Cache expensive queries
  - Cache API responses

### Monitoring

- [ ] **Review error logs weekly**

- [ ] **Track key metrics**
  - Response times
  - Error rates
  - Database query times
  - API costs

- [ ] **Setup dashboards**

---

## 🎯 Success Criteria

You've successfully migrated when:

✅ All tests pass  
✅ No errors in logs  
✅ All custom routes migrated  
✅ Application runs in Docker  
✅ CI/CD pipeline passes  
✅ Deployed to production  
✅ Team understands new structure  
✅ Monitoring in place  

---

## 🆘 Rollback Plan

If you need to revert:

1. **Keep `main_legacy.py`** until 100% confident
2. **Use git** to revert if needed:
   ```bash
   git revert HEAD
   ```
3. **Database backups** allow you to restore data
4. **Docker makes it easy** to switch between versions

---

## 📞 Need Help?

- Review REFACTORING_SUMMARY.md
- Check README.md
- Look at CONTRIBUTING.md
- Review existing test files for examples

---

**Good luck with your migration! 🚀**


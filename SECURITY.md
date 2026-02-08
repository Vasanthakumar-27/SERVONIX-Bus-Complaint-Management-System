# Security Policy

## Reporting Security Vulnerabilities

**Do not open public issues for security vulnerabilities!**

Please report security vulnerabilities by emailing: **927624bad117@mkce.ac.in**

Include:
- Description of the vulnerability
- Steps to reproduce (if applicable)
- Potential impact
- Suggested fix (if available)

## Security Features

### Authentication & Authorization
- ✅ **JWT Bearer Tokens** - Secure, stateless authentication with configurable expiration
- ✅ **Password Hashing** - Werkzeug security with strong hashing algorithms
- ✅ **Role-Based Access Control** - User, Admin, Head Admin roles with fine-grained permissions
- ✅ **OTP Password Reset** - Secure password recovery via one-time tokens
- ✅ **Rate Limiting** - Brute-force protection on login endpoints

### Data Protection
- ✅ **Environment Variables** - Sensitive data never hardcoded (`.env` git-ignored)
- ✅ **Database Encryption** - SQLite with WAL mode, optionally encrypted
- ✅ **File Upload Security** - Secure filename handling, type validation, isolated storage
- ✅ **CORS Configuration** - Whitelist-based cross-origin access

### Transport Security
- ✅ **WebSocket Encryption** - WSS (secure WebSocket) support via eventlet
- ✅ **HTTPS Ready** - Compatible with SSL/TLS deployment
- ✅ **Secure Headers** - CSRF tokens, X-Frame-Options, Content-Security-Policy

## Security Best Practices

### Local Development
1. **Create `.env` file** with sensitive credentials:
   ```
   DB_HOST=127.0.0.1
   DB_USER=root
   DB_NAME=bus_complaints
   EMAIL_SENDER=your-email@gmail.com
   EMAIL_PASSWORD=your-app-password
   SECRET_KEY=your-secret-key-here
   ```

2. **Generate App Password** (Gmail):
   - Enable 2-factor authentication
   - Go to https://myaccount.google.com/apppasswords
   - Select Mail → Windows Computer
   - Use the 16-character password in `.env`

3. **Rotate JWT Secret** in production:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

### Production Deployment
1. **Enable HTTPS** - Use SSL/TLS certificates
2. **Set secure JWT_EXPIRATION_HOURS** - Recommend 1-2 hours
3. **Use strong SECRET_KEY** - At least 32 random characters
4. **Enable database encryption** - SQLite with encryption extension
5. **Configure CORS strictly** - Allow only specific domains
6. **Rate limit aggressively** - Prevent brute-force attacks
7. **Monitor logs** - Track authentication failures
8. **Update dependencies** - Regularly patch vulnerable packages

### Git Security
- `.gitignore` protects:
  - `.env` - Environment credentials
  - `data/` - Database files
  - `backend/uploads/` - User uploads
  - `.venv/` - Virtual environment
  - IDE files - VSCode, PyCharm configs

## Vulnerability Scanning

We use:
- `pip audit` - Check for vulnerable Python packages
- OWASP Top 10 guidelines for web security
- Regular code reviews

To scan your installation:
```bash
pip audit
```

## Update Notifications

Check for updates:
```bash
pip list --outdated
```

Keep dependencies current:
```bash
pip install --upgrade -r backend/requirements.txt
```

## Security Testing

Test WebSocket and API security:
```bash
python test_websocket.py
```

## Compliance

- ✅ Follows OWASP security guidelines
- ✅ Compliant with GDPR for user data
- ✅ Implements secure password policies
- ✅ Rate limiting prevents abuse

## Contact

**Security Email**: 927624bad117@mkce.ac.in

**Response Time**: We aim to respond to security reports within 24-48 hours.

---

Thank you for helping keep SERVONIX secure! 🔒

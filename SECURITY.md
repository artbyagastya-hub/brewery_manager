# Brewery Manager - Security Documentation

## Security Features Implemented

### 1. Secret Key Management
- **Status**: ✅ Implemented
- **Details**: 
  - Secret key is now loaded from environment variable `SECRET_KEY`
  - Falls back to randomly generated key if not set
  - Uses `secrets.token_hex(32)` for cryptographically secure generation
  - **Important**: Always set `SECRET_KEY` in production via `.env` file

### 2. HTTPS Enforcement (Talisman)
- **Status**: ✅ Implemented
- **Details**:
  - Flask-Talisman integration for HTTPS enforcement
  - Force HTTPS in production environment (`FLASK_ENV=production`)
  - Content Security Policy (CSP) headers configured
  - Referrer policy set to `strict-origin-when-cross-origin`
  - Session cookies secured in production

### 3. CSRF Protection
- **Status**: ✅ Implemented
- **Details**:
  - Flask-WTF CSRF protection enabled
  - All POST forms require CSRF tokens
  - Protects against cross-site request forgery attacks

### 4. Rate Limiting
- **Status**: ✅ Implemented
- **Details**:
  - Flask-Limiter integration
  - Global limits: 200 requests/day, 50 requests/hour
  - Login endpoint: 5 attempts per minute
  - API endpoints: 10-30 requests per minute (varies by endpoint)
  - Prevents brute force attacks and API abuse

### 5. Session Security
- **Status**: ✅ Implemented
- **Details**:
  - `SESSION_COOKIE_SECURE`: True in production (HTTPS only)
  - `SESSION_COOKIE_HTTPONLY`: True (no JavaScript access)
  - `SESSION_COOKIE_SAMESITE`: Lax (CSRF protection)
  - `PERMANENT_SESSION_LIFETIME`: 1 hour

### 6. Input Validation & Sanitization
- **Status**: ✅ Implemented
- **Details**:
  - Created `utils/validation.py` with sanitization functions
  - HTML tag removal using bleach library
  - Email validation
  - Phone number validation (Vietnamese format)
  - Date format validation
  - Numeric validation with range checking
  - Form data sanitization utility

### 7. Content Security Policy (CSP)
- **Status**: ✅ Implemented
- **Details**:
  - Restricts resource loading to trusted sources
  - Allows CDN resources (Bootstrap, Chart.js, Font Awesome)
  - WebSocket connections allowed for real-time features
  - Prevents XSS attacks via CSP headers

## Security Headers

The following security headers are automatically set by Talisman:

- `Strict-Transport-Security`: Forces HTTPS
- `Content-Security-Policy`: Controls resource loading
- `X-Content-Type-Options`: Prevents MIME sniffing
- `X-Frame-Options`: Prevents clickjacking
- `X-XSS-Protection`: XSS filter (legacy browsers)

## Environment Variables

Required security-related environment variables:

```bash
# Required in production
SECRET_KEY=your-secret-key-here-min-32-chars
FLASK_ENV=production

# Optional
FLASK_DEBUG=false
```

## Best Practices for Deployment

1. **Always set SECRET_KEY** in production
2. **Use HTTPS** with valid SSL certificates
3. **Set FLASK_ENV=production** to enable security features
4. **Keep dependencies updated** regularly
5. **Monitor rate limit logs** for abuse detection
6. **Review CSP violations** in browser console

## Known Limitations

1. Rate limiting uses in-memory storage (resets on restart)
   - **Recommendation**: Use Redis for production (`storage_uri="redis://localhost:6379"`)

2. No password complexity requirements enforced
   - **Recommendation**: Add password strength validation

3. No account lockout after failed attempts
   - **Recommendation**: Implement account lockout policy

4. No email verification for new accounts
   - **Recommendation**: Add email verification flow

## Future Security Enhancements

- [ ] Redis-based rate limiting for persistence
- [ ] Password complexity requirements
- [ ] Account lockout after failed login attempts
- [ ] Two-factor authentication (2FA)
- [ ] Email verification for new accounts
- [ ] Audit logging for security events
- [ ] Automated security scanning
- [ ] Dependency vulnerability scanning
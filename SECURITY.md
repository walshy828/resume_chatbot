# Security Features - Quick Start Guide

## 🔒 Security Enhancements Implemented

This application now includes comprehensive security hardening with modern best practices.

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Database Migration
```bash
python3 migrate_user_security.py
```

### 3. Configure Environment
Copy `.env.example` to `.env` and update:
```bash
cp .env.example .env
```

**Important settings:**
- `SECRET_KEY` - Generate a strong secret key
- `SESSION_COOKIE_SECURE` - Set to `True` in production with HTTPS
- `CORS_ALLOWED_ORIGINS` - Restrict to your domain(s)

### 4. First Login
- Default credentials: `admin` / `changeme123`
- **You will be forced to change password on first login**

## 🆕 New Features

### User Management
Access at `/admin/users`

- Create new admin users
- Add email addresses for users
- Edit user details
- Deactivate/activate accounts
- Unlock locked accounts
- View login history

### Password Security
- Minimum 12 characters
- Must include: uppercase, lowercase, numbers, special characters
- Real-time strength indicator
- Blocks common passwords
- Prevents sequential/repeated characters

### Account Protection
- **5 failed login attempts** → 30-minute lockout
- Automatic unlock after lockout period
- Manual unlock by admins
- Failed attempt tracking

### Security Logging
All security events logged to `logs/security.log`:
- Login attempts (success/failure)
- Account lockouts
- Password changes
- User management actions
- Unauthorized access attempts

## 🛡️ Security Features

### Rate Limiting
- **Login**: 5 attempts per 15 minutes
- **API**: 100 requests per hour
- **Chat**: 30 messages per minute
- **Uploads**: 10 per hour
- **Admin actions**: 50 per hour

### Security Headers
- Content-Security-Policy (CSP)
- X-Frame-Options: DENY
- X-Content-Type-Options: nosniff
- X-XSS-Protection
- Strict-Transport-Security (HSTS in production)
- Referrer-Policy
- Permissions-Policy

### CSRF Protection
- All forms protected with CSRF tokens
- Automatic validation
- SSL-strict mode in production

### Session Security
- 1-hour timeout (configurable)
- Secure cookies in production
- HttpOnly cookies
- SameSite: Strict
- Auto-refresh on activity

## 📋 Admin Routes

| Route | Purpose |
|-------|---------|
| `/admin/login` | Admin login |
| `/admin/logout` | Logout |
| `/admin/change-password` | Change your password |
| `/admin/users` | User management |
| `/admin/users/create` | Create new user |
| `/admin/users/<id>/edit` | Edit user |
| `/admin/users/<id>/unlock` | Unlock locked account |

## 🔧 Configuration

### Environment Variables

```bash
# Security Settings
SESSION_COOKIE_SECURE=True  # Enable in production with HTTPS
SESSION_LIFETIME=3600  # Session timeout (seconds)
CORS_ALLOWED_ORIGINS=https://yourdomain.com
BCRYPT_LOG_ROUNDS=14  # Password hashing strength
MAX_LOGIN_ATTEMPTS=5
ACCOUNT_LOCKOUT_DURATION=30  # minutes

# Rate Limiting
RATELIMIT_STORAGE_URL=redis://localhost:6379  # Use Redis in production
```

### Production Deployment

1. **Generate strong SECRET_KEY**:
   ```python
   import secrets
   print(secrets.token_hex(32))
   ```

2. **Enable secure cookies**:
   ```bash
   SESSION_COOKIE_SECURE=True
   ```

3. **Set up Redis** for rate limiting:
   ```bash
   RATELIMIT_STORAGE_URL=redis://localhost:6379
   ```

4. **Configure CORS**:
   ```bash
   CORS_ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
   ```

5. **Set up HTTPS** (required for secure cookies)

## 📊 Monitoring

### Security Logs
Location: `logs/security.log`

Monitor for:
- Repeated failed login attempts
- Account lockouts
- Suspicious activity patterns
- Unauthorized access attempts

### Log Format
```
2025-12-05 15:30:45 - security - WARNING - Failed login attempt - Username: admin, IP: 192.168.1.100, Reason: Invalid password
2025-12-05 15:31:12 - security - INFO - Successful login - Username: admin, IP: 192.168.1.100
2025-12-05 15:35:20 - security - INFO - Password changed - Username: admin, IP: 192.168.1.100
```

## 🧪 Testing

### Test Login Security
1. Attempt 6 failed logins → should lock account
2. Verify locked message appears
3. Check `logs/security.log` for events

### Test Password Strength
1. Try weak password → should be rejected
2. Try password with username → should be rejected
3. Use strong password → should succeed

### Test User Management
1. Create new user at `/admin/users/create`
2. Add email address
3. Set "must change password"
4. Login as new user → forced to change password

## 🚨 Troubleshooting

### Account Locked
- Wait 30 minutes for auto-unlock
- OR admin can unlock at `/admin/users`

### Forgot Password
- Currently requires admin to reset
- Email-based reset coming in future update

### Rate Limited
- Wait for the time window to expire
- Check `RATELIMIT_STORAGE_URL` configuration

### Security Log Not Created
- Ensure `logs/` directory exists
- Check file permissions
- Logs created automatically on first security event

## 📝 Best Practices

1. **Change default password immediately**
2. **Use strong, unique passwords**
3. **Enable 2FA** (coming soon)
4. **Review security logs regularly**
5. **Keep dependencies updated**
6. **Use HTTPS in production**
7. **Restrict CORS origins**
8. **Set up Redis for production**
9. **Monitor failed login attempts**
10. **Regular security audits**

## 🔄 Updates & Maintenance

### Update Dependencies
```bash
pip install --upgrade -r requirements.txt
```

### Check for Vulnerabilities
```bash
pip install pip-audit
pip-audit
```

### Backup Database
```bash
cp instance/chatbot.db instance/chatbot.db.backup
```

## 📚 Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Flask Security Best Practices](https://flask.palletsprojects.com/en/latest/security/)
- [Password Security Guidelines](https://pages.nist.gov/800-63-3/sp800-63b.html)

## 🆘 Support

For security issues or questions:
1. Check `logs/security.log`
2. Review this documentation
3. Check implementation plan in `brain/implementation_plan.md`
4. Review walkthrough in `brain/walkthrough.md`

# Auth Service

OpenAuth-compatible OAuth token and userinfo service for local/UAT deployment.

Runtime credentials are configured through environment variables. Passwords are
stored as PBKDF2-SHA256 hashes in `OPENAUTH_USERS_JSON`; production deployments
must replace the local development identities and secrets.

For large local/UAT identity sets, set `OPENAUTH_USERS_JSON_FILE` to a mounted
JSON file path instead of putting hundreds of users into one environment
variable. This avoids process argument/environment length limits when loading
generated UAT students.

Pupil self-registration uses the protected `POST /internal/users` provisioning
endpoint. Configure `OPENAUTH_REGISTERED_USERS_JSON_FILE` on persistent storage;
new passwords are PBKDF2-SHA256 hashed before that file is written. The API must
send `OPENAUTH_CLIENT_SECRET`, and teacher accounts remain administrator-managed.

Create a new password hash:

```bash
python -m auth_service.hash_password 'new-password'
```

Endpoints:

- `POST /oauth/token`
- `POST /internal/users` (protected provisioning)
- `GET /userinfo`
- `GET /health`

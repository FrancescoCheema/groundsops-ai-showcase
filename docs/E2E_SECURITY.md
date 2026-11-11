# End-to-end testing and security checks

The Playwright suite verifies the public sign-in surface, the API authentication
boundary, and a complete development-mode workspace login. Failed runs retain a
trace, screenshot, and video for diagnosis.

## Local execution

Start PostgreSQL and the API, apply migrations, and then run:

```powershell
$env:NEXT_PUBLIC_API_URL = "http://127.0.0.1:8000"
$env:NEXT_PUBLIC_AUTH_MODE = "development"
$env:PLAYWRIGHT_API_URL = "http://127.0.0.1:8000"
npm --prefix .\frontend run test:e2e
```

To inspect an HTML report:

```powershell
npm --prefix .\frontend run test:e2e:report
```

## Continuous integration

`quality-security.yml` runs backend linting and tests, Python dependency audit,
the frontend production build, production npm audit, Playwright against an
ephemeral PostgreSQL database, and Gitleaks secret scanning.

The npm audit currently blocks critical production findings. The remaining
Next.js/PostCSS advisory requires a separately tested framework-major upgrade;
it must not be force-fixed inside unrelated feature work.

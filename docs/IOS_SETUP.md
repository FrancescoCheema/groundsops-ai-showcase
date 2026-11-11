# GroundsOps on iOS

The web frontend is installable as a PWA and is configured for a native Capacitor wrapper.
Both use the existing Next.js interface and FastAPI API.

## Fastest daily-use option

Deploy the frontend and API over HTTPS, open the frontend in Safari on the iPhone, then choose
**Share > Add to Home Screen**. Camera and file uploads use the existing mobile file picker.

## Create the native Xcode project

Run these commands from `frontend` on macOS:

```bash
npm install
npm run ios:setup
```

The setup command installs Capacitor, creates the native `ios` project, builds and synchronizes
the web application, adds camera/photo/location usage descriptions, and opens Xcode.

In Xcode, select your Apple development team and a unique bundle identifier, then run on a
connected iPhone. After each web change, run `npm run ios:sync` before rebuilding in Xcode.

## Required before TestFlight

- Set `NEXT_PUBLIC_API_URL` to an HTTPS API reachable by the phone.
- Set backend `CORS_ORIGIN_REGEX` to include both the public frontend and
  `capacitor://localhost`.
- Replace the provisional SVG icon with 1024px App Store artwork and generated iOS icon sizes.
- Add a privacy policy and App Store privacy disclosures for photos, location, files, and account data.
- Test authentication, uploads, offline failures, permission prompts, and account deletion on a real iPhone.
- Keep Cognito secrets and AWS credentials out of the app bundle.

The service worker caches only the application shell. It intentionally does not cache API responses
or private File Vault content.

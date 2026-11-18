# Security and deployment boundary

This is a single-user, local development application. It has no authentication or tenant isolation. Bind it to `127.0.0.1`; do not expose the API, MJPEG stream, database, or frontend dev server to a public network.

Mutating browser requests from unrelated origins are rejected. Host headers are constrained to localhost and loopback. Evidence paths are resolved from database UUIDs and checked against their storage root. These controls do not replace authentication for a remote deployment.

The model runs locally. No inference images are sent to a third-party AI API. Model download is a separate setup operation from official Ultralytics assets. Synchronization is disabled in the runtime model settings. Fonts and dashboard assets are local after the frontend build.

`.env`, `data/`, model weights and database files are excluded from Git. Check staged files before publishing. A private snapshot may still exist locally after monitoring ends; this release has no automatic retention/deletion policy.

## Development dependency advisory

The initial full npm audit reports an unresolved development dependency chain involving `picomatch`, `fdir`, `tinyglobby`, and Vite: [GHSA-fc5q-39xc-vjpf](https://github.com/advisories/GHSA-fc5q-39xc-vjpf). The current registry's latest picomatch version was still within the affected range when checked on November 18, 2026.

The affected operation is glob matching with adversarial patterns. The application does not accept glob patterns from users; the tools process the repository's own source patterns. The frontend build tool is not used to serve the built application in the normal run command. Keep the development server local and recheck for a patched release before upgrading or deploying development tooling.

The older Vite version suggested by the first audit response had separate file-access advisories, so the project retains the newer Vite 7.3.8 build tool rather than downgrading to it. `npm audit --omit=dev` checks the shipped runtime dependency set separately; a clean production-only audit does not resolve the full development audit.

Report vulnerabilities privately to the repository owner before disclosing sensitive reproduction material. Do not attach real surveillance footage or credentials to public issues.

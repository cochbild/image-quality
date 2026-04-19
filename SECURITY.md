# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| Latest  | Yes       |
| Older   | No        |

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

To report a security vulnerability, please contact **Dale Cochran** via [GitHub](https://github.com/cochbild).

Include as much of the following information as possible:

- Type of issue (e.g. buffer overflow, SQL injection, XSS, SSRF, auth bypass)
- Full paths of source file(s) related to the issue
- Location of the affected source code (tag/branch/commit or direct URL)
- Any special configuration required to reproduce the issue
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if possible)
- Impact of the issue, including how an attacker might exploit it

This is a solo-maintained project, so response times may vary. I will do my best to acknowledge your report and work toward a fix, but I cannot guarantee specific timelines.

## Scope

This project runs LM Studio HTTP calls, reads/writes image files on mounted host paths, and exposes a FastAPI backend plus an nginx-served React frontend. Areas of particular interest for reports:

- Path traversal in image serving or file-move logic
- SSRF via configurable `LM_STUDIO_URL` / `HOMEHUB_API_URL`
- Auth/authorization gaps on the backend API
- SQL injection or unsafe query construction
- Secrets leakage via logs or responses

## Disclosure Policy

- I will acknowledge receipt of your report as soon as I can
- I will investigate the vulnerability and assess its impact
- I will release a fix when one is ready, depending on complexity and severity
- I will coordinate public disclosure after the fix is available

Thank you for helping keep this project and its users safe.

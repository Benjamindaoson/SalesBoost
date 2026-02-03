# Security Policy

## Supported Versions

We release patches for security vulnerabilities. Which versions are eligible for receiving such patches depends on the CVSS v3.0 Rating:

| Version | Supported          |
| ------- | ------------------ |
| 2.0.x   | :white_check_mark: |
| 1.0.x   | :x:                |

## Reporting a Vulnerability

Please report (suspected) security vulnerabilities to **security@salesboost.ai**. You will receive a response from us within 48 hours. If the issue is confirmed, we will release a patch as soon as possible depending on complexity.

### What to Include

* Type of issue (e.g. buffer overflow, SQL injection, cross-site scripting, etc.)
* Full paths of source file(s) related to the manifestation of the issue
* The location of the affected source code (tag/branch/commit or direct URL)
* Any special configuration required to reproduce the issue
* Step-by-step instructions to reproduce the issue
* Proof-of-concept or exploit code (if possible)
* Impact of the issue, including how an attacker might exploit the issue

### What to Expect

* Acknowledgment of your report within 48 hours
* Regular updates on the progress of fixing the vulnerability
* Credit in the security advisory (unless you prefer to remain anonymous)

## Security Best Practices

When deploying SalesBoost:

1. **Environment Variables**: Never commit `.env` files or expose API keys
2. **Database**: Use strong passwords and enable SSL connections in production
3. **API Keys**: Rotate API keys regularly
4. **HTTPS**: Always use HTTPS in production
5. **Updates**: Keep dependencies up to date
6. **Access Control**: Implement proper authentication and authorization
7. **Rate Limiting**: Enable rate limiting on API endpoints
8. **Monitoring**: Set up security monitoring and alerting

## Known Security Considerations

* This application uses AI models - be aware of prompt injection risks
* User input should always be sanitized
* Implement proper CORS policies
* Use secure session management

## Disclosure Policy

* We will acknowledge your report within 48 hours
* We will provide an estimated timeline for a fix
* We will notify you when the vulnerability is fixed
* We will publicly disclose the vulnerability after a patch is released

Thank you for helping keep SalesBoost and our users safe!

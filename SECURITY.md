# Security Policy

Please do not report suspected vulnerabilities in a public issue. Use GitHub's private vulnerability reporting feature for this repository when available, or contact the repository owner through a private channel listed on their GitHub profile.

Never commit API keys, tokens, cookies, private URLs, user health information, or populated `.env` files. The checked-in `.env.example` contains configuration names and safe defaults only.

MediVita limits request sizes, validates public inputs, restricts CORS through configuration, applies external-request timeouts, and returns normalized errors rather than internal exception details. These controls reduce risk but do not replace a deployment-specific security review.

# Product Discovery Terminal Compliance Notes

Product Discovery Terminal is a private internal product research and FBA unit-economics tool for Adam Menker's own Amazon seller account.

The application uses Amazon Selling Partner API only for product research workflows, specifically catalog data, pricing and offer information, and product fee-estimate data. It does not access restricted buyer PII, order data, buyer messages, shipping addresses, tax data, or other restricted role data.

The tool is operated by the account owner/developer only. It is not a public SaaS product, not offered to third-party sellers, and not intended for third-party user access.

Security controls for SP-API production readiness are documented in this folder:

- [SECURITY.md](SECURITY.md)
- [ACCESS_CONTROL.md](ACCESS_CONTROL.md)
- [INCIDENT_RESPONSE.md](INCIDENT_RESPONSE.md)
- [NETWORK_SECURITY.md](NETWORK_SECURITY.md)
- [CREDENTIAL_MANAGEMENT.md](CREDENTIAL_MANAGEMENT.md)
- [AMAZON_DATA_HANDLING.md](AMAZON_DATA_HANDLING.md)
- [REVIEW_LOG.md](REVIEW_LOG.md)

These documents define required operating controls. Production SP-API access must not be enabled until the controls are in place for the runtime environment where Amazon Information is processed.


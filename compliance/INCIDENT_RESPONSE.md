# Incident Response Plan

Incident owner: Adam Menker

Backup owner: N/A while the application is single-owner.

Review cadence: every 6 months.

Any security incident involving Amazon Information will be reported to security@amazon.com within 24 hours of detection.

## Incident Definition

A security incident includes any suspected or confirmed unauthorized access, disclosure, alteration, loss, theft, or exposure of:

- Amazon SP-API credentials.
- LWA client secret, refresh token, or access token.
- Amazon Information retrieved through SP-API.
- Local database records containing Amazon catalog, pricing, offer, or fee-estimate data.
- Systems, devices, repositories, logs, or secret stores that can access Amazon Information.

## Response Checklist

1. Identify incident.
2. Contain affected system.
3. Revoke/rotate exposed credentials.
4. Determine whether Amazon Information was accessed, disclosed, altered, or lost.
5. Notify Amazon at security@amazon.com within 24 hours if Amazon Information is involved.
6. Document timeline, impact, and remediation.
7. Review controls and update this plan.

## Detection Steps

- Review application errors, plugin runs, and API failures.
- Review repository, secret manager, and deployment logs for unauthorized access.
- Review Amazon Developer Console and Seller Central authorization status.
- Check for unexpected SP-API calls, token use, or credential changes.
- Check endpoint/security tooling alerts for malware, intrusion, or suspicious outbound traffic.

## Containment Steps

- Stop the application or disconnect affected runtime from the network.
- Disable public access to the backend or deployment entrypoint.
- Revoke exposed or suspected credentials.
- Rotate LWA client secret and refresh tokens.
- Rotate related passwords and API credentials.
- Preserve relevant logs and timestamps for analysis.

## Credential Revocation and Rotation

- Rotate Amazon LWA credentials in the Amazon developer console.
- Revoke and regenerate private application refresh tokens.
- Update the local secret store or deployment secret store.
- Restart services after secret rotation.
- Confirm old credentials no longer work.

## Log Review Steps

- Review backend logs for authentication, token exchange, SP-API calls, plugin failures, and unusual errors.
- Review local/deployment shell history for accidental credential exposure.
- Review source control history for committed secrets.
- Review Amazon developer/seller account access history where available.
- Review cloud provider, firewall, IDS/IPS, and endpoint protection alerts where applicable.

## Impact Assessment

Determine:

- Which credentials or systems were affected.
- Whether Amazon Information was accessed, disclosed, altered, or lost.
- What data categories were involved: catalog, pricing, offer, or fee-estimate data.
- Whether restricted buyer PII, orders, messages, addresses, or tax data were involved. The application is designed not to access those categories.
- The timeline from detection to containment.
- Remediation steps completed and remaining risk.

## Notification Procedure

If Amazon Information is involved, send a notification to security@amazon.com within 24 hours of detection.

The notification should include:

- Incident summary.
- Detection time and timezone.
- Containment status.
- Data categories involved.
- Whether SP-API credentials were exposed or rotated.
- Initial impact assessment.
- Contact person: Adam Menker.

## Post-Incident Review

After containment:

- Update this incident response plan if gaps were found.
- Update controls, tests, and documentation.
- Rotate credentials again if exposure scope remains uncertain.
- Record the review in [REVIEW_LOG.md](REVIEW_LOG.md).


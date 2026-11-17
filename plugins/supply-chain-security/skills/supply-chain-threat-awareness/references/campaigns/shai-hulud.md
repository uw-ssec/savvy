# Shai-Hulud Campaign

**Observed:** first wave disclosed 15 September 2025; second wave ("Sha1-Hulud: The Second Coming") identified 24 November 2025. Facts below checked against the sources at the end on 2026-11-17.
**Ecosystem:** npm.
**Vector:** a self-propagating worm. An infected install steals the npm token on that machine or CI runner, then publishes infected versions of the other packages that token can publish.

## What happened

- **Wave 1 (September 2025).** Infected versions ran a `postinstall` script that started a bundled `bundle.js`. It searched the environment and files for secrets using TruffleHog [CERT/CC], uploaded what it found to a public GitHub repository named `Shai-Hulud` in the victim's account [CISA, Unit 42], and used the stolen npm token to inject itself into the victim's other packages and publish them [Unit 42]. Over 500 packages were affected [CISA, CERT/CC]. npm removed them and blocked uploads that matched the malware's indicators [GitHub].
- **Wave 2 (November 2025).** Switched to a `preinstall` script (`setup_bun.js`, which runs `bun_environment.js`), so the payload runs before the install finishes [Datadog]. It backdoored 796 unique npm packages [Datadog] and created over 25,000 public repositories of stolen secrets with the description "Sha1-Hulud: The Second Coming." [Unit 42]. It registered infected hosts as self-hosted GitHub runners named `SHA1HULUD`, and tried to delete the user's home directory when it found no usable GitHub or npm token [Datadog].
- The sources above don't establish how the first maintainer account was compromised.

## Indicators of exposure

- The lockfile resolves an affected version. List what is resolved with `npm ls <package> --all --package-lock-only` and compare it with the advisory's package list.
- An install, local or in CI, ran lifecycle scripts while that version was resolved.
- Repositories named `Shai-Hulud`, or described as "Sha1-Hulud: The Second Coming.", in your accounts or organizations.
- Workflow files you didn't add, such as `shai-hulud-workflow.yml` (wave 1) or `discussion.yaml` (wave 2) [Unit 42], or self-hosted runners named `SHA1HULUD`.
- npm publishes of your own packages that your release process didn't make.

## Containment checklist

- [ ] Pin affected packages to releases from before the campaign (for wave 1, CISA says before 16 September 2025).
- [ ] Rotate every npm, GitHub and cloud credential that a machine or runner could read when it ran the install [CISA].
- [ ] Revoke long-lived npm tokens and publish through trusted publishing (OIDC) [GitHub].
- [ ] Require phishing-resistant MFA on developer accounts [CISA].
- [ ] Install with `npm ci --ignore-scripts` from now on.

For rotation order and the account-takeover runbook, use the `supply-chain-incident-response` skill.

## Sources (accessed 2026-11-17)

- [CISA] CISA alert, "Widespread Supply Chain Compromise Impacting npm Ecosystem", 23 September 2025: <https://www.cisa.gov/news-events/alerts/2025/09/23/widespread-supply-chain-compromise-impacting-npm-ecosystem>
- [CERT/CC] Vulnerability note VU#534320: <https://kb.cert.org/vuls/id/534320>
- [GitHub] "Our plan for a more secure npm supply chain", 22 September 2025: <https://github.blog/security/supply-chain-security/our-plan-for-a-more-secure-npm-supply-chain/>
- [Unit 42] Palo Alto Networks Unit 42, npm supply chain attack (updated 3 December 2025): <https://unit42.paloaltonetworks.com/npm-supply-chain-attack/>
- [Datadog] Datadog Security Labs, Shai-Hulud 2.0: <https://securitylabs.datadoghq.com/articles/shai-hulud-2.0-npm-worm/>

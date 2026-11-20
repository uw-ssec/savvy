# TeamPCP Campaign

**Observed:** 19 March to 29 April 2026. Facts below checked against the sources at the end on 2026-11-17.
**Ecosystems:** GitHub Actions, then PyPI and npm.
**Vector:** credentials stolen from CI. The attacker force-pushed existing version tags of security-tool actions to malicious commits, and those actions stole secrets from the CI runs that used them. A PyPI token stolen this way published the malicious LiteLLM releases [GHSA-5mg7], and Checkmarx believes its own compromise came through Trivy [Checkmarx]. How the later npm targets were reached is not established in these sources.

## Timeline

| Date (2026) | Target | What happened |
|---|---|---|
| 19 Mar | `aquasecurity/trivy-action`, `aquasecurity/setup-trivy`, Trivy v0.69.4 | Compromised credentials were used to force-push 76 of 77 `trivy-action` tags and all 7 `setup-trivy` tags to malicious commits, and to release a malicious Trivy v0.69.4 [GHSA-69fq]. |
| 22 Mar | Trivy Docker Hub images 0.69.5, 0.69.6 | Pushed with separately compromised Docker Hub credentials [GHSA-69fq]. |
| 23 Mar | `checkmarx/kics-github-action`, `checkmarx/ast-github-action`, two Checkmarx OpenVSX extensions | Malicious action payloads live 12:58–16:50 UTC [Checkmarx]. Wiz reports all 35 KICS tags were repointed to imposter commits [Wiz]. |
| 24 Mar | `litellm` 1.82.7, 1.82.8 (PyPI) | Published with a PyPI token exposed through the compromised Trivy step in LiteLLM's CI [GHSA-5mg7]. 1.82.8 added the `.pth` payload (LiteLLM `.pth` campaign file). |
| 27 Mar | `telnyx` 4.87.1, 4.87.2 (PyPI) | Published with compromised PyPI credentials [GHSA-955r]; Datadog links it to TeamPCP by a shared RSA key [Datadog]. |
| 22 Apr | `@bitwarden/cli` 2026.4.0 (npm) | Live 17:57–19:30 ET; Bitwarden ties it to the Checkmarx incident [Bitwarden]. Same day, a second Checkmarx wave hit `ast-github-action` tag 2.3.35 and KICS Docker images [Checkmarx]. |
| 29 Apr | `@cap-js/sqlite` 2.2.2, `@cap-js/postgres` 2.2.2, `@cap-js/db-service` 2.10.1 (SAP CAP, npm) | Harvested credentials and tried to self-propagate [GHSA-pvw4]. Wiz attributes it to TeamPCP ("Mini Shai Hulud") with high confidence and adds `mbt` 1.2.48 [Wiz SAP]. |

## Action tag hijack mechanics (Trivy)

1. The attacker kept access from an incident that began in late February 2026, because credential rotation after the 1 March disclosure wasn't atomic [GHSA-69fq].
2. Existing tags were force-pushed to malicious commits. `trivy-action` tags were bare versions (`0.0.1`–`0.34.2`), so any workflow that ran on one of them during the window ran the payload. Only `0.35.0`, protected by GitHub immutable releases, was safe [GHSA-69fq].
3. The payload ran before the real scan. It read secrets from the `Runner.Worker` process memory, swept 50+ paths for SSH, cloud, Kubernetes, Docker and database credentials, and sent them out encrypted. If that failed, it created a public `tpcp-docs` repository in the victim's account [GHSA-69fq].
4. SHA pinning `trivy-action` to a commit from before 2025-04-09 still pulled the malicious `setup-trivy`, because that older `trivy-action` referenced `setup-trivy` without a SHA [GHSA-69fq]. Pinning must hold for nested actions too.

## Indicators of exposure

- A workflow references an affected action by tag or branch, including bare-version tags such as `@0.34.2`.
- A workflow run used an affected action during its exposure window (for Trivy, check run logs from 19–20 March 2026 [GHSA-69fq]).
- A repository named `tpcp-docs` in your account or organization [GHSA-69fq].
- A lockfile resolves an affected PyPI or npm version listed above.

## Containment checklist

- [ ] Find every `uses:` ref that isn't a full commit SHA (this skill's Step 2 scan).
- [ ] For each affected action, compare the SHA you ran with the vendor's known-good SHA.
- [ ] Rotate every secret the affected workflow runs could read [GHSA-69fq].
- [ ] Pin every `uses:` to a 40-character SHA, and check that pinned composite actions pin their own `uses:` too.

For pinning patterns, use the `supply-chain-hardened-ci-cd` skill; for the tag-hijack runbook, use the `supply-chain-incident-response` skill.

## Sources (accessed 2026-11-17)

- [GHSA-69fq] Aqua Security, "Trivy ecosystem supply chain was briefly compromised", GHSA-69fq-xp46-6x23 / CVE-2026-33634, published 24 March 2026: <https://github.com/advisories/GHSA-69fq-xp46-6x23>
- [Checkmarx] Checkmarx, "Update: Ongoing Checkmarx Supply Chain Security Incident": <https://checkmarx.com/blog/ongoing-security-updates/>
- [Wiz] Wiz, "KICS GitHub Action Compromised: TeamPCP Strikes Again", 23 March 2026: <https://www.wiz.io/blog/teampcp-attack-kics-github-action>
- [GHSA-5mg7] "Two LiteLLM versions published containing credential harvesting malware", GHSA-5mg7-485q-xm76, published 25 March 2026: <https://github.com/advisories/GHSA-5mg7-485q-xm76>
- [GHSA-955r] Telnyx, "Telnyx has malicious code in PyPI versions 4.87.1 and 4.87.2", GHSA-955r-262c-33jc: <https://github.com/advisories/GHSA-955r-262c-33jc>
- [Datadog] Datadog Security Labs, LiteLLM and Telnyx compromised on PyPI: <https://securitylabs.datadoghq.com/articles/litellm-compromised-pypi-teampcp-supply-chain-campaign/>
- [Bitwarden] Bitwarden community notice, "Bitwarden CLI 2026.4.0 infected with malware": <https://community.bitwarden.com/t/bitwarden-cli-2026-4-0-infected-with-malware/96126>
- [GHSA-pvw4] cap-js/cds-dbs, "Supply chain compromise via malicious package versions", GHSA-pvw4-cvr4-97p8: <https://github.com/advisories/GHSA-pvw4-cvr4-97p8>
- [Wiz SAP] Wiz, "Supply Chain Campaign Targets SAP npm Packages", 29 April 2026: <https://www.wiz.io/blog/mini-shai-hulud-supply-chain-sap-npm>

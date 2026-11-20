# axios Campaign

**Observed:** 31 March 2026. Facts below checked against the sources at the end on 2026-11-17.
**Ecosystem:** npm.
**Vector:** maintainer account compromise. The attacker reached the lead maintainer's computer through targeted social engineering and remote-access malware, took the npm credentials, and published directly to npm [post-mortem].
**Scale:** axios had 100,340,121 npm downloads in the week before (23–29 March 2026, npm downloads API).

## What happened

1. On 30 March, 05:57 UTC, `plain-crypto-js@4.2.0` was published as a clean decoy [post-mortem].
2. On 31 March, `axios@1.14.1` (00:21 UTC) and `axios@0.30.4` (about 01:00 UTC) were published. Their only change was a new dependency, `plain-crypto-js@4.2.1` [post-mortem, StepSecurity].
3. `plain-crypto-js@4.2.1` had a `postinstall` hook (`node setup.js`) that dropped a remote access trojan for macOS, Windows or Linux, then replaced its own `package.json` with a clean copy to hide [StepSecurity].
4. npm removed both axios versions at 03:15 UTC and `plain-crypto-js` at 03:29 UTC [post-mortem].
5. The releases didn't go through the project's GitHub Actions pipeline, and `plain-crypto-js` was published with no OIDC binding [StepSecurity].

## Indicators of exposure

- The lockfile resolves `axios@1.14.1`, `axios@0.30.4` or any `plain-crypto-js`. Check with `npm ls axios plain-crypto-js --all --package-lock-only`.
- A fresh install, without a lockfile pin to a clean version, ran between 00:21 and 03:15 UTC on 31 March 2026 [post-mortem].
- Network connections to the indicators in the post-mortem.

## Containment checklist

- [ ] Treat any machine that installed an affected version as compromised [post-mortem, GHSA-2x9r].
- [ ] Downgrade to `axios@1.14.0` (or `0.30.3` on 0.x) and delete `node_modules/plain-crypto-js/` [post-mortem].
- [ ] Rotate every secret, token and credential on that machine, and every secret injected into an affected CI build [post-mortem].
- [ ] Install with `npm ci --ignore-scripts` in CI, so a dependency's `postinstall` can't run.

For credential rotation, use the `supply-chain-incident-response` skill; for lockfile practice, use the `supply-chain-dependency-security` skill.

## Sources (accessed 2026-11-17)

- [post-mortem] Jason Saayman (axios lead maintainer), "Post Mortem: axios npm supply chain compromise", axios/axios#10636, 2 April 2026: <https://github.com/axios/axios/issues/10636>
- [GHSA-2x9r] "Malware in plain-crypto-js", GHSA-2x9r-6wxq-hrr7, published 31 March 2026: <https://github.com/advisories/GHSA-2x9r-6wxq-hrr7>
- [StepSecurity] StepSecurity, "axios compromised on npm: malicious versions drop remote access trojan": <https://www.stepsecurity.io/blog/axios-compromised-on-npm-malicious-versions-drop-remote-access-trojan>
- npm downloads API, axios, 2026-03-23 to 2026-03-29: <https://api.npmjs.org/downloads/point/2026-03-23:2026-03-29/axios>

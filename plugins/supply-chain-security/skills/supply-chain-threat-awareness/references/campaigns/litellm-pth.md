# LiteLLM `.pth` Campaign

**Observed:** 24 March 2026, as part of the TeamPCP campaign. Facts below checked against the sources at the end on 2026-11-17.
**Ecosystem:** PyPI.
**Vector:** a PyPI API token exposed through the compromised Trivy scanner in LiteLLM's CI was used to upload malicious releases directly to PyPI [GHSA-5mg7, LiteLLM].

## What happened

| Version | Payload | Runs when |
|---|---|---|
| 1.82.7 | Code injected into `litellm/proxy/proxy_server.py` | `litellm.proxy` is imported [issue] |
| 1.82.8 | The same, plus `litellm_init.pth` (34,628 bytes) in `site-packages` | Any Python interpreter starts, with no import needed [issue] |

- The payload collected SSH keys, environment variables, cloud and Kubernetes credentials and more, encrypted them, and sent them to `models.litellm.cloud`, a domain registered the day before [issue].
- It also installed persistence outside the package: `~/.config/sysmon/sysmon.py` and a user systemd unit, `sysmon.service` [Datadog].
- PyPI quarantined the releases about 2 h 32 min after upload; they were downloaded over 119,000 times [PyPI]. LiteLLM's own estimate of the live window is about 40 minutes [LiteLLM].

## Why `.pth` files matter

The `site` module reads every `.pth` file in `site-packages` at startup and executes lines that start with `import`, whether or not the package is ever used [Python docs]. Python 3.15 deprecates these lines but still runs them [Python docs].

`pip uninstall` removes a `.pth` file that the wheel's `RECORD` lists (checked with pip 25.0.1 on a test wheel), so the `.pth` itself doesn't outlive the package. The `sysmon` files above do.

## Indicators of exposure

- A `litellm-1.82.7.dist-info` or `litellm-1.82.8.dist-info` directory, or a `litellm_init.pth` file, exists in any `site-packages` directory [issue]. Check by reading files only, for each environment and the user site directory: `find <env-prefix> -path '*-packages/*' \( -name 'litellm-1.82.[78].dist-info' -o -name 'litellm_init.pth' \)`. Don't run `pip show` or any other Python from a suspect environment: starting its Python runs `litellm_init.pth`.
- `~/.config/sysmon/sysmon.py` or a `sysmon.service` user unit exists [Datadog].
- For other `.pth` files, use the PyPI `.pth` check in `supply-chain-ecosystem-quirks`.

## Containment checklist

- [ ] Treat the host as compromised: rotate every credential that a Python process on it could read after the install [GHSA-5mg7].
- [ ] Remove the affected version, `litellm_init.pth`, and the `sysmon` files and unit.
- [ ] Find which package owns any other suspicious `.pth` file, again without starting Python: `grep -l '^<file>\.pth,' <site-packages>/*.dist-info/RECORD` for pip-installed packages, or `grep -l 'site-packages/<file>\.pth"' <env-prefix>/conda-meta/*.json` for conda and pixi environments.
- [ ] Pin a known-good version in the lockfile.

For rotation, use the `supply-chain-incident-response` skill.

## Sources (accessed 2026-11-17)

- [GHSA-5mg7] "Two LiteLLM versions published containing credential harvesting malware", GHSA-5mg7-485q-xm76, published 25 March 2026: <https://github.com/advisories/GHSA-5mg7-485q-xm76>
- [issue] BerriAI/litellm#24518, "litellm PyPI package (v1.82.7 + v1.82.8) compromised — full timeline and status", with LiteLLM team updates: <https://github.com/BerriAI/litellm/issues/24518>
- [LiteLLM] LiteLLM, "Security Townhall Updates", 27 March 2026: <https://docs.litellm.ai/blog/security-townhall-updates>
- [PyPI] PyPI blog, "Incident Report: LiteLLM/Telnyx supply-chain attack", 2 April 2026: <https://blog.pypi.org/posts/2026-04-02-incident-report-litellm-telnyx-supply-chain-attack/>
- [Datadog] Datadog Security Labs, LiteLLM and Telnyx compromised on PyPI: <https://securitylabs.datadoghq.com/articles/litellm-compromised-pypi-teampcp-supply-chain-campaign/>
- [Python docs] `site` module, "Path extensions (.pth files)": <https://docs.python.org/3/library/site.html>

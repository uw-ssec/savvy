# Secret Rotation Runbook

## Contents

- [Safe Rotation Order](#safe-rotation-order)
- [PyPI Tokens](#pypi-tokens)
- [npm Tokens](#npm-tokens)
- [GitHub Actions Secrets](#github-actions-secrets)
- [Signing Keys (cosign, GPG)](#signing-keys-cosign-gpg)
- [Cloud Credentials](#cloud-credentials)
- [Durable Fix: OIDC Trusted Publishing](#durable-fix-oidc-trusted-publishing)

## Safe Rotation Order

For every credential type below: **issue the new credential first, deploy it to all consumers, verify, then revoke the old one.** Never revoke first unless you have a confirmed list of consumers — surprise revocations break production and provide cover for further attacker action. The only exception: if you have direct evidence the old credential is actively in use by the attacker (e.g., outbound traffic from your CI to an unknown host), revoke immediately and accept the downtime.

Keep new secret values out of shell history and agent transcripts. Run `gh secret set <NAME>` without `--body` in your own terminal and paste the value at the prompt, or redirect it from a file (`gh secret set <NAME> < <file>`). Without a terminal, gh reads standard input and accepts it empty, so an agent that runs it without input sets an empty secret. The AWS and Azure commands below redirect the new secret to a file (GCP writes one already). `umask 077` makes it owner-only only if the file doesn't exist yet, so use a new name, and delete the file once the secret is deployed.

## PyPI Tokens

1. Generate replacement: `https://pypi.org/manage/account/token/` → scope to single project where possible.
2. Update consumer: `gh secret set PYPI_API_TOKEN`, then paste the token at the prompt.
3. Check the secret was replaced: `gh secret list` shows `PYPI_API_TOKEN` with a new updated time. That shows the secret changed, not that the value is right or that the publish job reads it. Don't test it with a TestPyPI upload: TestPyPI is a separate service with its own accounts and tokens, so it can't check a pypi.org token. The next release that uses the new token proves it.
4. Revoke the old token from the same management page once a release has succeeded with the new one, or at once if the attacker is using it (see Safe Rotation Order).
5. **Durable fix:** migrate to OIDC trusted publishing — see `supply-chain-hardened-ci-cd`. Eliminates the long-lived token entirely.

## npm Tokens

The granular `npm token create` flags below need npm 11.6.3 or later (`npm --version`); npm 10 and npm 11.6.2 and earlier don't have them. On an older client, create the granular token on npmjs.com instead (profile picture → **Access Tokens** → **Generate New Token**) with the same package, permission and expiry.

```bash
# List all tokens for the account
npm token list
# Create a replacement granular token, limited to the package, with an expiry.
# It prints the new token: run it in your own terminal, not through an agent.
npm token create --name <ci-publish-YYYYMMDD> --packages <pkg> \
  --packages-and-scopes-permission read-write --expires <days> --bypass-2fa
# Update CI (prompts for the value)
gh secret set NPM_TOKEN
# Verify a publish dry-run
npm publish --dry-run
# Revoke the old token by ID
npm token revoke <old-token-id>
```

**Durable fix:** enable npm OIDC trusted publishing (`id-token: write` + `npm publish --provenance`). See `supply-chain-hardened-ci-cd`.

## GitHub Actions Secrets

```bash
# Enumerate
gh secret list
gh secret list --env <env-name>
gh secret list --org <org>

# For each compromised secret: regenerate at the source-of-truth provider, then
# paste the new value at the prompt:
gh secret set <NAME>
gh secret set <NAME> --env <env>

# Old values still cached in any in-progress run — cancel them
gh run list --status in_progress --limit 1000 --json databaseId --jq '.[].databaseId' \
  | xargs -I{} gh run cancel {}
```

Workflow-level secrets (`env:` at job level) and `${{ secrets.* }}` references are equivalent in scope — rotate both.

## Signing Keys (cosign, GPG)

**Cosign keyless (Sigstore Fulcio):** no long-lived key, but if a signed artifact was produced by the bad version, treat its attestation as untrusted and re-sign from a clean rebuild. Record the bad attestation's Rekor entry UUID in the incident report for downstream consumers.

**Cosign with persistent key:**
```bash
# Revoke the cert via Rekor (record the entry, then re-sign with new key)
cosign tree <artifact>
# Generate a new key pair
cosign generate-key-pair
# Update CI
gh secret set COSIGN_PRIVATE_KEY < cosign.key
gh secret set COSIGN_PASSWORD        # prompts for the value
```

**GPG:**
```bash
# Revoke the old key
gpg --gen-revoke <key-id> > revoke.asc
gpg --import revoke.asc
gpg --keyserver keys.openpgp.org --send-keys <key-id>
# Generate replacement
gpg --full-generate-key
```

## Cloud Credentials

**AWS:**
```bash
aws iam list-access-keys --user-name <user>
(umask 077; aws iam create-access-key --user-name <user> > new-key.json)  # deploy this to CI
aws iam update-access-key --access-key-id <old> --status Inactive --user-name <user>
aws iam delete-access-key --access-key-id <old> --user-name <user>
```

**GCP:**
```bash
gcloud iam service-accounts keys list --iam-account=<sa>@<proj>.iam.gserviceaccount.com
gcloud iam service-accounts keys create new.json --iam-account=<sa>@<proj>.iam.gserviceaccount.com
gcloud iam service-accounts keys delete <old-key-id> --iam-account=<sa>@<proj>.iam.gserviceaccount.com
```

**Azure:**
```bash
az ad sp credential list --id <sp-app-id>
(umask 077; az ad sp credential reset --id <sp-app-id> --append > new-sp.json)  # --append keeps the old secret until you delete it
az ad sp credential delete --id <sp-app-id> --key-id <old-key-id>
```

**Durable fix for all three:** federate to GitHub OIDC. AWS via `configure-aws-credentials` with `role-to-assume`, GCP via `google-github-actions/auth` with Workload Identity Federation, Azure via `azure/login` with `client-id` + `tenant-id`. No long-lived secrets in `gh secret list`.

## Durable Fix: OIDC Trusted Publishing

OIDC eliminates long-lived secrets entirely — each workflow run issues a short-lived token cryptographically bound to the run's identity (repo + workflow + ref). Every rotation here is an opportunity to migrate the consumer to OIDC instead. The next "rotate the PyPI token" task should become "delete the PyPI token, set up trusted publishing." Cross-link to `supply-chain-hardened-ci-cd` for the full migration playbook for PyPI, npm, AWS, GCP, and Azure.

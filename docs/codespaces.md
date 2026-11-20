# Using savvy in GitHub Codespaces

The **Open in GitHub Codespaces** badge in the [README](../README.md) opens a Codespace with every savvy plugin already installed, so Claude Code and GitHub Copilot CLI are ready to use as soon as it starts.

## Using a LiteLLM gateway (optional)

By default, Copilot in the Codespace uses the models in your GitHub Copilot subscription. To route Copilot through your own LiteLLM-compatible gateway instead, you set two secrets. GitHub Codespaces secrets can only be scoped to repositories you own, so the setup runs from a fork:

1. **Fork this repo.** Click **Fork** on [github.com/uw-ssec/savvy](https://github.com/uw-ssec/savvy).
2. **Add secrets.** In your GitHub account settings, go to **Settings → Codespaces → Secrets** and add:
   - `LITELLM_BASE_URL`: your gateway base URL
   - `LITELLM_API_KEY`: your gateway API key

   When adding each secret, select your fork under **Repository access**.
3. **Open a Codespace from your fork.** On your fork, click **Code → Codespaces → Create codespace on main**.

The Codespace detects the secrets when it starts and configures Copilot to route through your gateway. If you add the secrets to a Codespace that already exists, rebuild the container to pick them up.

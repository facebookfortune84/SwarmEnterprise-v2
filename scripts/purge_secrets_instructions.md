Secret purge & rotation instructions

1. Rotate any keys found in the repository immediately (Stripe, Ollama, SMTP, etc.). Treat any leaked keys as compromised.

2. Locally remove sensitive files and add .env to .gitignore (already done).

3. To purge secrets from git history, use either BFG or git-filter-repo. Example using git-filter-repo (recommended):

   # Install git-filter-repo (https://github.com/newren/git-filter-repo)
   git clone --mirror git@github.com:yourorg/SwarmEnterprise-v2.git
   cd SwarmEnterprise-v2.git
   # Remove file named .env from history
   git filter-repo --invert-paths --path .env
   # Force-push the cleaned repo (coordinate with team)
   git push --force --all
   git push --force --tags

4. Alternatively BFG:
   bfg --delete-files .env

5. After history rewrite, rotate all secrets and revoke any tokens that were leaked.

6. Add Secrets Manager integration (AWS Secrets Manager / HashiCorp Vault) and update deployment scripts to fetch secrets at runtime.

7. Add CI secret-scan and require PR review for history-rewriting changes.

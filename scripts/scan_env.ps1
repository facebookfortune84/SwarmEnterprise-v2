$envPath = "..env"
 if (-not (Test-Path $envPath)) { Write-Host ".env missing"; exit }
 $required = @(
 "DATABASE_URL","POSTGRES_HOST","POSTGRES_DB","POSTGRES_USER","POSTGRES_PASSWORD","POSTGRES_PORT",
 "REDIS_URL",
 "SSH_DEPLOY_PRIVATE_KEY","SSH_DEPLOY_HOST","SSH_DEPLOY_USER",
 "DOCKER_REGISTRY_HOST","DOCKER_REGISTRY_USER","DOCKER_REGISTRY_PASSWORD",
 "STRIPE_API_KEY","STRIPE_PUBLISHABLE_KEY","STRIPE_WEBHOOK_SECRET",
 "OLLAMA_URL","OLLAMA_API_KEY","EMBEDDING_MODEL","ANTHROPIC_API_KEY",
 "CHROMA_SERVER_HOST","CHROMA_SERVER_HTTP_PORT",
 "ELEVENLABS_API_KEY",
 "SMTP_USER","SMTP_PASS","SMTP_SERVER","SMTP_PORT","IMAP_USER","IMAP_PASS","IMAP_SERVER",
 "SENTRY_DSN","CLOUDFLARE_TUNNEL_TOKEN","COTURN_SHARED_SECRET",
 "FRONTEND_URL","BACKEND_URL","COOKIE_DOMAIN",
 "FACEBOOK_CLIENT_ID","FACEBOOK_CLIENT_SECRET","LINKEDIN_CLIENT_ID","LINKEDIN_CLIENT_SECRET"
 )
 $present = @{}
 Get-Content $envPath | ForEach-Object {
 $line = ($_ -split '#')[0].Trim()
 if (-not $line) { return }
 $parts = $line -split('=',2)
 if ($parts.Count -eq 2) { $present[$parts[0].Trim()]=1 }
 }
 Write-Host "Present keys:"; $present.Keys | ForEach-Object { Write-Host "  $_" }
 Write-Host "`nMissing keys:"
 foreach ($k in $required) { if (-not $present.ContainsKey($k)) { Write-Host "  $k" } }
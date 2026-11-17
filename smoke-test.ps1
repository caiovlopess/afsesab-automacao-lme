<#
.SYNOPSIS
  Teste de fumaça da API (sem chave Gemini): health + analyze + upload inválido.
#>
$ErrorActionPreference = 'Continue'
$base = 'http://127.0.0.1:8000'
$token = (Get-Content '.\ai-backend\runtime\auth_token' -Raw).Trim()
$headers = @{ 'X-Internal-Auth-Token' = $token }

Write-Host "--- /health ---"
Invoke-WebRequest -UseBasicParsing "$base/health" | Select-Object -ExpandProperty Content

Write-Host "`n--- /api/v1/analyze-context (RAG + Gemini) ---"
$body = @{
  drugs = @('metformina')
  dosages = @('850 mg')
  cid10 = @('E11')
  clinicalTerms = @('diabetes')
  safeText = 'metformina 850 mg E11 diabetes'
  capturedAt = '2026-11-16T12:00:00Z'
  source = 'afsesab'
} | ConvertTo-Json -Depth 5
try {
  $r = Invoke-WebRequest -UseBasicParsing -Method Post "$base/api/v1/analyze-context" `
    -Headers $headers -ContentType 'application/json' -Body $body
  $r.Content
} catch { "ERRO: $($_.Exception.Message)" }

Write-Host "`n--- sem token (deve ser 401) ---"
try {
  Invoke-WebRequest -UseBasicParsing -Method Post "$base/api/v1/analyze-context" `
    -ContentType 'application/json' -Body $body | Out-Null
} catch { "Status: $($_.Exception.Response.StatusCode.value__) (esperado 401)" }

Write-Host "`n--- upload inválido (deve ser 415; multipart manual p/ PS 5.1) ---"
$boundary = '----AFBoundary12345'
$nl = "`r`n"
$bodyText =
  "--$boundary$nl" +
  "Content-Disposition: form-data; name=`"file`"; filename=`"invalido.txt`"$nl" +
  "Content-Type: text/plain$nl$nl" +
  "nao sou uma imagem$nl" +
  "--$boundary$nl" +
  "Content-Disposition: form-data; name=`"context`"$nl$nl" +
  "{}$nl" +
  "--$boundary--$nl"
$bodyBytes = [Text.Encoding]::UTF8.GetBytes($bodyText)
try {
  Invoke-WebRequest -UseBasicParsing -Method Post "$base/api/v1/validate-prescription" `
    -Headers $headers -ContentType "multipart/form-data; boundary=$boundary" `
    -Body $bodyBytes | Out-Null
} catch { "Status: $($_.Exception.Response.StatusCode.value__) (esperado 415)" }

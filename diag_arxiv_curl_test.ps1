Write-Host "======================================================================"
Write-Host "TEST E: Same query via curl.exe (different TLS stack than Python)"
Write-Host "======================================================================"
curl.exe -s -o NUL -w "Status: %{http_code}`n" "https://export.arxiv.org/api/query?search_query=all:quantum&start=0&max_results=1&_cb=77777"

Write-Host ""
Write-Host "======================================================================"
Write-Host "TEST F: curl.exe with verbose headers (to see actual response)"
Write-Host "======================================================================"
curl.exe -s -D - "https://export.arxiv.org/api/query?search_query=all:quantum&start=0&max_results=1&_cb=66666" -o NUL

Write-Host ""
Write-Host "======================================================================"
Write-Host "TEST G: curl.exe forcing HTTP/1.1 explicitly"
Write-Host "======================================================================"
curl.exe -s --http1.1 -o NUL -w "Status: %{http_code}`n" "https://export.arxiv.org/api/query?search_query=all:quantum&start=0&max_results=1&_cb=55555"

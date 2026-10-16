# PowerShell Kubernetes Setup Script for Library Lending System across qa, stage, and prod
param(
    [string]$DockerUser = "adityaprof01-ai",
    [string]$DockerToken = ""
)

Write-Host "=== 1. Creating Namespaces (qa, stage, prod) ===" -ForegroundColor Cyan
kubectl apply -f k8s/namespaces.yaml

if ($DockerToken -ne "") {
    Write-Host "=== 2. Creating Docker Hub secret 'dockerhub' in qa, stage, prod ===" -ForegroundColor Cyan
    foreach ($ns in @("qa", "stage", "prod")) {
        kubectl create secret docker-registry dockerhub `
            --docker-username=$DockerUser `
            --docker-password=$DockerToken `
            -n $ns `
            --dry-run=client -o yaml | kubectl apply -f -
        Write-Host "Configured dockerhub secret in namespace: $ns" -ForegroundColor Green
    }
} else {
    Write-Host "NOTE: No Docker token provided. Run with: .\k8s\setup-k8s.ps1 -DockerUser <user> -DockerToken <token>" -ForegroundColor Yellow
}

Write-Host "=== 3. Applying Workloads to qa, stage, prod ===" -ForegroundColor Cyan
kubectl apply -f k8s/qa.yaml
kubectl apply -f k8s/stage.yaml
kubectl apply -f k8s/prod.yaml

Write-Host ""
Write-Host "=== Deployment Applied Successfully ===" -ForegroundColor Green
Write-Host "To monitor QA namespace rollout:" -ForegroundColor White
Write-Host "  kubectl rollout status deployment/library-app -n qa" -ForegroundColor Yellow
Write-Host "  kubectl get pods -n qa" -ForegroundColor Yellow

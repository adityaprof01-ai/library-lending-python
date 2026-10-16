#!/bin/bash
set -e

# Kubernetes Setup Script for Library Lending System across qa, stage, and prod

DOCKER_USER="${1:-adityaprof01-ai}"
DOCKER_TOKEN="${2}"

echo "=== 1. Creating Namespaces (qa, stage, prod) ==="
kubectl apply -f k8s/namespaces.yaml

if [ -n "$DOCKER_TOKEN" ]; then
  echo "=== 2. Creating Docker Hub secret 'dockerhub' in qa, stage, prod ==="
  for ns in qa stage prod; do
    kubectl create secret docker-registry dockerhub \
      --docker-username="$DOCKER_USER" \
      --docker-password="$DOCKER_TOKEN" \
      -n "$ns" \
      --dry-run=client -o yaml | kubectl apply -f -
    echo "Configured dockerhub secret in namespace: $ns"
  done
else
  echo "NOTE: No Docker token provided. Run with ./setup-k8s.sh <docker-user> <docker-token> to create pull secrets."
fi

echo "=== 3. Applying Workloads to qa, stage, prod ==="
kubectl apply -f k8s/qa.yaml
kubectl apply -f k8s/stage.yaml
kubectl apply -f k8s/prod.yaml

echo ""
echo "=== Deployment Applied Successfully ==="
echo "To monitor QA namespace rollout:"
echo "  kubectl rollout status deployment/library-app -n qa"
echo "  kubectl get pods -n qa -o wide"

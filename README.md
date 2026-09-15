# Modern Cloud-Native Development PoC

A production-ready Proof of Concept demonstrating modern cloud-native developer workflows, containerization security, multi-container orchestration, Kubernetes deployment manifests, and automated CI/CD security scanning.

---

## 📊 Architecture Data Flow

```text
+------+      +----------------------+      +----------------------+      +------------------+
| User | ---> | API Gateway / Ingress | ---> | App Container (FastAPI)| ---> | Database (Redis) |
+------+      +----------------------+      +----------------------+      +------------------+
  (Client)      (K8s Ingress / Port 80)       (Non-root, Port 8000)         (Port 6379, Vol)
```

---

## 📁 Project Structure

```text
cloud-native-poc/
├── .github/
│   └── workflows/
│       └── deploy.yml        # CI/CD pipeline (Lint, Hadolint, Trivy scan, Build, Push)
├── app/
│   ├── main.py               # FastAPI application with health check and Redis integration
│   └── requirements.txt      # Python dependencies
├── k8s/
│   ├── deployment.yaml       # Kubernetes deployments with security hardening & probes
│   └── service.yaml          # Kubernetes ClusterIP services
├── Dockerfile                # Multi-stage security-hardened Dockerfile (non-root user)
├── docker-compose.yml        # Local multi-container orchestration setup
└── README.md                 # Documentation and step-by-step instructions
```

---

## 🚀 Getting Started & Step-by-Step Instructions

### 1. Local Execution with Docker Compose

To spin up the multi-container stack locally:

```bash
# Build and start services in detached mode
docker compose up --build -d

# Verify containers are running
docker compose ps
```

### 2. Testing the Application

Test the health check endpoint and database connectivity:

```bash
curl http://localhost:8000/health
```

Expected Output:
```json
{"status":"healthy","database":"connected","ping_latency_ms":0.45}
```

Store and retrieve test items in Redis:
```bash
# Store an item
curl -X POST "http://localhost:8000/items/poc-key?value=CloudNative101"

# Retrieve the item
curl http://localhost:8000/items/poc-key
```

### 3. Measuring Performance Metrics

#### A. Build Times
Measure the time taken to build the Docker container image:
```bash
time docker compose build --no-cache
```

#### B. Startup Latency
Measure container startup time and time-to-first-healthy response:
```bash
docker compose up -d --force-recreate
time curl -s --retry 10 --retry-delay 1 --retry-connrefused http://localhost:8000/health
```

#### C. Memory Consumption
Monitor live resource usage (CPU and Memory) across containers:
```bash
docker stats --no-stream
```

---

## ☸️ Kubernetes Deployment

Deploy the manifests to a local Kubernetes cluster (e.g., Minikube, Kind):

```bash
# Apply deployments and services
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml

# Check pod and service status
kubectl get pods
kubectl get svc

# Port forward to test locally
kubectl port-forward svc/cloud-native-api-service 8000:80
```

---

## 🛡️ Security & CI/CD Pipeline (`.github/workflows/deploy.yml`)

The automated pipeline performs:
1. **Dockerfile Linting:** Uses `hadolint` to enforce Docker best practices.
2. **Vulnerability Scanning:** Uses `Trivy` to scan filesystem and container image for HIGH/CRITICAL vulnerabilities.
3. **Build & Push:** Uses Docker Buildx to build and push images securely to GitHub Container Registry (GHCR).

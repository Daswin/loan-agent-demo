# GCP deployment

## Prerequisites

- A GCP project with billing enabled.
- Terraform and the Google Cloud CLI authenticated to that project.
- A Document AI OCR processor created in the `us` location. Record its processor
  ID; the processor itself is intentionally supplied as an input rather than
  recreated when environments change.

The deployment is intentionally separate from the workspace's Query Stats
Terraform.

## 1. Configure Terraform

From `loan-agent-demo/terraform`, copy `terraform.tfvars.example` to
`terraform.tfvars` and set `project_id` and `document_ai_processor_id`.

Keep both image variables empty for the bootstrap apply:

```hcl
backend_image  = ""
frontend_image = ""
```

Then initialize and create APIs, IAM, Artifact Registry, Firestore, and the
private versioned document bucket:

```bash
terraform init
terraform plan -out bootstrap.tfplan
terraform apply bootstrap.tfplan
```

If the project already has a default Firestore database, import it before the
apply instead of attempting to create a second default database.

## 2. Build and push both images

From `loan-agent-demo`, submit the build:

```bash
gcloud builds submit --config cloudbuild.yaml .
```

Cloud Build runs the tests, builds both containers, and pushes images tagged with
the build ID. It does not deploy Cloud Run; Terraform remains authoritative for
that infrastructure.

Copy the two image URLs from the completed build into `terraform.tfvars`, for
example:

```hcl
backend_image  = "us-central1-docker.pkg.dev/PROJECT/loan-agent/backend/BUILD_ID"
frontend_image = "us-central1-docker.pkg.dev/PROJECT/loan-agent/frontend/BUILD_ID"
```

Apply again to create the backend and frontend Cloud Run services:

```bash
terraform plan -out services.tfplan
terraform apply services.tfplan
terraform output
```

## 3. Lock CORS to the frontend

Copy the `frontend_url` output into `frontend_origins`:

```hcl
frontend_origins = ["https://loan-agent-frontend-....run.app"]
```

Apply once more. This updates both FastAPI CORS and Cloud Storage upload CORS.
Do not leave a wildcard origin for this application.

## 4. Smoke test

1. Open the frontend URL.
2. Confirm a new `APP-YYYY-XXXXXXXX` application appears.
3. Complete intake and start document collection.
4. Upload each required document and run Document AI processing.
5. Record explicit consent, then use the demo operator control to select PASS or
   FAIL.
6. Validate and submit the package.
7. Confirm the final bank response says only `RECEIVED` with a reference.
8. Repeat with the opposite credit result and confirm it also reaches receipt.

## Operational notes

- Firestore is selected with `APPLICATION_STORE=firestore`; local tests default
  to the in-memory repository.
- Uploaded files are private, versioned, and stored under
  `loan-applications/Customer_Name/APP-YYYY-XXXXXXXX/<document>.ext` inside the
  configured bucket.
- The backend service account can access Firestore, documents, Document AI,
  Vertex AI, and IAM signing for short-lived upload URLs.
- The frontend receives its backend URL at container startup from Terraform.
- This remains a prototype. Production use still requires applicant/operator
  authentication, authorization, audit retention, malware scanning, data
  retention rules, monitoring, rate limiting, and a formal PII/compliance review.

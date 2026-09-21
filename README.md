# Loan application assistant

This prototype collects loan-application information and required documents. It
does not approve, decline, score, recommend, or underwrite loans. The backend is
authoritative for application state; Gemini is limited to conversational intake
and workflow orchestration.

The implemented stack includes FastAPI, Vertex AI/Gemini through Google ADK,
Cloud Storage signed uploads, Document AI OCR, Firestore persistence, a simulated
operator-selected credit result, a receipt-only bank simulator, Cloud Run,
Artifact Registry, Cloud Build, and Terraform.

See [DEPLOYMENT.md](DEPLOYMENT.md) for setup and deployment. Run local tests with:

```bash
python -m unittest discover -s tests -v
```

The old prototype documentation is retained below as a hidden historical note.

<!-- ARCHIVED ORIGINAL README

# Loan sales agent — basic prototype

Minimal demo: asks a few questions, accepts one document upload, parses income
from it via Document AI + Gemini, then calls one mock decision API that
approves or declines.

## 1. One-time GCP setup

```bash
export PROJECT_ID="your-project-id"
export REGION="us-central1"

gcloud config set project $PROJECT_ID

gcloud services enable \
  aiplatform.googleapis.com \
  run.googleapis.com \
  storage.googleapis.com \
  documentai.googleapis.com

# Bucket for uploaded documents
gsutil mb -l $REGION gs://$PROJECT_ID-loan-uploads
```

Create a Document AI processor (Console → Document AI → Create Processor →
"Document OCR" is fine for this demo — it just needs raw text, not structured
fields). Note the processor ID and its location (usually `us` or `eu`).

## 2. Local test run

```bash
pip install -r requirements.txt

export GOOGLE_CLOUD_PROJECT=$PROJECT_ID
export GOOGLE_CLOUD_LOCATION=$REGION
export UPLOAD_BUCKET=$PROJECT_ID-loan-uploads
export DOCAI_LOCATION=us
export DOCAI_PROCESSOR_ID=your-processor-id
export DECISION_API_URL=http://localhost:8080/api/decision
export GOOGLE_GENAI_USE_VERTEXAI=True

uvicorn main:app --reload --port 8080
```

Open `static/index.html` in a browser (set `API_BASE` inside it to
`http://localhost:8080` first) and try the flow.

## 3. Deploy to Cloud Run

```bash
gcloud run deploy loan-agent-demo \
  --source . \
  --region $REGION \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_CLOUD_PROJECT=$PROJECT_ID,GOOGLE_CLOUD_LOCATION=$REGION,UPLOAD_BUCKET=$PROJECT_ID-loan-uploads,DOCAI_LOCATION=us,DOCAI_PROCESSOR_ID=your-processor-id,GOOGLE_GENAI_USE_VERTEXAI=True
```

Once deployed, set `DECISION_API_URL` to the same service's public URL +
`/api/decision` (it's calling itself here for simplicity — in a real setup
this would point at an actual loan origination system), then redeploy:

```bash
gcloud run services update loan-agent-demo \
  --region $REGION \
  --update-env-vars DECISION_API_URL=https://YOUR-CLOUD-RUN-URL/api/decision
```

Grant the Cloud Run service account access to the bucket and Document AI:

```bash
SERVICE_ACCOUNT=$(gcloud run services describe loan-agent-demo --region $REGION --format 'value(spec.template.spec.serviceAccountName)')
gsutil iam ch serviceAccount:$SERVICE_ACCOUNT:objectAdmin gs://$PROJECT_ID-loan-uploads
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member serviceAccount:$SERVICE_ACCOUNT \
  --role roles/documentai.apiUser
```

## 4. Wire up the microsite

Edit `static/index.html`, set `API_BASE` to your Cloud Run URL, and host that
one file anywhere (Firebase Hosting, a Cloud Run static bucket, or embedded
directly into the existing microsite as an iframe/component).

## Known limits of this prototype (flag these in the proposal)

- Session state is in-memory — restarts or multiple instances will lose
  progress. Fine for a live demo, not for production.
- No auth, rate-limiting, or bot protection (reCAPTCHA / Cloud Armor) yet —
  add before this is truly public.
- The decision logic is a placeholder rule, not real underwriting.
- Uploaded documents aren't encrypted/restricted beyond default bucket
  permissions — needs a real PII/compliance pass before handling real
  applications.

END ARCHIVED ORIGINAL README -->

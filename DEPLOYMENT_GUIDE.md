# Google Cloud Run Deployment Guide

This guide provides step-by-step instructions for deploying the Document Processing API to Google Cloud Run.

## 🚀 Quick Start

### Prerequisites Checklist

- [ ] Google Cloud account with billing enabled
- [ ] Google Cloud SDK installed ([Download here](https://cloud.google.com/sdk/docs/install))
- [ ] Authenticated with gcloud (`gcloud auth login`)
- [ ] Project ID ready (e.g., `electric-charge-431108-f7`)

### One-Click Deployment

**Windows (PowerShell):**

```powershell
.\deploy_to_cloudrun.ps1
```

**Linux/macOS:**

```bash
chmod +x deploy_to_cloudrun.sh
./deploy_to_cloudrun.sh
```

## 📋 Detailed Steps

### 1. Prepare Your Environment

```bash
# Set your project ID
export PROJECT_ID="your-gcp-project-id"

# Authenticate with Google Cloud
gcloud auth login

# Set the project
gcloud config set project $PROJECT_ID
```

### 2. Enable Required APIs

```bash
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable aiplatform.googleapis.com
```

### 3. Build and Deploy

```bash
# Build the container image
gcloud builds submit --tag gcr.io/$PROJECT_ID/document-processing-api

# Deploy to Cloud Run
gcloud run deploy document-processing-api \
    --image gcr.io/$PROJECT_ID/document-processing-api \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated \
    --set-env-vars="GCP_PROJECT_ID=$PROJECT_ID,GCP_REGION=us-central1,MODEL_NAME=gemini-2.5-flash" \
    --memory=2Gi \
    --cpu=2 \
    --timeout=300 \
    --max-instances=10 \
    --min-instances=0
```

## ⚙️ Configuration Details

### Resource Allocation

| Setting       | Value   | Reason                                       |
| ------------- | ------- | -------------------------------------------- |
| Memory        | 2GB     | Sufficient for image processing and AI calls |
| CPU           | 2 vCPUs | Good balance for concurrent requests         |
| Timeout       | 300s    | Allows for longer AI processing times        |
| Max Instances | 10      | Prevents runaway scaling costs               |
| Min Instances | 0       | Scales to zero when not in use               |

### Environment Variables

The deployment automatically sets:

- `GCP_PROJECT_ID`: Your Google Cloud project ID
- `GCP_REGION`: Deployment region (us-central1)
- `MODEL_NAME`: Gemini model (gemini-2.5-flash)

### Security Settings

- **Public Access**: Enabled by default (`--allow-unauthenticated`)
- **For Production**: Remove `--allow-unauthenticated` and implement proper authentication

## 🧪 Testing Your Deployment

After deployment, you'll receive a service URL. Test it:

```bash
# Replace YOUR_SERVICE_URL with your actual URL
SERVICE_URL="https://your-service-url"

# Health check
curl $SERVICE_URL/health

# Test business license processing
curl -X POST "$SERVICE_URL/process-business-license" \
  -F "file=@sample-license.pdf" \
  -F "country=korea"

# Test receipt processing (dynamic format)
curl -X POST "$SERVICE_URL/process-receipt" \
  -F "file=@sample-receipt.jpg"
```

## 📊 Monitoring and Maintenance

### View Logs

```bash
gcloud run services logs tail document-processing-api --region us-central1
```

### Monitor Performance

- Visit [Cloud Run Console](https://console.cloud.google.com/run)
- Monitor request count, latency, and error rates
- Set up alerts for high error rates or latency

### Update Deployment

```bash
# After making code changes
gcloud builds submit --tag gcr.io/$PROJECT_ID/document-processing-api
gcloud run deploy document-processing-api \
    --image gcr.io/$PROJECT_ID/document-processing-api \
    --region us-central1
```

## 💰 Cost Optimization

### Pricing Model

Cloud Run charges for:

- CPU and memory usage during request processing
- Number of requests
- Networking (minimal for most use cases)

### Cost-Saving Tips

1. **Auto-scaling**: Set `--min-instances=0` to scale to zero
2. **Right-sizing**: Monitor usage and adjust CPU/memory if needed
3. **Request optimization**: Optimize image sizes before processing
4. **Caching**: Implement caching for repeated requests

### Estimated Costs

For typical usage (100 requests/day, 30s avg processing time):

- **Monthly cost**: ~$5-15 USD
- **Per request**: ~$0.001-0.003 USD

## 🔒 Production Security

### Authentication

```bash
# Deploy with authentication required
gcloud run deploy document-processing-api \
    --image gcr.io/$PROJECT_ID/document-processing-api \
    --no-allow-unauthenticated \
    --region us-central1
```

### IAM Setup

```bash
# Allow specific users/service accounts
gcloud run services add-iam-policy-binding document-processing-api \
    --member="user:user@example.com" \
    --role="roles/run.invoker" \
    --region us-central1
```

### Environment Variables Security

For sensitive data, use Google Secret Manager:

```bash
# Create a secret
gcloud secrets create api-key --data-file=api-key.txt

# Deploy with secret
gcloud run deploy document-processing-api \
    --set-secrets="API_KEY=api-key:latest" \
    --region us-central1
```

## 🛠️ Troubleshooting

### Common Issues

**Build Failures:**

- Check `.gcloudignore` excludes unnecessary files
- Verify all dependencies in `requirements.txt`
- Ensure Dockerfile syntax is correct

**Deployment Failures:**

- Verify APIs are enabled
- Check IAM permissions
- Ensure project billing is enabled

**Runtime Errors:**

- Check logs: `gcloud run services logs tail document-processing-api`
- Verify environment variables are set correctly
- Test locally first with Docker

**Performance Issues:**

- Increase memory/CPU allocation
- Check for memory leaks in logs
- Monitor request patterns

### Getting Help

1. **Cloud Run Documentation**: https://cloud.google.com/run/docs
2. **Support**: Use Google Cloud Support for production issues
3. **Community**: Stack Overflow with `google-cloud-run` tag

## 📝 Deployment Checklist

- [ ] Prerequisites installed and configured
- [ ] Project ID set correctly in deployment scripts
- [ ] APIs enabled
- [ ] Deployment script executed successfully
- [ ] Service URL received
- [ ] Health check passes
- [ ] Both endpoints tested with sample files
- [ ] Monitoring set up
- [ ] Security configured for production use

---

**Next Steps:**

- Set up monitoring and alerting
- Implement authentication for production
- Configure custom domain if needed
- Set up CI/CD pipeline for automated deployments

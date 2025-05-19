https://codelabs.developers.google.com/mcp-toolbox-bigquery-dataset?hl=en#0

# setup bq table
```
export BQ_DATASET_NAME="mcp_dataset"
export BQ_LOCATION="US"

bq --location=$BQ_LOCATION mk $BQ_DATASET_NAME


CREATE TABLE IF NOT EXISTS `mcp_dataset.hotels` (
  id            INT64 NOT NULL,
  name          STRING NOT NULL,
  location      STRING NOT NULL,
  price_tier    STRING NOT NULL,
  checkin_date  DATE NOT NULL,
  checkout_date DATE NOT NULL,
  booked        BOOLEAN NOT NULL
);

INSERT INTO `mcp_dataset.hotels` (id, name, location, price_tier, checkin_date, checkout_date, booked)
VALUES
  (1, 'Hilton Basel', 'Basel', 'Luxury', '2024-04-20', '2024-04-22', FALSE),
  (2, 'Marriott Zurich', 'Zurich', 'Upscale', '2024-04-14', '2024-04-21', FALSE),
  (3, 'Hyatt Regency Basel', 'Basel', 'Upper Upscale', '2024-04-02', '2024-04-20', FALSE),
  (4, 'Radisson Blu Lucerne', 'Lucerne', 'Midscale', '2024-04-05', '2024-04-24', FALSE),
  (5, 'Best Western Bern', 'Bern', 'Upper Midscale', '2024-04-01', '2024-04-23', FALSE),
  (6, 'InterContinental Geneva', 'Geneva', 'Luxury', '2024-04-23', '2024-04-28', FALSE),
  (7, 'Sheraton Zurich', 'Zurich', 'Upper Upscale', '2024-04-02', '2024-04-27', FALSE),
  (8, 'Holiday Inn Basel', 'Basel', 'Upper Midscale', '2024-04-09', '2024-04-24', FALSE),
  (9, 'Courtyard Zurich', 'Zurich', 'Upscale', '2024-04-03', '2024-04-13', FALSE),
  (10, 'Comfort Inn Bern', 'Bern', 'Midscale', '2024-04-04', '2024-04-16', FALSE);
```

```
mkdir mcp-toolbox
cd mcp-toolbox

export OS="darwin/arm64" # one of linux/amd64, darwin/arm64, darwin/amd64, or windows/amd64
curl -O https://storage.googleapis.com/genai-toolbox/v0.5.0/$OS/toolbox

chmod +x toolbox

./toolbox --tools-file "tools.yaml"

pip install toolbox-langchain langchain


# --- Define Queries and Run the Agent ---
queries = [
    "Find hotels in Basel with Basel in it's name.",
    "Can you book the Hilton Basel for me?",
    "Oh wait, this is too expensive. Please cancel it and book the Hyatt Regency instead.",
    "My check in dates would be from April 10, 2024 to April 19, 2024.",
]
```

# deploy the mcp toolbox to cloud run
```
gcloud secrets create tools --data-file=tools.yaml

export IMAGE=us-central1-docker.pkg.dev/database-toolbox/toolbox/toolbox:latest
gcloud run deploy toolbox \
    --image $IMAGE \
    --region us-central1 \
    --set-secrets "/app/tools.yaml=tools:latest" \
    --args="--tools-file=/app/tools.yaml","--address=0.0.0.0","--port=8080" \
    --network default \
    --subnet default \
    --allow-unauthenticated

gcloud run services describe toolbox --format 'value(status.url)'
```

# deploy adk agent to cloud run
```
export GOOGLE_CLOUD_PROJECT=lufeng-demo
export GOOGLE_CLOUD_LOCATION=us-central1

# Set the path to your agent code directory
export AGENT_PATH="./bq_mcp_agent"

# Set a name for your Cloud Run service (optional)
export SERVICE_NAME="hotelbooking-agent-service"

# Set an application name (optional)
export APP_NAME="hotelbooking-agent-app"

adk deploy cloud_run \
--project=$GOOGLE_CLOUD_PROJECT \
--region=$GOOGLE_CLOUD_LOCATION \
--service_name=$SERVICE_NAME \
--app_name=$APP_NAME \
--with_ui \
$AGENT_PATH

export APP_URL="https://hotelbooking-agent-service-988469099469.us-central1.run.app"
curl -X GET $APP_URL/list-apps

curl -X POST https://hotelbooking-agent-service-988469099469.us-central1.run.app \
-H "Authorization: bearer $(gcloud auth print-identity-token)" \
-H "Content-Type: application/json" \
-d '{
  "name": "Developer"
}'

```

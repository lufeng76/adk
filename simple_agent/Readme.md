pip install google-adk -q
pip install litellm -q


export GOOGLE_CLOUD_PROJECT=lufeng-demo
export GOOGLE_CLOUD_LOCATION=us-central1

# Set the path to your agent code directory
export AGENT_PATH="./simple_agent"

# Set a name for your Cloud Run service (optional)
export SERVICE_NAME="simple-agent-service"

# Set an application name (optional)
export APP_NAME="simple-agent-app"

adk deploy cloud_run \
--project=$GOOGLE_CLOUD_PROJECT \
--region=$GOOGLE_CLOUD_LOCATION \
--service_name=$SERVICE_NAME \
--app_name=$APP_NAME \
--with_ui \
$AGENT_PATH
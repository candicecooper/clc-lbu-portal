#!/bin/bash
# Creates .streamlit/secrets.toml from Render environment variables
# then starts the Streamlit app

mkdir -p .streamlit

cat > .streamlit/secrets.toml << EOF
# Auto-generated from environment variables at startup

SUPABASE_URL = "${SUPABASE_URL}"
SUPABASE_KEY = "${SUPABASE_KEY}"
${SUPABASE_SERVICE_KEY:+SUPABASE_SERVICE_KEY = \"$SUPABASE_SERVICE_KEY\"}
${SUPABASE_URL_MEETINGS:+SUPABASE_URL_MEETINGS = \"$SUPABASE_URL_MEETINGS\"}
${SUPABASE_KEY_MEETINGS:+SUPABASE_KEY_MEETINGS = \"$SUPABASE_KEY_MEETINGS\"}
${SUPABASE_SERVICE_KEY_MEETINGS:+SUPABASE_SERVICE_KEY_MEETINGS = \"$SUPABASE_SERVICE_KEY_MEETINGS\"}
GROQ_API_KEY = "${GROQ_API_KEY}"
ANTHROPIC_API_KEY = "${ANTHROPIC_API_KEY}"
ADMIN_PASSWORD = "${ADMIN_PASSWORD}"
PAC_ADMIN_PASSWORD = "${PAC_ADMIN_PASSWORD}"
CAL_ADMIN_PASSWORD = "${CAL_ADMIN_PASSWORD}"
TIPPING_ADMIN_PASSWORD = "${TIPPING_ADMIN_PASSWORD}"
FINANCE_PASSWORD = "${FINANCE_PASSWORD}"
WHS_PASSWORD = "${WHS_PASSWORD}"
SOCIAL_PASSWORD = "${SOCIAL_PASSWORD}"
COMMITTEE_ADMIN_PASSWORD = "${COMMITTEE_ADMIN_PASSWORD}"
APP_URL = "${APP_URL}"
STAFF_NAMES = "${STAFF_NAMES}"

[smtp]
host = "${SMTP_HOST}"
port = ${SMTP_PORT:-587}
user = "${SMTP_USER}"
password = "${SMTP_PASSWORD}"
from_name = "CLC Staff Portal"

[supabase]
url = "${BEHAVIOUR_SUPABASE_URL}"
key = "${BEHAVIOUR_SUPABASE_KEY}"

[admin]
email = "${BEHAVIOUR_ADMIN_EMAIL}"
password = "${BEHAVIOUR_ADMIN_PASSWORD}"

[email]
smtp_server = "${SMTP_HOST}"
smtp_port = ${SMTP_PORT:-587}
sender_email = "${SMTP_USER}"
sender_password = "${SMTP_PASSWORD}"
enabled = true
EOF

echo "✅ secrets.toml created"

cat > .streamlit/config.toml << EOF
[server]
enableXsrfProtection = false
enableCORS = false
maxUploadSize = 200

[client]
showSidebarNavigation = false

[browser]
gatherUsageStats = false
EOF

echo "✅ config.toml created"

streamlit run Home.py --server.port $PORT --server.address 0.0.0.0 --server.headless true

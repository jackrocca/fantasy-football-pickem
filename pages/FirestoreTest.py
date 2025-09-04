import traceback

import streamlit as st

from utils.firestore_client import get_firestore_client, firestore_healthcheck


st.set_page_config(page_title="Firestore Test", page_icon="🧪", layout="centered")

st.title("🧪 Firestore connectivity test")
st.write(
    "Use this page to verify that Streamlit can connect to Google Cloud Firestore "
    "using your service account configured in `st.secrets`."
)

with st.expander("Secrets setup (read-only)", expanded=False):
    st.code("""# In Streamlit Cloud → App → Settings → Secrets
[gcp_service_account]
type = "service_account"
project_id = "..."
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "..."
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "..."
universe_domain = "googleapis.com"
""", language="toml")

st.divider()

run = st.button("Run healthcheck (write + read)")

placeholder = st.empty()

if run:
    try:
        db = get_firestore_client()
        result = firestore_healthcheck(db)
        st.success(
            f"Success! Wrote document `{result['wrote_doc_id']}` to collection "
            f"`{result['collection']}`."
        )
        st.subheader("Recent healthchecks (latest 5)")
        st.json(result["recent"])  # shows server-parsed timestamps as RFC3339
    except Exception as exc:  # noqa: BLE001
        st.error("Firestore test failed. See details below.")
        with st.expander("Error details", expanded=True):
            st.exception(exc)
            st.text(traceback.format_exc())
else:
    st.info("Click the button above to perform a write + read connectivity test.")



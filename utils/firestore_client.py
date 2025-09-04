from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import streamlit as st
from google.cloud import firestore
from google.oauth2 import service_account


@st.cache_resource(show_spinner=False)
def get_firestore_client() -> firestore.Client:
    """Create and cache a Firestore client using credentials from st.secrets.

    Expects a `[gcp_service_account]` block in Streamlit secrets.
    """
    if "gcp_service_account" not in st.secrets:
        raise RuntimeError(
            "Missing [gcp_service_account] in Streamlit secrets. "
            "Add your service account JSON to the Streamlit Cloud Secrets UI."
        )

    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"]
    )
    project_id: str = st.secrets["gcp_service_account"]["project_id"]
    client = firestore.Client(project=project_id, credentials=credentials)
    return client


def firestore_healthcheck(db: firestore.Client) -> Dict[str, Any]:
    """Write a healthcheck document and read back recent entries.

    Returns a dictionary with details of the write and recent reads.
    """
    collection_name = "healthchecks"
    doc_id = f"hc_{uuid.uuid4().hex}"

    payload = {
        "doc_id": doc_id,
        "alive": True,
        "ts": datetime.now(timezone.utc),
        "notes": "Connectivity test from Streamlit",
    }

    db.collection(collection_name).document(doc_id).set(payload)

    # Fetch the 5 most recent healthchecks
    recent_docs = (
        db.collection(collection_name)
        .order_by("ts", direction=firestore.Query.DESCENDING)
        .limit(5)
        .stream()
    )
    recent_raw = [d.to_dict() for d in recent_docs]
    # Ensure JSON-serializable output for Streamlit rendering
    recent = []
    for item in recent_raw:
        converted = dict(item)
        if isinstance(converted.get("ts"), datetime):
            converted["ts"] = converted["ts"].isoformat()
        recent.append(converted)

    written_payload = dict(payload)
    if isinstance(written_payload.get("ts"), datetime):
        written_payload["ts"] = written_payload["ts"].isoformat()

    return {
        "wrote_doc_id": doc_id,
        "written_payload": written_payload,
        "recent": recent,
        "collection": collection_name,
    }



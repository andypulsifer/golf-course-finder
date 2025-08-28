import os
import requests
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Golf Course Finder", layout="centered")
st.title("🏌️‍♂️ Golf Course Finder (GolfCourseAPI)")

# Get API key from Streamlit secrets or environment variable
API_KEY = st.secrets.get("GOLFCOURSEAPI_KEY", os.environ.get("GOLFCOURSEAPI_KEY", ""))

if not API_KEY:
    st.warning("Add your API key in Streamlit Secrets as `GOLFCOURSEAPI_KEY`, or set env var `GOLFCOURSEAPI_KEY`.")
    st.stop()

# Correct API base URL
BASE_URL = "https://api.golfcourseapi.com"

# -------------------
# API calls
# -------------------
@st.cache_data(ttl=3600)
def search_courses(query: str):
    """Search for courses by name."""
    url = f"{BASE_URL}/courses"
    params = {"search": query}
    headers = {"Authorization": f"Key {API_KEY}"}
    r = requests.get(url, params=params, headers=headers, timeout=20)
    r.raise_for_status()
    return r.json()

@st.cache_data(ttl=3600)
def get_course_detail(course_id: str):
    """Get detailed course info including tees/holes."""
    url = f"{BASE_URL}/courses/{course_id}"
    headers = {"Authorization": f"Key {API_KEY}"}
    r = requests.get(url, headers=headers, timeout=20)
    r.raise_for_status()
    return r.json()

# -------------------
# Streamlit UI
# -------------------
with st.form("search"):
    q = st.text_input("Course name", value="Prairie Green")
    submitted = st.form_submit_button("Search")

if submitted:
    try:
        data = search_courses(q.strip())
        if not data:
            st.info("No courses found.")
        else:
            # Display search results
            df = pd.json_normalize(data)
            cols = [c for c in ["id", "name", "city", "state", "country"] if c in df.columns]
            st.dataframe(df[cols] if cols else df, use_container_width=True)

            # Allow user to pick a course and fetch details
            if "id" in df.columns:
                course_id = st.selectbox("Select a course to view details", df["id"].astype(str).tolist())
                if st.button("Load Course Details"):
                    detail = get_course_detail(course_id)
                    st.subheader(detail.get("name", "Course Details"))

                    # Tee boxes
                    tees = detail.get("tees") or detail.get("teeBoxes") or []
                    if tees:
                        st.markdown("### Tee Boxes")
                        st.dataframe(pd.json_normalize(tees), use_container_width=True)

                    # Holes
                    holes = detail.get("holes") or []
                    if holes:
                        st.markdown("### Hole-by-Hole")
                        st.dataframe(pd.json_normalize(holes), use_container_width=True)

    except Exception as e:
        st.error(f"Error: {e}")

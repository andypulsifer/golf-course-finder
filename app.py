import os
import requests
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Golf Course Finder", layout="centered")
st.title("🏌️‍♂️ Golf Course Finder (GolfCourseAPI)")

API_KEY = st.secrets.get("GOLFCOURSEAPI_KEY", os.environ.get("GOLFCOURSEAPI_KEY", ""))
if not API_KEY:
    st.warning("Add your API key in Streamlit Secrets as `GOLFCOURSEAPI_KEY`, or set env var `GOLFCOURSEAPI_KEY`.")
    st.stop()

BASE_URL = "https://api.golfcourseapi.com/v1"

def _get(url, params=None):
    headers = {"Authorization": f"Key {API_KEY}"}
    r = requests.get(url, params=params, headers=headers, timeout=20)
    r.raise_for_status()
    return r.json()

@st.cache_data(ttl=3600)
def search_courses(query: str):
    return _get(f"{BASE_URL}/search", params={"search_query": query})

@st.cache_data(ttl=3600)
def get_course_detail(course_id: int | str):
    # Try /v1/course?id=ID then /v1/courses/{id}
    try:
        return _get(f"{BASE_URL}/course", params={"id": course_id})
    except requests.HTTPError:
        return _get(f"{BASE_URL}/courses/{course_id}")

# ---------- Search form ----------
with st.form("search_form"):
    q = st.text_input("Course name", value="oxmoor ridge")
    submitted = st.form_submit_button("Search")

if submitted:
    try:
        payload = search_courses(q.strip())
        st.session_state["last_query"] = q.strip()
        st.session_state["last_payload"] = payload
    except Exception as e:
        st.error(f"Search error: {e}")

# Pull from session if we have previous results
payload = st.session_state.get("last_payload", {})
courses = payload.get("courses", []) if isinstance(payload, dict) else []

# ---------- Results table & picker ----------
if courses:
    df = pd.json_normalize(courses)
    if "display_name" not in df.columns:
        df["display_name"] = df.get("club_name", "") + " — " + df.get("course_name", "")
    cols = [c for c in ["id","display_name","club_name","course_name",
                        "location.city","location.state","location.country"] if c in df.columns]
    st.dataframe(df[cols] if cols else df, use_container_width=True)

    # selection persists across reruns
    default_id = df["id"].iloc[0] if "id" in df.columns and not df.empty else None
    pick = st.selectbox(
        "Select a course to view details",
        options=df["id"].tolist() if "id" in df.columns else [],
        format_func=lambda cid: df.loc[df["id"]==cid, "display_name"].values[0],
        key="selected_course_id",
        index=0
    ) if "id" in df.columns else None

    if st.button("Load Course Details", key="load_details_btn"):
        try:
            # Prefer the object from the search payload if it already includes detail
            detail = next((c for c in courses if c.get("id")==pick), None) or get_course_detail(pick)

            st.subheader(detail.get("course_name") or detail.get("name") or "Course Details")

            # Location
            loc = detail.get("location", {}) or {}
            loc_bits = [loc.get("address"), loc.get("city"), loc.get("state"), loc.get("country")]
            loc_str = ", ".join([x for x in loc_bits if x])
            if loc_str:
                st.caption(loc_str)

            # Tees (dict grouped by gender OR flat list)
            tees = detail.get("tees", {})
            if isinstance(tees, dict) and tees:
                st.markdown("### Tee Boxes")
                frames = []
                for group, items in tees.items():
                    if isinstance(items, list) and items:
                        tdf = pd.json_normalize(items)
                        if not tdf.empty:
                            tdf.insert(0, "group", group)
                            frames.append(tdf)
                if frames:
                    st.dataframe(pd.concat(frames, ignore_index=True), use_container_width=True)
                else:
                    st.info("No tee list found.")
            elif isinstance(tees, list) and tees:
                st.markdown("### Tee Boxes")
                st.dataframe(pd.json_normalize(tees), use_container_width=True)

            # Holes
            holes = detail.get("holes") or []
            if holes:
                st.markdown("### Hole-by-Hole")
                st.dataframe(pd.json_normalize(holes), use_container_width=True)

        except requests.HTTPError as e:
            st.error(f"HTTP error: {e} — {getattr(e.response, 'text', '')[:400]}")
        except Exception as e:
            st.error(f"Error: {e}")
else:
    if "last_query" in st.session_state:
        st.info("No results for your last search. Try a different spelling or nearby city.")

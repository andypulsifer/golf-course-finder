import os
import requests
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Golf Course Finder", layout="centered")
st.title("🏌️‍♂️ Golf Course Finder (GolfCourseAPI)")

# Read your API key from Streamlit Secrets or env var
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
    """Use /v1/search?search_query=... which returns {'courses': [...]}"""
    return _get(f"{BASE_URL}/search", params={"search_query": query})

@st.cache_data(ttl=3600)
def get_course_detail(course_id: int | str):
    """
    Some accounts return full detail in the search payload already.
    If not, try a detail endpoint. We'll attempt two common patterns.
    """
    # Try /v1/course?id=ID
    try:
        return _get(f"{BASE_URL}/course", params={"id": course_id})
    except requests.HTTPError:
        # Fallback /v1/courses/{id}
        return _get(f"{BASE_URL}/courses/{course_id}")

with st.form("search"):
    q = st.text_input("Course name", value="oxmoor ridge")
    submitted = st.form_submit_button("Search")

if submitted:
    try:
        payload = search_courses(q.strip())
        courses = payload.get("courses", [])
        if not courses:
            st.info("No courses found. Try a different spelling or nearby city.")
        else:
            # Show a friendly table to pick from
            df = pd.json_normalize(courses)
            # derive a display name
            if "display_name" not in df.columns:
                df["display_name"] = df.get("club_name", "") + " — " + df.get("course_name", "")
            cols = [c for c in ["id","display_name","club_name","course_name",
                                "location.city","location.state","location.country"] if c in df.columns]
            st.dataframe(df[cols] if cols else df, use_container_width=True)

            # Picker
            if "id" in df.columns:
                pick = st.selectbox(
                    "Select a course to view details",
                    options=df["id"].tolist(),
                    format_func=lambda cid: df.loc[df["id"]==cid, "display_name"].values[0]
                )

                if st.button("Load Course Details"):
                    # Many times the search payload already includes tees/holes; prefer that object
                    detail = next((c for c in courses if c.get("id")==pick), None)
                    if not detail:
                        detail = get_course_detail(pick)

                    st.subheader(detail.get("course_name") or detail.get("name") or "Course Details")

                    # Location
                    loc = detail.get("location", {})
                    loc_bits = [loc.get("city"), loc.get("state"), loc.get("country")]
                    st.caption(", ".join([x for x in loc_bits if x]))

                    # Tees (the sample shows tees grouped by gender dict, e.g., {"female":[...], "male":[...]})
                    tees = detail.get("tees", {})
                    if isinstance(tees, dict) and tees:
                        st.markdown("### Tee Boxes")
                        frames = []
                        for group, items in tees.items():
                            if isinstance(items, list):
                                tdf = pd.json_normalize(items)
                                if not tdf.empty:
                                    tdf.insert(0, "group", group)
                                    frames.append(tdf)
                        if frames:
                            tees_df = pd.concat(frames, ignore_index=True)
                            st.dataframe(tees_df, use_container_width=True)
                        else:
                            st.info("No tee list found.")
                    elif isinstance(tees, list):
                        st.markdown("### Tee Boxes")
                        st.dataframe(pd.json_normalize(tees), use_container_width=True)

                    # Holes (array of dicts with par/yardage/handicap)
                    holes = detail.get("holes") or []
                    if holes:
                        st.markdown("### Hole-by-Hole")
                        holes_df = pd.json_normalize(holes)
                        st.dataframe(holes_df, use_container_width=True)

    except requests.HTTPError as e:
        st.error(f"HTTP error: {e} — {getattr(e.response, 'text', '')[:400]}")
    except Exception as e:
        st.error(f"Error: {e}")

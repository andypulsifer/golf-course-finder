# Golf Course Finder (GolfCourseAPI)
A minimal Streamlit app that searches golf courses and shows tees/yardages using GolfCourseAPI.

## Run locally
pip install -r requirements.txt
export GOLFCOURSEAPI_KEY="YOUR_KEY_HERE"  # or use Streamlit secrets
streamlit run app.py

## Deploy on Streamlit Cloud
- Push this repo to GitHub.
- In Streamlit Cloud, set a secret:
  GOLFCOURSEAPI_KEY = your_api_key
- Deploy app file: app.py

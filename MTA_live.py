import streamlit as st
import pandas as pd
import requests
from datetime import datetime
from google.transit import gtfs_realtime_pb2
from streamlit_autorefresh import st_autorefresh

# ----------------------------------
# CONFIG
# ----------------------------------

FEED_URL = (
    "https://api-endpoint.mta.info/"
    "Dataservice/mtagtfsfeeds/nyct%2Fgtfs-g"
)

REFRESH_MS = 30000

# ----------------------------------
# AUTO REFRESH
# ----------------------------------

st_autorefresh(interval=REFRESH_MS, key="refresh")

# ----------------------------------
# PAGE SETTINGS
# ----------------------------------

st.set_page_config(
    page_title="MTA Live Tracker",
    page_icon="🚇",
    layout="wide"
)

st.title("🚇 MTA G Train Live Feed")
st.caption("Data source: MTA GTFS-Realtime API")

# ----------------------------------
# DOWNLOAD FEED
# ----------------------------------

@st.cache_data(ttl=20)
def get_feed():

    response = requests.get(
        FEED_URL,
        timeout=15
    )

    response.raise_for_status()

    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(response.content)

    return feed


# ----------------------------------
# PARSE FEED
# ----------------------------------

def parse_feed(feed):

    rows = []

    for entity in feed.entity:

        if not entity.HasField("trip_update"):
            continue

        trip = entity.trip_update

        trip_id = ""

        route_id = ""

        if trip.trip.trip_id:
            trip_id = trip.trip.trip_id

        if trip.trip.route_id:
            route_id = trip.trip.route_id

        for stop in trip.stop_time_update:

            arrival_time = None

            if stop.HasField("arrival"):
                if stop.arrival.time:
                    arrival_time = datetime.fromtimestamp(
                        stop.arrival.time
                    )

            rows.append(
                {
                    "Route": route_id,
                    "Trip ID": trip_id,
                    "Stop ID": stop.stop_id,
                    "ETA": arrival_time,
                }
            )

    return pd.DataFrame(rows)


# ----------------------------------
# MAIN
# ----------------------------------

try:

    feed = get_feed()

    df = parse_feed(feed)

    if df.empty:
        st.warning("No train updates available.")
        st.stop()

    st.metric(
        "Predictions",
        len(df)
    )

    routes = sorted(
        df["Route"].dropna().unique().tolist()
    )

    selected_route = st.selectbox(
        "Filter route",
        ["All"] + routes
    )

    if selected_route != "All":
        df = df[df["Route"] == selected_route]

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Live Predictions")
        st.dataframe(
            df.sort_values("ETA"),
            use_container_width=True
        )

    with col2:
        st.subheader("Route Counts")

        route_counts = (
            df.groupby("Route")
            .size()
            .reset_index(name="Updates")
        )

        st.bar_chart(
            route_counts.set_index("Route")
        )

    st.success(
        f"Last updated: {datetime.now():%H:%M:%S}"
    )

except Exception as e:

    st.error(
        f"Unable to retrieve feed: {e}"
    )
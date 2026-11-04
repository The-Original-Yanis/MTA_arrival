import streamlit as st
import pandas as pd
import requests

from datetime import datetime
from google.transit import gtfs_realtime_pb2
from google.protobuf.json_format import MessageToDict
from streamlit_autorefresh import st_autorefresh


# ==================================================
# CONFIG
# ==================================================

FEED_URL = (
    "https://api-endpoint.mta.info/"
    "Dataservice/mtagtfsfeeds/nyct%2Fgtfs-g"
)

REFRESH_INTERVAL = 30000  # 30 seconds


# ==================================================
# PAGE CONFIG
# ==================================================

st.set_page_config(
    page_title="MTA G Train Live Tracker",
    page_icon="🚇",
    layout="wide",
)

st.title("🚇 MTA G Train Live Tracker")

st.caption(
    "Live GTFS-Realtime feed from MTA"
)


# ==================================================
# AUTO REFRESH
# ==================================================

st_autorefresh(
    interval=REFRESH_INTERVAL,
    key="gtfs_refresh"
)


# ==================================================
# FETCH FEED
# ==================================================

@st.cache_data(ttl=20)
def get_feed_bytes():

    response = requests.get(
        FEED_URL,
        timeout=20,
    )

    response.raise_for_status()

    return response.content


# ==================================================
# PARSE FEED
# ==================================================

def parse_feed(feed):

    rows = []

    for entity in feed.entity:

        if not entity.HasField("trip_update"):
            continue

        trip_update = entity.trip_update

        route_id = ""
        trip_id = ""

        if trip_update.trip.route_id:
            route_id = trip_update.trip.route_id

        if trip_update.trip.trip_id:
            trip_id = trip_update.trip.trip_id

        for stop_update in trip_update.stop_time_update:

            arrival_time = None

            if (
                stop_update.HasField("arrival")
                and stop_update.arrival.time
            ):
                arrival_time = datetime.fromtimestamp(
                    stop_update.arrival.time
                )

            departure_time = None

            if (
                stop_update.HasField("departure")
                and stop_update.departure.time
            ):
                departure_time = datetime.fromtimestamp(
                    stop_update.departure.time
                )

            rows.append(
                {
                    "Route": route_id,
                    "Trip ID": trip_id,
                    "Stop ID": stop_update.stop_id,
                    "Arrival": arrival_time,
                    "Departure": departure_time,
                }
            )

    return pd.DataFrame(rows)


# ==================================================
# MAIN
# ==================================================

try:

    feed_bytes = get_feed_bytes()

    feed = gtfs_realtime_pb2.FeedMessage()

    feed.ParseFromString(feed_

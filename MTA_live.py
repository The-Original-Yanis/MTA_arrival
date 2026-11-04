import requests
import pandas as pd
import streamlit as st

from datetime import datetime
from google.transit import gtfs_realtime_pb2
from google.protobuf.json_format import MessageToDict
from streamlit_autorefresh import st_autorefresh


# --------------------------------------------------
# CONFIG
# --------------------------------------------------

FEED_URL = (
    "https://api-endpoint.mta.info/"
    "Dataservice/mtagtfsfeeds/nyct%2Fgtfs-g"
)

REFRESH_INTERVAL_MS = 30000


# --------------------------------------------------
# PAGE
# --------------------------------------------------

st.set_page_config(
    page_title="MTA Live Arrivals",
    page_icon="🚇",
    layout="wide"
)

st.title("🚇 MTA Live Arrivals")

st.caption("Live data from MTA GTFS-Realtime feed")


# --------------------------------------------------
# AUTO REFRESH
# --------------------------------------------------

st_autorefresh(
    interval=REFRESH_INTERVAL_MS,
    key="refresh"
)


# --------------------------------------------------
# DOWNLOAD FEED
# --------------------------------------------------

@st.cache_data(ttl=20)
def get_feed_bytes():

    response = requests.get(
        FEED_URL,
        timeout=20
    )

    response.raise_for_status()

    return response.content


# --------------------------------------------------
# PARSE FEED
# --------------------------------------------------

def parse_feed(feed):

    records = []

    for entity in feed.entity:

        if not entity.HasField("trip_update"):
            continue

        trip_update = entity.trip_update

        route_id = trip_update.trip.route_id
        trip_id = trip_update.trip.trip_id

        for stop in trip_update.stop_time_update:

            arrival = None
            departure = None

            if (
                stop.HasField("arrival")
                and stop.arrival.time
            ):
                arrival = datetime.fromtimestamp(
                    stop.arrival.time
                )

            if (
                stop.HasField("departure")
                and stop.departure.time
            ):
                departure = datetime.fromtimestamp(
                    stop.departure.time
                )

            records.append(
                {
                    "Route": route_id,
                    "Trip ID": trip_id,
                    "Stop ID": stop.stop_id,
                    "Arrival": arrival,
                    "Departure": departure,
                }
            )

    return pd.DataFrame(records)


# --------------------------------------------------
# MAIN
# --------------------------------------------------

try:

    feed_bytes = get_feed_bytes()

    feed = gtfs_realtime_pb2.FeedMessage()

    feed.ParseFromString(feed_bytes)

    df = parse_feed(feed)

    st.success(
        f"Feed loaded at "
        f"{datetime.now().strftime('%H:%M:%S')}"
    )

    st.metric(
        "Feed Entities",
        len(feed.entity)
    )

    if df.empty:

        st.warning(
            "No trip updates found in the feed."
        )

        feed_dict = MessageToDict(feed)

        st.subheader("Raw Feed")
        st.json(feed_dict)

    else:

        routes = sorted(
            [
                route
                for route in df["Route"]
                .dropna()
                .unique()
                if route
            ]
        )

        selected_route = st.selectbox(
            "Route Filter",
            ["All"] + routes
        )

        if selected_route != "All":

            df = df[
                df["Route"] == selected_route
            ]

        st.subheader("Arrival Predictions")

        st.dataframe(
            df.sort_values(
                by="Arrival",
                na_position="last"
            ),
            use_container_width=True,
            height=600
        )

        st.subheader("Updates by Route")

        route_counts = (
            df.groupby("Route")
            .size()
            .reset_index(name="Updates")
        )

        if not route_counts.empty:

            st.bar_chart(
                route_counts.set_index("Route")
            )

        with st.expander(
            "Show Raw Feed JSON"
        ):

            st.json(
                MessageToDict(feed)
            )

except Exception as error:

    st.error(
        f"Error retrieving feed: {error}"
    )

    st.exception(error)

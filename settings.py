from datetime import timedelta as td


def init():
    global update_after, popular_count, viewer_minimum, tolerance_for_watching_broadcasts, temp_view_clear_period, view_elapsed_maximum_default, allow_maximum_default, refresh_maximum_default, streams_allow_maximum, data

    data_raw = [
        i[:-1].split(",") if i[:-1] == "\n" else i.split(",")
        for i in open("settings.txt").readlines()
    ]
    data = {i[0]: int(i[1]) for i in data_raw}
    update_after = td(days=data["update_after"])
    viewer_minimum = data["viewer_minimum"]
    popular_count = data["popular_count"]
    tolerance_for_watching_broadcasts = data["tolerance_for_watching_broadcasts"]
    temp_view_clear_period = data["temp_view_clear_period"]
    view_elapsed_maximum_default = data["view_elapsed_maximum_default"]
    allow_maximum_default = data["allow_maximum_default"]
    refresh_maximum_default = data["refresh_maximum_default"]
    # view_refresh_maximum = data["view_refresh_maximum"]
    streams_allow_maximum = data["streams_allow_maximum"]

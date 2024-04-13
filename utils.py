import profiles

def parse_heartrate_measurement_data(data):
    hr = int.from_bytes(data[1:2], byteorder="little", signed=False)
    rr_intervals = []

    if len(list(data)) > 2:
        offset = 2
        while offset < len(list(data)):
            rr_interval_raw = int.from_bytes(data[offset : offset + 2], byteorder="little", signed=False)
            rr_intervals.append(rr_interval_raw / 1024.0 * 1000.0)

            offset += 2

    return hr, rr_intervals

def parse_ecg_data(data):
    timestamp = int.from_bytes(data[1:9], byteorder="little", signed=False)
    timestamp += profiles.timestamp_offset

    samples = data[10:]

    offset = 0
    ecg_list = []
    while offset < len(samples):
        ecg = int.from_bytes(samples[offset : offset + 3], byteorder="little", signed=True)
        offset += 3

        ecg_list.extend([ecg])

    return timestamp, ecg_list
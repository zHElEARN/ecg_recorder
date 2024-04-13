from bleak import BleakClient, BleakScanner
from rich import console, inspect, panel
import asyncio
import signal
import numpy
import profiles
import utils

c = console.Console()

stop = False
def sigint_handler(signum, frame):
    global stop
    stop = True

heartrate_data, heartrate_changed = None, False
async def heartrate_handler(sender, data):
    global heartrate_data, heartrate_changed
    heartrate_data, heartrate_changed = data, True

ecg_data, ecg_changed = None, False
async def ecg_handler(sender, data):
    global ecg_data, ecg_changed
    ecg_data, ecg_changed = data, True

async def main():
    global stop
    global heartrate_data, heartrate_changed
    global ecg_data, ecg_changed

    devices = await BleakScanner.discover()
    polar_device = next((device for device in devices if "Polar H10" in device.name), None)
    if polar_device is None:
        c.print("No devices found")
        stop = True
        exit()

    c.print(
        panel.Panel(
            f"Name: {polar_device.name}\nAddress: {polar_device.address}\nRSSI: {polar_device.rssi}", title="Bluetooth LE Information", border_style="cyan"
        )
    )

    async with BleakClient(polar_device) as polar_client:
        device_name = "".join(map(chr, await polar_client.read_gatt_char(profiles.DEVICE_NAME_UUID)))
        manufacturer_name = "".join(map(chr, await polar_client.read_gatt_char(profiles.MANUFACTURER_NAME_UUID)))
        battery_level = int((await polar_client.read_gatt_char(profiles.BATTERY_LEVEL_UUID))[0])

        c.print(
            panel.Panel(
                f"Device Name: {device_name}\nManufacturer Name: {manufacturer_name}\nBattery Level: {battery_level}%",
                title="Device Information",
                border_style="cyan",
            )
        )

        await polar_client.start_notify(profiles.HEARTRATE_MEASUREMENT_UUID, heartrate_handler)

        await polar_client.write_gatt_char(profiles.PMD_CONTROL_UUID, profiles.START_ECG_STREAM_BYTES)
        await polar_client.start_notify(profiles.PMD_DATA_UUID, ecg_handler)

        ecg_data_list = []

        while not stop:
            if heartrate_changed == True:
                heartrate_changed = False

                hr, rr_intervals = utils.parse_heartrate_measurement_data(heartrate_data)

                if not rr_intervals:
                    c.log(f"HR Measurement: {hr} bpm")
                else:
                    c.log(f"HR Measurement: {hr} bpm, RR Intervals: {', '.join(str(rr_interval) for rr_interval in rr_intervals)} received.")

            if ecg_changed == True:
                ecg_changed = False

                timestamp, ecg = utils.parse_ecg_data(ecg_data)
                # c.log(f"ECG Data Timestamp: {timestamp}, ECG: {ecg}")
                ecg_data_list.extend(ecg)
            await asyncio.sleep(0.001)

        await polar_client.stop_notify(profiles.HEARTRATE_MEASUREMENT_UUID)
        await polar_client.stop_notify(profiles.PMD_DATA_UUID)
        numpy.save("ecg_data", ecg_data_list)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, sigint_handler)
    asyncio.run(main())
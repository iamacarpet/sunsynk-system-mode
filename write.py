import asyncio
import sys
import json
import re
import backoff
import pysolarmanv5
from sunsynk import SolarmanSunsynk, InverterState, Sensor
from sunsynk import SwitchRWSensor, TimeRWSensor, NumberRWSensor, SelectRWSensor
from sunsynk import AMPS, CELSIUS, KWH, VOLT, WATT

async def main():
    print("START", file=sys.stderr)

    request = json.load(sys.stdin)

    print("VALIDATE", file=sys.stderr)

    if not isinstance(request["use_timer"], bool):
        raise Exception("use_timer must be boolean")

    if not len(request["schedule"]) == 6:
        raise Exception("schedule requires 6 entries")

    for idx, entry in enumerate(request["schedule"]):
        if re.search("^([0-9]|[1][0-9]|2[0-3]):([012345][05])$", entry["start_time"]) == None:
            raise Exception("schedule entry " + str(idx+1) + " has an invalid start_time")

        end_index = (idx+1) if not idx == 5 else 0
        if entry["end_time"] != request["schedule"][end_index]["start_time"]:
            raise Exception("schedule entry " + str(idx+1) + " end time doesn't match start time of next entry")
        
        if not isinstance(entry["grid_charge"], bool):
            raise Exception("schedule entry " + str(idx+1) + " grid_charge must be boolean")

        if not isinstance(entry["capacity"], int):
            raise Exception("schedule entry " + str(idx+1) + " capacity must be an integer")

        if not (entry["capacity"] >= 0) and (entry["capacity"] <= 100):
            raise Exception("schedule entry " + str(idx+1) + " capacity must be between 0 and 100")

    RATED_POWER = Sensor((16, 17), "Rated power", WATT, 0.1)

    BATTERY_LOW_CAP = NumberRWSensor(219, "Battery Low Capacity", "%", max=50)

    USE_TIMER = SwitchRWSensor(248, "Use Timer", bitmask=1)

    PROG1_TIME = TimeRWSensor(250, "Prog1 Time")
    PROG2_TIME = TimeRWSensor(251, "Prog2 Time", min=PROG1_TIME)
    PROG3_TIME = TimeRWSensor(252, "Prog3 Time", min=PROG2_TIME)
    PROG4_TIME = TimeRWSensor(253, "Prog4 Time", min=PROG3_TIME)
    PROG5_TIME = TimeRWSensor(254, "Prog5 Time", min=PROG4_TIME)
    PROG6_TIME = TimeRWSensor(255, "Prog6 Time", min=PROG5_TIME)
    PROG1_TIME.min = PROG6_TIME
    PROG1_TIME.max = PROG2_TIME
    PROG2_TIME.max = PROG3_TIME
    PROG3_TIME.max = PROG4_TIME
    PROG4_TIME.max = PROG5_TIME
    PROG5_TIME.max = PROG6_TIME
    PROG6_TIME.max = PROG1_TIME

    PROG_CHARGE_OPTIONS = {
        0: "No Grid or Gen",
        1: "Allow Grid",
        2: "Allow Gen",
        3: "Allow Grid & Gen",
    }
    PROG_MODE_OPTIONS = {
        0: "None",
        4: "General",
        8: "Backup",
        16: "Charge",
    }

    PROG1_POWER = NumberRWSensor(256, "Prog1 power", WATT, max=RATED_POWER)
    PROG2_POWER = NumberRWSensor(257, "Prog2 power", WATT, max=RATED_POWER)
    PROG3_POWER = NumberRWSensor(258, "Prog3 power", WATT, max=RATED_POWER)
    PROG4_POWER = NumberRWSensor(259, "Prog4 power", WATT, max=RATED_POWER)
    PROG5_POWER = NumberRWSensor(260, "Prog5 power", WATT, max=RATED_POWER)
    PROG6_POWER = NumberRWSensor(261, "Prog6 power", WATT, max=RATED_POWER)
    PROG1_CAPACITY = NumberRWSensor(268, "Prog1 Capacity", "%", min=BATTERY_LOW_CAP)
    PROG2_CAPACITY = NumberRWSensor(269, "Prog2 Capacity", "%", min=BATTERY_LOW_CAP)
    PROG3_CAPACITY = NumberRWSensor(270, "Prog3 Capacity", "%", min=BATTERY_LOW_CAP)
    PROG4_CAPACITY = NumberRWSensor(271, "Prog4 Capacity", "%", min=BATTERY_LOW_CAP)
    PROG5_CAPACITY = NumberRWSensor(272, "Prog5 Capacity", "%", min=BATTERY_LOW_CAP)
    PROG6_CAPACITY = NumberRWSensor(273, "Prog6 Capacity", "%", min=BATTERY_LOW_CAP)
    PROG1_CHARGE = SelectRWSensor(274, "Prog1 charge", options=PROG_CHARGE_OPTIONS, bitmask=0x03)
    PROG2_CHARGE = SelectRWSensor(275, "Prog2 charge", options=PROG_CHARGE_OPTIONS, bitmask=0x03)
    PROG3_CHARGE = SelectRWSensor(276, "Prog3 charge", options=PROG_CHARGE_OPTIONS, bitmask=0x03)
    PROG4_CHARGE = SelectRWSensor(277, "Prog4 charge", options=PROG_CHARGE_OPTIONS, bitmask=0x03)
    PROG5_CHARGE = SelectRWSensor(278, "Prog5 charge", options=PROG_CHARGE_OPTIONS, bitmask=0x03)
    PROG6_CHARGE = SelectRWSensor(279, "Prog6 charge", options=PROG_CHARGE_OPTIONS, bitmask=0x03)
    PROG1_MODE = SelectRWSensor(274, "Prog1 mode", options=PROG_MODE_OPTIONS, bitmask=0x1C)
    PROG2_MODE = SelectRWSensor(275, "Prog2 mode", options=PROG_MODE_OPTIONS, bitmask=0x1C)
    PROG3_MODE = SelectRWSensor(276, "Prog3 mode", options=PROG_MODE_OPTIONS, bitmask=0x1C)
    PROG4_MODE = SelectRWSensor(277, "Prog4 mode", options=PROG_MODE_OPTIONS, bitmask=0x1C)
    PROG5_MODE = SelectRWSensor(278, "Prog5 mode", options=PROG_MODE_OPTIONS, bitmask=0x1C)
    PROG6_MODE = SelectRWSensor(279, "Prog6 mode", options=PROG_MODE_OPTIONS, bitmask=0x1C)

    track = [
        USE_TIMER,
        PROG1_TIME,
        PROG1_POWER,
        PROG1_CAPACITY,
        PROG1_CHARGE,
        PROG1_MODE,
        PROG2_TIME,
        PROG2_POWER,
        PROG2_CAPACITY,
        PROG2_CHARGE,
        PROG2_MODE,
        PROG3_TIME,
        PROG3_POWER,
        PROG3_CAPACITY,
        PROG3_CHARGE,
        PROG3_MODE,
        PROG4_TIME,
        PROG4_POWER,
        PROG4_CAPACITY,
        PROG4_CHARGE,
        PROG4_MODE,
        PROG5_TIME,
        PROG5_POWER,
        PROG5_CAPACITY,
        PROG5_CHARGE,
        PROG5_MODE,
        PROG6_TIME,
        PROG6_POWER,
        PROG6_CAPACITY,
        PROG6_CHARGE,
        PROG6_MODE,
    ]

    ivstate = InverterState()
    for t in track:
        ivstate.track(t)

    inverter = SolarmanSunsynk(
        state=ivstate,
        port="tcp://10.25.0.223:8899",
        dongle_serial_number=1797718863,
    )

    print("CONNECT", file=sys.stderr)

    await inverter.connect()

    print("WRITE USE_TIMER", file=sys.stderr)
    await write_sensor(inverter, USE_TIMER, "ON" if request["use_timer"] == True else "OFF")

    print("WRITE PROG1", file=sys.stderr)
    await write_sensor(inverter, PROG1_TIME, request["schedule"][0]["start_time"])
    await write_sensor(inverter, PROG1_CAPACITY, request["schedule"][0]["capacity"])
    await write_sensor(inverter, PROG1_CHARGE, PROG_CHARGE_OPTIONS[1] if request["schedule"][0]["grid_charge"] == True else PROG_CHARGE_OPTIONS[0])

    print("WRITE PROG2", file=sys.stderr)
    await write_sensor(inverter, PROG2_TIME, request["schedule"][1]["start_time"])
    await write_sensor(inverter, PROG2_CAPACITY, request["schedule"][1]["capacity"])
    await write_sensor(inverter, PROG2_CHARGE, PROG_CHARGE_OPTIONS[1] if request["schedule"][1]["grid_charge"] == True else PROG_CHARGE_OPTIONS[0])

    print("WRITE PROG3", file=sys.stderr)
    await write_sensor(inverter, PROG3_TIME, request["schedule"][2]["start_time"])
    await write_sensor(inverter, PROG3_CAPACITY, request["schedule"][2]["capacity"])
    await write_sensor(inverter, PROG3_CHARGE, PROG_CHARGE_OPTIONS[1] if request["schedule"][2]["grid_charge"] == True else PROG_CHARGE_OPTIONS[0])

    print("WRITE PROG4", file=sys.stderr)
    await write_sensor(inverter, PROG4_TIME, request["schedule"][3]["start_time"])
    await write_sensor(inverter, PROG4_CAPACITY, request["schedule"][3]["capacity"])
    await write_sensor(inverter, PROG4_CHARGE, PROG_CHARGE_OPTIONS[1] if request["schedule"][3]["grid_charge"] == True else PROG_CHARGE_OPTIONS[0])

    print("WRITE PROG5", file=sys.stderr)
    await write_sensor(inverter, PROG5_TIME, request["schedule"][4]["start_time"])
    await write_sensor(inverter, PROG5_CAPACITY, request["schedule"][4]["capacity"])
    await write_sensor(inverter, PROG5_CHARGE, PROG_CHARGE_OPTIONS[1] if request["schedule"][4]["grid_charge"] == True else PROG_CHARGE_OPTIONS[0])

    print("WRITE PROG6", file=sys.stderr)
    await write_sensor(inverter, PROG6_TIME, request["schedule"][5]["start_time"])
    await write_sensor(inverter, PROG6_CAPACITY, request["schedule"][5]["capacity"])
    await write_sensor(inverter, PROG6_CHARGE, PROG_CHARGE_OPTIONS[1] if request["schedule"][5]["grid_charge"] == True else PROG_CHARGE_OPTIONS[0])

@backoff.on_exception(backoff.expo, pysolarmanv5.pysolarmanv5.V5FrameError)
async def write_sensor(inverter, sensor, value):
    await inverter.write_sensor(sensor, value)

if __name__ == "__main__":
    asyncio.run(main())
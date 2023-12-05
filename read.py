import asyncio
import json
import sys
import backoff
from sunsynk import SolarmanSunsynk, InverterState, Sensor
from sunsynk import SwitchRWSensor, TimeRWSensor, NumberRWSensor, SelectRWSensor
from sunsynk import AMPS, CELSIUS, KWH, VOLT, WATT

@backoff.on_exception(backoff.expo, (IOError, OSError))
async def main():
    print("START", file=sys.stderr)

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

    print("READ", file=sys.stderr)

    await inverter.read_sensors(track)

    print("GENERATE RESULT", file=sys.stderr)

    result = {}

    result["use_timer"] = True if inverter.state.get(USE_TIMER) == "ON" else False

    result["schedule"] = [
        {
            "start_time": inverter.state.get(PROG1_TIME),
            "end_time": inverter.state.get(PROG2_TIME),
            "capacity": inverter.state.get(PROG1_CAPACITY),
            "grid_charge": True if inverter.state.get(PROG1_CHARGE) == "Allow Grid" else False
        },
        {
            "start_time": inverter.state.get(PROG2_TIME),
            "end_time": inverter.state.get(PROG3_TIME),
            "capacity": inverter.state.get(PROG2_CAPACITY),
            "grid_charge": True if inverter.state.get(PROG2_CHARGE) == "Allow Grid" else False
        },
        {
            "start_time": inverter.state.get(PROG3_TIME),
            "end_time": inverter.state.get(PROG4_TIME),
            "capacity": inverter.state.get(PROG3_CAPACITY),
            "grid_charge": True if inverter.state.get(PROG3_CHARGE) == "Allow Grid" else False
        },
        {
            "start_time": inverter.state.get(PROG4_TIME),
            "end_time": inverter.state.get(PROG5_TIME),
            "capacity": inverter.state.get(PROG4_CAPACITY),
            "grid_charge": True if inverter.state.get(PROG4_CHARGE) == "Allow Grid" else False
        },
        {
            "start_time": inverter.state.get(PROG5_TIME),
            "end_time": inverter.state.get(PROG6_TIME),
            "capacity": inverter.state.get(PROG5_CAPACITY),
            "grid_charge": True if inverter.state.get(PROG5_CHARGE) == "Allow Grid" else False
        },
        {
            "start_time": inverter.state.get(PROG6_TIME),
            "end_time": inverter.state.get(PROG1_TIME),
            "capacity": inverter.state.get(PROG6_CAPACITY),
            "grid_charge": True if inverter.state.get(PROG6_CHARGE) == "Allow Grid" else False
        },
    ]

    print("DUMP", file=sys.stderr)

    print(json.dumps(result, sort_keys=False, indent=4))

if __name__ == "__main__":
    asyncio.run(main())
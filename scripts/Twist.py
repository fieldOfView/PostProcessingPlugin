# Copyright (c) 2016 Aldo Hoeben / fieldOfView
# The PostProcessingPlugin is released under the terms of the AGPLv3 or higher.
from ..Script import Script

from UM.Application import Application

import re
import math

class Twist(Script):
    def __init__(self):
        super().__init__()

    def getSettingDataString(self):
        return """{
            "name":"Twist",
            "key": "Twist",
            "metadata": {},
            "version": 2,
            "settings":
            {
                "amount_per_layer":
                {
                    "label": "Rotation per layer",
                    "description": "None",
                    "unit": "degrees",
                    "type": "float",
                    "default_value": 0.1,
                    "minimum_value_warning": "-1",
                    "maximum_value_warning": "1"
                }
            }
        }"""

    def execute(self, data):
        global_container_stack = Application.getInstance().getGlobalContainerStack()
        if not global_container_stack:
            return data

        half_machine_width = global_container_stack.getProperty("machine_width", "value") / 2
        half_machine_depth = global_container_stack.getProperty("machine_depth", "value") / 2

        move_pattern = re.compile("(G[0-1]\s.*?)X([0-9\.]+)(.*?)Y([0-9\.]+)(.*)")

        layer_count = -1
        layer_nr = -1
        angle = 0
        process_lines = False
        amount_per_layer = math.pi * float(self.getSettingValueByKey("amount_per_layer")) / 180
        data_index = 0
        for chunk in data:
            new_chunk = ""
            lines = chunk.split("\n")
            for line in lines:
                if not process_lines:
                    if line.startswith(";LAYER_COUNT:"):
                        layer_count = int(line[13:])
                    elif line.startswith(";LAYER:"):
                        process_lines = True
                        new_chunk += ";START_Twist\n"
                    else:
                        # copy the input unprocessed and continue
                        new_chunk += line + "\n"
                        continue

                if line.startswith(";LAYER:"):
                    # start of a new layer
                    layer_nr = int(line[7:])
                    angle = layer_nr * amount_per_layer

                elif line.startswith(";TIME_ELAPSED:"):
                    # end of a layer
                    if layer_nr == layer_count - 1:
                        # last layer processed; stop porcessing lines
                        process_lines = False
                        new_chunk += line + "\n"
                        new_chunk += ";END_Twist\n"
                        continue

                result = move_pattern.match(line)
                if result:
                    x = float(result.group(2)) - half_machine_width
                    y = float(result.group(4)) - half_machine_depth

                    r = math.sqrt(x*x + y*y)
                    theta = math.atan2(y, x)
                    theta += angle

                    x = r * math.cos(theta) + half_machine_width
                    y = r * math.sin(theta) + half_machine_depth

                    line = result.expand("\\1X%.3f\\3Y%.3f\\5" % (x, y))

                new_chunk += line + "\n"

            data[data_index] = new_chunk
            data_index += 1

        return data
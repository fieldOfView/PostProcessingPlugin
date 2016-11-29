# Copyright (c) 2015 Jaime van Kessel, Ultimaker B.V.
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

        move_pattern = re.compile("G[0-1]\s.*?X([0-9\.]*).*?Y([0-9\.]*)")

        layer_nr = -1
        angle = 0
        layers_started = False
        amount_per_layer = math.pi * float(self.getSettingValueByKey("amount_per_layer")) / 180
        data_index = 0
        for chunk in data:
            new_chunk = ""
            lines = chunk.split("\n")
            for line in lines:
                if not layers_started:
                    if line.startswith(";LAYER:"):
                        layers_started = True
                    else:
                        new_chunk += line + "\n"

                if line.startswith(";LAYER:"):
                    layer_nr += 1
                    angle = layer_nr * amount_per_layer

                result = move_pattern.match(line)
                if result:
                    x = float(result.group(1)) - half_machine_width
                    y = float(result.group(2)) - half_machine_depth

                    r = math.sqrt(x*x + y*y)
                    theta = math.atan2(y, x)
                    theta += angle

                    x = r * math.cos(theta) + half_machine_width
                    y = r * math.sin(theta) + half_machine_depth

                    line = line.replace("X" + result.group(1), "X" + str(x)).replace("Y" + result.group(2), "Y" + str(y))

                new_chunk += line + "\n"

            data[data_index] = new_chunk
            data_index += 1

        return data
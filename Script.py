# Copyright (c) 2015 Jaime van Kessel, Ultimaker B.V.
# The PostProcessingPlugin is released under the terms of the AGPLv3 or higher.
from UM.Logger import Logger
from UM.Signal import Signal, signalemitter
from UM.i18n import i18nCatalog

# Setting stuff import
from UM.Application import Application
from UM.Settings.ContainerStack import ContainerStack
from UM.Settings.InstanceContainer import InstanceContainer
from UM.Settings.DefinitionContainer import DefinitionContainer
from UM.Settings.ContainerRegistry import ContainerRegistry

import re
import json
import collections
i18n_catalog = i18nCatalog("cura")


## Base class for scripts. All scripts should inherit the script class.
@signalemitter
class Script:
    def __init__(self):
        super().__init__()
        self._settings = None
        self._stack = None

        setting_data = self.getSettingData()
        self._stack = ContainerStack(stack_id=id(self))
        self._stack.setDirty(False)  # This stack does not need to be saved.


        ## Check if the definition of this script already exists. If not, add it to the registry.
        if "key" in setting_data:
            definitions = ContainerRegistry.getInstance().findDefinitionContainers(id = setting_data["key"])
            if definitions:
                # Definition was found
                self._definition = definitions[0]
            else:
                self._definition = DefinitionContainer(setting_data["key"])
                self._definition.deserialize(json.dumps(setting_data))
                ContainerRegistry.getInstance().addContainer(self._definition)
        self._stack.addContainer(self._definition)
        self._instance = InstanceContainer(container_id="ScriptInstanceContainer")
        self._instance.setDefinition(self._definition)
        self._stack.addContainer(self._instance)
        self._stack.propertyChanged.connect(self._onPropertyChanged)

        ContainerRegistry.getInstance().addContainer(self._stack)

    settingsLoaded = Signal()
    valueChanged = Signal()  # Signal emitted whenever a value of a setting is changed

    def _onPropertyChanged(self, key, property_name):
        if property_name == "value":
            self.valueChanged.emit()

            # Property changed: trigger reslice
            # To do this we use the global container stack propertyChanged.
            # Reslicing is necessary for setting changes in this plugin, because the changes
            # are applied only once per "fresh" gcode
            global_container_stack = Application.getInstance().getGlobalContainerStack()
            global_container_stack.propertyChanged.emit(key, property_name)

    ##  Needs to return a dict that can be used to construct a settingcategory file.
    #   See the example script for an example.
    #   It follows the same style / guides as the Uranium settings.
    #   Scripts can either override getSettingData directly, or use getSettingDataString
    #   to return a string that will be parsed as json. The latter has the benefit over
    #   returning a dict in that the order of settings is maintained.
    def getSettingData(self):
        setting_data = self.getSettingDataString()
        if type(setting_data) == str:
            setting_data = json.loads(setting_data, object_pairs_hook = collections.OrderedDict)
        return setting_data

    def getSettingDataString(self):
        raise NotImplementedError()

    def getDefinitionId(self):
        if self._stack:
            return self._stack.getBottom().getId()

    def getStackId(self):
        if self._stack:
            return self._stack.getId()

    ##  Convenience function that retrieves value of a setting from the stack.
    def getSettingValueByKey(self, key):
        return self._stack.getProperty(key, "value")

    ##  Convenience function that finds the value in a line of g-code.
    #   When requesting key = x from line "G1 X100" the value 100 is returned.
    def getValue(self, line, key, default = None):
        if not key in line or (';' in line and line.find(key) > line.find(';')):
            return default
        sub_part = line[line.find(key) + 1:]
        m = re.search('^-?[0-9]+\.?[0-9]*', sub_part)
        if m is None:
            return default
        try:
            return float(m.group(0))
        except:
            return default

    ##  This is called when the script is executed. 
    #   It gets a list of g-code strings and needs to return a (modified) list.
    def execute(self, data):
        raise NotImplementedError()

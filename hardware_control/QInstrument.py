class QInstrument(QGroupBox):

    __init__(self, name:str):
        super().__init__(name);
        self.settings = {};
        self.value = {};
        self.name = "";
        self.status = False;

class HCApp(QApplication):

    __init__(self):
        self.instruments = [];

    #
    # Copys the settings dictionaries from each instrument into a new dictionary
    # with the instrument's name serving as the key. The dictionary is then saved
    # to a JSON file.
    #
    def save_settings(self, filename:str):

        app_settings = {};

        #For each instrument...
        for instr in self.instruments:

            key_name = instr.name;

            #Prevent duplicate keys
            if (instr.name in app_settings):
                num = 2;
                while ((instr.name + "_" + str(num)) in app_settings ):
                    num = num + 1;
                key_name = instr.name + "_" + str(num);

            #Add instrument settings to master dictionary
            app_settings[key_name] = instr.settings;

        #Write JSON file
        try:
            with open(filename, 'w') as file:
                json.dump(app_settings, file);
                print(f"settings for {self.comm.instr.ID} saved to file '{filename}'");
        except Exception as e:
            print(f"ERROR: Failed to write file '{filename}'. State not saved.");
            print(f"\t{e}")

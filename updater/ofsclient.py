#!/usr/bin/env python3

import dbus
import sys
import os
import pwd

class OFSClient():
    def __init__(self):
      bus = dbus.SystemBus()
      service = bus.get_object('com.ofsservice', "/com/ofsservice")
      self.update = service.get_dbus_method('update', 'com.ofsservice.Update')
      self.discard = service.get_dbus_method('discard', 'com.ofsservice.Discard')
      self.apply = service.get_dbus_method('apply', 'com.ofsservice.Apply')
      self._quit = service.get_dbus_method('quit', 'com.ofsservice.Quit')

    def rebootSystem(self):
        print("Rebooting... ")
        os.system("reboot")
        quit()

    def run(self):
        if len(sys.argv[1:]) == 2 and sys.argv[1] == "update":
            if len(sys.argv[2]) and sys.argv[2][0] == '/' and os.path.isfile(sys.argv[2]):
                errorCode, errorText = self.update(sys.argv[2])
                if errorCode == 0:
                    self.rebootSystem()
                else:
                    print(errorText)
            else:
                print("Error: you should specify absolute path to the update file")
                
        elif len(sys.argv[1:]) == 1 and  sys.argv[1] == "discard":
            errorCode, errorText = self.discard()
            if errorCode == 0:
                self.rebootSystem()
            else:
                print(errorText)
        elif len(sys.argv[1:]) == 1 and sys.argv[1] == "apply":
            errorCode, errorText = self.apply()
            if errorCode == 0:
                self.rebootSystem()
            else:
                print(errorText)
        else:
            print("Error: invalid command.\n" \
                  "Usage:\n" \
                  "python3 /updater/ofsclient.py update <absolute_path_to_update>\n" \
                  "python3 /updater/ofsclient.py discard\n" \
                  "python3 /updater/ofsclient.py apply\n")

if __name__ == "__main__":
   if not pwd.getpwuid(os.getuid()).pw_name == "root":
       print("Error: Only root user can perform this command.")
   else:
       OFSClient().run()

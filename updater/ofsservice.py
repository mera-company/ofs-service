
#!/usr/bin/env python3

import os
import shutil
import hashlib

import gi.repository.GLib
import dbus
import dbus.service
import dbus.mainloop.glib

import syslog

class OFSService(dbus.service.Object):
    def __init__(self):
        self._wkDir = os.path.dirname("/.workdir/")
        self._updDir = os.path.dirname("/.updates/")
        self._manifest = "/.updates/manifest"
        self._ofsXino = "off"
        self._ofsName = "overlayfs"

        data = None
        try:
            data = open("/updater/state", "r")
            state = int(data.read())
            if state:
                self.updateRootfs()
        except:
            pass
        finally:
            if data:
                data.close()

    def run(self):
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        busName = dbus.service.BusName("com.ofsservice", dbus.SystemBus())
        dbus.service.Object.__init__(self, busName, "/com/ofsservice")

        self._loop = gi.repository.GLib.MainLoop()
        print("OFSService running...")
        self._loop.run()
        print("OFSService stopped")

    def unpackTar(self, tar_path):
        os.system("tar -xf " + tar_path + " -C " + 
                  self._updDir + " --overwrite")

        if not len(os.listdir(self._updDir)):
            syslog.syslog(syslog.LOG_ERR, 
                          "Unpacking of " + tar_path + " failed.")
            return False

        return True

    def _checkHash(self, imagePath, imageHashPath, hashType):
        res = False
        target = None
        required = None
        try:
            target = open(imagePath, 'rb')
            required = open(imageHashPath, 'r')
            targetHash = hashType(target.read()).hexdigest()
            requiredHash = required.read().split('\n')[0].strip()
            if targetHash == requiredHash:
                res = True
        except:
            pass
        finally:
            if target:
                target.close()
            if required:
                required.close()
            return res

    def checkHash(self, imagePath):
        checked = False
        if os.path.exists(imagePath + ".md5"):
            if not self._checkHash(imagePath, imagePath + ".md5", hashlib.md5):
                return False
            else:
                checked = True

        if os.path.exists(imagePath + ".sha256"):
            if not checkSha256(imagePath, imagePath + ".sha256", 
                               hashlib.sha256):
                return False
            else:
                checked = True

        return checked

    def createDir(self, dirPath, access=0o700):
        res = True
        try:
            os.mkdir(dirPath)
            # In accordance with
            # https://docs.python.org/3/library/os.html
            # "On some systems, mode is ignored... 
            # they are ignored and you should call chmod() 
            # explicitly to set them."
            os.chmod(dirPath, access)
        except:
            syslog.syslog(syslog.LOG_ERR, dirPath +
                          " can not be created or modified access to it.")
            res = False
        finally:
            return res

    def prepareUpdateData(self, imagePath):
        # Check for version current and new versions
        # if OLD_VERSION >= NEW_VERSION:
        #    return False

        if not os.path.exists(imagePath):
            syslog.syslog(syslog.LOG_ERR, imagePath + " can not be found.")
            return (-1, "Error: " + imagePath + " patch not found.")

        if not self.checkHash(imagePath):
            syslog.syslog(syslog.LOG_ERR, "Check sum for " +
                          imagePath + " is invalid or does not exist")
            return (-1, "Error: Check sum for "
                    + imagePath + " is invalid or does not exist")
        try:
            shutil.copy2("/etc/fstab", "/etc/fstab.original")
        except EnvironmentError:
            syslog.syslog(syslog.LOG_ERR, "Error: Can not prepare /etc/fstab.")
            return (-1, "Error: Can not backup /etc/fstab")

        if not self.createDir(self._updDir)  \
            or not self.createDir(self._wkDir):
            syslog.syslog(syslog.LOG_ERR, "Another update in process." +
                          "Please, apply or discard.")
            return (-1, "Error: Another update in process." +
                    "Please, apply or discard.")


        if not imagePath.split(".")[-1] == "tar":
            syslog.syslog(syslog.LOG_ERR, "Tar archive " +
                          imagePath + " is not found.")
            return (-1,  imagePath + " is not .tar archive.")

        if not self.unpackTar(imagePath):
            return (-1, "Error: Unpack of " + imagePath + " is failed.")

        return (0, "Success")

    def mountOverlayFS(self, overlayMountPoint):
        _updDir = self._updDir + overlayMountPoint
        _wkDir = self._wkDir + overlayMountPoint
        syslog.syslog("mount -t overlay -o rw,lowerdir=" +
                      overlayMountPoint + ",upperdir=" +
                      _updDir + ",workdir=" + _wkDir +
                      ",xino=" + self._ofsXino + " none " + overlayMountPoint)

        res = os.popen("mount -t overlay -o rw,lowerdir=" +
                       overlayMountPoint + ",upperdir=" +
                       _updDir + ",workdir=" + _wkDir + ",xino=" +
                       self._ofsXino + " none " + overlayMountPoint).read()
    
        syslog.syslog(res)
        if len(res):
            return False
        return True


    def prepareOverlayFs(self):
        overlaySubDirs = []

        if not os.path.exists(self._manifest):
            syslog.syslog(syslog.LOG_ERR,
                          "Error: Patch is invalid, manifest file not found.")
            return (-1, "Error: Patch is invalid, manifest file not found.")

        for updateSubDir in os.listdir(self._updDir):
            el = self._updDir + "/" + updateSubDir
            if os.path.isdir(el):
                overlaySubDirs.append(updateSubDir)

        if not len(overlaySubDirs):
            syslog.syslog(syslog.LOG_ERR,
                          "Upper level is empty. Cancel update.")
            return ( -1, "Error: Upper level is empty. Cancel update.")

        fstab_h = open("/etc/fstab", "a")
        for overlaySubDir in overlaySubDirs:
            _ovrDir = "/" + overlaySubDir
            _updDir = self._updDir + _ovrDir
            _wkDir = self._wkDir + _ovrDir
            self.createDir(_wkDir)

            fstab_h.write("none " + _ovrDir +
                          " overlay rw,relatime,lowerdir=" +
                          _ovrDir + ",upperdir=" + _updDir + ",workdir=" +
                          _wkDir + ",xino=" +
                          self._ofsXino + " 0 0\n")

            if _ovrDir == "/etc":
                continue

            if not self.mountOverlayFS(_ovrDir):
               return (-1, "Mount " + _ovrDir + " failed")
        fstab_h.close()

        if "etc" in overlaySubDirs:
            if not self.mountOverlayFS("/etc"):
                return (-1, "Mount /etc failed")

        if not self.removeFiles(overlaySubDirs):
            return (-1, "Error: Invalid Manifest file.")

        return (0, "Success")

    @dbus.service.method("com.ofsservice.Update",
                         in_signature='s', out_signature='is')
    def update(self, imagePath):
        syslog.syslog(syslog.LOG_ERR, "com.ofsservice.Update")
        errorCode, errorText =  self.prepareUpdateData(imagePath)
        if not errorCode == 0:
            self.discard()
            return (errorCode, errorText)

        errorCode, errorText =  self.prepareOverlayFs()
        if not  errorCode == 0:
            self.discard()
        return (errorCode, errorText)

    def restoreDefaultFstab(self):
        etcRequired = False
        if os.path.exists(self._updDir):
            if "etc" in os.listdir(self._updDir):
                os.system("umount /etc")
                etcRequired = True
#                el = self._updDir + "/" + updateSubDir
#                if os.path.isdir(el):
#                    overlaySubDirs.append(updateSubDir)

#            for overlaySubDir in overlaySubDirs:
#                _ovrDir = "/" + overlaySubDir
#                os.system("umount " + _ovrDir)

        if os.path.exists("/etc/fstab.original"):
            shutil.copy2("/etc/fstab.original", "/etc/fstab")
            os.remove("/etc/fstab.original")

        if etcRequired:
            self.mountOverlayFS("/etc")

    def removeFiles(self, overlaySubDirs):
        result = True
        manifestFile = open(self._manifest, "r")
        for line in manifestFile.readlines():
            fileToRemove = line.split("\n")[0]
            if os.path.exists(fileToRemove):
                subdir = ""
                if not fileToRemove[0] == "/":
                    syslog.syslog(syslog.LOG_ERR,
                                  "ERROR: Path " + fileToRemove +
                                  " from manifest file is wrong.")
                    result = False
                    break
                else:
                    subdir = fileToRemove.split("/")[1]

                if subdir in overlaySubDirs:
                    if os.path.isfile(fileToRemove):
                        os.remove(fileToRemove)
                    elif os.path.isdir(fileToRemove):
                        shutil.rmtree(fileToRemove)
                else:
                    syslog.syslog(syslog.LOG_ERR,
                                  "ERROR: file " + fileToRemove +
                                  " from manifest file not found, but continue...")
                    continue
            else:
                syslog.syslog(syslog.LOG_ERR,
                              "ERROR: file " + fileToRemove +
                              " from manifest file not found, but continue...")
                continue

        manifestFile.close()
        return result

    def removeUpdateData(self):
        if os.path.exists(self._updDir):
            shutil.rmtree(self._updDir)

        if os.path.exists(self._wkDir):
            shutil.rmtree(self._wkDir)

    def copyOwnerGroup(self, src, dest):
        statInfo = os.stat(src)
        os.chown(dest, statInfo.st_uid, statInfo.st_gid)

    def disableAvahi(self):
        os.system("systemctl disable avahi-daemon")
        os.system("systemctl stop avahi-daemon")

    @dbus.service.method("com.ofsservice.Discard",
                         in_signature='', out_signature='is')
    def discard(self):
        syslog.syslog(syslog.LOG_ERR, "com.ofsservice.Discard")
        self.disableAvahi()
        self.restoreDefaultFstab()
        self.removeUpdateData()
        return (0, "Success")

    @dbus.service.method("com.ofsservice.Apply",
                         in_signature='', out_signature='is')
    def apply(self):
        syslog.syslog(syslog.LOG_ERR, "com.ofsservice.Apply")

        if not os.path.exists(self._wkDir) or not os.path.exists(self._updDir):
            syslog.syslog(syslog.LOG_ERR, "Error: OverlayFs is corrupted.")
            return (-1, "Error: OverlayFs is corrupted or does not exist.")

        if not os.path.exists(self._manifest):
            syslog.syslog(syslog.LOG_ERR, "Error: Manifest file not found.")
            return (-1, "Error: Manifest file not found.")

        self.disableAvahi()
        self.restoreDefaultFstab()

        with open("/updater/state", "w+") as data:
            data.write("1")
        data.close()

        return (0, "Success")

    def updateRootfs(self):
        overlaySubDirs = []
        for updateSubDir in os.listdir(self._updDir):
            el = self._updDir + "/" + updateSubDir
            if os.path.isdir(el):
                overlaySubDirs.append(updateSubDir)

        if not self.removeFiles(overlaySubDirs):
            syslog.syslog(syslog.LOG_ERR,
                          "Error: Can not find files from  Manifest file on rootfs.")
            return

        filesToRemove = []
        manifestFile = open(self._manifest, "r")
        for line in manifestFile.readlines():
            filesToRemove.append(line.split("\n")[0])
        manifestFile.close()
        filesToRemove.append("/manifest")

        for root, subfolders, files in os.walk(self._updDir):
            initCatalog = root.split(self._updDir, 1)[-1] + "/"
            if len(files):
                for f in files:
                    if (initCatalog + f) in filesToRemove:
                        continue

                    print(root + "/" + f)
                    print(initCatalog + f)
                    shutil.copy2(root + "/" + f, initCatalog + f)
                    self.copyOwnerGroup(root + "/" + f, initCatalog + f)

            if len(subfolders):
                for subfolder in subfolders:
                    destCatalog = initCatalog + subfolder
                    print(destCatalog)

                    if not os.path.exists(destCatalog):
                        os.makedirs(destCatalog)
                        shutil.copystat(root + "/" + subfolder, destCatalog)
                        self.copyOwnerGroup(root + "/" + subfolder, destCatalog)

        self.removeUpdateData()

        with open("/updater/state", "w+") as data:
            data.write("0")
        data.close()

    @dbus.service.method("com.ofsservice.Quit",
                         in_signature='', out_signature='')
    def quit(self):
      syslog.syslog(syslog.LOG_ERR, "com.ofsservice.Quit")
      self._loop.quit()

if __name__ == "__main__":
   OFSService().run()

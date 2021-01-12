# Over-the-air Overlay File System Service (OTA OFSS)

Service used overlayFS functionality to install updates from external repositories.
Updates are represented as tar archive for now. 

## Deployment

You need to run install/install_*.sh shell script are apropriated for your architecture.
The following script will install service on Ubuntu 20.04/18.04:
```
./install_ubuntu2004.sh
```

### Requirements
```
python3
python3-pip
```
### Python libraries Requirements
```
shutil
hashlib
gi.repository.GLib
dbus
syslog
```

## Updates preparation

You should prepare tar archive and file with check-sum (md5 or sha256). For example:
```
update1.tar 
update1.tar.md5
```

The 'tar' archive should contain:
* files for update (this files will be copied to target system)
* the 'manifest' file with list of files to remove (each line is absolute path to file or folder which should be removed on target system)

Check-sum file should contains only hash. 
Example of generation:
```
md5sum  ./update1.tar | cut -d ' ' -f 1 > update1.tar.md5
```

Note: tar and check-sum files should be placed to the same folder (path) during 'update' command.

## Usage 

Common procedure:
* Run 'update' command. System will be rebooted automatically.
* Check the system state/stability.
  Note: all changes on filesystem until 'apply' or 'discard' commands will be lost.
* Run 'apply' command, if you want to apply update, or run 'discard' in order to revert.
  System will be rebooted.

You can use following commands to access ofsservice dbus service (all commands require system's reboot):

```python3 /updater/ofsclient.py update absolute_path_to_update``` 
It will prepare path to update to use throuht overlay file system 

```python3 /updater/ofsclient.py discard```
It will discard changes after update command

```python3 /updater/ofsclient.py apply```
It will apply changes after update command and copy path's data to real file system

## Running the tests

Tests are not ready yet, to be filled once tests are added

## Coding style

* We're using [PEP-0008)](https://www.python.org/dev/peps/pep-0008/)) indentation style
* The identation is 4 spaces

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct, and the process for submitting pull requests to us.

## Versioning

We use [SemVer](http://semver.org/) for versioning. For the versions available, see the [tags on this repository](https://github.com/mera-company/cpp-serialization-library/tags).

## Authors

* **Dmitry Yudenich** - *Initial work* - [Overlay File System Service](https://github.com/mera-company/ofs-service)

See also the list of [contributors](https://github.com/mera-company/ofs-service/graphs/contributors) who participated in this project.

## License

This project is licensed under the Apache 2.0 License - see the [LICENSE](LICENSE) file for details

## Acknowledgments

* Hat tip to anyone whose code was used
* Inspiration
* etc
rpm-patch-system
================

A simple tool to apply and track patches. You will need to change configs/targets based on your own usage. 

Description
-----------
This tool has mainly been developed to apply patches to Zenoss. However, it can be used to patch anything on the system. Features include:

* Detailed log
* Check if the patch is already applied
* Rollback process
* Backup
* Spec file for RPM creation
* json file to list patch details

Usage:
------
```
[zenoss@pal ~]$ /usr/share/rpm-patch-system/apply_patch.py --help
usage: apply_patch.py [-h] [--revert] [--apply] [--backup] [--dryrun]
                      [--patchdetails] [--targetfiles] [--verbose]
                      [--patchesfolder PATCHES_SRC] [--logfile LOGFILE]
                      [--patchlist PATCHLIST] [--version]

Applies patches from the list /usr/share/rpm-patch-system/patchlist.json and
source folder /usr/share/rpm-patch-system/patches then log results to
/var/log/patches.log. After usage ensure the log does not contain
errors.

optional arguments:
  -h, --help            show this help message and exit
  --revert              Revert all the changes from .backup files.
  --apply               Apply all the changes.(Automatically takes backup)
  --backup              Create backup files. Ignores the files which have
                        .orig backup.
  --dryrun              Dry run the patches and log the results. No actual
                        changes are made.
  --patchdetails        Prints name and description of the all patches listed
                        in Json file.
  --targetfiles         Prints name and target files of the all patches listed
                        in Json file.
  --verbose             Turns on debug mode.
  --patchesfolder PATCHES_SRC
                        Set the patches source folder. Default: /usr/share
                        /bbc-zenoss-patches/patches
  --logfile LOGFILE     Log file path. Default: /opt/zenoss/log/patches.log
  --patchlist PATCHLIST
                        Json formated patches list. See the sample template
                        for details. Default:/usr/share/bbc-zenoss-
                        patches/patchlist.json
  --version             show program's version number and exit
  ```
  
  Dependencies
  ------------
  * lsdiff
  * patch
  * rpm-build
  * gcc
  * redhat-rpm-config
  
  Build
  -----
  In your home dir create following dirs RPMS/ SOURCES/ SPECS/ SRPMS/  ( 'mkdir -p ~/{BUILD,RPMS,SOURCES,SPECS,SRPMS}' ) and clone the repo contents in SOURCES then run:
  
  ```
  rpmbuild -ba ./SOURCES/SPECS/*.spec
  ```

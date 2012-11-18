#!/usr/bin/env python
'''
@author: whyzgeek
@version: 1.1
@summary: Apply patches
'''
__doc__ = """Apply patches: for more info run with --help and check the runbook for details
misuse of this package can create disasterous results.
"""
VERSION = '1.1'
import os
import logging
import logging.handlers
import commands
import shutil
import sys
import argparse
import json
import grp
import pwd


PATCH_SRCDIR = '/usr/share/rpm-patch-system/patches'
LOG_FILENAME = '/var/log/patches.log'
PATCH_LISTFILE = '/usr/share/rpm-patch-system/patchlist.json'
USERID = pwd.getpwnam('root').pw_uid
GROUPID = grp.getgrnam('root').gr_gid

LOG_MAXBYTE = 500000
LOG_BACKUP_COUNT = 3

log = logging.getLogger('apply_patch')
log.setLevel(logging.INFO)
# Add the log message handler to the logger
try:
    handler = logging.handlers.RotatingFileHandler(LOG_FILENAME, maxBytes=LOG_MAXBYTE, backupCount=LOG_BACKUP_COUNT)
    fmt = logging.Formatter("%(asctime)s - %(name)s - "
                                    "%(levelname)s - %(message)s")
    handler.setFormatter(fmt)
    log.addHandler(handler)
except Exception, e:
    print "Logfile %s couldn't be created because %s" % \
                                        (LOG_FILENAME, str(e))
log.info("STARTED! Logfile opened for writing...")


def runCommand(cmd):
    status = 1
    output = None
    if not cmd:
        raise Exception("No command provided")
    log.debug("Running %s" % cmd)
    (status, output) = commands.getstatusoutput(cmd)
    log.debug("Ran %s, output %s, status %s" % (cmd, output, status))
    if status != 0:
        raise Exception("%s failed with status %s and error %s" % \
                            (cmd, status, output))
    return output


class PatchList(object):
    patchList = []

    def __init__(self, input):
        if type(input) != type(dict()):
            raise Exception('A dict needed')
        for k, v in sorted(input.items(),
                key=lambda t: t[1]['patchPriority']):
            self.patchList.append(Patch(k, v))

    def __repr__(self):
        return "\n".join([str(x) for x in self.patchList])

    def validateAll(self):
        lastPriority = 0
        for patch in self.patchList:
            patch.validate()
            if patch.patchPriority <= lastPriority:
                log.error("%s patch priority is messed up, quiting..." % patch.patchFile)
                sys.exit(1)
            else:
                lastPriority = patch.patchPriority

    def detailsAll(self):
        self.validateAll()
        log.info("Giving stdout all patch details...")
        for patch in self.patchList:
            print "%s- %s : %s" % (patch.patchPriority, \
                                patch.patchFile, patch.description)

    def affectedfilesAll(self):
        self.validateAll()
        log.info("Giving stdout all affected files...")
        for patch in self.patchList:
            print "%s- %s : %s" % (patch.patchPriority, \
                                patch.patchFile, str(patch.affectedFiles()))

    def dryRunAll(self):
        self.validateAll()
        for patch in self.patchList:
            patch.dryRun()

    def revertAll(self):
        self.validateAll()
        for patch in self.patchList:
            patch.revert()

    def backupAll(self):
        self.validateAll()
        for patch in self.patchList:
            patch.backup()

    def applyAll(self):
        self.validateAll()
        self.backupAll()
        for patch in self.patchList:
            patch.apply()


class Patch(object):

    def __init__(self, patchFile, kw):
        self.patchFile = patchFile
        self.patchLevel = kw.get('patchLevel', -1)
        self.baseDir = kw.get('baseDir', None)
        self.patchPriority = kw.get('patchPriority', 0)
        self.description = kw.get('description', 0)
        self.validated = False
        self.patchFilePath = None
        self.patchCmd = None

    def __repr__(self):
        return "<Patch %s : %s>" % (self.patchFile, str(dict([(k, v) for (k, v) in  \
            self.__dict__.iteritems() if k in ['patchPriority', 'baseDir', \
                                'patchLevel']])))

    def validate(self):
        # Validate patch file
        self.patchFilePath = os.path.join(PATCH_SRCDIR + '/' + self.patchFile)
        self.patchFilePath = os.path.normpath(self.patchFilePath)

        try:
            with open(self.patchFilePath) as fh:
                pass
                #self.patchContent = fh.readlines()
        except Exception, e:
            log.error("Couldn't read patch %s, %s" % \
                                (self.patchFilePath, str(e)))
            sys.exit(1)
        # Check other parameters
        try:
            if self.patchLevel < 0:
                raise Exception("patch level should be set")
            if self.baseDir is None:
                raise Exception("patch needs a base dir")
            if self.patchPriority == 0:
                raise Exception("patch needs a apply priority >0")
            self.patchCmd = 'patch -p%s -t -d %s -F 0 -i %s -N --no-backup-if-mismatch -r /tmp/reject' % \
                                            (self.patchLevel, self.baseDir, self.patchFilePath)
            self.validated = True
        except Exception, e:
            log.error("Could not validate patch %s, because %s" % \
                                                (self.patchFilePath, str(e)))

    def hasApplied(self):
        if not self.validated:
            self.validate()
        cmd = self.patchCmd + ' --dry-run'
        try:
            output = runCommand(cmd)
            log.debug("CHECKAPPLIED: output for cmd %s is %s" % (cmd, output))
        except Exception, e:
            if str(e).find('patch detected!') > -1:
                return True
            else:
                log.error("CHECKAPPLIED: Couldn't check if the patch %s is applied because %s" % \
                        (self.patchFile, str(e)))
        return False

    def affectedFiles(self):
        if not self.validated:
            raise Exception('Needs validating')
        cmd = "/usr/bin/lsdiff --strip=%s '%s'" % (self.patchLevel, self.patchFilePath)
        output = None
        try:
            output = runCommand(cmd)
            log.debug("AFFECTEDFILES: output for cmd %s is %s" % (cmd, output))
        except Exception, e:
            log.error("AFFECTEDFILES: Can't list affected files because %s and output:%s" % \
                                                (str(e), output))
            sys.exit(3)
        result = []
        for line in output.splitlines():
            file = os.path.join(self.baseDir + '/' + line.strip())
            file = os.path.normpath(file)
            result.append(file.encode('ascii', 'ignore'))
        return result

    def backup(self):
        affectedFiles = self.affectedFiles()
        for file in affectedFiles:
            if os.path.exists(file + '.orig'):
                log.info('BACKUP: %s.orig backup file exist, skipping backup' % file)
                continue
            if  os.path.exists(file) and not (os.path.exists(file + '.backup') \
                or os.path.exists(file + '.revert')):
                try:
                    shutil.copy2(file, file + '.backup')
                    os.chown(file + '.backup', USERID, GROUPID)
                    log.info("BACKUP: %s backed up successfully" % file)
                    continue
                except Exception, e:
                    log.error("BACKUP: %s backup failed. I can't proceeed. %s" % \
                                        (file, str(e)))
                    sys.exit(3)
            if not os.path.exists(file) and not os.path.exists(file + '.revert'):
                try:
                    fh = open(file + '.revert', 'w')
                    fh.close()
                    os.chown(file + '.revert', USERID, GROUPID)
                    log.warning("BACKUP: No source file exist for %s, %s.revert file created."
                              % (file, file))
                    continue
                except Exception, e:
                    log.error("BACKUP: %s.revert couldn't be created. %s" % (file, str(e)))
                    sys.exit(3)

    def revert(self):
        affectedFiles = self.affectedFiles()
        for file in affectedFiles:
            if os.path.exists(file) and os.path.exists(file + '.backup'):
                try:
                    shutil.copy2(file + '.backup', file)
                    os.chown(file, USERID, GROUPID)
                    os.remove(file + '.backup')
                    log.info("REVERT: %s original file reverted successfuly" % file)
                    continue
                except Exception, e:
                    log.error("REVERT: Couldn't revert %s from backup file" % file)
                    sys.exit(2)
            elif os.path.exists(file) and os.path.exists(file + '.revert'):
                try:
                    os.remove(file)
                    os.remove(file + '.revert')
                    log.warning("REVERT: Removed %s original and revert files successfuly."
                                                " Apparently patch created it." % file)
                    continue
                except Exception, e:
                    log.error("REVERT: Couldn't remove patch created %s file, exception:e" % (file, str(e)))
                    sys.exit(2)
            elif os.path.exists(file + '.revert') or os.path.exists(file + '.backup'):
                log.warning("REVERT: Removed an abandoned %s{.revert, .backup}, it seems"
                                        " previous run has failed." % file)
            else:
                log.warning("REVERT: For file %s no .revert or .backup exists, skipping..." % file)

    def apply(self):
        if self.hasApplied():
            log.warning("APPLY: Patch %s is already applied, skipping..."
                        " Note the backup file is not original!" % self.patchFile)
            return
        command = self.patchCmd
        if log.level == logging.DEBUG:
            command += ' --verbose'
        try:
            output = runCommand(command)
            log.info("APPLY: Applied %s" % command)
            log.debug("APPLY: Applied %s, output is %s" % (command, output))
        except Exception, e:
            log.error("APPLY: Couldn't apply patch %s because %s" % \
                                        (str(self.patchFile), str(e)))
            sys.exit(3)

    def dryRun(self):
        if not self.validated:
            self.validate()
        command = self.patchCmd + ' --dry-run'
        if log.level == logging.DEBUG:
            command += ' --verbose'
        try:
            log.info("DRYRUN: Running %s" % command)
            output = runCommand(command)
            log.info(output)
        except Exception, e:
            log.error(str(e))

if __name__ == '__main__':

    if len(sys.argv) == 1:
        print "Specify at least one command. Use --help for help."
        sys.exit(0)

    parser = argparse.ArgumentParser(description='Applies patches from the list %s and source folder %s then log results'
                    ' to %s. After usage ensure the log does not contain errors.' % \
                    (PATCH_LISTFILE, PATCH_SRCDIR, LOG_FILENAME))
    parser.add_argument('--revert', dest='revert', action='store_true',
                                           help='Revert all the changes from .backup files.')
    parser.add_argument('--apply', dest='apply', action='store_true',
                                           help='Apply all the changes.(Automatically takes backup)')
    parser.add_argument('--backup', dest='backup', action='store_true',
                                           help='Create backup files. Ignores the files which have .orig backup.')
    parser.add_argument('--dryrun', dest='dryrun', action='store_true',
                                           help='Dry run the patches and log the results. No actual changes are made.')
    parser.add_argument('--patchdetails', dest='patchdetails', action='store_true',
                                           help='Prints name and description of the all patches listed in Json file.')
    parser.add_argument('--targetfiles', dest='targetfiles', action='store_true',
                                           help='Prints name and target files of the all patches listed in Json file.')
    parser.add_argument('--verbose', dest='verbose', action='store_true',
                                           help='Turns on debug mode.')
    parser.add_argument('--patchesfolder', dest='patches_src', default=PATCH_SRCDIR,
            help='Set the patches source folder. Default: %s' % PATCH_SRCDIR)
    parser.add_argument('--logfile', dest='logfile', default=LOG_FILENAME,
           help='Log file path. Default: %s' % LOG_FILENAME)
    parser.add_argument('--patchlist', dest='patchlist', default=PATCH_LISTFILE,
            help='Json formated patches list. See the sample template for details. Default:%s' % PATCH_LISTFILE)
    parser.add_argument('--version', action='version', version='apply_patch %s' % VERSION)

    args = parser.parse_args()

    LOG_FILENAME = args.logfile
    PATCH_LISTFILE = args.patchlist
    PATCH_SRCDIR = args.patches_src

    if args.verbose:
        log.setLevel(logging.DEBUG)
    if int(args.apply) + int(args.backup) + int(args.revert) + \
            int(args.dryrun) + int(args.patchdetails) + int(args.targetfiles) > 1:
        print "You are allowed to used only one command"
        sys.exit(0)

    if (args.apply or args.backup or args.dryrun or args.revert
                            or args.patchdetails or args.targetfiles):
        try:
            with open(PATCH_LISTFILE) as fh:
                patchList = json.load(fh)
        except Exception, e:
            print "Couldn't access %s to load patch list because %s, quiting" % \
                                        (PATCH_LISTFILE, str(e))
            sys.exit(3)
        patchListObj = PatchList(patchList)
        if args.apply:
            patchListObj.applyAll()
        elif args.revert:
            patchListObj.revertAll()
        elif args.backup:
            patchListObj.backupAll()
        elif args.dryrun:
            patchListObj.dryRunAll()
        elif args.patchdetails:
            patchListObj.detailsAll()
        elif args.targetfiles:
            patchListObj.affectedfilesAll()

    log.info("FINISHED running %s" % __file__)

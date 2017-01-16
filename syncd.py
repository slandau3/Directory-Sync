#!/usr/bin/env python3
import sys, os
import time
import resource

__author__ = 'Steven Landau'

# Sets the numeric mass of the daemon
UMASK = 0

# Directory where a log file will be placed
LOGDIR = '/tmp/'

MAXFD = 1024

# Directories to search through and upload (absolute path)
DIRS_TO_WATCH = ['Users/slandau/Desktop', 'Users/slandau/bin',
                 'Users/slandau/Documents', 'Users/slandau/Downloads'
                 'Users/slandau/Pictures', 'Users/slandau/Movies']

# The main user of the computer
MAIN_DIR_NAME = 'slandau'

# Where you want the data to be synced to.
# Ex: pi@xx.yyy.zz.aaa:/home/pi/folder
BASE_REMOTE_DIR = 'pi@98.113.95.132:/home/pi/Seagate/steven_stuff'

# recursive, update (do not erase newer), preserve permissions, compress while uploading
RSYNC_COMMANDS = '-rupz'

# Number of times written to a log file. Will overwrite every 100 writes so the
# file does not become infinite in size.
TIMES_WRITTEN = 0

NAP_TIME = 120  # Time between syncs in seconds
if hasattr(os, 'devnull'):
    REDIRECT_TO = os.devnull
else:
    REDIRECT_TO = '/dev/null'


def create_daemon():
    """
    Creates the actual daemon by double forking which
    disconnects from the terminal and makes the program into an entirely new process
    :return: 0 for success
    """
    try:
        pid = os.fork()
    except OSError as e:
        raise Exception("{} [{}]".format(e.strerror, e.errno))

    if pid == 0:  # if we are the child
        os.setsid()  # set the session id
        try:
            pid = os.fork()  # fork again to complete the transfer
        except OSError as e:
            raise Exception("{} [{}]".format(e.strerror, e.errno))

        if pid == 0:
            os.chdir(LOGDIR)  # change the working directory to where the logfile will be
            os.umask(UMASK)
        else:  # if we are not the child, exit
            os._exit(0)
    else:
        os._exit(0)

    # Ensures that we cannot have an absurd number of file descriptors
    maxfd = resource.getrlimit(resource.RLIMIT_NOFILE)[1]
    if maxfd == resource.RLIM_INFINITY:
        maxfd = MAXFD

    # Iterate through and close all file descriptors.
    for fd in range(0, maxfd):
        try:
            os.close(fd)
        except OSError:  # ERROR, fd wasn't open to begin with (ignored)
            pass

    os.open(REDIRECT_TO, os.O_RDWR)
    os.dup2(0, 1)  # redirect standard input to stdout
    os.dup2(0, 2)  # redirect stdin to stderr
    return 0


def sync_files():
    for cur_dir in DIRS_TO_WATCH:
        os.chdir(cur_dir)

        # on the remote disk
        i = 0
        dir_path = os.getcwd().split('/')
        """
        The loop below iterates through each part of the current directory to determine
        where the cutoff point is. The reason for this is to determine where the path on the remote disk will go.
        For example, we want to transfer example.txt on the local pc. The absolute path is Users/person/documents/example.txt
        The location we want on the remote pc is person/documents/example.txt. The for loop below, ensures that the file on the remote
        disk will be person/documents/...
        """
        for index, piece in enumerate(dir_path):
            if piece == MAIN_DIR_NAME:
                i = index
                break

        dir_path = dir_path[i:]
        remote_dir_name = '/'.join(dir_path)

        # Assemble the remote directory path
        remote_dir = '{base_remote}{dirname}/'.format(base_remote=BASE_REMOTE_DIR, dirname=remote_dir_name)
        # The entire transfer command
        rsync_command = 'rsync {commands} {current_dir_path}/. {remote_dirWpath}'\
            .format(commands=RSYNC_COMMANDS, current_dir_path=cur_dir, remote_dirWpath=remote_dir)

        os.system(rsync_command)

        log_sync(cur_dir, remote_dir)


def log_sync(dir, remote_dir):
    global TIMES_WRITTEN
    if TIMES_WRITTEN == 100: # Reset every 100 times
        write_d_info(0)  # ret code is usually 0
        TIMES_WRITTEN = 0

    os.chdir(LOGDIR)
    dfile = open("syncd.log", 'a')
    dfile.write(dir + ' synced to ' + remote_dir + 'at ' + str(time.localtime()) + '\n\n')
    dfile.flush()
    dfile.close()
    TIMES_WRITTEN += 1


def write_d_info(ret_code):
    procParams = """
           return code = %s
           process ID = %s
           parent process ID = %s
           process group ID = %s
           session ID = %s
           user ID = %s
           effective user ID = %s
           real group ID = %s
           effective group ID = %s
           """ % (ret_code, os.getpid(), os.getppid(), os.getpgrp(), os.getsid(0),
                  os.getuid(), os.geteuid(), os.getgid(), os.getegid())


    dfile = open("syncd.log", "w")
    dfile.write(procParams + "\n")
    dfile.flush()
    dfile.close()

if __name__ == '__main__':
    retCode = create_daemon()

    write_d_info(retCode)

    while True:
        sync_files()
        time.sleep(NAP_TIME)

    sys.exit(retCode)
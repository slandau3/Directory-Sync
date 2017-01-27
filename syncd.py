#!/usr/bin/env python3
import sys, os
import time
import resource
import subprocess

__author__ = 'Steven Landau'

# Sets the numeric mass of the daemon
UMASK = 0

# Directory where a log file will be placed
LOGDIR = '/tmp'

LOGFILE = '/tmp/syncd.log'
MAXFD = 1024

# Directories to search through and upload (absolute path)
DIRS_TO_WATCH = ['/Users/slandau/bin', '/Users/slandau/Documents', '/Users/slandau/Downloads',
                 '/Users/slandau/Pictures', '/Users/slandau/Movies', '/Users/slandau/Desktop']

# The main user of the computer
MAIN_DIR_NAME = 'slandau'

# Where you want the data to be synced to.
# Ex: pi@xx.yyy.zz.aaa:/home/pi/folder
BASE_REMOTE_DIR = ''

# recursive, update (do not erase newer), preserve permissions, compress while uploading. Respective.
RSYNC_COMMANDS = '-rupz'

# Number of times written to a log file. Will overwrite every 100 writes so the
# file does not become infinite in size.
TIMES_WRITTEN = 0

NAP_TIME = 300  # Time between syncs in seconds

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

            """I have been unable to redirect stdout and stderr via the method below.             
            fd = os.open("/tmp/syncd.log", os.O_RDWR)  # TODO determine if this is a good idea

            os.dup2(0, 1)  # redirect standard input to stdout
            os.dup2(1, fd)  # redirect stdout to a file
            os.dup2(2, fd)  # redirect stderr to a file
            """
            log_file = open(LOGFILE, 'w')
            sys.stdout = log_file
            sys.stderr = log_file
            print("BEGINNING DAEMON\n")
            exec("start(log_file)")
            # fd will be closed at the end of the start method.
            #os.close(fd)  # in the event that it is not a good idea, delete this
            """
            A few things about the small section above. 
            1. the /tmp/syncd.log file does not appear to contain "BEGAN", nor does "END". 
            2. Am I redirecting the output correctly. It's my understanding that os.open returns a file descriptor, unlike normal open() which returns a file object.
            3. I'm not entirely sure if I'm working with the file descriptor correctly. Is the file staying open until the program fully closes? Is that a problem?
            4. Is there anything else I should be doing or considering here?
            """


        else:  # if we are not the child, exit
            os._exit(0)
    else:
        os._exit(0)
    return 0

# Change this function as you wish. Simply iterate over the directories you want to sync and send to the remote
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

        dir_path = dir_path[i:len(dir_path)-1]
        remote_dir_name = '/'.join(dir_path)

        # Assemble the remote directory path
        remote_dir = '{base_remote}{dirname}/'.format(base_remote=BASE_REMOTE_DIR, dirname=remote_dir_name)
        # The entire transfer command
        rsync_command = 'scp {commands} {current_dir_path}/. {remote_dirWpath}'\
            .format(commands=RSYNC_COMMANDS, current_dir_path=cur_dir, remote_dirWpath=remote_dir)


        subprocess.run(['rsync', RSYNC_COMMANDS, cur_dir, remote_dir])
        #print(rsync_command)
        #os.system(rsync_command)

        log_sync(cur_dir, remote_dir)


def log_sync(dir, remote_dir):  # Log anytime a transfer takes place
    #os.chdir(LOGDIR)

    # stdout and stderr are redirected to the log file. The commented out code is deprecated.
    # dfile means daemon-file (daemon process log)
    #dfile = open("syncd.log", 'a')
    #dfile.write(dir + ' synced to ' + remote_dir + 'at ' + str(time.localtime()) + '\n\n')
    #dfile.flush()
    #dfile.close()
    print(dir + ' synced to ' + remote_dir + ' at ' + str(time.asctime()) + '\n')
    sys.stdout.flush()


def write_d_info(ret_code):  # write all process information to a file
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

    print(procParams + "\n")

def redirect_stdout_and_stderr():
    log_file = open(LOGFILE, 'a')
    sys.stdout = log_file
    sys.stderr = log_file
    sys.stdout.flush()
    sys.stderr.flush()
    return log_file

def start(log_file):
    write_d_info(0)
    sys.stdout.flush()
    times_written = 0
    while True:
        try:
            sync_files()
        except Exception as e:
            print(e)
        finally:
            sys.stdout.flush()
            sys.stderr.flush()
            log_file.close()
            times_written += 1
            if times_written == 100:
                erase_file = open(LOGFILE, 'w')
                sys.stdout = erase_file
                sys.stderr = erase_file
                write_d_info(0)
                sys.stdout.flush()
                erase_file.close()

            log_file = redirect_stdout_and_stderr()
            time.sleep(NAP_TIME)

if __name__ == '__main__':
    retCode = create_daemon()
    sys.exit(retCode)

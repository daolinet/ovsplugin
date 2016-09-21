import logging
import os
import random
import subprocess
import time

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

class InvalidArgumentError(Exception):
    def __init__(self, message=None):
        super(InvalidArgumentError, self).__init__(message)

class UnknownArgumentError(Exception):
    def __init__(self, message=None):
        super(UnknownArgumentError, self).__init__(message)

class ProcessExecutionError(Exception):
    def __init__(self, cmd=None, description=None):
        self.cmd = cmd
        self.description = description

        if description is None:
            description = "Unexpected error while running command."
        message = ('%(description)s\n'
                   'Command: %(cmd)s\n') % {'description': description,
                                            'cmd': cmd}
        super(ProcessExecutionError, self).__init__(message)

def execute(*cmd, **kwargs):
    """Helper method to shell out and execute a command through suprocess.

    Allows optional retry.
    :param cwd:    Set the current working directory
    """

    cwd = kwargs.pop('cwd', None)
    delay = kwargs.pop('delay', None)
    attempts  = kwargs.pop('attempts', 1)
    shell = kwargs.pop('shell', False)

    if kwargs:
        raise UnknownArgumentError('Got unknown keyword args: %r' % kwargs)

    cmd = [str(c) for c in cmd]

    while attempts > 0:
        attempts -= 1
        _PIPE = subprocess.PIPE

        if os.name == 'nt':
            close_fds = False
        else:
            close_fds = True

        try:
            obj = subprocess.Popen(cmd,
                                   stdin=_PIPE,
                                   stdout=_PIPE,
                                   stderr=_PIPE,
                                   close_fds=close_fds,
                                   shell=shell,
                                   cwd=cwd)
            result = obj.communicate(None)
            obj.stdin.close()
            if obj.returncode:
                raise ProcessExecutionError(cmd=" ".join(cmd), description=result)

            return result
        except (ProcessExecutionError, OSError) as err:
            if isinstance(err, ProcessExecutionError):
                format = '%(desc)r\ncommand: %(cmd)r'
                log.debug(format, {"desc": err.description, "cmd": err.cmd})
            else:
                format = 'Got an OSError\ncommand: %(cmd)r\nerrno: %(errno)r'
                log.debug(format, {"cmd": " ".join(cmd), "errno": err.errno})

            if not attempts:
                log.error('%r failed. Not Retrying.', " ".join(cmd))
                raise
            else:
                log.warn('%r failed. Retrying.', " ".join(cmd))
                if delay:
                    time.sleep(random.randint(20, 200) / 100.0)

def generate_devname(prefix, eid):
    if len(prefix) > 3:
        raise ValueError("Prefix must be less than 3.")
    return prefix + eid[:11]

def generate_mac():
    mac = [0xda, 0x01,
           random.randint(0x00, 0xff),
           random.randint(0x00, 0xff),
           random.randint(0x00, 0xff),
           random.randint(0x00, 0xff)]
    return ':'.join(map(lambda x: "%02x" % x, mac))

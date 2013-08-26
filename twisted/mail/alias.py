# -*- test-case-name: twisted.mail.test.test_mail -*-
#
# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.


"""
Support for aliases(5) configuration files.

@author: Jp Calderone
"""

import os
import tempfile

from twisted.mail import smtp
from twisted.internet import reactor
from twisted.internet import protocol
from twisted.internet import defer
from twisted.python import failure
from twisted.python import log
from zope.interface import implements, Interface


def handle(result, line, filename, lineNo):
    """
    Parse a line from an aliases file.

    @type result: L{dict} of L{bytes} -> L{list} of L{bytes}
    @param result: A dictionary mapping username to aliases to which
        the results of parsing the line are added.

    @type line: L{bytes}
    @param line: A line from an aliases file.

    @type filename: L{bytes}
    @param filename: The name of the aliases file.

    @type lineNo: L{int}
    @param lineNo: The position of the line within the aliases file.
    """
    parts = [p.strip() for p in line.split(':', 1)]
    if len(parts) != 2:
        fmt = "Invalid format on line %d of alias file %s."
        arg = (lineNo, filename)
        log.err(fmt % arg)
    else:
        user, alias = parts
        result.setdefault(user.strip(), []).extend(map(str.strip, alias.split(',')))



def loadAliasFile(domains, filename=None, fp=None):
    """
    Load a file containing email aliases.

    Lines in the file should be formatted like so::

         username: alias1, alias2, ..., aliasN

    Aliases beginning with a C{|} will be treated as programs, will be run, and
    the message will be written to their stdin.

    Aliases beginning with a C{:} will be treated as a file containing
    additional aliases for the username.

    Aliases beginning with a C{/} will be treated as the full pathname to a file
    to which the message will be appended.

    Aliases without a host part will be assumed to be addresses on localhost.

    If a username is specified multiple times, the aliases for each are joined
    together as if they had all been on one line.

    Lines beginning with a space or a tab are continuations of the previous
    line.

    Lines beginning with C{#} are comments.

    @type domains: L{dict} of L{bytes} -> L{IDomain} provider
    @param domains: A mapping of domain name to domain object.

    @type filename: L{bytes} or L{NoneType <types.NoneType>}
    @param filename: The name of a file from which to load aliases.
        If omitted, the C{fp} parameter must be specified.

    @type fp: file-like object or L{NoneType <types.NoneType>}
    @param fp: The file from which to load aliases. If specified,
        the C{filename} parameter is ignored.

    @rtype: L{dict} of L{bytes} -> L{AliasGroup}
    @return: A mapping from username to group of aliases.
    """
    result = {}
    if fp is None:
        fp = file(filename)
    else:
        filename = getattr(fp, 'name', '<unknown>')
    i = 0
    prev = ''
    for line in fp:
        i += 1
        line = line.rstrip()
        if line.lstrip().startswith('#'):
            continue
        elif line.startswith(' ') or line.startswith('\t'):
            prev = prev + line
        else:
            if prev:
                handle(result, prev, filename, i)
            prev = line
    if prev:
        handle(result, prev, filename, i)
    for (u, a) in result.items():
        addr = smtp.Address(u)
        result[u] = AliasGroup(a, domains, u)
    return result



class IAlias(Interface):
    """
    An interface for aliases.
    """
    def createMessageReceiver():
        """
        Create a message receiver.

        @rtype: L{IMessage <smtp.IMessage>} provider
        @return: A message receiver.
        """
        pass



class AliasBase:
    """
    The default base class for aliases.

    @ivar domains: See L{__init__}

    @type original: L{Address}
    @ivar original: The original address being aliased.
    """
    def __init__(self, domains, original):
        """
        @type domains: L{dict} of L{bytes} -> L{IDomain} provider
        @param domains: A mapping of domain name to domain object.

        @type original: L{bytes}
        @param original: The original address being aliased.
        """
        self.domains = domains
        self.original = smtp.Address(original)


    def domain(self):
        """
        Return the domain associated with original address.

        @rtype: L{IDomain} provider
        @return: The domain for the original address.
        """
        return self.domains[self.original.domain]


    def resolve(self, aliasmap, memo=None):
        """
        Map this alias to its ultimate destination.

        @type aliasmap: L{dict} of L{bytes} -> L{AliasBase}
        @param aliasmap: A mapping of username to alias or group of aliases.

        @type memo: L{NoneType <types.NoneType>} or L{dict} of L{AliasBase}
        @param memo: A record of the aliases already considered in the
            resolution process.  If provided, C{memo} is modified to include
            this alias.

        @rtype: L{IMessage <smtp.IMessage>} or L{NoneType <types.NoneType>}
        @return: A message receiver for the ultimate destination or None for
            an invalid destination.
        """
        if memo is None:
            memo = {}
        if str(self) in memo:
            return None
        memo[str(self)] = None
        return self.createMessageReceiver()



class AddressAlias(AliasBase):
    """
    An alias which translates one email address into another.

    @type alias : L{Address}
    @ivar alias: The destination address.
    """
    implements(IAlias)

    def __init__(self, alias, *args):
        """
        @type alias: L{Address}, L{User}, L{bytes} or object which can be
            converted into L{bytes}
        @param alias: The destination address.

        @type args: 2-L{tuple} of (E{1}) L{dict} of L{bytes} -> L{IDomain}
            provider, (E{2}) L{bytes}
        @param args: Parameters for L{AliasBase.__init__}.
        """
        AliasBase.__init__(self, *args)
        self.alias = smtp.Address(alias)


    def __str__(self):
        """
        Build a string representation of this L{AddressAlias} instance.

        @rtype: L{bytes}
        @return: A string containing the destination address.
        """
        return '<Address %s>' % (self.alias,)


    def createMessageReceiver(self):
        """
        Create a message receiver which delivers a message to
        the destination address.

        @rtype: L{IMessage <smtp.IMessage>} provider
        @return: A message receiver.
        """
        return self.domain().exists(str(self.alias))


    def resolve(self, aliasmap, memo=None):
        """
        Map this alias to its ultimate destination.

        @type aliasmap: L{dict} of L{bytes} -> L{AliasBase}
        @param aliasmap: A mapping of username to alias or group of aliases.

        @type memo: L{NoneType <types.NoneType>} or L{dict} of L{AliasBase}
        @param memo: A record of the aliases already considered in the
            resolution process.  If provided, C{memo} is modified to include
            this alias.

        @rtype: L{IMessage <smtp.IMessage>} or L{NoneType <types.NoneType>}
        @return: A message receiver for the ultimate destination or None for
            an invalid destination.
        """
        if memo is None:
            memo = {}
        if str(self) in memo:
            return None
        memo[str(self)] = None
        try:
            return self.domain().exists(smtp.User(self.alias, None, None, None), memo)()
        except smtp.SMTPBadRcpt:
            pass
        if self.alias.local in aliasmap:
            return aliasmap[self.alias.local].resolve(aliasmap, memo)
        return None



class FileWrapper:
    """
    A message receiver which delivers a message to a file.

    @type fp: file-like object
    @ivar fp: A file used for temporary storage of the message.

    @type finalname: L{bytes}
    @ivar finalname: The name of the file to which the message should be
        stored.
    """
    implements(smtp.IMessage)

    def __init__(self, filename):
        """
        @type filename: L{bytes}
        @param filename: The name of the file to which the message should be
            stored.
        """
        self.fp = tempfile.TemporaryFile()
        self.finalname = filename


    def lineReceived(self, line):
        """
        Write a received line to the temporary file.

        @type line: L{bytes}
        @param line: A received line of the message.
        """
        self.fp.write(line + '\n')


    def eomReceived(self):
        """
        Handle end of message by writing the message to the file.

        @rtype: L{Deferred <defer.Deferred>} which successfully results in
            L{bytes}
        @return: A deferred which succeeds with the name of the file to which
            the message has been stored or fails if the message cannot be
            saved to the file.
        """
        self.fp.seek(0, 0)
        try:
            f = file(self.finalname, 'a')
        except:
            return defer.fail(failure.Failure())

        f.write(self.fp.read())
        self.fp.close()
        f.close()

        return defer.succeed(self.finalname)


    def connectionLost(self):
        """
        Close the temporary file when the connection is lost.
        """
        self.fp.close()
        self.fp = None


    def __str__(self):
        """
        Build a string representation of this L{FileWrapper} instance.

        @rtype: L{bytes}
        @return: A string containing the file name of the message.
        """
        return '<FileWrapper %s>' % (self.finalname,)



class FileAlias(AliasBase):
    """
    An alias which translates an address to a file.

    @ivar filename: See L{__init__}
    """
    implements(IAlias)

    def __init__(self, filename, *args):
        """
        @type filename: L{bytes}
        @param filename: The name of the file in which to store the message.

        @type args: 2-L{tuple} of (E{1}) L{dict} of L{bytes} -> L{IDomain}
            provider, (E{2}) L{bytes}
        @param args: Parameters for L{AliasBase.__init__}.
        """
        AliasBase.__init__(self, *args)
        self.filename = filename


    def __str__(self):
        """
        Build a string representation of this L{FileAlias} instance.

        @rtype: L{bytes}
        @return: A string containing the name of the file.
        """
        return '<File %s>' % (self.filename,)


    def createMessageReceiver(self):
        """
        Create a message receiver which delivers a message to the file.

        @rtype: L{FileWrapper}
        @return: A message receiver which writes a message to the file.
        """
        return FileWrapper(self.filename)



class ProcessAliasTimeout(Exception):
    """
    An error indicating that a timeout occurred while waiting for a process
    to complete.
    """



class MessageWrapper:
    """
    A message receiver which delivers a message to a child process.

    @type completionTimeout: L{int} or L{float}
    @ivar completionTimeout: The number of seconds to wait for the child
        process to exit before reporting the delivery as a failure.

    @type _timeoutCallID: L{NoneType <types.NoneType>} or
        L{IDelayedCall <twisted.internet.interfaces.IDelayedCall>} provider
    @ivar _timeoutCallID: The call used to time out delivery, started when the
        connection to the child process is closed.

    @type done: L{bool}
    @ivar done: A flag indicating whether the child process has exited
        (C{True}) or not (C{False}).

    @type reactor: L{IReactorTime <twisted.internet.interfaces.IReactorTime>}
        provider
    @ivar reactor: A reactor which will be used to schedule timeouts.

    @ivar protocol: See L{__init__}.

    @type processName: L{bytes} or L{NoneType <types.NoneType>}
    @ivar processName: The process name.

    @type completion: L{Deferred <defer.Deferred>}
    @ivar completion: The deferred which will be triggered by the protocol
        when the child process exits.
    """
    implements(smtp.IMessage)

    done = False

    completionTimeout = 60
    _timeoutCallID = None

    reactor = reactor

    def __init__(self, protocol, process=None, reactor=None):
        """
        @type protocol: L{ProcessAliasProtocol}
        @param protocol: The protocol associated with the child process.

        @type process: L{bytes} or L{NoneType <types.NoneType>}
        @param process: The process name.

        @type reactor: L{NoneType <types.NoneType>} or L{IReactorTime
            <twisted.internet.interfaces.IReactorTime>} provider
        @param reactor: A reactor which will be used to schedule timeouts.
        """
        self.processName = process
        self.protocol = protocol
        self.completion = defer.Deferred()
        self.protocol.onEnd = self.completion
        self.completion.addBoth(self._processEnded)

        if reactor is not None:
            self.reactor = reactor


    def _processEnded(self, result):
        """
        Record process termination and cancel the timeout call if it is active.

        @type result: L{Failure <failure.Failure>}
        @param result: The reason the child process terminated.

        @rtype: L{NoneType <types.NoneType>} or
            L{Failure <failure.Failure>}
        @return: None, if the process end is expected, or the reason the child
            process terminated, if the process end is unexpected.
        """
        self.done = True
        if self._timeoutCallID is not None:
            # eomReceived was called, we're actually waiting for the process to
            # exit.
            self._timeoutCallID.cancel()
            self._timeoutCallID = None
        else:
            # eomReceived was not called, this is unexpected, propagate the
            # error.
            return result


    def lineReceived(self, line):
        """
        Write a received line to the child process.

        @type line: L{bytes}
        @param line: A received line of the message.
        """
        if self.done:
            return
        self.protocol.transport.write(line + '\n')


    def eomReceived(self):
        """
        Disconnect from the child process and set up a timeout to wait for it
        to exit.

        @rtype: L{Deferred <defer.Deferred>}
        @return: A deferred which will be called back when the child process
            exits.
        """
        if not self.done:
            self.protocol.transport.loseConnection()
            self._timeoutCallID = self.reactor.callLater(
                self.completionTimeout, self._completionCancel)
        return self.completion


    def _completionCancel(self):
        """
        Handle the expiration of the timeout for the child process to exit by
        terminating the child process forcefully and issuing a failure to the
        L{completion} deferred.
        """
        self._timeoutCallID = None
        self.protocol.transport.signalProcess('KILL')
        exc = ProcessAliasTimeout(
            "No answer after %s seconds" % (self.completionTimeout,))
        self.protocol.onEnd = None
        self.completion.errback(failure.Failure(exc))


    def connectionLost(self):
        """
        Ignore notification of lost connection.
        """
        pass


    def __str__(self):
        """
        Build a string representation of this L{MessageWrapper} instance.

        @rtype: L{bytes}
        @return: A string containing the name of the process.
        """
        return '<ProcessWrapper %s>' % (self.processName,)



class ProcessAliasProtocol(protocol.ProcessProtocol):
    """
    A process protocol which calls an errback when the associated
    process ends.

    @type onEnd: L{NoneType <types.NoneType>} or L{Deferred <defer.Deferred>}
    @ivar onEnd: If set, a deferred on which to errback when the process ends.
    """
    onEnd = None

    def processEnded(self, reason):
        """
        Call an errback.

        @type reason: L{Failure <failure.Failure>}
        @param reason: The reason the child process terminated.
        """
        if self.onEnd is not None:
            self.onEnd.errback(reason)



class ProcessAlias(AliasBase):
    """
    An alias which is handled by the execution of a program.

    @type path: L{list} of L{bytes}
    @ivar path: The arguments to pass to the process. The first string should
        be the executable's name.

    @type program: L{bytes}
    @ivar program: The path of the program to be executed.

    @type reactor: L{IReactorTime <twisted.internet.interfaces.IReactorTime>}
        and L{IReactorProcess <twisted.internet.interfaces.IReactorProcess>}
        provider
    @ivar reactor: A reactor which will be used to create and timeout the
        child process.
    """
    implements(IAlias)

    reactor = reactor

    def __init__(self, path, *args):
        """
        @type path: L{bytes}
        @param path: The command to invoke the program consisting of the path
            to the executable followed by any arguments.

        @type args: 2-L{tuple} of (E{1}) L{dict} of L{bytes} -> L{IDomain}
            provider, (E{2}) L{bytes}
        @param args: Parameters for L{AliasBase.__init__}.
        """

        AliasBase.__init__(self, *args)
        self.path = path.split()
        self.program = self.path[0]


    def __str__(self):
        """
        Build a string representation of this L{ProcessAlias} instance.

        @rtype: L{bytes}
        @return: A string containing the command used to invoke the process.
        """
        return '<Process %s>' % (self.path,)


    def spawnProcess(self, proto, program, path):
        """
        Spawn a process.

        This wraps the L{spawnProcess
        <twisted.internet.interfaces.IReactorProcess.spawnProcess>} method on
        L{reactor} so that it can be customized for test purposes.

        @type proto: L{IProcessProtocol
            <twisted.internet.interfaces.IProcessProtocol>} provider
        @param proto: An object which will be notified of all events related to
            the created process.

        @type program: L{bytes}
        @param program: The full path name of the file to execute.

        @type path: L{list} of L{bytes}
        @param path: The arguments to pass to the process. The first string
            should be the executable's name.

        @rtype: L{IProcessTransport
            <twisted.internet.interfaces.IProcessTransport>} provider
        @return: A process transport.
        """
        return self.reactor.spawnProcess(proto, program, path)


    def createMessageReceiver(self):
        """
        Launch a process and create a message receiver to pass a message
        to the process.

        @rtype: L{MessageWrapper}
        @return: A message receiver which delivers a message to the process.
        """
        p = ProcessAliasProtocol()
        m = MessageWrapper(p, self.program, self.reactor)
        fd = self.spawnProcess(p, self.program, self.path)
        return m



class MultiWrapper:
    """
    A message receiver which delivers a single message to multiple other
    message receivers.

    @ivar objs: See L{__init__}
    """
    implements(smtp.IMessage)

    def __init__(self, objs):
        """
        @type objs: L{list} of L{IMessage <smtp.IMessage>} provider
        @param objs: Message receivers to which the incoming message should be
            directed.
        """
        self.objs = objs


    def lineReceived(self, line):
        """
        Pass a received line to the message receivers.

        @type line: L{bytes}
        @param line: A line of the message.
        """
        for o in self.objs:
            o.lineReceived(line)


    def eomReceived(self):
        """
        Pass the end of message along to the message receivers.

        @rtype: L{DeferredList <defer.DeferredList>} whose successful results
            are L{bytes} or L{NoneType <types.NoneType>}
        @return: A deferred list which triggers when all of the message
            receivers have finished handling their end of message.
        """
        return defer.DeferredList([
            o.eomReceived() for o in self.objs
        ])


    def connectionLost(self):
        """
        Inform the message receivers that the connection has been lost.
        """
        for o in self.objs:
            o.connectionLost()


    def __str__(self):
        """
        Build a string representation of this L{MultiWrapper} instance.

        @rtype: L{bytes}
        @return: A string containing a list of the message receivers.
        """
        return '<GroupWrapper %r>' % (map(str, self.objs),)



class AliasGroup(AliasBase):
    """
    An alias which points to multiple destination aliases.

    @type processAliasFactory: L{type} of L{ProcessAlias}
    @ivar processAliasFactory: A factory for process aliases.

    @type aliases: L{list} of L{AliasBase} which implements L{IAlias}
    @ivar aliases: The destination aliases.
    """
    implements(IAlias)

    processAliasFactory = ProcessAlias

    def __init__(self, items, *args):
        """
        Create a group of aliases.

        Parse a list of alias strings and, for each, create an appropriate
        alias object.

        @type items: L{list} of L{bytes}
        @param items: Aliases.

        @type args: n-L{tuple} of (E{1}) L{dict} of L{bytes} -> L{IDomain}
            provider, (E{2}) L{bytes}
        @param args: Parameters for L{AliasBase.__init__}.
        """

        AliasBase.__init__(self, *args)
        self.aliases = []
        while items:
            addr = items.pop().strip()
            if addr.startswith(':'):
                try:
                    f = file(addr[1:])
                except:
                    log.err("Invalid filename in alias file %r" % (addr[1:],))
                else:
                    addr = ' '.join([l.strip() for l in f])
                    items.extend(addr.split(','))
            elif addr.startswith('|'):
                self.aliases.append(self.processAliasFactory(addr[1:], *args))
            elif addr.startswith('/'):
                if os.path.isdir(addr):
                    log.err("Directory delivery not supported")
                else:
                    self.aliases.append(FileAlias(addr, *args))
            else:
                self.aliases.append(AddressAlias(addr, *args))


    def __len__(self):
        """
        Return the number of aliases in the group.

        @rtype: L{int}
        @return: The number of aliases in the group.
        """
        return len(self.aliases)


    def __str__(self):
        """
        Build a string representation of this L{AliasGroup} instance.

        @rtype: L{bytes}
        @return: A string containing the aliases in the group.
        """
        return '<AliasGroup [%s]>' % (', '.join(map(str, self.aliases)))


    def createMessageReceiver(self):
        """
        Create a message receiver for each alias and return a message receiver
        which will pass on a message to each of those.

        @rtype: L{MultiWrapper}
        @return: A message receiver which passes a message on to message
            receivers for each alias in the group.
        """
        return MultiWrapper([a.createMessageReceiver() for a in self.aliases])


    def resolve(self, aliasmap, memo=None):
        """
        Map each of the aliases in the group to its ultimate destination.

        @type aliasmap: L{dict} of L{bytes} -> L{AliasBase}
        @param aliasmap: A mapping of username to alias or group of aliases.

        @type memo: L{NoneType <types.NoneType>} or L{dict} of L{AliasBase}
        @param memo: A record of the aliases already considered in the
            resolution process.  If provided, C{memo} is modified to include
            this alias.

        @rtype: L{MultiWrapper}
        @return: A message receiver which passes the message on to message
            receivers for the ultimate destination of each alias in the group.
        """
        if memo is None:
            memo = {}
        r = []
        for a in self.aliases:
            r.append(a.resolve(aliasmap, memo))
        return MultiWrapper(filter(None, r))

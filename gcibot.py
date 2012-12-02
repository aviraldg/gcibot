# Copyright (C) 2012 Aviral Dasgupta <aviraldg@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from twisted.internet import reactor, protocol
from twisted.words.protocols import irc
import sys
import re
import requests
from bs4 import BeautifulSoup

META = '''Hey, I\'m a bot written by aviraldg who inserts metadata about GCI links!
Source at: https://github.com/aviraldg/gcibot.'''

class GCIBot(irc.IRCClient):
    nickname = 'gcibot'

    def connectionMade(self):
        irc.IRCClient.connectionMade(self)

    def connectionLost(self, reason):
        irc.IRCClient.connectionLost(self, reason)

    def signedOn(self):
        for c in self.factory.channels:
            self.join(c)

    def joined(self, channel):
        self.msg(channel, META)

    def privmsg(self, user, channel, msg):
        user = user.split('!', 1)[0]

        if msg.startswith(self.nickname + ":"):
            msg = "{user}: {META}".format(user=user, META=META)
            self.msg(channel, msg)
            return

        links = re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', msg)
        for _ in links:
            if ('google-melange.com' in _) or ('google-melange.appspot.com' in _):
                r = requests.get(_)
                s = BeautifulSoup(r.text)
                A = {}
                A['title'] = s.find('span', class_='title').string
                A['status'] = s.find('span', class_='status').span.string
                A['mentor'] = s.find('span', class_='mentor').span.string
                A['hours'] = s.find('div', class_='time time-first')
                if A['hours']:
                    A['hours'] = A['hours'].span.string
                    A['minutes'] = s.find_all('div', class_='time')[1].span.string
                else:
                    del A['hours']

                for _ in A.keys():
                    A[_] = str(A[_])  # IRC and Unicode don't mix very well, it seems.

                self.msg(channel, A['title'])
                if 'hours' in A:
                    self.msg(channel, 'Status: ' + A['status'] +
                        ' ({hours} hours, {minutes} minutes left)'.format(
                            hours=A['hours'], minutes=A['minutes']))
                else:
                    self.msg(channel, 'Status: ' + A['status'])
                self.msg(channel, 'Mentor(s): ' + A['mentor'])

    def alterCollidedNick(self, nickname):
        return '_' + nickname + '_'



class BotFactory(protocol.ClientFactory):
    def __init__(self, channels):
        self.channels = channels

    def buildProtocol(self, addr):
        p = GCIBot()
        p.factory = self
        return p

    def clientConnectionLost(self, connector, reason):
        connector.connect()

    def clientConnectionFailed(self, connector, reason):
        print "connection failed:", reason
        reactor.stop()


if __name__ == '__main__':
    f = BotFactory(sys.argv)
    reactor.connectTCP("irc.freenode.net", 6667, f)
    reactor.run()

''' Copyright (c) 2017 Francesco Zoccheddu

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
"Software"), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE. '''

import argparse
import serial
import signal
import collections
import sys
import serial.tools.list_ports

class SerialStream:
    def __init__(self):
        self.ptr = 0

    def read(self, sw):
        byte = sw.peek(self.ptr)
        self.ptr += 1
        return byte

    def trim(self, index):
        self.ptr -= index

    def getIndex(self):
        return self.ptr

class SerialWrapper:
    def __init__(self, port, baudrate, bytesize, parity, stopbits, timeout, swflowctl, rtscts, dsrdtr):
        self.ser = serial.Serial(port, baudrate, bytesize, parity, stopbits, timeout, swflowctl, rtscts, dsrdtr)
        self.buf = []

    def push(self):
        byte = self.ser.read()
        self.buf += [byte]

    def peek(self, index):
        while index >= len(self.buf):
            self.push()
        return self.buf[index]

    def pop(self, count):
        self.buf = self.buf[count:]

    def close(self):
        if self.ser is not None:
            self.ser.close()
            self.ser = None
            return True
        return False


class Session:

    @staticmethod
    def genEscapeHandlers():

        class EscapeHandler:
            def __init__(self, char, description):
                self.char = char
                self.description = description
            
            def process(self, stream, session):
                raise NotImplementedError("Abstract EscapeHandler")

            def getDescription(self):
                return self.description

            def getChar(self):
                return self.char

        handlers = []

        #Binary byte
        class BinByteEscapeHandler(EscapeHandler):
            def process(self, stream, session):
                return str(session.intToBin(session.byteToInt(stream.read(session.sw))))

        handlers += [BinByteEscapeHandler("b", "print next byte as binary string")]

        #Hex byte
        class HexByteEscapeHandler(EscapeHandler):
            def process(self, stream, session):
                return str(session.intToHex(session.byteToInt(stream.read(session.sw))))

        handlers += [HexByteEscapeHandler("h", "print next byte as hexadecimal string")]

        #Integer byte
        class IntegerByteEscapeHandler(EscapeHandler):
            def process(self, stream, session):
                return str(session.byteToInt(stream.read(session.sw)))

        handlers += [IntegerByteEscapeHandler("i", "print next byte as decimal integer")]

        #Integer word
        class IntegerWordEscapeHandler(EscapeHandler):
            def process(self, stream, session):
                return str((session.byteToInt(stream.read(session.sw)) << 8) | session.byteToInt(stream.read(session.sw)))

        handlers += [IntegerWordEscapeHandler("d", "print next word as decimal integer")]

        #Ascii byte
        class AsciiByteEscapeHandler(EscapeHandler):
            def process(self, stream, session):
                return str(chr(session.byteToInt(stream.read(session.sw))))

        handlers += [AsciiByteEscapeHandler("a", "print next byte as ascii char")]

        #Discard byte
        class DiscardByteEscapeHandler(EscapeHandler):
            def process(self, stream, session):
                stream.read(session.sw)
                return ""

        handlers += [DiscardByteEscapeHandler("x", "discard next byte")]

        #Recursive escape
        class RecursiveByteEscapeHandler(EscapeHandler):
            def process(self, stream, session):
                resc = str(chr(session.byteToInt(stream.read(session.sw))))
                if resc == self.getChar():
                    return "<RECESC>"
                return session.processEscape(resc, stream)

        handlers += [RecursiveByteEscapeHandler("e", "use next byte as ascii escape char")]

        #New line
        class NewlineEscapeHandler(EscapeHandler):
            def process(self, stream, session):
                return "\n"

        handlers += [NewlineEscapeHandler("n", "print new line")]

        #Tab
        class TabEscapeHandler(EscapeHandler):
            def process(self, stream, session):
                return "\t"

        handlers += [TabEscapeHandler("t", "print tab")]
        
        return handlers

    escapeHandlers = genEscapeHandlers.__func__()    

    @staticmethod
    def printEscapeHandlers():
        print("Available format chars:")
        for h in Session.escapeHandlers:
            print("  " + h.getChar() + "  " + h.getDescription())

    def __init__(self, sw, escape, byteorder, formats, buffer):
        self.sw = sw
        self.escape = escape
        self.byteorder = byteorder
        self.formats = formats if formats is not None else [escape + "a"]
        self.buffer = buffer
        self.streams = []
        for f in self.formats:
            stream = SerialStream()
            self.streams += [stream]

    def byteToInt(self, byte):
        return int.from_bytes(byte, byteorder=self.byteorder)

    def intToBin(self, integer):
        return bin(integer).lstrip("0b").zfill(8)

    def intToHex(self, integer):
        return hex(integer).lstrip("0x").zfill(2)        

    def processEscape(self, escape, stream):
        for h in Session.escapeHandlers:
            if escape == h.getChar():
                return h.process(stream, self)
        return "<BADESC>"

    def read(self):
        buf = ""
        for f, s in zip(self.formats, self.streams):
            toks = f.split(self.escape)
            buf += toks[0]
            toks = toks[1:]
            for t in toks:
                if len(t) > 0:
                    buf += self.processEscape(t[0], s)
                    buf += t[1:]
                else:
                    buf += self.processEscape(self.escape, s)
        if self.buffer:
            minInd = None
            for s in self.streams:
                if minInd is None or minInd > s.getIndex():
                    minInd = s.getIndex()
            for s in self.streams:
                s.trim(minInd)
            self.sw.pop(minInd)
        else:
            maxInd = None
            for s in self.streams:
                if maxInd is None or maxInd < s.getIndex():
                    maxInd = s.getIndex()
                s.trim(s.getIndex())
            self.sw.pop(maxInd)
        return buf
                
                
def qt(msg):
    return "'" + str(msg) + "'"

def parseArgs():
    
    def checkPositive(value):
        ivalue = int(value)
        if ivalue <= 0:
            raise argparse.ArgumentTypeError("%s is an invalid positive int value" % value)
        return ivalue

    def checkChar(value):
        svalue = str(value)
        if len(svalue) != 1:
            raise argparse.ArgumentTypeError("%s is an invalid char value" % value)
        return svalue
    
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    #Output group
    oGroup = parser.add_argument_group("output file settings")
    #File
    oGroup.add_argument("-of", "--ofile", type=argparse.FileType('w'), action="append", help="output to file")
    #Char limit
    default = 65535
    oGroup.add_argument("-om", "--omax", type=checkPositive, default=default, help="output to file formatted line limit")

    #Format group
    fGroup = parser.add_argument_group("format settings")    
    #Format string
    fGroup.add_argument("-f", "--format", type=str, action='append', help="custom format strings")
    #Escape char
    default = "%"
    fGroup.add_argument("-e", "--escape", type=checkChar, default=default, help="format escape char")
    #Escape char
    default = "big"
    choices = "big", "little"
    fGroup.add_argument("-bo", "--byteorder", type=str, default=default, choices=choices, help="format byte order")
    #Bufferize
    fGroup.add_argument("-fb", "--fbuffer", action="store_true", help="allow asynchronous format strings with buffer")
    #Help
    fGroup.add_argument("-fl", "--flist", action="store_true", help="list format chars")

    #Connection group
    cGroup = parser.add_argument_group("connection settings")
    #List
    clGroup = cGroup.add_mutually_exclusive_group()
    clGroup.add_argument("-l", "--list", action="store_true", help="list available ports")
    clGroup.add_argument("-le", "--listex", action="store_true", help="list available ports and their description") 
    #Port
    cGroup.add_argument("-p", "--port", type=str, help="port to connect to")
    #Baud rate
    default = 9600
    cGroup.add_argument("-b", "--baudrate", type=checkPositive, default=default, help="set baud rate")
    #Byte size
    default = 8
    choices = [5, 6, 7, 8]
    cGroup.add_argument("-bs", "--bytesize", type=int, choices=choices, default=default, help="set byte size")    
    #Parity bits
    default = "NONE"
    choices = ["NONE", "EVEN", "ODD", "SPACE", "MARK"]
    cGroup.add_argument("-pb", "--parity", choices=choices, default=default, help="set parity bits")
    #Stop bits
    default = "ONE"
    choices = ["ONE", "ONE_POINT_FIVE", "TWO"]
    cGroup.add_argument("-sb", "--stopbits", choices=choices, default=default, help="set stop bits")
    #Timeout
    default = 1
    cGroup.add_argument("-t", "--timeout", type=checkPositive, default=default, help="set timeout")
    #Software flow control 
    cGroup.add_argument("-sfc", "--swflowctl", action="store_true", help="enable software flow control")
    #RTS/CTS
    cGroup.add_argument("-rc", "--rtscts", action="store_true", help="enable RTS/CTS")
    #DSR/DTR
    cGroup.add_argument("-dd", "--dsrdtr", action="store_true", help="enable DSR/DTR")
    
    return parser.parse_args()

def main():
    print("Serial monitor")
    print("Copyright (c) 2017 Francesco Zoccheddu")
    args = parseArgs()

    if args.flist:
        print()
        Session.printEscapeHandlers()

    if args.list or args.listex:
        print()
        ports = serial.tools.list_ports.comports()
        if len(ports) > 0:
            print("Avaliable ports:")
            for p in ports:
                if args.listex:
                    print(p.device + "\t" + p.description)
                else:
                    print(p.device)
        else:
            print("No port available")

    if (args.fbuffer):
        print()
        print("Warning: Format buffer enabled")
        print("This may cause high memory consumption")                

    if args.port is not None:
        print()
        ports = serial.tools.list_ports.comports()
        available = False
        for p in ports:
            if args.port == p.device:
                available = True
                break

        if available:
            print("Port " + qt(args.port) + " available")
            sw = None
            try:
                sw = SerialWrapper(args.port, args.baudrate, args.bytesize, getattr(serial, "PARITY_" + args.parity), getattr(serial, "STOPBITS_" + args.stopbits), args.timeout, args.swflowctl, args.rtscts, args.dsrdtr)
                print("Connection to port " + qt(args.port) + " opened")
            except (ValueError, serial.SerialException) as err:
                print("Error happened while connecting to port " + qt(args.port) + ":")
                print(err)

            if sw is not None:
                session = Session(sw, args.escape, args.byteorder, args.format, args.fbuffer)
                history = collections.deque([], maxlen=args.omax) if args.ofile is not None else None

                try:
                    running = True
                    
                    def quitSignal(signal, frame):
                        nonlocal running
                        if running:
                            running = False
                        else:
                            print()
                            print("Aborted by keyboard")
                            sys.exit(0)
                        return
                    
                    signal.signal(signal.SIGINT, quitSignal)
                    signal.signal(signal.SIGTERM, quitSignal)

                    while running:
                        line = session.read()
                        if history is not None:
                            history.extend(line)
                        sys.stdout.write(line)
                        sys.stdout.flush()
                
                except serial.SerialException as err:
                    print()
                    print("Error happened while reading from port " + qt(args.port) + ":")
                    print(err)
    
                if sw.close():
                    print()                    
                    print("Connection to port " + qt(args.port) + " closed")

                if args.ofile is not None:
                    print()
                    print("Writing " + str(len(history)) + " formatted lines to output file" + ("s" if len(args.ofile) > 1 else ""))
                    for f in args.ofile:
                        try:
                            for l in history:
                                f.write(l)
                            f.close()
                            print("File " + qt(f.name) + " succesfully closed")
                        except IOError as err:
                            print("Error while writing file " + qt(f.name))
                            print(err)
                        
        else:
            print("Port " + qt(args.port) + " not available")

if __name__ == "__main__":
    main()
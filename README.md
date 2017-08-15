# SerialMonitor
Small python serial monitor commandline utility

Copyright (c) 2017 Francesco Zoccheddu

## Features
- Print data from serial port
- Advanced connection settings
- Output to file
- Output formatting support
- Easy to use

## Help
### Print help message
Right-click and save 
**[serialmonitor.py](https://raw.githubusercontent.com/francescozoccheddu/SerialMonitor/master/serialmonitor.py)**
python script and execute it with 
**-h** or **--help**
command line argument
to print the usage message.
<pre>
python ./serialmonitor.py <b>-h</b>
</pre>
### Examples
List available ports
<pre>
python ./serialmonitor.py <b>-le</b>
</pre>
Connect to port */dev/ttyUSB0* and print ascii output to console
<pre>
python ./serialmonitor.py -p /dev/ttyUSB0
</pre>
Connect to port 
*COM3*, 
print decimal output to console 
and save it to 
*output.txt* and *outputCopy.txt* files
<pre>
python ./serialmonitor.py -p COM3 -f "%i" -of output.txt -of outputCopy.txt
</pre>
### Formatting examples
Format the alphabet
<pre>
python ./serialmonitor.py -p <i>PORT</i> -f "<b>%a</b>"
</pre>
> abcdefghijklmnopqrstuvw...
<pre>
python ./serialmonitor.py -p <i>PORT</i> -f "<b>Character '%a' read%n</b>"
</pre>
> Character 'a' read<br>
Character 'b' read<br>
Character 'c' read...
<pre>
python ./serialmonitor.py -p <i>PORT</i> -f "<b>%i %a </b>"
</pre>
> 97 b 99 d 101 e 203 g...
<pre>
python ./serialmonitor.py -p <i>PORT</i> -f "<b>Bin byte: %b Hex byte: %h Int byte: %i Int word: %d </b>"
</pre>
> Bin byte: 1100001 Hex byte: 62 Int byte: 99 Int word: 25701 Bin byte: 1100110...
<pre>
python ./serialmonitor.py -p <i>PORT</i> -f "<b>%a%x</b>"
</pre>
> acegikmoqsuwyac...
<pre>
python ./serialmonitor.py -p <i>PORT</i> -f "<b>%e </b>"
</pre>
> b `<BADESC>` 101 `<BADESC>` `<BADESC>` 69...
<pre>
python ./serialmonitor.py -p <i>PORT</i> -f "<b>ASCII: %a %a %a </b>" -f "<b>Decimal: %i %i %i</b>" -f "<b>Hexadecimal: %h %h %h </b>"
</pre>
> ASCII: a b c Decimal: 97 98 99 Hexadecimal: 61 62 63 ASCII: d e f Decimal: 100 101...

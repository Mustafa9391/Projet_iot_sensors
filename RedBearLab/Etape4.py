import os
import sys
import pexpect
import time
import urllib2
import urllib
import datetime

URL = 'https://api.thingspeak.com/update?api_key=25IUA7K6EIOQ3XO4'
ble_addr="D5:A7:AD:18:DD:64"
class RedBearLab:
   
  def __init__(self,ble_addr):
    self.ble_addr=ble_addr
    self.child = pexpect.spawn('gatttool -t random -b ' + ble_addr + ' -I')
    self.child.expect('\[LE\]>')
    print("Try to connect to the board")
    self.child.sendline('connect')
    self.child.expect('Connection successful')
    print("Connected")
    return
	

  def getTemperature(self):
    #print("try to update the temperature")
    self.child.sendline('char-write-cmd 0x000e A00100')
    self.child.sendline('char-write-req 0x0011 0100 -listen')
    self.child.expect('Characteristic value was written successfully')
    self.child.expect('Notification handle = 0x0010 value: .*')
    rval = self.child.after.split()
    print("temperature: " + str(int(rval[7], 16)) +" C")
    return int(rval[7], 16)

  def getPressure(self):
    #print("try to update the pressure")
    self.child.sendline('char-write-cmd 0x000e A00300')
    self.child.sendline('char-write-req 0x0011 0100 -listen')
    self.child.expect('Characteristic value was written successfully')
    self.child.expect('Notification handle = 0x0010 value: .*')
    rval = self.child.after.split()
    pressure = "" + rval[6] + rval[7]+rval[8]
    print("pressure: " + str(int(pressure, 16))+ " Pa")
    return int(pressure, 16)

  def exit(self):
    self.child.sendline('exit');
    return

def getAltitude(pression):
  A = float(pression)/103311
  B = 1/5.25588
  C = pow(A,B)
  C = 1 - C
  C = C /0.0000225577
  return int(C)

def main(): 
  redBearLab=RedBearLab(ble_addr)
  while True:
    print('******************'+datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")+'****************')
    tmpIR=redBearLab.getTemperature()
    prsIR=redBearLab.getPressure()
    print('L"altitude : '+str(getAltitude(prsIR))+" m\n")
    req=URL + '&field1='+str(tmpIR)+'&field2='+str(prsIR)+'&field3='+str(getAltitude(prsIR))
    f = urllib2.urlopen(req)
    f.close()
    time.sleep(2)
  redBearLab.exit();
    #time.sleep(10)


if __name__ == "__main__":
    main()

import os
import sys
import pexpect
import time
import urllib2
import urllib
import json
import requests
import datetime

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
    self.child.sendline('char-write-cmd 0x000e A00100')
    self.child.sendline('char-write-req 0x0011 0100 -listen')
    self.child.expect('Characteristic value was written successfully')
    self.child.expect('Notification handle = 0x0010 value: .*')
    rval = self.child.after.split()
    print("temperature: " + str(int(rval[7], 16)) +" C")
    return int(rval[7], 16)

  def getPressure(self):
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

    

def main(): 
  redBearLab=RedBearLab(ble_addr)
  URL = 'http://138.68.67.137:5000/api/v0/measurement/data'
  headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}

  while True:
  
    print('******************'+datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")+'****************')
    #l'envoi de la temperature :
    tmpIR=redBearLab.getTemperature()
    jsonTemp = {'title': 'temperature', 'value': tmpIR, 'unit': 'Degree C'}
    r = requests.post(URL, data=json.dumps(jsonTemp), headers=headers)

    #l'envoi de la pression :
    prsIR=redBearLab.getPressure()
    jsonpres = {'title': 'pressure', 'value': prsIR, 'unit': 'hPa'}
    r = requests.post(URL, data=json.dumps(jsonpres), headers=headers)

    #l'envoi de l'altitude :
    Alti=getAltitude(prsIR)
    jsonAti = {'title': 'altitude', 'value': Alti, 'unit': 'Meter'}
    r = requests.post(URL, data=json.dumps(jsonAti), headers=headers)
        
    print('L"altitude : '+str(getAltitude(prsIR))+" m\n")
    time.sleep(3)
  redBearLab.exit();
    #time.sleep(10)

def getAltitude(pression):
  A = float(pression)/104300
  B = 1/5.25588
  C = pow(A,B)
  C = 1 - C
  C = C /0.0000225577
  return int(C)
if __name__ == "__main__":
    main()

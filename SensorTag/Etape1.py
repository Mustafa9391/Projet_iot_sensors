#*****************************************************************************************************
#
#                  Robert DORIGNY - www.doritique.fr le 6 aout 2014
#
# Ce script est charge de recuperer les donnees des sondes du TI Sensortag CC2541 via une connexion  
# bluetooth low energy (BLE). N oubliez pas de modifier l'adresse  BLE de votre Sensortag, et d'appuyer 
# sur le side button pour allumer le tag. 
#
#*****************************************************************************************************

import os
import sys
import pexpect
import time
import urllib2
import urllib

#Adresse BLE du sensortag
ble_addr="78:A5:04:8C:2C:7F"

tosigned = lambda n: float(n-0x10000) if n>0x7fff else float(n)
tosignedbyte = lambda n: float(n-0x100) if n>0x7f else float(n)


#Fonction de transformation de valeur hexa en float
def floatfromhex(h):
  t = float.fromhex(h)
  if t > float.fromhex('7FFF'):
      t = -(float.fromhex('FFFF') - t)
      pass
  return t 

#Classe du sensortag  
class Sensortag:
   
  #Le constructeur 
  def __init__(self,ble_addr):
    self.ble_addr=ble_addr
    self.child = pexpect.spawn('gatttool -b ' + ble_addr + ' --interactive')
    self.child.expect('\[LE\]>')
    print "Tentative de connection sur le sensortag..."
    self.child.sendline('connect')
    self.child.expect('Connection successful')
    #Recup valeurs de calibration du barometre
    self.child.sendline('char-write-cmd 0x4f 02') #Active la lecture des datas de calibration
    self.child.expect('\[LE\]>')
    self.child.sendline('char-read-hnd 0x52')
    self.child.expect('descriptor: .*')
    rval=self.child.after.split()
    mycalib=[]
    for i in range(1,17) :
      mycalib.append(int(rval[i],16))
    #print mycalib
    self.barometer = Barometer(mycalib)
    return
	
  #Getter de la temperature IR
  def get_IRtmp(self):
   #Active la sonde
   self.child.sendline('char-write-cmd 0x29 01')
   self.child.expect('\[LE\]>') 
   self.child.sendline('char-read-hnd 0x25')
   self.child.expect('descriptor: .*')  
   rval = self.child.after.split()
   objT = floatfromhex(rval[2] + rval[1])
   ambT = floatfromhex(rval[4] + rval[3])
   #Desactive la sonde
   #self.child.sendline('char-write-cmd 0x29 00')
   return(self.IRTmp(objT, ambT))

  #Getter de l humidite et de la temperature
  def get_HUM(self):
    self.child.sendline('char-write-cmd 0x3C 01')
    self.child.expect('\[LE\]>')
    self.child.sendline('char-read-hnd 0x38')
    self.child.expect('descriptor: .*')
    rval=self.child.after.split()
    #print rval
    self.child.sendline('char-write-cmd 0x3C 00')
    return(self.HUMtmp(floatfromhex(rval[2]+rval[1])),self.HUMhum(floatfromhex(rval[4]+rval[3]))) 
 
  def get_PRES(self):
	#Recup valeurs de pression et calcul
    self.child.sendline('char-write-cmd 0x4f 01') #Active la lecture des datas
    self.child.expect('\[LE\]>')	
    self.child.sendline('char-write-cmd 0x4C 0x01 00') #Active la lecture des datas
    self.child.expect('\[LE\]>')		
    self.child.sendline('char-read-hnd 0x4b')
    self.child.expect('descriptor: .*')
    rval=self.child.after.split()	
    #print rval
    temp=int(rval[2] + rval[1],16)
    pres=int(rval[4] + rval[3],16)
    return self.barometer.calc(temp,pres)

  
  #Calcul de la temperature par le capteur IR
  def IRTmp(self,objT, ambT):
    m_tmpAmb = ambT/128.0
    Vobj2 = objT * 0.00000015625
    Tdie2 = m_tmpAmb + 273.15
    S0 = 6.4E-14            # Calibration factor
    a1 = 1.75E-3
    a2 = -1.678E-5
    b0 = -2.94E-5
    b1 = -5.7E-7
    b2 = 4.63E-9
    c2 = 13.4
    Tref = 298.15
    S = S0*(1+a1*(Tdie2 - Tref)+a2*pow((Tdie2 - Tref),2))
    Vos = b0 + b1*(Tdie2 - Tref) + b2*pow((Tdie2 - Tref),2)
    fObj = (Vobj2 - Vos) + c2*pow((Vobj2 - Vos),2)
    temp = pow(pow(Tdie2,4) + (fObj/S),.25)
    temp = (temp - 273.15)
    #print "%.2f C" % temp
    #sendval(temp)
    return temp

  #Calcul de la temperature par le capteur d humidite
  def HUMtmp(self,temp):
    t = -46.85 + 175.72/65536.0 * temp
    #print "%.2f C" % t
    return t
	
  #Calcul de l humidite
  def HUMhum(self,hum):
    hum = float(int(hum) & ~0x0003); 
    h = -6.0 + 125.0/65536.0 * hum 
    #print "%.2f pourcents" % h
    return abs(h)

#Classe particuliere pour le barometre	
class Barometer:
  def __init__(self, rawCalibration):
    self.m_barCalib = self.Calib( rawCalibration )
    return

  def calc(self,  rawT, rawP):
    self.m_raw_temp = tosigned(rawT)
    self.m_raw_pres = rawP 
    bar_temp = self.calcBarTmp( self.m_raw_temp )
    bar_pres = self.calcBarPress( self.m_raw_temp, self.m_raw_pres )
    return( bar_temp, bar_pres)
	
  def calcBarTmp(self, raw_temp):
    c1 = self.m_barCalib.c1
    c2 = self.m_barCalib.c2
    val = long((c1 * raw_temp) * 100)
    temp = val >> 24
    val = long(c2 * 100)
    temp += (val >> 10)
    return float(temp) / 100.0

  def calcBarPress(self,Tr,Pr):
    c3 = self.m_barCalib.c3
    c4 = self.m_barCalib.c4
    c5 = self.m_barCalib.c5
    c6 = self.m_barCalib.c6
    c7 = self.m_barCalib.c7
    c8 = self.m_barCalib.c8
    # Sensitivity
    s = long(c3)
    val = long(c4 * Tr)
    s += (val >> 17)
    val = long(c5 * Tr * Tr)
    s += (val >> 34)
    # Offset
    o = long(c6) << 14
    val = long(c7 * Tr)
    o += (val >> 3)
    val = long(c8 * Tr * Tr)
    o += (val >> 19)
    # Pression en Pa
    pres = ((s * Pr) + o) >> 14
    return float(pres)/100.0

  class Calib:
    def bld_int(self, lobyte, hibyte):
      return (lobyte & 0x0FF) + ((hibyte & 0x0FF) << 8)
        
    def __init__( self, pData ):	
      self.c1 = self.bld_int(pData[0],pData[1])
      self.c2 = self.bld_int(pData[2],pData[3])
      self.c3 = self.bld_int(pData[4],pData[5])
      self.c4 = self.bld_int(pData[6],pData[7])
      self.c5 = tosigned(self.bld_int(pData[8],pData[9]))
      self.c6 = tosigned(self.bld_int(pData[10],pData[11]))
      self.c7 = tosigned(self.bld_int(pData[12],pData[13]))
      self.c8 = tosigned(self.bld_int(pData[14],pData[15]))
 

 
#*******************************************Fonction principale************************************ 
def main(): 

  #Creation de l instance et connection sur le sensortag
  sensortag=Sensortag(ble_addr)
  
  while True:
    #Recuperation de la temperature infra rouge
    tmpIR=sensortag.get_IRtmp()
    print "La temperature IR : %.2f" % tmpIR +" C"
    #Recuperation de la temperature et l humidite 
    TabHUM=[]
    TabHUM=sensortag.get_HUM()
    print "La temperature : %.2f" % TabHUM[0]+" C"
    print "L'humidite : %.2f" % TabHUM[1]+" %"
    #Recuperation de la temperature et de la pression
    TabPRES=sensortag.get_PRES()
    print "La temperature : %.2f" % TabPRES[0]+" C"
    print "La pression : %.2f" % TabPRES[1]+" hPa"

    print "*************************************"
	#Transmission des donnees
    time.sleep(4)
	
if __name__ == "__main__":
    main()

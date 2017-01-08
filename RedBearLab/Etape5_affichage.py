# Mustafa DRISSI & Tung Hoang
# ce script permet de consulter les donnees enregistres dans la base de donnees par
# le script Etape5.py

import MySQLdb
servername = '127.0.0.1'
dbname = 'iot'
username = 'root'
password = 'root'
connectionObject = MySQLdb.connect(host=servername, user=username, passwd=password, db=dbname)
c = connectionObject.cursor()
c.execute("SELECT * FROM Capteur")
print ('+---------------------+-------------+----------+----------+')
print ('| time                | temperature | pression | altitude |')
print ('+---------------------+-------------+----------+----------+')
for row in c.fetchall():
   print('| '+str(row[0])+' |      '+str(row[1])+'     |   '+str(row[2])+' |     '+str(row[3])+' |')
	

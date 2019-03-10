import os
import sys
import time
from influx import InfluxDB
import json
import argparse
import datetime
import random
 
# Global für vorhandene Temperatursensoren
tempSensorBezeichnung = [] #Liste mit den einzelnen Sensoren-Kennungen
tempSensorAnzahl = 0 #INT für die Anzahl der gelesenen Sensoren

# Get absolut path of config file
configFile = open(os.path.join(os.path.dirname(
    os.path.realpath(__file__)), "config.json"), "r")
config = json.load(configFile)  # Load the json config file to a dict
configFile.close()

# Load important values from config
host = config.get('host')
port = config.get('port')
database = config.get('database')
waitTime = config.get('interval')

client = None

def ds1820einlesen():
    global tempSensorBezeichnung, tempSensorAnzahl
    #Verzeichnisinhalt auslesen mit allen vorhandenen Sensorbezeichnungen 28-xxxx
    try:
        for x in os.listdir("/sys/bus/w1/devices"):
            if (x.split("-")[0] == "28") or (x.split("-")[0] == "10"):
                tempSensorBezeichnung.append(x)
                tempSensorAnzahl = tempSensorAnzahl + 1
    except:
        # Auslesefehler
        print("Der Verzeichnisinhalt konnte nicht ausgelesen werden.")
        sys.exit(-1)

def readVars(verboose=False):
    data = []
    x = 0
    try:
        # 1-wire Slave Dateien gem. der ermittelten Anzahl auslesen 
        while x < tempSensorAnzahl:
            dateiName = "/sys/bus/w1/devices/" + tempSensorBezeichnung[x] + "/w1_slave"
            file = open(dateiName)
            filecontent = file.read()
            file.close()
            # Temperaturwerte auslesen und konvertieren
            stringvalue = filecontent.split("\n")[1].split(" ")[9]
            sensorwert = float(stringvalue[2:]) / 1000
            data.append(sensorwert)
            x = x + 1
    except:
        # Fehler bei Auslesung der Sensoren
        print("Die Auslesung der DS1820 Sensoren war nicht möglich.")
        sys.exit(-1)
    return data

def postVars(data):
    # Construct the connection to InfluxDB
    client = InfluxDB('http://' + host + ':' + str(port))
    for i in range(len(data)):
        # Post data to db
        client.write(database, 'Temps', fields={'Sensor{}'.format(i): data[i]})

def processVars(data, action="DB", verboose=False, formatingTXT=None):
    if action.lower() == "DB".lower():
        postVars(data)

    if (verboose):
        for i in range(len(data)):
            # Post data to db
            print('Sensor{}={}'.format(i, data[i]))


def main():

    ap = argparse.ArgumentParser()
    ap.add_argument("-t", "--type", required=False, default="multi",
                    help="Set the type of execution (multi/single)")
    ap.add_argument("-a", "--action", required=False, default="DB",
                    help="Set the action it should do (DB)")
    ap.add_argument("-q", "--quiet", required=False,
                    help="No output", action='store_true')
    ap.add_argument("-v", "--verboose", required=False,
                    help="Output debug/information messages", action='store_true')
    args = ap.parse_args()

    if args.quiet:
        args.verboose = False

    ds1820einlesen()

    # Print Debug messages if program is not quiet
    if not args.quiet:
        print("Process started!")
        if args.action.lower() == "DB".lower():
            print("Sending measurements to InfluxDB")
            print("Host: ", host)
            print("Port: ", port)
            print("Database: ", database)

        if(args.type == "multi"):
            print("Interval: {} seconds".format(waitTime))

        print("Sensors detected: ", tempSensorAnzahl)

    # if the type is multi it will continue processing
    while (args.type == "multi"):
        data = readVars(verboose=args.verboose)
        processVars(data, action=args.action,
                    verboose=args.verboose)
        time.sleep(waitTime)

    # if the type is single it only processes once
    if (args.type == "single"):
        data = readVars(verboose=args.verboose)
        processVars(data, action=args.action,
                    verboose=args.verboose)

if __name__ == '__main__':
    main()

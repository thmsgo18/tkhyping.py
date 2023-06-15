#!/usr/bin/python

# -*- coding: UTF-8 -*-

import serial
import sys
import json
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np
from base64 import b64decode
import wave
from tabulate import tabulate
import os
import select
import time
import sounddevice as sd
import pygame
from scipy.signal import butter, filtfilt

color_red = "\x1b[31m"
color_green = "\x1b[32m"
color_reset = "\x1b[0m"

method = ""
argc = len(sys.argv)
mode_BLE = False

tableau = [
    ["Method", "Allowed with BLE", "Option"],
    ["AuxOut", "YES", "NONE"],
    ["AuxIn", "YES", "NONE"],
    ["Calibrate", "YES", "NONE"],
    ["DumpFile", "YES", "NAME"],
    ["", "", "ex: hyping /dev/ttyUSB0 DumpFile config_user.json"],
    ["SetDate", "YES", "NONE"],
    ["GetDate", "YES", "NONE"],
    ["SetGain", "YES", "gain_master | gain_preamp | gain_air | gain_wire_out | gain_wire_in | gain_looper & <value>"],
    ["", "", "values in: master=[0;1]|preamp =[-96;0]|air =[0;1]|wire_out =[-45;4.5]|wire_in =[-96;0]|looper =[0;1]"],
    ["GetGains", "YES", "NONE"],
    ["StartMetronome", "YES", "NONE"],
    ["StopMetronome", "YES", "NONE"],
    ["UpdateMetronome", "YES", "bmp & num & den & nbbars"],
    ["ReadMetronome", "YES", "NONE"],
    ["BTcheck", "YES", "NONE"],
    ["ReadConfig", "YES", "NONE"],
    ["GetStatus", "YES", "NONE"],
    ["StartTuner", "YES", "NONE"],
    ["StopTuner", "YES", "NONE"],
    ["GetFileInfo", "YES", "name of file"],
    ["SustainKiller", "YES", "bank_num & on & reset"],
    ["RemoveEffect", "YES", "bank_num & effect_num"],
    ["AddEffect", "YES", "bank_num & type & preset & params"],
    ["SetGainBank", "YES", "bank_num & gain"],
    ["SwitchBank", "YES", "bank_num"],
    ["FileRemove", "YES", "name"],
    ["PowampStatus", "YES", "NONE"],
    ["McuReset", "YES", "NONE"],
    ["RemoveBank", "YES", "bank_num"],
    ["ReadBank", "YES", "bank_num & offset & size"],
    ["SetBankName", "YES", "bank_num & name"],
    ["SetController", "YES", "bank_num & effect_num & parameter & source & minimum & maximum"],
    ["StartRecording", "YES", "NONE"],
    ["StopRecording", "YES", "NONE"],
    ["StartRendering", "YES", "NONE"],
    ["StopRendering", "YES", "NONE"],
    ["SetEQBandGain", "YES", "band & gain"],
    ["SetEQGain", "YES", "gain"],
    ["GetDataRec", "YES", "NONE"],
    ["AuxOutDryWet", "YES", "value"],
    ["AuxInDryWet", "YES", "value"],
    ["PrintBank", "YES", "bank_num"],
    ["BypassEffect", "YES", "bank_num, effect_num, bypass"],
    ["SetPhaseInv", "YES", "value"],
    ["SustainKiller", "YES", "bank_num, on, reset"],
    ["", "", "hyping /dev/ttyUSB0 SustainKiller 1 true false"],
    ["GetAudio", "NO", "sensor | codec | a2dp"],
    ["BMS", "YES", "NONE"],
    ["GBF", "YES", "<freq> & <amp> & start | stop"],
    ["", "", "ex: hyping /dev/ttyUSB0 gbf 1000 0.7 start , hyping /dev/ttyUSB0 gbf stop"],
    ["GetLastLoop", "YES", "NONE"],
    ["Meter", "YES", "add | remove | get & input_level | output_level | mix_level | codec_in_level | bt_level"],
    ["", "", "For the get you have a dynamic display | For exit the get press space and return "],
    ["ButUpdate", "YES", "Bt1=[0 | 1] & Bt2=[0 | 1] & Bt3=[0 | 1] & Bt4=[0 | 1] & Pot1=[0;100] & Pot2=[0;100]"],
    ["TestGetAudioFile", "NO", "sensor | codec | a2dp & (name of the file)"],
    ["", "", "hyping /dev/ttyUSB0 TestGetAudioFile sensor test.wav"],
    ["TestGetAudio","NO","sensor | codec | a2dp & (duration of the pulse)"],
    ["", "", "hyping /dev/ttyUSB0 TestGetAudioFile sensor 100"],
    ["GetCPU", "YES", "NONE"],
    ["Temp", "YES", "NONE"]]

dico = {
'AuxOut': ['YES', 'NONE'],
 'AuxIn': ['YES', 'NONE'],
 'Calibrate': ['YES', 'NONE'],
 'DumpFile': ['YES', 'NAME'],
 'SetDate': ['YES', 'NONE'],
 'GetDate': ['YES', 'NONE'],
 'SetGain': ['YES', 'gain_master | gain_preamp | gain_air | gain_wire_out | gain_wire_in | gain_looper & <value>'],
 'GetGains': ['YES', 'NONE'],
 'StartMetronome': ['YES', 'NONE'],
 'StopMetronome': ['YES', 'NONE'],
 'UpdateMetronome': ['YES', 'bmp & num & den & nbbars'],
 'ReadMetronome': ['YES', 'NONE'],
 'BTcheck': ['YES', 'NONE'],
 'ReadConfig': ['YES', 'NONE'],
 'GetStatus': ['YES', 'NONE'],
 'StartTuner': ['YES', 'NONE'],
 'StopTuner': ['YES', 'NONE'],
 'GetFileInfo': ['YES', 'name of file'],
 'SustainKiller': ['YES', 'bank_num, on, reset'],
 'RemoveEffect': ['YES', 'bank_num & effect_num'],
 'AddEffect': ['YES', 'bank_num & type & preset & params'],
 'SetGainBank': ['YES', 'bank_num & gain'],
 'SwitchBank': ['YES', 'bank_num'],
 'FileRemove': ['YES', 'name'],
 'PowampStatus': ['YES', 'NONE'],
 'McuReset': ['YES', 'NONE'],
 'RemoveBank': ['YES', 'bank_num'],
 'ReadBank': ['YES', 'bank_num & offset & size'],
 'SetBankName': ['YES', 'bank_num & name'],
 'SetController': ['YES', 'bank_num & effect_num & parameter & source & minimum & maximum'],
 'StartRecording': ['YES', 'NONE'],
 'StopRecording': ['YES', 'NONE'],
 'StartRendering': ['YES', 'NONE'],
 'StopRendering': ['YES', 'NONE'],
 'SetEQBandGain': ['YES', 'band & gain'],
 'SetEQGain': ['YES', 'gain'],
 'GetDataRec': ['YES', ''],
 'AuxOutDryWet': ['YES', 'value'],
 'AuxInDryWet': ['YES', 'value'],
 'PrintBank': ['YES', 'bank_num'],
 'BypassEffect': ['YES', 'bank_num, effect_num, bypass'],
 'SetPhaseInv': ['YES', 'value'],
 'GetAudio': ['NO', 'sensor | codec | a2dp'],
 'BMS': ['YES', 'NONE'],
 'GBF': ['YES', '<freq> & <amp> & start | stop'],
 'GetLastLoop': ['YES', 'NONE'],
 'Meter': ['YES', 'add | remove | get & input_level | output_level | mix_level | codec_in_level | bt_level'],
 'ButUpdate': ['YES', 'Bt1=[0 | 1] & Bt2=[0 | 1] & Bt3=[0 | 1] & Bt4=[0 | 1] & Pot1=[0;100] & Pot2=[0;100]'],
 'TestGetAudioFile': ['NO', 'sensor | codec | a2dp & (name of the file)'],
 'TestGetAudio': ['NO', 'sensor | codec | a2dp & (duration of the pulse)'],
 'GetCPU': ['YES', 'NONE'],
 'Temp': ['YES', 'NONE']}

liste_methode = ['AuxOut', 'AuxIn', 'Calibrate', 'DumpFile', '', 'SetDate', 'GetDate', 'SetGain', '', 'GetGains', 'StartMetronome', 'StopMetronome', 'UpdateMetronome', 'ReadMetronome', 'BTcheck', 'ReadConfig', 'GetStatus', 'StartTuner', 'StopTuner', 'GetFileInfo', 'SustainKiller', 'RemoveEffect', 'AddEffect', 'SetGainBank', 'SwitchBank', 'FileRemove', 'PowampStatus', 'McuReset', 'RemoveBank', 'ReadBank', 'SetBankName', 'SetController', 'StartRecording', 'StopRecording', 'StartRendering', 'StopRendering', 'SetEQBandGain', 'SetEQGain', 'GetDataRec', 'AuxOutDryWet', 'AuxInDryWet', 'PrintBank', 'BypassEffect', 'SetPhaseInv', 'SustainKiller', '', 'GetAudio', 'BMS', 'GBF', '', 'GetLastLoop', 'Meter', '', 'ButUpdate', 'TestGetAudioFile', '', 'TestGetAudio', '', 'GetCPU', 'Temp']


def usage():
    """

    Returns
    -------
    Send a table with the different action and options
    """
    print("Usage : \nhyping [ble H2-UV196] /dev/ttyUSB0 [method] [option]")
    print(tabulate(tableau, headers="firstrow", tablefmt="fancy_grid"))
    if mode_BLE:
        """
        stop connection by BLE
        """
        print("Closing BLE ")
        dev.write(str.encode("@stop\n")) 
        resp = dev.read_until()   
        print("got", resp)
    sys.exit()

if argc == 1:
    usage()
if argc == 2:
    dev = sys.argv[1]
    method = "ping"
elif argc == 3:
    dev = sys.argv[1]
    method = sys.argv[2]
elif argc >= 4:
    if sys.argv[1] == "ble":
        mode_BLE = True
        print("Using BLE gateway with ESP32-wroom32 on", sys.argv[3])
        dev = sys.argv[3]
        method = sys.argv[4]
        option = sys.argv[5:]
    else:
        dev = sys.argv[1]
        method = sys.argv[2]
        option = sys.argv[3:]
else:
    usage()

print("\nhyping opening device")
try:
    dev = serial.Serial(port=dev, baudrate=115200, timeout=5)
    print("Ok device open\n")
except serial.SerialException:
    print("Device %s can not be found or can not be configured\n"%(dev))
    sys.exit()

if mode_BLE:
    """
    start connection by BLE
    """
    print("Connecting BLE to %s..."%(sys.argv[2]))
    dev.write(str.encode("@start %s\n"%(sys.argv[2]))) 
    resp = dev.read_until()   
    print("got", resp)

def is_space_pressed():
    """

    Returns
    -------
    Check if the 'space' is pressed
    fonction used in the fonction meter
    """
    if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
        key = sys.stdin.read(1)
        if key == ' ':
            return True
    return False

def print_red(*args, **kwargs):
    print(color_red, end="")
    print(*args, **kwargs)
    print(color_reset, end="")

def print_green(*args, **kwargs):
    print(color_green, end="")
    print(*args, **kwargs)
    print(color_reset, end="")

def send_req(method, params = None):
    """
    Returns
    -------
    json or None

    Creation of jsonrpc
    """
    req = {"jsonrpc": "2.0", "method": method, "id": 1}
    if params:
        req["params"] = params
    es = str.encode(json.dumps(req)+'\n')                                                                                                               
    dev.write(es)
    resp = dev.read_until()
    if len(resp):
        return json.loads(resp)
    else:
        return None

def ping():
    """
    Returns
    -------
    None.
    
    Connection test send ping and the system return pong 
    """
    jr = send_req("ping")
    if "result" in jr and jr["result"] == "pong":
        print("OK device returned pong\n")
    else:
        print("ERROR got", json.dumps(jr))

def SetDate():
    """
    Returns
    -------
    None.
    
    Request for setting up the date and the clock 
    """
    now = datetime.now()
#   {"jsonrpc": "2.0", "method": "SetDate", "params": {"year": 2023, "month":02, "day":16, "hour":19, "minute":01, "second":32}}
    params = {}
    params["year"] = now.year
    params["month"] = now.month
    params["day"] = now.day
    params["hour"] = now.hour
    params["minute"] = now.minute
    params["second"] = now.second
    jr = send_req("SetDate", params)
    if "result" in jr and jr["result"] == True:
        print("OK device returned True\n")
    else:
        print("ERROR got %s\n", json.dumps(jr))

def GetDate():
    """
    Returns
    -------
    None.

    Request the date and the clock 
    """
    jr = send_req("GetDate")
    if "result" in jr:
        d = jr["result"]
        print("Returned date %u/%u/%u %u:%u:%u\n"%(d["day"], d["month"], d["year"], d["hour"], d["minute"], d["second"]))
    else:
        print("ERROR got %s\n"%(json.dumps(jr)))

def GetAudio(source):
    audio = bytes()
    run = True
    if source not in ["sensor", "codec", "a2dp", "output"]:
        print("Error method GetAudio source %s unkown")
        return
    if source == "sensor":
        source = "sensor_in"
    if source == "codec":
        source = "codec_in"
    params = {"target":"AudioSpl", "command":"Start", "source": source, "duration": 2000}
    jr = send_req("GetInternals", params)
    while run:
        params = {"target":"AudioSpl", "command":"NextChunk"}
        jr = send_req("GetInternals", params)
        if "result" in jr:
            res = jr["result"]
            buff = b64decode(res["data"])
            print("received nb bytes=", len(buff))
            audio += buff
            run = not res["last_chunk"]
        elif "error" in jr:
            raise RuntimeError(jr["error"]["message"])
        else:
            raise RuntimeError("Bad response")

    with wave.open( "audio_%s.wav"% (source), "wb" ) as wv:
            wv.setnchannels(1)
            wv.setsampwidth(2)
            wv.setframerate(44100)
            wv.writeframes( audio )

    audio_signed = np.frombuffer( audio, dtype=np.int16 )
    plt.hist(audio_signed)
    plt.title("Noise density")
    plt.show()

    return np.frombuffer( audio, dtype=np.int16 ) / ((1<<15)-1)

def bms():
    reg_name = ["VSET", "CHGSET", "TIM", "STAT", "FAULT"]
    for reg in range(5):
        jr = send_req("bms.read.reg", reg)
        if "result" in jr:
            res = jr["result"]
            print(reg_name[reg], ": %02x"%res)

def gbf(freq, amp, onoff):
    print(freq, amp, onoff)
    if onoff == "start":
        params = {"target":"StartOsc", "f0":freq, "amp": amp}
        jr = send_req("SetInternals", params)
        if "result" in jr and jr["result"] == True:
            print("GBF set with success Freq =", freq, "Amp =", amp)
        else :
            print_red(jr)
    else:
        params = {"target":"StopOsc"}
        jr = send_req("SetInternals", params)
        if "result" in jr and jr["result"] == True:
            print("GBF stopped with success")

def get_last_loop():
    """
    Returns
    -------
    None.

    Request the last loop 
    """
    jr = send_req("GetLastRecordingName")
    if "result" in jr:
        last_loop_path = jr["result"]
    else:
        print_red("GetLastRecordingName ERROR got %s\n"%(json.dumps(jr)))
        return
    
    loopnbr = int(last_loop_path[11:15]) 
    if loopnbr > 0:
        loopnbr -= 1
    last_loop_path = "/Loops/loop%04d.wav"%(loopnbr)
    print("Dowloading", last_loop_path)
    audio = bytearray()
    run = True
    ofs = 0
    while run:
        params = {"name":last_loop_path, "offset":ofs, "size": 128}
        jr = send_req("DumpFile", params)
        if "result" in jr:
            buff   = bytearray.fromhex(jr["result"])
            print("received nb bytes=", len(buff))
            rdlen  = len(buff) # /2 because 1 frame is 2 byte long
            audio += buff
            ofs += 128
            run = rdlen == 128
        elif "error" in jr:
            print_red("ERROR received :", jr["error"]["message"])
            break
        else:
            print_red("Bad response from device")
            break
    with open("audio.wav", "wb" ) as binary_file:
        binary_file.write(audio)

def meter(cde, meter, test=False):
    """

    Parameters
    ----------
    cde (add | remove | get)
    meter (input_level | output_level | mix_level | codec_in_level | bt_level)
    test

    Returns
    -------
    Add or remove or get a meter on input_level or output_level or mix_level or codec_in_level or bt_level
    """
    if cde == "add":
        target = "AddMeter"
    elif cde == "remove":
        target = "RemMeter"
    elif cde != "get":
        print_red("Bad option " + cde)
        return
    params = {"target":"RemoveBank", "name":"out"}
    jr = send_req("SetInternals", params)
    if "result" in jr and jr["result"] == True:
        print("EQ bank removed ok")
    else:
        print_red("Error trying to remove EQ bank")
    if cde in ["add", "remove"]:
        params = {"target":target, "name":meter, "time_constant": 0.1}
        jr = send_req("SetInternals", params)
        if "result" in jr and jr["result"] == True:
            print("Meter", target, "done with success")
        else :
            print_red(jr)
    else:
        while True:
            params = {"target":"Levels_dBfs"}
            jr = send_req("GetInternals", params)
            if jr is None:
                print_red("Error in send_req, probably a timeout")
                break
            elif "result" in jr:
                res = jr["result"]
                print("\t",res[meter], end='\r')
                time.sleep(0.1)
                if test == True:
                    return res[meter]
                if is_space_pressed():
                    break
            else:
                print_red(jr)
                break

def DumpFile(name):
    """

    Parameters
    ----------
    name (name of the file)

    Returns
    -------
    Download the file request
    """
    if mode_BLE:
        size = 128
    else:
        size = 1024
    i=True
    counter=0
    file_path = os.path.join(os.getcwd(), name)
    with open(file_path, "w") as fichier:
        pass
    while i==True:
        params = {"name": name, "offset": counter*size, "size": size}
        jr = send_req("DumpFile", params)
        counter+=1
        if "result" in jr :
            data = jr["result"]
            size_data = len(data)
            bytes_object = bytes.fromhex(data)
            text = bytes_object.decode("utf-8")
            with open(file_path, "a") as fichier:
                fichier.write(text)
            if size_data < (size*2):
                i = False
            else:
             i=True
        else:
            i=False

def GetGain():
    """

    Returns
    -------
    Request all the gain (gain_master | gain_preamp | gain_air | gain_wire_out | gain_wire_in | gain_looper)
    """
    params = {"target": "Gains"}
    jr = send_req("Getinternals",params)
    if "result" in jr:
        d = jr["result"]
        print("Returned Gains")
        print("gain_master =",d["gain_master"])
        print("gain_preamp =", d["gain_preamp"])
        print("gain_air =",d["gain_air"])
        print("gain_wire_out =", d["gain_wire_out"])
        print("gain_wire_in =", d["gain_wire_in"])
        print("gain_looper =", d["gain_looper"])
    else:
        print("ERROR got %s\n" % (json.dumps(jr)))

def SetGain(name,value):
    """

    Parameters
    ----------
    name (of the gain)
    value (of the gain)

    Returns
    -------
    Set the gain at a value
    """
    def run(name, value):
        params = {"target": "Gain", "name": name, "value": int(value)}
        jr = send_req("SetInternals", params)
        if "result" in jr:
            print(name, "set with success value =", value)
        else:
            print_red(jr)
    testvalue = int(value)
    if name == "gain_master":
        if 0 <= testvalue <= 1:
            run(name, value)
        else:
            print("value out of range")
            usage()

    elif name == "gain_preamp":
        if -96 <= testvalue <= 0:
            run(name, value)
        else:
            print("value out of range")
            usage()
    elif name == "gain_air":
        if 0 <= testvalue <= 1:
            run(name, value)
        else:
            print("value out of range")
            usage()
    elif name == "gain_wire_out":
        if -45 <= testvalue <= 4.5:
            run(name, value)
        else:
            print("value out of range")
            usage()
    elif name == "gain_wire_in":
        if 0 <= testvalue <= 1:
            run(name, value)
        else:
            print("value out of range")
            usage()
    else:
        if 0 <= testvalue <= 1:
            run(name, value)
        else:
            print("value out of range")
            usage()

def temp():
    """
    Returns
    -------
    None.

    Request the temperature
    """
    params = {"target":"Temp"}
    jr = send_req("GetInternals", params)
    if jr is None:
        print_red("Error in send_req, probably a timeout")
    elif "result" in jr:
        res = jr["result"]
        print_green("CPU Temperature :", res["temperature"])
    else:
        print_red(jr)

def ButUpdate(Bt1, Bt2, Bt3, Bt4, Pot1, Pot2):
    """

    Parameters
    ----------
    Bt1
    Bt2
    Bt3
    Bt4
    Pot1
    Pot2

    Returns
    -------
    Set the state of Bt1 | Bt2 | Bt3 | Bt4 | Pot1 | Pot2
    """
    if ((0 == int(Bt1)) or (1 == int(Bt1))) and ((0 == int(Bt2)) or (1 == int(Bt2))) and ((0 == int(Bt3)) or (1 == int(Bt3))) and ((0 == int(Bt4)) or (1 == int(Bt4))) and (0 <= int(Pot1) <= 100) and (0 <= int(Pot1) <= 100):
        params = {"Bt1": Bt1, "Bt2": Bt2, "Bt3": Bt3, "Bt4": Bt4, "Pot1": Pot1, "Pot2": Pot2}
        jr = send_req("ButUpdate", params)
    else:
        print("value out of range")
        usage()

def TestCalibrate(freq, amplitude, test =False):
    SetGain("gain_preamp","0")
    meter("add", "input_level")
    frequency = int(freq)
    duration = 0.5
    amplitude_db = int(amplitude)
    amplitude_linear = 10 ** (amplitude_db / 20)
    samples = np.sin(2 * np.pi * frequency * np.linspace(0, duration, int(duration * 44100)))
    samples *= amplitude_linear
    sd.play(samples, samplerate=44100)
    time.sleep(0.2)
    val = int(meter("get", "input_level", True))
    sd.wait()
    difference = abs(amplitude_db)-abs(val)
    if test==False :
        if val >= -1:
            print("son trop fort")
            return False
        elif val <= -30:
            print("son trop faible")
            return False
        else:
            print("valeur en db capté",val)
            print("difference avec la valeur envoyer ",difference)
    else:
        return difference
    meter("remove","input_level")

def ResponseSensorInput(amplitude,freq_start, freq_end,number_point):
    if -60 <= int(amplitude) <= 0:
        difference = TestCalibrate(100,-20,True)
        meter("add", "input_level")
        print(difference)
        SetGain("gain_preamp", "0")
        real_amplitude= int(amplitude) + difference
        step = (int(freq_end)/int(freq_start))**(1/int(number_point))
        i = int(freq_start)
        result = []
        duration = 0.5
        amplitude_linear = 10 ** (real_amplitude / 20)
        while i <= int(freq_end):
            samples = np.sin(2 * np.pi * i * np.linspace(0, duration, int(duration * 44100)))
            samples *= amplitude_linear
            sd.play(samples, samplerate=44100)
            time.sleep(0.2)
            val = meter("get", "input_level", True)
            sd.wait()
            result.append(val)
            i = i*step
        meter("remove", "input_level")
        abscissa = np.logspace(freq_start,freq_end,number_point)
        plt.plot(abscissa, result)
        plt.show()

def TestMeter(amplitude,freq):
    meter("add", "input_level")
    result = []
    frequency = int(freq)
    duration = 10
    amplitude_db = int(amplitude)
    amplitude_linear = 10 ** (amplitude_db / 20)
    samples = np.sin(2 * np.pi * frequency * np.linspace(0, duration, int(duration * 44100)))
    samples *= amplitude_linear
    sd.play(samples, samplerate=44100)
    time.sleep(0.2)
    start_time = time.time()
    while time.time() - start_time < 9:
        val = int(meter("get", "input_level", True))
        result.append(val)
    sd.wait()
    print(result)
    print("le maximum est :", max(result), "et le minimum est :", min(result))

def StartMetronome():
    """

    Returns
    -------
    Start the Metronome
    """
    jr = send_req("StartMetronome")
    if "result" in jr:
        res = jr["result"]
        print(res)
    else:
        print("ERROR got %s\n" % (json.dumps(jr)))

def StopMetronome():
    """

    Returns
    -------
    Stop the Metronome
    """
    jr = send_req("StopMetronome")
    if "result" in jr:
        res = jr["result"]
        print(res)
    else:
        print("ERROR got %s\n" % (json.dumps(jr)))

def UpdateMetronome(bpm, num, den, nbbars):
    """

    Parameters
    ----------
    bpm
    num
    den
    nbbars

    Returns
    -------
    Update the Metronome
    """
    params = {"bpm": float(bpm), "num": int(num), "den": int(den), "nbbars": int(nbbars)}
    jr = send_req("UpdateMetronome", params)
    if "result" in jr:
        res = jr["result"]
        print(res)
    else:
        print("ERROR got %s\n" % (json.dumps(jr)))

def ReadMetronome():
    """

    Returns
    -------
    Request the values of the Metronome
    """
    jr = send_req("ReadMetronome")
    if "result" in jr:
        res = jr["result"]
        print(res)
    else:
        print("ERROR got %s\n" % (json.dumps(jr)))

def MoveBank(src, dst):
    """

    Parameters
    ----------
    src
    dst

    Returns
    -------
    Move bank from src to dst
    """
    params = {"scr": int(src), "dst": dst}
    jr = send_req("MoveBank", params)
    if "result" in jr:
        res = jr["result"]
        print(res)
    else:
        print("ERROR got %s\n" % (json.dumps(jr)))

def RemoveBank(bank_num):
    """

    Parameters
    ----------
    bank_num

    Returns
    -------
    Remove a bank
    """
    params = {"bank_num":int(bank_num)}
    jr = send_req("RemoveBank", params)
    if "result" in jr:
        res = jr["result"]
        print(res)
    else:
        print("ERROR got %s\n" % (json.dumps(jr)))

def ReadBank(bank_num, offset, size):
    """

    Parameters
    ----------
    bank_num
    offset
    size

    Returns
    -------
    Read a bank content as a serialized json string, processed like a binary content
        in order to avoid any double quote escaping issue.
        Because result string could be too big, the parameters offset and size allow
        to get it by chunks limited to "size"

    """
    params = {"bank_num": int(bank_num), "offset": int(offset), "size": int(size)}
    jr = send_req("RemoveBank", params)
    if "result" in jr:
        res = jr["result"]
        print(res)
    else:
        print("ERROR got %s\n" % (json.dumps(jr)))

def SetBankName (bank_num, name):
    """

    Parameters
    ----------
    bank_num
    name

    Returns
    -------
    Change the name of a specified bank
    """
    params = {"bank_num": int(bank_num), "name": name}
    jr = send_req("SetBankName", params)
    if "result" in jr:
        res = jr["result"]
        print(res)
    else:
        print("ERROR got %s\n" % (json.dumps(jr)))

def SetController(bank_num, effect_num, parameter, source, minimum, maximum):
    """

    Parameters
    ----------
    bank_num
    effect_num
    parameter
    source
    minimum
    maximum

    Returns
    -------
    Affects the controller to a specific effect's parameter
    """
    params = {"bank_num": int(bank_num),"effect_num": int(effect_num), "parameter": parameter, "source": source, "min":minimum, "max": maximum}
    jr = send_req("SetController", params)
    if "result" in jr:
        res = jr["result"]
        print(res)
    else:
        print("ERROR got %s\n" % (json.dumps(jr)))

def Calibrate():
    """

    Returns
    -------
    Start a calibration
    """
    jr = send_req("SetController")
    if "result" in jr:
        res = jr["result"]
        print(res)
    else:
        print("ERROR got %s\n" % (json.dumps(jr)))

def StartRecording():
    """

    Returns
    -------
    Start audio recording (free set to false when looper activated)
    """
    params = {"free": True}
    jr = send_req("StartRecording", params)
    if "result" in jr:
        res = jr["result"]
        print(res)
    else:
        print("ERROR got %s\n" % (json.dumps(jr)))

def StopRecording():
    """

    Returns
    -------
    Stop audio recording
    """
    jr = send_req("StopRecording")
    if "result" in jr:
        res = jr["result"]
        print(res)
    else:
        print("ERROR got %s\n" % (json.dumps(jr)))

def StartRendering():
    """

    Returns
    -------
    Start audio rendering
    """
    jr = send_req("StartRendering")
    if "result" in jr:
        res = jr["result"]
        print(res)
    else:
        print("ERROR got %s\n" % (json.dumps(jr)))

def StopRendering():
    """

    Returns
    -------
    Stop audio rendering

    """
    jr = send_req("StopRendering")
    if "result" in jr:
        res = jr["result"]
        print(res)
    else:
        print("ERROR got %s\n" % (json.dumps(jr)))

def SetEQBandGain(band, gain):
    """

    Parameters
    ----------
    band
    gain

    Returns
    -------
    Set the gain for a band of the main EQ
    """
    params = {"band": int(band), "gain": float(gain)}
    jr = send_req("SetEQBandGain", params)
    if "result" in jr:
        res = jr["result"]
        print(res)
    else:
        print("ERROR got %s\n" % (json.dumps(jr)))

def SetEQGain(gain):
    """

    Parameters
    ----------
    gain

    Returns
    -------
    Set the gain of the main EQ
    """
    params = {"gain": float(gain)}
    jr = send_req("SetEQGain", params)
    if "result" in jr:
        res = jr["result"]
        print(res)
    else:
        print("ERROR got %s\n" % (json.dumps(jr)))

def GetStatus():
    """

    Returns
    -------
    Get the free space in GB, free space in %, battery status in %, versions and cpuid
    """
    jr = send_req("GetStatus")
    if "result" in jr:
        res = jr["result"]
        print(res)
    else:
        print("ERROR got %s\n" % (json.dumps(jr)))

def GetDataRec():
    jr = send_req("GetDataRec")
    if "result" in jr:
        res = jr["result"]
        print(res)
    else:
        print("ERROR got %s\n" % (json.dumps(jr)))

def AuxOut():
    """

    Returns
    -------
    Turns aux out on & off
    """
    params = {"on": False}
    jr = send_req("AuxOut", params)
    if "result" in jr:
        res = jr["result"]
        print(res)
    else:
        print("ERROR got %s\n" % (json.dumps(jr)))

def AuxIn():
    """

    Returns
    -------
    Turns aux in on & off
    """
    params = {"on": False}
    jr = send_req("AuxIn", params)
    if "result" in jr:
        res = jr["result"]
        print(res)
    else:
        print("ERROR got %s\n" % (json.dumps(jr)))

def AuxOutDryWet(value):
    """

    Parameters
    ----------
    value

    Returns
    -------
    Changes the value of the aux out dry/wet

    """
    params = {"value": float(value)}
    jr = send_req("AuxOutDryWet", params)
    if "result" in jr:
        res = jr["result"]
        print(res)
    else:
        print("ERROR got %s\n" % (json.dumps(jr)))

def AuxInDryWet(value):
    """

    Parameters
    ----------
    value

    Returns
    -------
    Changes the value of the aux in dry/wet
    """
    params = {"value": float(value)}
    jr = send_req("AuxInDryWet", params)
    if "result" in jr:
        res = jr["result"]
        print(res)
    else:
        print("ERROR got %s\n" % (json.dumps(jr)))

def BTcheck():
    """

    Returns
    -------
    Handshake the guitar. Can be used to test the connection.
    """
    jr = send_req("BTcheck")
    if "result" in jr:
        res = jr["result"]
        print(res)
    else:
        print("ERROR got %s\n" % (json.dumps(jr)))

def PrintBank(bank_num):
    """

    Parameters
    ----------
    bank_num

    Returns
    -------
    Print a bank content (debug)
    """
    params = {"bank_num":int(bank_num)}
    jr = send_req("PrintBank", params)
    if "result" in jr:
        res = jr["result"]
        print(res)
    else:
        print("ERROR got %s\n" % (json.dumps(jr)))

def ReadConfig():
    """

    Returns
    -------
    Read and return the current config
    """
    jr = send_req("ReadConfig")
    if "result" in jr:
        res = jr["result"]
        print(res)
    else:
        print("ERROR got %s\n" % (json.dumps(jr)))

def BypassEffect(bank_num, effect_num, bypass):
    """

    Parameters
    ----------
    bank_num
    effect_num
    bypass

    Returns
    -------
    Enable or disable the bypass parameter of an effect
    """
    params = {"bank_num": int(bank_num), "effect_num": int(effect_num), "bypass": bool(bypass)}
    jr = send_req("BypassEffect", params)
    if "result" in jr:
        res = jr["result"]
        print(res)
    else:
        print("ERROR got %s\n" % (json.dumps(jr)))

def SetPhaseInv(value):
    """

    Parameters
    ----------
    value

    Returns
    -------
    Set the phase inverter
    """
    params = {"value": int(value)}
    jr = send_req("SetPhaseInv", params)
    if "result" in jr:
        res = jr["result"]
        print(res)
    else:
        print("ERROR got %s\n" % (json.dumps(jr)))

def StartTuner():
    """

    Returns
    -------
    Start the Tuner in the guitar
    """
    jr = send_req("StartTuner")
    if "result" in jr:
        res = jr["result"]
        print(res)
    else:
        print("ERROR got %s\n" % (json.dumps(jr)))

def StopTuner():
    """

    Returns
    -------
    Stop the Tuner in the guitar
    """
    jr = send_req("StopTuner")
    if "result" in jr:
        res = jr["result"]
        print(res)
    else:
        print("ERROR got %s\n" % (json.dumps(jr)))

def ActivateSpkFilter(value):
    """

    Parameters
    ----------
    value

    Returns
    -------
    Activate or deactivate the calibration
    """
    params = {"value": int(value)}
    jr = send_req("ActivateSpkFilter", params)
    if "result" in jr:
        res = jr["result"]
        print(res)
    else:
        print("ERROR got %s\n" % (json.dumps(jr)))

def LaunchCalibration(amp, f0, f1, mode, feedback):
    """

    Parameters
    ----------
    amp
    f0
    f1
    mode
    feedback

    Returns
    -------
    Start a calibration
    """
    params = {"amp": float(amp), "f0": float(f0), "f1": float(f1), "mode": int(mode), "feedback": float(feedback)}
    jr = send_req("LaunchCalibration", params)
    if "result" in jr:
        res = jr["result"]
        print(res)
    else:
        print("ERROR got %s\n" % (json.dumps(jr)))

def GetFileInfo(name):
    """

    Parameters
    ----------
    name

    Returns
    -------
    Return size and crc32 of a file
    """
    params = {"name": name}
    jr = send_req("GetFileInfo", params)
    if "result" in jr:
        res = jr["result"]
        print(res)
    elif "error" in jr:
        res = jr["error"]
        print(res)
    else:
        print("ERROR got %s\n" % (json.dumps(jr)))

def FileRemove(name):
    """

    Parameters
    ----------
    name

    Returns
    -------
    Remove a file from the emmc flash
    """
    params = {"name": name}
    jr = send_req("FileRemove", params)
    if "result" in jr:
        res = jr["result"]
        print(res)
    else:
        print("ERROR got %s\n" % (json.dumps(jr)))

def PowampStatus():
    """
    NONE ACTIVATE IN THE H2
    Returns
    -------
    Returns current powamp's status
    """
    jr = send_req("powamp.status")
    if "result" in jr:
        res = jr["result"]
        print(res)
    else:
        print("ERROR got %s\n" % (json.dumps(jr)))

def UiLedDim(led_up, led_middle, led_down):
    """

    Parameters
    ----------
    led_up
    led_middle
    led_down

    Returns
    -------
    Dim the 3 leds. Given value must be in 0..100 range
    """
    if (0 <= int(led_up) <= 100 ) and (0 <= int(led_middle) <= 100 ) and (0 <= int(led_down) <= 100 ):
        params = {"led_up": int(led_up), "led_middle": int(led_up), "led_down": int(led_down)}
        jr = send_req("ui.led.dim", params)
        if "result" in jr:
            res = jr["result"]
            print(res)
        else:
            print("ERROR got %s\n" % (json.dumps(jr)))
    else :
        usage()

def UiEnableSet(params):
    """

    Parameters
    ----------
    params

    Returns
    -------
    Enable or disable the physical buttons, when disabled pressing buttons or encoder
       or turning encoder does nothing on the menus. But ui.monitor works.
    """
    if (params == "True") :
        jr = send_req("ui.enable.set", True)
        if "result" in jr:
            res = jr["result"]
            print(res)
        else:
            print("ERROR got %s\n" % (json.dumps(jr)))
    elif (params == "False"):
        jr = send_req("ui.enable.set", False)
        if "result" in jr:
            res = jr["result"]
            print(res)
        else:
            print("ERROR got %s\n" % (json.dumps(jr)))
    else:
        usage()

def UiScreenFill(action, color=0):
    """

    Parameters
    ----------
    action
    color

    Returns
    -------
    Fill screen with given color or release screen
    """
    if action == "release":
        params = {"action": action}
        jr = send_req("ui.screen.fill", params)
        if "result" in jr:
            res = jr["result"]
            print(res)
        else:
            print("ERROR got %s\n" % (json.dumps(jr)))
    elif action == "fill":
        params = {"action": action, "color": int(color)}
        jr = send_req("ui.screen.fill", params)
        if "result" in jr:
            res = jr["result"]
            print(res)
        else:
            print("ERROR got %s\n" % (json.dumps(jr)))
    else:
        usage()

def TestMonostable():
    """

    Returns
    -------
    Read the internal RTC
    """
    jr = send_req("testMonostable")
    if "result" in jr:
        res = jr["result"]
        print(res)
    else:
        print("ERROR got %s\n" % (json.dumps(jr)))

def TestChargerWakeup():
    """

    Returns
    -------
    Read the internal RTC
    """
    jr = send_req("testChargerWakeup")
    if "result" in jr:
        res = jr["result"]
        print(res)
    else:
        print("ERROR got %s\n" % (json.dumps(jr)))

def PowerMode():
    """

    Returns
    -------
    Read the internal RTC
    """
    jr = send_req("powerMode")
    if "result" in jr:
        res = jr["result"]
        print(res)
    else:
        print("ERROR got %s\n" % (json.dumps(jr)))

def UiMonitor(time):
    """

    Parameters
    ----------
    time

    Returns
    -------
    Start the monitoring of the UI buttons and encoder for the time passed in params
    """
    jr = send_req("ui.monitor", time)
    if "result" in jr:
        res = jr["result"]
        if res == False :
            print("Nothing is touched on UI, after the time given")
        else:
            print(res)
    else:
        print("ERROR got %s\n" % (json.dumps(jr)))

def McuReset():
    jr = send_req("mcu.reset")
    if "result" in jr:
        res = jr["result"]
        print(res)
    else:
        print("ERROR got %s\n" % (json.dumps(jr)))

def RtaudioInGainSet(params):
    """

    Parameters
    ----------
    params

    Returns
    -------
    Sets the gain of the sensor input
    """
    if -96 <= int(params) <= 0 :
        jr = send_req("rtaudio.in.gain.set")
        if "result" in jr:
            res = jr["result"]
            print(res)
        else:
            print("ERROR got %s\n" % (json.dumps(jr)))
    else:
        usage()

def RtaudioOutEnable(left, right):
    """

    Parameters
    ----------
    left
    right

    Returns
    -------
    Activates or deactivates actuators according to given config.
    """
    params = {"left": bool(left), "right": bool(right)}
    jr = send_req("rtaudio.out.gain.set",params)
    if "result" in jr:
        res = jr["result"]
        print(res)
    else:
        print("ERROR got %s\n" % (json.dumps(jr)))

def FileUpload(file_path, status, data):
    """

    Parameters
    ----------
    file_path
    status
    data

    Returns
    -------
    Uploads a file from the serial port to emmc memory. Input data has to be encoded as a base64 string.
    """
    params = {"file_path": file_path, "status" : status, "data": data}
    jr = send_req("file.upload", params)
    if "result" in jr:
        res = jr["result"]
        print(res)
    else:
        print("ERROR got %s\n" % (json.dumps(jr)))

def SetSpeakerBiquads(params):
    """

    Parameters
    ----------
    params

    Returns
    -------
    Set the calibration biquads
    """
    jr = send_req("SetSpeakerBiquads", params)
    if "result" in jr:
        res = jr["result"]
        print(res)
    else:
        print("ERROR got %s\n" % (json.dumps(jr)))

def GetLastRecordingName():
    """

    Returns
    -------
    Get the last recording name
    """
    jr = send_req("GetLastRecordingName", )
    if "result" in jr:
        res = jr["result"]
        print(res)
    else:
        print("ERROR got %s\n" % (json.dumps(jr)))

def AutoPowerOff(value):
    params = {"target":"AutoPowerOff", "value": bool(value)}
    jr = send_req("SetInternal", params)
    if "result" in jr:
        res = jr["result"]
        print(res)
    else:
        print("ERROR got %s\n" % (json.dumps(jr)))

def GetCPU():
    """

    Returns
    -------
    Get CPU usage in %
    """
    params = {"target": "CPU"}
    jr = send_req("GetInternals", params)
    if "result" in jr:
        res = jr["result"]
        print_green("CPU usage :", res["cpu"], "%")
    else:
        print_red(jr)

def GetFreeHeap():
    """

    Returns
    -------
    Get free Heap
    """
    params = {"target": "Heap"}
    jr = send_req("GetInternals", params)
    if "result" in jr:
        res = jr["result"]
        print(res)
    else:
        print_red(jr)

def GetSignalLevelsInRMS():
    """

    Returns
    -------
    Get signal levels in RMS
    """
    params = {"target": "Levels_rms"}
    jr = send_req("GetInternals", params)
    if "result" in jr:
        res = jr["result"]
        print(res)
    else:
        print_red(jr)

def SwitchBank(bank_num):
    """

    Parameters
    ----------
    bank_num

    Returns
    -------
    Switch the internal guitar program to a specified bank
    """
    params = {"bank_num": int(bank_num)}
    jr = send_req("SwitchBank", params)
    if "result" in jr:
        res = jr["result"]
        print(res)
    else:
        print("ERROR got %s\n" % (json.dumps(jr)))

def SetGainBank(bank_num, gain):
    """

    Parameters
    ----------
    bank_num
    gain

    Returns
    -------
    Sets the gain of a bank
    """
    params = {"bank_num": int(bank_num), "gain":int(gain)}
    jr = send_req("SetGainBank", params)
    if "result" in jr:
        res = jr["result"]
        print(res)
    else:
        print("ERROR got %s\n" % (json.dumps(jr)))

def MoveEffect(bank_num, effect_num, effect_dest):
    """

    Parameters
    ----------
    bank_num
    effect_num
    effect_dest

    Returns
    -------
    Move an effect from a position to an other in a bank
    """
    params = {"bank_num": int(bank_num), "effect_num": int(effect_num), "effect_dest": int(effect_dest)}
    jr = send_req("MoveEffect", params)
    if "result" in jr:
        res = jr["result"]
        print(res)
    else:
        print("ERROR got %s\n" % (json.dumps(jr)))

def UpdateEffect(bank_num, effect_num, type, preset, params):
    """

    Parameters
    ----------
    bank_num
    effect_num
    type
    preset
    params

    Returns
    -------
    Update parameters of an effect (the number you want)
    """
    param = {"bank_num": int(bank_num), "effect_num": int(effect_num), "effect": {"type": type, "preset": preset, "params": params}}
    jr = send_req("UpdateEffect", param)
    if "result" in jr:
        res = jr["result"]
        print(res)
    else:
        print("ERROR got %s\n" % (json.dumps(jr)))

def RemoveEffect(bank_num, effect_num):
    """

    Parameters
    ----------
    bank_num
    effect_num

    Returns
    -------
    Remove an effect from a bank
    """
    params = {"bank_num": int(bank_num), "effect_num": int(effect_num)}
    jr = send_req("RemoveEffect", params)
    if "result" in jr:
        res = jr["result"]
        print(res)
    else:
        print("ERROR got %s\n" % (json.dumps(jr)))

def AddEffect(bank_num, type, preset, params):
    """

    Parameters
    ----------
    bank_num
    type
    preset
    params

    Returns
    -------
    Add an effect to a bank (append at the end of the list). Bypass and Preset can be ignored.
    """
    param = {"bank_num": int(bank_num), "effect": {"type": type, "preset": preset, "params": params}}
    jr = send_req("AddEffectt", param)
    if "result" in jr:
        res = jr["result"]
        print(res)
    else:
        print("ERROR got %s\n" % (json.dumps(jr)))

def SaveConfig():
    """

    Returns
    -------
    Save the current guitar configuration in memory. Return immediately, save is parallelized. No way to check if the save was successful.
    """
    jr = send_req("SaveConfig")
    if "result" in jr:
        res = jr["result"]
        print(res)
    else:
        print_red(jr)

def SustainKiller(bank_num, on, reset):
    """

    Parameters
    ----------
    bank_num
    on
    reset

    Returns
    -------
    Activate/Deactivate the sutstain killer for a bank. Can reset it too.
    """
    if on not in ["True", "False"]:
        print("Error method SustainKiller source %s unkown")
        return
    if reset not in ["True", "False"]:
        print("Error method SustainKiller source %s unkown")
        return
    params = {"bank_num": int(bank_num), "on": bool(on), "effect_dest": bool(reset)}
    jr = send_req("SustainKiller", params)
    if "result" in jr:
        res = jr["result"]
        print(res)
    else:
        print("ERROR got %s\n" % (json.dumps(jr)))

def TestGetAudioFile(source, file):
    """

    Parameters
    ----------
    source
    file

    Returns
    -------
    Sending a file audio and response an audio file
    """
    pygame.init()
    audio = pygame.mixer.Sound(file)
    audio.play()
    GetAudio(source)
    audio.stop()
    pygame.quit()

def TestGetAudio(source, taille_pulse):
    """

    Parameters
    ----------
    source
    taille_pulse

    Returns
    -------
    Sending a pulse and response an audio file
    """
    samples = np.zeros((88200,))
    for i in range(int(taille_pulse)):
        samples[2200+i] = 0.4
    low_pass_filter(samples)
    sd.play(samples, samplerate=44100)
    GetAudio(source)
    sd.wait()

def low_pass_filter(samples):
    """

    Parameters
    ----------
    samples

    Returns
    -------
    Filter samples
    """
    cutting_frequency = 15000
    order = 10
    normalized_frequency = cutting_frequency / (44100 / 2)
    b, a = butter(order, normalized_frequency, btype='low', analog=False, output='ba')
    filtered_samples = filtfilt(b, a, samples)
    samples[:] = filtered_samples

if method == "ping":
    ping()
elif method == "SetDate":
    SetDate()
elif method == "GetDate":
    GetDate()
elif method == "GetAudio":
    if len(option) != 1:
        usage()
    else:
        GetAudio(option[0])
elif method == "BMS":
    bms()
elif method == "GBF":
    if len(option) == 1 and option[0] == "stop":
        gbf(0, 0, "stop")
    elif len(option) == 3:
        gbf((float)(option[0]), (float)(option[1]), option[2])
    else:
        usage()
elif method == "GetLastLoop":
    get_last_loop()
elif method == "Meter":
    print("for exit press space and return ")
    meter(option[0], option[1])
elif method == "Temp":
    temp()
elif method == "DumpFile":
    if len(option) != 1:
        usage()
    else:
        DumpFile(option[0])
elif method == "GetGains":
    GetGain()
elif method == "SetGain":
    if len(option) == 0:
        usage()
    else:
        SetGain(option[0], option[1])
elif method == "ButUpdate":
    if len(option) < 6:
        usage()
    else:
        ButUpdate(option[0],option[1],option[2],option[3],option[4],option[5])
elif method == "TestCalibrate":
    if len(option) == 0:
        usage()
    else:
        TestCalibrate(option[0],option[1])
elif method == "ResponseSensorInput":
    if len(option) < 4:
        usage()
    else:
        ResponseSensorInput(option[0], option[1], option[2], option[3])
elif method == "TestMeter":
    if len(option) < 2:
        usage()
    else:
        TestMeter(option[0], option[1])
elif method == "StartMetronome":
    StartMetronome()
elif method == "StopMetronome":
    StopMetronome()
elif method == "UpdateMetronome":
    if len(option) < 4:
        usage()
    else:
        UpdateMetronome(option[0], option[1], option[2], option[3])
elif method == "ReadMetronome":
    ReadMetronome()
elif method == "TestGetAudioFile":
    if len(option) < 2:
        usage()
    else:
        TestGetAudioFile(option[0], option[1])
elif method == "TestGetAudio":
    if len(option) < 2:
        usage()
    else:
        TestGetAudio(option[0], option[1])
elif method == "AuxIn":
    AuxIn()
elif method == "AuxOut":
    AuxOut()
elif method == "Calibrate":
    Calibrate()
elif method == "BTcheck":
    BTcheck()
elif method == "ReadConfig":
    ReadConfig()
elif method == "GetStatus":
    GetStatus()
elif method == "StartTuner":
    StartTuner()
elif method == "StopTuner":
    StopTuner()
elif method == "GetFileInfo":
    if len(option) < 1:
        usage()
    else:
        GetFileInfo(option[0])
elif method == "GetCPU":
    GetCPU()
elif method == "SaveConfig":
    SaveConfig()
elif method == "SustainKiller":
    if len(option) < 3:
        usage()
    else:
        SustainKiller(option[0], option[1], option[2])
elif method == "RemoveEffect":
    if len(option) < 2:
        usage()
    else:
        RemoveEffect(option[0], option[1])
elif method == "AddEffect":
    if len(option) < 4:
        usage()
    else:
        AddEffect(option[0], option[1], option[2], option[3])
elif method == "SetGainBank":
    if len(option) < 2:
        usage()
    else:
        SetGainBank(option[0], option[1])
elif method == "SwitchBank":
    if len(option) < 1:
        usage()
    else:
        SwitchBank(option[0])
elif method == "FileRemove":
    if len(option) < 1:
        usage()
    else:
        FileRemove(option[0])
elif method == "PowampStatus":
    PowampStatus()
elif method == "McuReset":
    McuReset()
elif method == "RemoveBank":
    if len(option) < 1:
        usage()
    else:
        RemoveBank(option[0])
elif method == "ReadBank":
    if len(option) < 3:
        usage()
    else:
        ReadBank(option[0], option[1], option[2])
elif method == "SetBankName":
    if len(option) < 2:
        usage()
    else:
        SetBankName(option[0], option[1])
elif method == "SetController":
    if len(option) < 6:
        usage()
    else:
        SetController(option[0], option[1], option[2], option[3], option[4], option[5])
elif method == "MoveBank":
    if len(option) < 2:
        usage()
    else:
        MoveBank(option[0], option[1])
elif method == "StartRecording":
    StartRecording()
elif method == "StopRecording":
    StopRecording()
elif method == "StartRendering":
    StartRendering()
elif method == "StopRendering":
    StopRendering()
elif method == "SetEQBandGain":
    if len(option) < 2:
        usage()
    else:
        SetEQBandGain(option[0], option[1])
elif method == "SetEQGain":
    if len(option) < 1:
        usage()
    else:
        SetEQGain(option[0])
elif method == "GetDataRec":
    GetDataRec()
elif method == "AuxOutDryWets":
    if len(option) < 1:
        usage()
    else:
        AuxOutDryWet(option[0])
elif method == "AuxInDryWet":
    if len(option) < 1:
        usage()
    else:
        AuxInDryWet(option[0])
elif method == "PrintBank":
    if len(option) < 1:
        usage()
    else:
        PrintBank(option[0])
elif method == "BypassEffect":
    if len(option) < 3:
        usage()
    else:
        BypassEffect(option[0], option[1], option[2])
elif method == "SetPhaseInv":
    if len(option) < 1:
        usage()
    else:
        SetPhaseInv(option[0])
elif method == "ActivateSpkFilter":
    if len(option) < 1:
        usage()
    else:
        ActivateSpkFilter(option[0])
elif method == "LaunchCalibration":
    if len(option) < 5:
        usage()
    else:
        LaunchCalibration(option[0], option[1], option[2], option[3], option[4])
elif method == "UiLedDim":
    if len(option) < 3:
        usage()
    else:
        UiLedDim(option[0], option[1], option[2])
elif method == "UiEnableSet":
    if len(option) < 1:
        usage()
    else:
        UiEnableSet(option[0])
elif method == "UiScreenFill":
    if len(option) < 1:
        usage()
    else:
        UiScreenFill(option[0])
elif method == "TestMonostable":
    TestMonostable()
elif method == "TestChargerWakeup":
    TestChargerWakeup()
elif method == "PowerMode":
    PowerMode()
elif method == "UiMonitor":
    if len(option) < 1:
        usage()
    else:
        UiMonitor(option[0])
elif method == "RtaudioInGainSet":
    if len(option) < 1:
        usage()
    else:
        RtaudioInGainSet(option[0])
elif method == "RtaudioOutEnable":
    if len(option) < 2:
        usage()
    else:
        RtaudioOutEnable(option[0], option[1])
elif method == "FileUpload":
    if len(option) < 3:
        usage()
    else:
        FileUpload(option[0], option[1], option[2])
elif method == "SetSpeakerBiquads":
    if len(option) < 1:
        usage()
    else:
        SetSpeakerBiquads(option[0])
elif method == "GetLastRecordingName":
    GetLastRecordingName()
elif method == "AutoPowerOff":
    if len(option) < 1:
        usage()
    else:
        AutoPowerOff(option[0])
elif method == "GetFreeHeap":
    GetFreeHeap()
elif method == "GetSignalLevelsInRMS":
    GetSignalLevelsInRMS()
elif method == "MoveEffect":
    if len(option) < 3:
        usage()
    else:
        MoveEffect(option[0], option[1], option[2])
elif method == "UpdateEffect":
    if len(option) < 5:
        usage()
    else:
        UpdateEffect(option[0], option[1], option[2], option[3], option[4])


else:
    usage()

if mode_BLE:
    """
    stop connection by BLE
    """
    print("Closing BLE ")
    dev.write(str.encode("@stop\n")) 
    resp = dev.read_until()   
    print("got", resp)

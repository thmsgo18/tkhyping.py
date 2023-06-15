import tkinter as tk
import serial
import sys
import json
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np
from base64 import b64decode
import wave

color_red = "\x1b[31m"
color_green = "\x1b[32m"
color_reset = "\x1b[0m"

method = ""
argc = len(sys.argv)
mode_BLE = False


def usage():
    print("Usage : \nhyping [ble H2-UV196] /dev/ttyUSB0 [method] [option]")
    print("\tmethod :  SetDate | GetDate | GetAudio | BMS | GBF | GetLastLoop | Meter | Temp")
    print("\tmethod for BLE :  SetDate | GetDate | BMS | GBF | GetLastLoop | Meter | Temp")
    print("\toptions GetAudio :  sensor | codec | a2dp")
    print("\toptions GBF      :  <freq> & <amp> & start | stop  ex: hyping /dev/ttyUSB0 gbf 1000 0.7 start , hyping /dev/ttyUSB0 gbf stop")
    print("\toptions Meter    :  add | remove | get & input_level | output_level | mix_level | codec_in_level | bt_level")
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
    print("Device %s can not be found or can not be configured\n" % (dev))
    sys.exit()

if mode_BLE:
    """
    start connection by BLE
    """
    print("Connecting BLE to %s..." % (sys.argv[2]))
    dev.write(str.encode("@start %s\n" % (sys.argv[2])))
    resp = dev.read_until()
    print("got", resp)


def print_red(*args, **kwargs):
    print(color_red, end="")
    print(*args, **kwargs)
    print(color_reset, end="")

def print_green(*args, **kwargs):
    print(color_green, end="")
    print(*args, **kwargs)
    print(color_reset, end="")

def send_req(method, params=None):
    """
    Returns
    -------
    json or None

    Creation of jsonrpc
    """
    req = {"jsonrpc": "2.0", "method": method, "id": 1}
    if params:
        req["params"] = params
    es = str.encode(json.dumps(req) + '\n')
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
    params = {};
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
        print("Returned date %u/%u/%u %u:%u:%u\n" % (
        d["day"], d["month"], d["year"], d["hour"], d["minute"], d["second"]))
    else:
        print("ERROR got %s\n" % (json.dumps(jr)))

def GetAudio(source):
    audio = bytes()
    run = True
    if source not in ["sensor", "codec", "a2dp"]:
        print("Error method GetAudio source %s unkown")
        return
    if source == "sensor":
        source = "sensor_in"
    if source == "codec":
        source = "codec_in"
    params = {"target": "AudioSpl", "command": "Start", "source": source, "duration": 100};
    jr = send_req("GetInternals", params)
    while run:
        params = {"target": "AudioSpl", "command": "NextChunk"}
        jr = send_req("GetInternals", params)
        if "result" in jr:
            res = jr["result"]
            buff = b64decode(res["data"])
            print("received nb bytes=", len(buff));
            audio += buff
            run = not res["last_chunk"]
        elif "error" in jr:
            raise RuntimeError(jr["error"]["message"])
        else:
            raise RuntimeError("Bad response")

    with wave.open("audio_%s.wav" % (source), "wb") as wv:
        wv.setnchannels(1)
        wv.setsampwidth(2)
        wv.setframerate(44100)
        wv.writeframes(audio)

    audio_signed = np.frombuffer(audio, dtype=np.int16)
    plt.hist(audio_signed)
    plt.title("Noise density")
    plt.show()

    return np.frombuffer(audio, dtype=np.int16) / ((1 << 15) - 1)

def bms():
    reg_name = ["VSET", "CHGSET", "TIM", "STAT", "FAULT"]
    for reg in range(5):
        jr = send_req("bms.read.reg", reg)
        if "result" in jr:
            res = jr["result"]
            print(reg_name[reg], ": %02x" % res)

def gbf(freq, amp, onoff):
    print(freq, amp, onoff)
    if onoff == "start":
        params = {"target": "StartOsc", "f0": freq, "amp": amp}
        jr = send_req("SetInternals", params)
        if "result" in jr and jr["result"] == True:
            print("GBF set with success Freq =", freq, "Amp =", amp)
        else:
            print_red(jr)
    else:
        params = {"target": "StopOsc"};
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
        print_red("GetLastRecordingName ERROR got %s\n" % (json.dumps(jr)))
        return

    loopnbr = int(last_loop_path[11:15])
    if loopnbr > 0:
        loopnbr -= 1
    last_loop_path = "/Loops/loop%04d.wav" % (loopnbr)
    print("Dowloading", last_loop_path)
    audio = bytearray()
    run = True
    ofs = 0
    while run:
        params = {"name": last_loop_path, "offset": ofs, "size": 128};
        jr = send_req("DumpFile", params)
        if "result" in jr:
            buff = bytearray.fromhex(jr["result"])
            print("received nb bytes=", len(buff));
            rdlen = len(buff)  # /2 because 1 frame is 2 byte long
            audio += buff
            ofs += 128
            run = rdlen == 128
        elif "error" in jr:
            print_red("ERROR received :", jr["error"]["message"])
            break
        else:
            print_red("Bad response from device")
            break
    with open("audio.wav", "wb") as binary_file:
        binary_file.write(audio)

def meter(cde, meter):
    if cde == "add":
        target = "AddMeter"
    elif cde == "remove":
        target = "RemMeter"
    elif cde != "get":
        print_red("Bad option " + cde)
        return
    params = {"target": "RemoveBank", "name": "out"}
    jr = send_req("SetInternals", params)
    if "result" in jr and jr["result"] == True:
        print("EQ bank removed ok")
    else:
        print_red("Error trying to remove EQ bank")
    if cde in ["add", "remove"]:
        params = {"target": target, "name": meter}
        jr = send_req("SetInternals", params)
        if "result" in jr and jr["result"] == True:
            print("Meter", target, "done with success")
        else:
            print_red(jr)
    else:
        params = {"target": "Levels_dBfs"}
        jr = send_req("GetInternals", params)
        if jr is None:
            print_red("Error in send_req, probably a timeout")
        elif "result" in jr:
            res = jr["result"]
            print(res[meter])
        else:
            print_red(jr)

def temp():
    """
    Returns
    -------
    None.

    Request the temperature
    """
    params = {"target": "Temp"}
    jr = send_req("GetInternals", params)
    if jr is None:
        print_red("Error in send_req, probably a timeout")
    elif "result" in jr:
        res = jr["result"]
        print_green("CPU Temperature :", res["temperature"])
    else:
        print_red(jr)

def who_fonction():
    if method == "ping":
        ping()
    elif method == "SetDate":
        SetDate();
    elif method == "GetDate":
        GetDate();
    elif method == "GetAudio":
        if len(option) != 1:
            usage()
        else:
            GetAudio(option[0]);
    elif method == "BMS":
        bms();
    elif method == "GBF":
        if len(option) == 1 and option[0] == "stop":
            gbf(0, 0, "stop");
        elif len(option) == 3:
            gbf((float)(option[0]), (float)(option[1]), option[2]);
        else:
            usage()
    elif method == "GetLastLoop":
        get_last_loop()
    elif method == "Meter":
        meter(option[0], option[1])
    elif method == "Temp":
        temp()
    else:
        usage();

who_fonction()

fenetre = tk.Tk()
fenetre.title("Menu")
valeur_selectionnee = tk.StringVar()
method = tk.StringVar()
option = tk.StringVar()

def selection_Noneoption():
    def run_window():
        fenetre_lancement.destroy()
        who_fonction()
    fenetre_lancement = tk.Tk()
    fenetre_lancement.title("Run")
    button_quit = tk.Button(fenetre_lancement, text="Send", command=run_window)
    button_quit.pack()

def selection_Withoption():
    choix = valeur_selectionnee.get()
    print(choix)
    print(type(choix))
    fenetre_lancement = tk.Tk()
    fenetre_lancement.title("Options")
    if choix=="gdf":
        def option():
            try:
                freq = float(entry_option1.get())
                amp = float(entry_option2.get())
            except ValueError:
                label_run.config(text="Veuillez saisir des nombres valides.")

        label_option1 = tk.Label(fenetre_lancement, text="freq:")
        label_option1.pack()

        entry_option1 = tk.Entry(fenetre_lancement)
        entry_option1.pack()

        label_option2 = tk.Label(fenetre_lancement, text="amp:")
        label_option2.pack()

        entry_option2 = tk.Entry(fenetre_lancement)
        entry_option2.pack()

        button_calculate = tk.Button(fenetre_lancement, text="Send", command=option)
        button_calculate.pack()

        label_run = tk.Label(fenetre_lancement)
        label_run.pack()

label = tk.Label(fenetre, text="BT id:")
label.pack()

zone_texte = tk.Text(fenetre, height=1, width=9)
zone_texte.pack()


bouton_ping = tk.Radiobutton(fenetre, text="Ping", variable=valeur_selectionnee, value="ping", command=selection_Noneoption)
bouton_ping.pack()

bouton_setdate = tk.Radiobutton(fenetre, text="SetDate", variable=valeur_selectionnee, value="setdate", command=selection_Noneoption)
bouton_setdate.pack()

bouton_guetdate = tk.Radiobutton(fenetre, text="GuetDate", variable=valeur_selectionnee, value="guetdate", command=selection_Noneoption)
bouton_guetdate.pack()

bouton_guetaudio = tk.Radiobutton(fenetre, text="GuetAudio", variable=valeur_selectionnee, value="guetaudio", command=selection_Withoption)
bouton_guetaudio.pack()

bouton_bms = tk.Radiobutton(fenetre, text="BMS", variable=valeur_selectionnee, value="bms", command=selection_Noneoption)
bouton_bms.pack()

bouton_gdf = tk.Radiobutton(fenetre, text="GDF", variable=valeur_selectionnee, value="gdf", command=selection_Withoption)
bouton_gdf.pack()

bouton_get_last_loop = tk.Radiobutton(fenetre, text="Get last loop", variable=valeur_selectionnee, value="get_last_loop", command=selection_Noneoption)
bouton_get_last_loop.pack()

bouton_meter = tk.Radiobutton(fenetre, text="Meter", variable=valeur_selectionnee, value="meter", command=selection_Withoption)
bouton_meter.pack()

bouton_temp = tk.Radiobutton(fenetre, text="Temp", variable=valeur_selectionnee, value="temp", command=selection_Noneoption)
bouton_temp.pack()

fenetre.mainloop()

if mode_BLE:
    """
    stop connection by BLE
    """
    print("Closing BLE ")
    dev.write(str.encode("@stop\n"))
    resp = dev.read_until()
    print("got", resp)

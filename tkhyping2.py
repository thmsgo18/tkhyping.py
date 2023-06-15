import serial
import sys
import json
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np
from base64 import b64decode
import wave
import os
import select
import time
import sounddevice as sd
import pygame
from scipy.signal import butter, filtfilt
import tkinter as tk
import inspect
from tkinter import ttk, simpledialog

mode_BLE = False

class methode :

    def print_texte_indentation(self, texte, level_indentation):
        indentation = " " * level_indentation
        texte_with_indentation = indentation + texte
        print(texte_with_indentation)

    def is_space_pressed(self):
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

    def send_req(self, method, params=None):
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

    def Ping(self):
        """
        Returns
        -------
        None.

        Connection test send ping and the system return pong
        """
        jr = self.send_req("ping")
        if "result" in jr and jr["result"] == "pong":
            return("OK device returned pong\n")
        else:
            return("ERROR got", json.dumps(jr))

    def SetDate(self):
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
        jr = self.send_req("SetDate", params)
        if "result" in jr and jr["result"] == True:
            return("OK device returned True\n")
        else:
            return("ERROR got %s\n", json.dumps(jr))

    def GetDate(self):
        """
        Returns
        -------
        None.

        Request the date and the clock
        """
        jr = self.send_req("GetDate")
        if "result" in jr:
            d = jr["result"]
            return("Returned date %u/%u/%u %u:%u:%u\n" % (
                d["day"], d["month"], d["year"], d["hour"], d["minute"], d["second"]))
        else:
            return("ERROR got %s\n" % (json.dumps(jr)))

    def GetAudio(self, source):
        audio = bytes()
        run = True
        if source not in ["sensor", "codec", "a2dp", "output"]:
            return("Error method GetAudio source %s unkown")
        if source == "sensor":
            source = "sensor_in"
        if source == "codec":
            source = "codec_in"
        params = {"target": "AudioSpl", "command": "Start", "source": source, "duration": 2000}
        jr = self.send_req("GetInternals", params)
        while run:
            params = {"target": "AudioSpl", "command": "NextChunk"}
            jr = self.send_req("GetInternals", params)
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

    def BMS(self):
        reg_name = ["VSET", "CHGSET", "TIM", "STAT", "FAULT"]
        for reg in range(5):
            jr = self.send_req("bms.read.reg", reg)
            if "result" in jr:
                res = jr["result"]
                return(reg_name[reg], ": %02x" % res)

    def GBF(self, freq, amp, onoff):
        print(freq, amp, onoff)
        if onoff == "start":
            params = {"target": "StartOsc", "f0": freq, "amp": amp}
            jr = self.send_req("SetInternals", params)
            if "result" in jr and jr["result"] == True:
                return("GBF set with success Freq =", freq, "Amp =", amp)
            else:
                return(jr)
        else:
            params = {"target": "StopOsc"}
            jr = self.send_req("SetInternals", params)
            if "result" in jr and jr["result"] == True:
                return("GBF stopped with success")

    def Get_last_loop(self):
        """
        Returns
        -------
        None.

        Request the last loop
        """
        jr = self.send_req("GetLastRecordingName")
        if "result" in jr:
            last_loop_path = jr["result"]
        else:
            return("GetLastRecordingName ERROR got %s\n" % (json.dumps(jr)))

        loopnbr = int(last_loop_path[11:15])
        if loopnbr > 0:
            loopnbr -= 1
        last_loop_path = "/Loops/loop%04d.wav" % (loopnbr)
        print("Dowloading", last_loop_path)
        audio = bytearray()
        run = True
        ofs = 0
        while run:
            params = {"name": last_loop_path, "offset": ofs, "size": 128}
            jr = self.send_req("DumpFile", params)
            if "result" in jr:
                buff = bytearray.fromhex(jr["result"])
                print("received nb bytes=", len(buff))
                rdlen = len(buff)  # /2 because 1 frame is 2 byte long
                audio += buff
                ofs += 128
                run = rdlen == 128
            elif "error" in jr:
                return("ERROR received :", jr["error"]["message"])
            else:
                return("Bad response from device")
        with open("audio.wav", "wb") as binary_file:
            binary_file.write(audio)

    def Meter(self, cde, meter, test=False):
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
            return("Bad option " + cde)
        params = {"target": "RemoveBank", "name": "out"}
        jr = self.send_req("SetInternals", params)
        if "result" in jr and jr["result"] == True:
            print("EQ bank removed ok")
        else:
            return("Error trying to remove EQ bank")
        if cde in ["add", "remove"]:
            params = {"target": target, "name": meter, "time_constant": 0.1}
            jr = self.send_req("SetInternals", params)
            if "result" in jr and jr["result"] == True:
                return("Meter", target, "done with success")
            else:
                return(jr)
        else:
            while True:
                params = {"target": "Levels_dBfs"}
                jr = self.send_req("GetInternals", params)
                if jr is None:
                    return("Error in send_req, probably a timeout")
                elif "result" in jr:
                    res = jr["result"]
                    print("\t", res[meter], end='\r')
                    time.sleep(0.1)
                    if test == True:
                        return res[meter]
                    if self.is_space_pressed():
                        break
                else:
                    return(jr)

    def DumpFile(self, name):
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
        i = True
        counter = 0
        file_path = os.path.join(os.getcwd(), name)
        with open(file_path, "w") as fichier:
            pass
        while i == True:
            params = {"name": name, "offset": counter * size, "size": size}
            jr = self.send_req("DumpFile", params)
            counter += 1
            if "result" in jr:
                data = jr["result"]
                size_data = len(data)
                bytes_object = bytes.fromhex(data)
                text = bytes_object.decode("utf-8")
                with open(file_path, "a") as fichier:
                    fichier.write(text)
                if size_data < (size * 2):
                    i = False
                else:
                    i = True
            else:
                i = False

    def GetGain(self):
        """

        Returns
        -------
        Request all the gain (gain_master | gain_preamp | gain_air | gain_wire_out | gain_wire_in | gain_looper)
        """
        params = {"target": "Gains"}
        jr = self.send_req("Getinternals", params)
        if "result" in jr:
            d = jr["result"]
            return ("Returned Gains : gain_master =", d["gain_preamp"], "gain_air =", d["gain_air"], "gain_wire_out =", d["gain_wire_out"], "gain_wire_in =", d["gain_wire_in"], "gain_looper =", d["gain_looper"])
        else:
            return("ERROR got %s\n" % (json.dumps(jr)))

    def SetGain(self, name, value):
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
            jr = self.send_req("SetInternals", params)
            if "result" in jr:
                return(name, "set with success value =", value)
            else:
                return(jr)

        testvalue = int(value)
        if name == "gain_master":
            if 0 <= testvalue <= 1:
                run(name, value)
            else:
                print("value out of range")
        elif name == "gain_preamp":
            if -96 <= testvalue <= 0:
                run(name, value)
            else:
                print("value out of range")
        elif name == "gain_air":
            if 0 <= testvalue <= 1:
                run(name, value)
            else:
                print("value out of range")
        elif name == "gain_wire_out":
            if -45 <= testvalue <= 4.5:
                run(name, value)
            else:
                print("value out of range")
        elif name == "gain_wire_in":
            if 0 <= testvalue <= 1:
                run(name, value)
            else:
                print("value out of range")
        else:
            if 0 <= testvalue <= 1:
                run(name, value)
            else:
                print("value out of range")

    def Temp(self):
        """
        Returns
        -------
        None.

        Request the temperature
        """
        params = {"target": "Temp"}
        jr = self.send_req("GetInternals", params)
        if jr is None:
            return("Error in send_req, probably a timeout")
        elif "result" in jr:
            res = jr["result"]
            return("CPU Temperature :", res["temperature"])
        else:
            return(jr)

    def ButUpdate(self, Bt1, Bt2, Bt3, Bt4, Pot1, Pot2):
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
        if ((0 == int(Bt1)) or (1 == int(Bt1))) and ((0 == int(Bt2)) or (1 == int(Bt2))) and (
                (0 == int(Bt3)) or (1 == int(Bt3))) and ((0 == int(Bt4)) or (1 == int(Bt4))) and (
                0 <= int(Pot1) <= 100) and (0 <= int(Pot1) <= 100):
            params = {"Bt1": Bt1, "Bt2": Bt2, "Bt3": Bt3, "Bt4": Bt4, "Pot1": Pot1, "Pot2": Pot2}
            jr = self.send_req("ButUpdate", params)
        else:
            return("value out of range")

    def TestCalibrate(self, freq, amplitude, test=False):
        self.SetGain("gain_preamp", "0")
        self.Meter("add", "input_level")
        frequency = int(freq)
        duration = 0.5
        amplitude_db = int(amplitude)
        amplitude_linear = 10 ** (amplitude_db / 20)
        samples = np.sin(2 * np.pi * frequency * np.linspace(0, duration, int(duration * 44100)))
        samples *= amplitude_linear
        sd.play(samples, samplerate=44100)
        time.sleep(0.2)
        val = int(self.Meter("get", "input_level", True))
        sd.wait()
        difference = abs(amplitude_db) - abs(val)
        if test == False:
            if val >= -1:
                print("son trop fort")
                return False
            elif val <= -30:
                print("son trop faible")
                return False
            else:
                print("valeur en db capté", val)
                print("difference avec la valeur envoyer ", difference)
        else:
            return difference
        self.Meter("remove", "input_level")

    def ResponseSensorInput(self, amplitude, freq_start, freq_end, number_point):
        if -60 <= int(amplitude) <= 0:
            difference = self.TestCalibrate(100, -20, True)
            self.Meter("add", "input_level")
            print(difference)
            self.SetGain("gain_preamp", "0")
            real_amplitude = int(amplitude) + difference
            step = (int(freq_end) / int(freq_start)) ** (1 / int(number_point))
            i = int(freq_start)
            result = []
            duration = 0.5
            amplitude_linear = 10 ** (real_amplitude / 20)
            while i <= int(freq_end):
                samples = np.sin(2 * np.pi * i * np.linspace(0, duration, int(duration * 44100)))
                samples *= amplitude_linear
                sd.play(samples, samplerate=44100)
                time.sleep(0.2)
                val = self.Meter("get", "input_level", True)
                sd.wait()
                result.append(val)
                i = i * step
            self.Meter("remove", "input_level")
            abscissa = np.logspace(freq_start, freq_end, number_point)
            plt.plot(abscissa, result)
            plt.show()

    def TestMeter(self, amplitude, freq):
        self.Meter("add", "input_level")
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
            val = int(self.Meter("get", "input_level", True))
            result.append(val)
        sd.wait()
        return("result : ", result,"le maximum est :", max(result), "et le minimum est :", min(result))

    def StartMetronome(self):
        """

        Returns
        -------
        Start the Metronome
        """
        jr = self.send_req("StartMetronome")
        if "result" in jr:
            res = jr["result"]
            return(res)
        else:
            return("ERROR got %s\n" % (json.dumps(jr)))

    def StopMetronome(self):
        """

        Returns
        -------
        Stop the Metronome
        """
        jr = self.send_req("StopMetronome")
        if "result" in jr:
            res = jr["result"]
            return(res)
        else:
            return("ERROR got %s\n" % (json.dumps(jr)))

    def UpdateMetronome(self, bpm, num, den, nbbars):
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
        jr = self.send_req("UpdateMetronome", params)
        if "result" in jr:
            res = jr["result"]
            return(res)
        else:
            return("ERROR got %s\n" % (json.dumps(jr)))

    def ReadMetronome(self):
        """

        Returns
        -------
        Request the values of the Metronome
        """
        jr = self.send_req("ReadMetronome")
        if "result" in jr:
            res = jr["result"]
            return(res)
        else:
            return("ERROR got %s\n" % (json.dumps(jr)))

    def MoveBank(self, src, dst):
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
        jr = self.send_req("MoveBank", params)
        if "result" in jr:
            res = jr["result"]
            return(res)
        else:
            return("ERROR got %s\n" % (json.dumps(jr)))

    def RemoveBank(self, bank_num):
        """

        Parameters
        ----------
        bank_num

        Returns
        -------
        Remove a bank
        """
        params = {"bank_num": int(bank_num)}
        jr = self.send_req("RemoveBank", params)
        if "result" in jr:
            res = jr["result"]
            return(res)
        else:
            return("ERROR got %s\n" % (json.dumps(jr)))

    def ReadBank(self, bank_num, offset, size):
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
        jr = self.send_req("ReadBank", params)
        if "result" in jr:
            res = jr["result"]
            return(res)
        else:
            return("ERROR got %s\n" % (json.dumps(jr)))

    def SetBankName(self, bank_num, name):
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
        jr = self.send_req("SetBankName", params)
        if "result" in jr:
            res = jr["result"]
            return(res)
        else:
            return("ERROR got %s\n" % (json.dumps(jr)))

    def SetController(self, bank_num, effect_num, parameter, source, minimum, maximum):
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
        params = {"bank_num": int(bank_num), "effect_num": int(effect_num), "parameter": parameter, "source": source,
                  "min": minimum, "max": maximum}
        jr = self.send_req("SetController", params)
        if "result" in jr:
            res = jr["result"]
            return(res)
        else:
            return("ERROR got %s\n" % (json.dumps(jr)))

    def Calibrate(self):
        """

        Returns
        -------
        Start a calibration
        """
        jr = self.send_req("Calibrate")
        if "result" in jr:
            res = jr["result"]
            return(res)
        else:
            return("ERROR got %s\n" % (json.dumps(jr)))

    def StartRecording(self):
        """

        Returns
        -------
        Start audio recording (free set to false when looper activated)
        """
        params = {"free": True}
        jr = self.send_req("StartRecording", params)
        if "result" in jr:
            res = jr["result"]
            return(res)
        else:
            return("ERROR got %s\n" % (json.dumps(jr)))

    def StopRecording(self):
        """

        Returns
        -------
        Stop audio recording
        """
        jr = self.send_req("StopRecording")
        if "result" in jr:
            res = jr["result"]
            return(res)
        else:
            return("ERROR got %s\n" % (json.dumps(jr)))

    def StartRendering(self):
        """

        Returns
        -------
        Start audio rendering
        """
        jr = self.send_req("StartRendering")
        if "result" in jr:
            res = jr["result"]
            return(res)
        else:
            return("ERROR got %s\n" % (json.dumps(jr)))

    def StopRendering(self):
        """

        Returns
        -------
        Stop audio rendering

        """
        jr = self.send_req("StopRendering")
        if "result" in jr:
            res = jr["result"]
            return(res)
        else:
            return("ERROR got %s\n" % (json.dumps(jr)))

    def SetEQBandGain(self, band, gain):
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
        jr = self.send_req("SetEQBandGain", params)
        if "result" in jr:
            res = jr["result"]
            return(res)
        else:
            return("ERROR got %s\n" % (json.dumps(jr)))

    def SetEQGain(self, gain):
        """

        Parameters
        ----------
        gain

        Returns
        -------
        Set the gain of the main EQ
        """
        params = {"gain": float(gain)}
        jr = self.send_req("SetEQGain", params)
        if "result" in jr:
            res = jr["result"]
            return(res)
        else:
            return("ERROR got %s\n" % (json.dumps(jr)))

    def GetStatus(self):
        """

        Returns
        -------
        Get the free space in GB, free space in %, battery status in %, versions and cpuid
        """
        jr = self.send_req("GetStatus")
        if "result" in jr:
            res = jr["result"]
            return(res)
        else:
            return("ERROR got %s\n" % (json.dumps(jr)))

    def GetDataRec(self):
        jr = self.send_req("GetDataRec")
        if "result" in jr:
            res = jr["result"]
            return(res)
        else:
            return("ERROR got %s\n" % (json.dumps(jr)))

    def AuxOut(self):
        """

        Returns
        -------
        Turns aux out on & off
        """
        params = {"on": False}
        jr = self.send_req("AuxOut", params)
        if "result" in jr:
            res = jr["result"]
            return(res)
        else:
            return("ERROR got %s\n" % (json.dumps(jr)))

    def AuxIn(self):
        """

        Returns
        -------
        Turns aux in on & off
        """
        params = {"on": False}
        jr = self.send_req("AuxIn", params)
        if "result" in jr:
            res = jr["result"]
            return(res)
        else:
            return("ERROR got %s\n" % (json.dumps(jr)))

    def AuxOutDryWet(self, value):
        """

        Parameters
        ----------
        value

        Returns
        -------
        Changes the value of the aux out dry/wet

        """
        params = {"value": float(value)}
        jr = self.send_req("AuxOutDryWet", params)
        if "result" in jr:
            res = jr["result"]
            return(res)
        else:
            return("ERROR got %s\n" % (json.dumps(jr)))

    def AuxInDryWet(self, value):
        """

        Parameters
        ----------
        value

        Returns
        -------
        Changes the value of the aux in dry/wet
        """
        params = {"value": float(value)}
        jr = self.send_req("AuxInDryWet", params)
        if "result" in jr:
            res = jr["result"]
            return(res)
        else:
            return("ERROR got %s\n" % (json.dumps(jr)))

    def BTcheck(self):
        """

        Returns
        -------
        Handshake the guitar. Can be used to test the connection.
        """
        jr = self.send_req("BTcheck")
        if "result" in jr:
            res = jr["result"]
            return(res)
        else:
            return("ERROR got %s\n" % (json.dumps(jr)))

    def PrintBank(self, bank_num):
        """

        Parameters
        ----------
        bank_num

        Returns
        -------
        Print a bank content (debug)
        """
        params = {"bank_num": int(bank_num)}
        jr = self.send_req("PrintBank", params)
        if "result" in jr:
            res = jr["result"]
            return(res)
        else:
            return("ERROR got %s\n" % (json.dumps(jr)))

    def ReadConfig(self):
        """

        Returns
        -------
        Read and return the current config
        """
        jr = self.send_req("ReadConfig")
        if "result" in jr:
            res = jr["result"]
            return(res)
        else:
            return("ERROR got %s\n" % (json.dumps(jr)))

    def BypassEffect(self, bank_num, effect_num, bypass):
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
        jr = self.send_req("BypassEffect", params)
        if "result" in jr:
            res = jr["result"]
            return(res)
        else:
            return("ERROR got %s\n" % (json.dumps(jr)))

    def SetPhaseInv(self, value):
        """

        Parameters
        ----------
        value

        Returns
        -------
        Set the phase inverter
        """
        params = {"value": int(value)}
        jr = self.send_req("SetPhaseInv", params)
        if "result" in jr:
            res = jr["result"]
            return(res)
        else:
            return("ERROR got %s\n" % (json.dumps(jr)))

    def StartTuner(self):
        """

        Returns
        -------
        Start the Tuner in the guitar
        """
        jr = self.send_req("StartTuner")
        if "result" in jr:
            res = jr["result"]
            return(res)
        else:
            return("ERROR got %s\n" % (json.dumps(jr)))

    def StopTuner(self):
        """

        Returns
        -------
        Stop the Tuner in the guitar
        """
        jr = self.send_req("StopTuner")
        if "result" in jr:
            res = jr["result"]
            return(res)
        else:
            return("ERROR got %s\n" % (json.dumps(jr)))

    def ActivateSpkFilter(self, value):
        """

        Parameters
        ----------
        value

        Returns
        -------
        Activate or deactivate the calibration
        """
        params = {"value": int(value)}
        jr = self.send_req("ActivateSpkFilter", params)
        if "result" in jr:
            res = jr["result"]
            return(res)
        else:
            return("ERROR got %s\n" % (json.dumps(jr)))

    def LaunchCalibration(self, amp, f0, f1, mode, feedback):
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
        jr = self.send_req("LaunchCalibration", params)
        if "result" in jr:
            res = jr["result"]
            return(res)
        else:
            return("ERROR got %s\n" % (json.dumps(jr)))

    def GetFileInfo(self, name):
        """

        Parameters
        ----------
        name

        Returns
        -------
        Return size and crc32 of a file
        """
        params = {"name": name}
        jr = self.send_req("GetFileInfo", params)
        if "result" in jr:
            res = jr["result"]
            return(res)
        elif "error" in jr:
            res = jr["error"]
            return(res)
        else:
            return("ERROR got %s\n" % (json.dumps(jr)))

    def FileRemove(self, name):
        """

        Parameters
        ----------
        name

        Returns
        -------
        Remove a file from the emmc flash
        """
        params = {"name": name}
        jr = self.send_req("FileRemove", params)
        if "result" in jr:
            res = jr["result"]
            return(res)
        else:
            return("ERROR got %s\n" % (json.dumps(jr)))

    def PowampStatus(self):
        """
        NONE ACTIVATE IN THE H2
        Returns
        -------
        Returns current powamp's status
        """
        jr = self.send_req("powamp.status")
        if "result" in jr:
            res = jr["result"]
            return(res)
        else:
            return("ERROR got %s\n" % (json.dumps(jr)))

    def UiLedDim(self, led_up, led_middle, led_down):
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
        if (0 <= int(led_up) <= 100) and (0 <= int(led_middle) <= 100) and (0 <= int(led_down) <= 100):
            params = {"led_up": int(led_up), "led_middle": int(led_up), "led_down": int(led_down)}
            jr = self.send_req("ui.led.dim", params)
            if "result" in jr:
                res = jr["result"]
                return(res)
            else:
                return("ERROR got %s\n" % (json.dumps(jr)))

    def UiEnableSet(self, params):
        """

        Parameters
        ----------
        params

        Returns
        -------
        Enable or disable the physical buttons, when disabled pressing buttons or encoder
           or turning encoder does nothing on the menus. But ui.monitor works.
        """
        if (params == "True"):
            jr = self.send_req("ui.enable.set", True)
            if "result" in jr:
                res = jr["result"]
                return(res)
            else:
                return("ERROR got %s\n" % (json.dumps(jr)))
        elif (params == "False"):
            jr = self.send_req("ui.enable.set", False)
            if "result" in jr:
                res = jr["result"]
                return(res)
            else:
                return("ERROR got %s\n" % (json.dumps(jr)))

    def UiScreenFill(self, action, color=0):
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
            jr = self.send_req("ui.screen.fill", params)
            if "result" in jr:
                res = jr["result"]
                return(res)
            else:
                return("ERROR got %s\n" % (json.dumps(jr)))
        elif action == "fill":
            params = {"action": action, "color": int(color)}
            jr = self.send_req("ui.screen.fill", params)
            if "result" in jr:
                res = jr["result"]
                return(res)
            else:
                return("ERROR got %s\n" % (json.dumps(jr)))

    def TestMonostable(self):
        """

        Returns
        -------
        Read the internal RTC
        """
        jr = self.send_req("testMonostable")
        if "result" in jr:
            res = jr["result"]
            return(res)
        else:
            return("ERROR got %s\n" % (json.dumps(jr)))

    def TestChargerWakeup(self):
        """

        Returns
        -------
        Read the internal RTC
        """
        jr = self.send_req("testChargerWakeup")
        if "result" in jr:
            res = jr["result"]
            return(res)
        else:
            return("ERROR got %s\n" % (json.dumps(jr)))

    def PowerMode(self):
        """

        Returns
        -------
        Read the internal RTC
        """
        jr = self.send_req("powerMode")
        if "result" in jr:
            res = jr["result"]
            return(res)
        else:
            return("ERROR got %s\n" % (json.dumps(jr)))

    def UiMonitor(self, time):
        """

        Parameters
        ----------
        time

        Returns
        -------
        Start the monitoring of the UI buttons and encoder for the time passed in params
        """
        jr = self.send_req("ui.monitor", time)
        if "result" in jr:
            res = jr["result"]
            if res == False:
                return("Nothing is touched on UI, after the time given")
            else:
                return(res)
        else:
            return("ERROR got %s\n" % (json.dumps(jr)))

    def McuReset(self):
        jr = self.send_req("mcu.reset")
        if "result" in jr:
            res = jr["result"]
            return(res)
        else:
            return("ERROR got %s\n" % (json.dumps(jr)))

    def RtaudioInGainSet(self, params):
        """

        Parameters
        ----------
        params

        Returns
        -------
        Sets the gain of the sensor input
        """
        if -96 <= int(params) <= 0:
            jr = self.send_req("rtaudio.in.gain.set")
            if "result" in jr:
                res = jr["result"]
                return(res)
            else:
                return("ERROR got %s\n" % (json.dumps(jr)))

    def RtaudioOutEnable(self, left, right):
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
        jr = self.send_req("rtaudio.out.gain.set", params)
        if "result" in jr:
            res = jr["result"]
            return(res)
        else:
            return("ERROR got %s\n" % (json.dumps(jr)))

    def FileUpload(self, file_path, status, data):
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
        params = {"file_path": file_path, "status": status, "data": data}
        jr = self.send_req("file.upload", params)
        if "result" in jr:
            res = jr["result"]
            return(res)
        else:
            return("ERROR got %s\n" % (json.dumps(jr)))

    def SetSpeakerBiquads(self, params):
        """

        Parameters
        ----------
        params

        Returns
        -------
        Set the calibration biquads
        """
        jr = self.send_req("SetSpeakerBiquads", params)
        if "result" in jr:
            res = jr["result"]
            return(res)
        else:
            return("ERROR got %s\n" % (json.dumps(jr)))

    def GetLastRecordingName(self):
        """

        Returns
        -------
        Get the last recording name
        """
        jr = self.send_req("GetLastRecordingName", )
        if "result" in jr:
            res = jr["result"]
            return(res)
        else:
            return("ERROR got %s\n" % (json.dumps(jr)))

    def AutoPowerOff(self, value):
        params = {"target": "AutoPowerOff", "value": bool(value)}
        jr = self.send_req("SetInternal", params)
        if "result" in jr:
            res = jr["result"]
            return(res)
        else:
            return("ERROR got %s\n" % (json.dumps(jr)))

    def GetCPU(self):
        """

        Returns
        -------
        Get CPU usage in %
        """
        params = {"target": "CPU"}
        jr = self.send_req("GetInternals", params)
        if "result" in jr:
            res = jr["result"]
            return("CPU usage :", res["cpu"], "%")
        else:
            return(jr)

    def GetFreeHeap(self):
        """

        Returns
        -------
        Get free Heap
        """
        params = {"target": "Heap"}
        jr = self.send_req("GetInternals", params)
        if "result" in jr:
            res = jr["result"]
            return(res)
        else:
            return(jr)

    def GetSignalLevelsInRMS(self):
        """

        Returns
        -------
        Get signal levels in RMS
        """
        params = {"target": "Levels_rms"}
        jr = self.send_req("GetInternals", params)
        if "result" in jr:
            res = jr["result"]
            return(res)
        else:
            return(jr)

    def SwitchBank(self, bank_num):
        """

        Parameters
        ----------
        bank_num

        Returns
        -------
        Switch the internal guitar program to a specified bank
        """
        params = {"bank_num": int(bank_num)}
        jr = self.send_req("SwitchBank", params)
        if "result" in jr:
            res = jr["result"]
            return(res)
        else:
            return("ERROR got %s\n" % (json.dumps(jr)))

    def SetGainBank(self, bank_num, gain):
        """

        Parameters
        ----------
        bank_num
        gain

        Returns
        -------
        Sets the gain of a bank
        """
        params = {"bank_num": int(bank_num), "gain": int(gain)}
        jr = self.send_req("SetGainBank", params)
        if "result" in jr:
            res = jr["result"]
            return(res)
        else:
            return("ERROR got %s\n" % (json.dumps(jr)))

    def MoveEffect(self, bank_num, effect_num, effect_dest):
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
        jr = self.send_req("MoveEffect", params)
        if "result" in jr:
            res = jr["result"]
            return(res)
        else:
            return("ERROR got %s\n" % (json.dumps(jr)))

    def UpdateEffect(self, bank_num, effect_num, type, preset, params):
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
        param = {"bank_num": int(bank_num), "effect_num": int(effect_num),
                 "effect": {"type": type, "preset": preset, "params": params}}
        jr = self.send_req("UpdateEffect", param)
        if "result" in jr:
            res = jr["result"]
            return(res)
        else:
            return("ERROR got %s\n" % (json.dumps(jr)))

    def RemoveEffect(self, bank_num, effect_num):
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
        jr = self.send_req("RemoveEffect", params)
        if "result" in jr:
            res = jr["result"]
            return(res)
        else:
            return("ERROR got %s\n" % (json.dumps(jr)))

    def AddEffect(self, bank_num, type, preset, params):
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
        jr = self.send_req("AddEffectt", param)
        if "result" in jr:
            res = jr["result"]
            return(res)
        else:
            return("ERROR got %s\n" % (json.dumps(jr)))

    def SaveConfig(self):
        """

        Returns
        -------
        Save the current guitar configuration in memory. Return immediately, save is parallelized. No way to check if the save was successful.
        """
        jr = self.send_req("SaveConfig")
        if "result" in jr:
            res = jr["result"]
            return(res)
        else:
            return(jr)

    def SustainKiller(self, bank_num, on, reset):
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
            return("Error method SustainKiller source %s unkown")
        if reset not in ["True", "False"]:
            return("Error method SustainKiller source %s unkown")
        params = {"bank_num": int(bank_num), "on": bool(on), "effect_dest": bool(reset)}
        jr = self.send_req("SustainKiller", params)
        if "result" in jr:
            res = jr["result"]
            return(res)
        else:
            return("ERROR got %s\n" % (json.dumps(jr)))

    def TestGetAudioFile(self, source, file):
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
        self.GetAudio(source)
        audio.stop()
        pygame.quit()

    def TestGetAudio(self, source, taille_pulse):
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
            samples[2200 + i] = 0.4
        self.low_pass_filter(samples)
        sd.play(samples, samplerate=44100)
        self.GetAudio(source)
        sd.wait()

    def low_pass_filter(self, samples):
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

    def run_methode(self, name_fonction, *args):
        if hasattr(self, name_fonction):
            method = getattr(self, name_fonction)
            method(*args)

class GUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Run Method")
        self.my_object = methode()
        self.method_var = tk.StringVar()

        self.method_label = ttk.Label(self.root, text="Which method :")
        self.method_label.pack()

        self.method_combobox = ttk.Combobox(self.root, textvariable=self.method_var)
        self.method_combobox.pack()

        self.execute_button = ttk.Button(self.root, text="Run", command=self.execute_method)
        self.execute_button.pack()

        self.quitter_button = tk.Button(self.root, text="Quit", command=self.root.quit)
        self.quitter_button.pack()

        self.result_label = ttk.Label(self.root, text="Result :")
        self.result_label.pack()

        self.result_text = tk.Text(self.root, height=8, width=30)
        self.result_text.pack()

        self.populate_combobox()

    def populate_combobox(self):
        methods = inspect.getmembers(self.my_object, predicate=inspect.ismethod)
        method_names = [name for name, _ in methods]
        self.method_combobox["values"] = method_names

    def execute_method(self):
        method_name = self.method_combobox.get()
        print(method_name)
        method = getattr(self.my_object, method_name)
        parameters = self.get_parameters(method)
        if parameters:
            param_values = self.get_parameter_values(parameters)
            if param_values:
                result = method(*param_values)
                self.result_text.delete("1.0", tk.END)
                self.result_text.insert(tk.END, result)
        else:
            result = method()
            self.result_text.delete("1.0", tk.END)
            self.result_text.insert(tk.END, result)

    def get_parameters(self, method):
        signature = inspect.signature(method)
        parameters = signature.parameters
        return [name for name, param in parameters.items() if param.default == inspect.Parameter.empty]

    def get_parameter_values(self, parameters):
        param_values = []
        method_name = self.method_combobox.get()
        l = []
        for i in range(2, (len(dico[method_name]))):
            l.append(dico[method_name][i])
        j=0
        for param in parameters:
            value = simpledialog.askstring("Paramètre",f"possibilité = {l[j]}. \nVeuillez entrer une valeur pour '{param}':")
            j+=1
            if value is None:
                return None
            param_values.append(value)
        return param_values

    def run(self):
        self.root.mainloop()

class TableauGUI:
    def __init__(self, data):
        self.root = tk.Tk()
        self.root.title("table of methods")
        self.data = data
        self.variable_texte = tk.StringVar()

        self.table = ttk.Treeview(self.root, columns=("Allowed BLE", "Number options"))
        self.table.heading("#0", text="Name methode")
        self.table.heading("Allowed BLE", text="Allowed BLE")
        self.table.heading("Number options", text="Number options")

        self.table.pack()

        self.populate_table()

        self.label = tk.Label(self.root, text="Entrez du texte :")
        self.label.pack()

        self.champ_entree = tk.Entry(self.root, textvariable=self.variable_texte)
        self.champ_entree.pack()

        self.bouton_valider = tk.Button(self.root, text="Valider", command=self.root.quit)
        self.bouton_valider.pack()

        self.texte_saisi = tk.StringVar()
        self.label_texte_saisi = tk.Label(self.root, textvariable=self.texte_saisi)
        self.label_texte_saisi.pack()

    def variable(self):
        return str(self.variable_texte.get())

    def populate_table(self):
        for key, values in self.data.items():
            self.table.insert("", "end", text=key, values=values)

    def run(self):
        self.root.mainloop()

Methode = methode()
dico = {
 'AuxOut': [True, 0, 'NONE'],
 'AuxIn': [True, 0, 'NONE'],
 'Calibrate': [True, 0, 'NONE'],
 'DumpFile': [True, 1, '(name of file)'],
 'SetDate': [True, 0, 'NONE'],
 'GetDate': [True, 0, 'NONE'],
 'SetGain': [True, 2,'gain_master | gain_preamp | gain_air | gain_wire_out | gain_wire_in | gain_looper', '<value>'],
 'GetGain': [True, 0, 'NONE'],
 'StartMetronome': [True, 0, 'NONE'],
 'StopMetronome': [True, 0, 'NONE'],
 'UpdateMetronome': [True, 4, 'bmp', 'num', 'den', 'nbbars'],
 'ReadMetronome': [True, 0, 'NONE'],
 'BTcheck': [True, 0, 'NONE'],
 'ReadConfig': [True, 0, 'NONE'],
 'GetStatus': [True, 0, 'NONE'],
 'StartTuner': [True, 0, 'NONE'],
 'StopTuner': [True, 0, 'NONE'],
 'GetFileInfo': [True, 1, '(name of file)'],
 'SustainKiller': [True, 3, 'bank_num', 'on', 'reset'],
 'RemoveEffect': [True, 2, 'bank_num', 'effect_num'],
 'AddEffect': [True, 4, 'bank_num', 'type', 'preset', 'params'],
 'SetGainBank': [True, 2, 'bank_num', 'gain'],
 'SwitchBank': [True, 1, 'bank_num'],
 'FileRemove': [True, 1, 'name'],
 'PowampStatus': [True, 0, 'NONE'],
 'McuReset': [True, 0, 'NONE'],
 'ActivateSpkFilter': [True, 1, '1/100'],
 'RemoveBank': [True, 1, 'bank_num'],
 'ReadBank': [True, 3, 'bank_num', 'offset', 'size'],
 'SetBankName': [True, 2, 'bank_num', 'name'],
 'SetController': [True, 6, 'bank_num', 'effect_num', 'parameter', 'source', 'minimum', 'maximum'],
 'StartRecording': [True, 0, 'NONE'],
 'StopRecording': [True, 0, 'NONE'],
 'StartRendering': [True, 0, 'NONE'],
 'StopRendering': [True, 0, 'NONE'],
 'SetEQBandGain': [True, 2, 'band', 'gain'],
 'SetEQGain': [True, 1, 'gain'],
 'GetDataRec': [True, 0, 'NONE'],
 'AuxOutDryWet': [True, 1, 'value'],
 'AuxInDryWet': [True, 1, 'value'],
 'PrintBank': [True, 1, 'bank_num'],
 'BypassEffect': [True, 3, 'integer value', 'integer value', 'boolean value'],
 'SetPhaseInv': [True, 1, 'value'],
 'GetAudio': [False, 1, 'sensor', 'codec', 'a2dp'],
 'BMS': [True, 0, 'NONE'],
 'GBF': [True, 3, '<freq>', '<amp>', 'start | stop'],
 'GetLastLoop': [True, 0, 'NONE'],
 'Meter': [True, 2, 'add | remove | get', 'input_level | output_level | mix_level | codec_in_level | bt_level'],
 'ButUpdate': [True, 6, 'Bt1=[0 | 1]', 'Bt2=[0 | 1]', 'Bt3=[0 | 1]', 'Bt4=[0 | 1]', 'Pot1=[0;100]', 'Pot2=[0;100]'],
 'TestGetAudioFile': [False, 2, 'sensor | codec | a2dp', '(name of the file)'],
 'TestGetAudio': [False, 2, 'sensor | codec | a2dp', '(duration of the pulse)'],
 'TestCalibrate': [True, 3, 'frequency in HZ', 'amplitude in db'],
 'ResponseSensorInput': [True, 4, 'amplitude in db', 'frequency in HZ', 'frequency in HZ', 'integer value'],
 'TestMeter': [True, 2, 'amplitude in db', 'frequency in HZ'],
 'MoveBank': [True, 2, 'integer value', 'integer value'],
 'LaunchCalibration': [True, 5, 'amp', 'f0', 'f1', 'mode', 'feedback'],
 'UiLedDim': [True, 3, '0-->100', '0-->100', '0-->100'],
 'UiEnableSet': [True, 1, 'params'],
 'UiScreenFill': [True, 1, 'action'],
 'GetCPU': [True, 0, 'NONE'],
 'TestMonostable': [True, 0, 'NONE'],
 'TestChargerWakeup': [True, 0, 'NONE'],
 'UiMonitor': [True, 1, 'time in seconde'],
 'RtaudioInGainSet': [True, 1, 'params'],
 'RtaudioOutEnable': [True, 2, 'left', 'right'],
 'FileUpload': [True, 3, 'file_path', 'status', 'data'],
 'SetSpeakerBiquads': [True, 1, 'params'],
 'GetLastRecordingName': [True, 0, 'NONE'],
 'AutoPowerOff': [True, 1, 'value'],
 'GetFreeHeap': [True, 0, 'NONE'],
 'GetSignalLevelsInRMS': [True, 0, 'NONE'],
 'MoveEffect': [True, 3, 'bank_num', 'effect_num', 'effect_dest'],
 'UpdateEffect': [True, 5, 'bank_num', 'effect_num', 'type', 'preset', 'params'],
 'SaveConfig': [True, 0, 'NONE'],
 'PowerMode': [True, 0, 'NONE'],
 'Ping': [True, 0, 'NONE'],
 'Temp': [True, 0, 'NONE']}
tab = TableauGUI(dico)
tab.run()
dev = tab.variable()

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

gui = GUI()
gui.run()

if mode_BLE:
    """
    stop connection by BLE
    """
    print("Closing BLE ")
    dev.write(str.encode("@stop\n"))
    resp = dev.read_until()
    print("got", resp)
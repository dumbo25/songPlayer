#!/usr/bin/env python3

#########################
#
# songPlayer.py is a python3 script to play songs using mpd and mpc
#
# One goal of writing this script was to understand how these commands
# could be used in a larger alarm clock radio project. Also, in working
# on the script and using the script, I was able to determine the features 
# needed in the alarm clock
#
# I use three question (???) marks to indicate features that are not quite
# finished
#
# songPlayer.py was tested on a Raspberry Pi 3 model B+ running raspbian 
# stretch
#
# This script requires the following:
#
#    $ sudo apt-get install mpc mpd -y
#    $ sudo apt-get alsa -y
#
#    HiFiBerry AMP 2 top board, barrel power supply and Speaker
#
#    alsamixer is used to set the digital volume to 20%
#
#    I copied my iTunes Library in m4a format to /home/pi/Music
#       iTunes creates folders by artist and then by album
#       In a MacBook Finder window I searched music library for *.m4a
#       I selected all of those m4a files and copied them to a temp folder
#       and then scp'd all of those from the MacBook to Raspberry Pi
#       Open a MacBook terminal window cd to the temp directory and run:
#
#       $ scp * pi@<your-hostname>:Music/.
#
#    On Raspberry Pi
#
#       Config files:
#          /etc/mpd.conf
#          /etc/asound.conf
#          /usr/share/alsa/alsa.conf
#          /home/pi/radio/songPlayer.conf
#
#       Logs are stored here:
#          /var/log/mpd/mpd.log
#          /home/pi/radio/songPlayer.log
#
#       Playlists are stored here:
#          /var/lib/mpd/playlists
#
#       Songs are stored here:
#          /home/pi/Music
#
#       commands to control/examine mpd service
#          $ sudo service mpd stop
#          $ sudo service mpd start
#          $ sudo service --status-all | grep mpd
#
#       details of the mpc and mpd commands
#          man mpd
#          man mpc
#
# Start the script running using:
#    python3 songPlayer.py
#
# Notes:
#    If music file name contains a backquote, you will get error message:
#       EOF in backquote substitution
#
#########################

import time
import datetime
import os
import sys
import subprocess

#########################
# Global Variables

fileLog = open('/home/pi/radio/songPlayer.log', 'w+')
currentSongConfig = '/home/pi/radio/songPlayer.conf'
tempSongFile = '/home/pi/radio/songPlayer.tmp'

directoryMusic = "/home/pi/Music"

defaultVolume = 60
currentVolume = defaultVolume

muteVolume = False

# mpd doesn't remember the current playlist
# so, mpc has no way to retrieve it
# if mpc commands are run outside of this script, then there is no
# way to find if the playlist changed
defaultPlaylist = "all_songs"
currentPlaylist = defaultPlaylist

# Instead of starting with the first song every time, remember last song
# played or get current song playing and start playing it
# ??? if exit with x, then get currently playing song when restarting rather than
#     last known song to be playing ???
currentSong = ""

# On commands like play, prev and next, mpc outputs a line similar to:
#
#    volume: n/a repeat: off random: off single: off consume: off
#
# adding the following to any mpc command suppresses that output

limitMPCoutput = " | grep \"[-,'[']\""


#########################
# Log messages should be time stamped
def timeStamp():
    t = time.time()
    s = datetime.datetime.fromtimestamp(t).strftime('%Y/%m/%d %H:%M:%S - ')
    return s

# Write messages in a standard format
def printMsg(s):
    fileLog.write(timeStamp() + s + "\n")

def lastSong():
    f = tempSongFile
    cmd = "mpc current > " + f
    subprocess.call(cmd, shell=True)
    try:
        fileSong = open(f, 'r')
        songAndTitle = fileSong.readline()
        i = songAndTitle.find("-") + 2
        songAndNewline = songAndTitle[i:]
        song = songAndNewline.rstrip()
        fileSong.close()
    except Exception as ex:
        printMsg("Exception in lastSong = [" + ex + "]")
        song = ""

    return song

def readSongPlayerConfig():
    global currentSong
    global currentVolume
    global currentPlaylist

    song = lastSong()

    try:
        f = open(currentSongConfig, 'r')
        songAndTitle = f.readline()
        if song == "":
            st = songAndTitle.rstrip()
            i = st.find("-") + 2
            song = st[i:]

        currentSong = song
        l = f.readline()
        v = l.rstrip()
        currentVolume = int(v)
        l = f.readline()
        currentPlaylist = l.rstrip()
        f.close()
    except Exception as ex:
        printMsg("Exception in readSongPlayerConfig [" + ex + "]")
        currentSong = ""
        currentVolume = defaultVolume
        currentPlaylist = defaultPlaylist
        f.close()

    printMsg("read songPlayer config")
    printMsg(" song = [" + currentSong + "]")
    printMsg(" volume = [" + str(currentVolume) + "]")
    printMsg(" playlist = [" + currentPlaylist + "]")

    cmd = "rm " + tempSongFile
    subprocess.call(cmd, shell=True)
    return

def writeSongPlayerTxt():
    global currentSong

    # current song can be null
    o = subprocess.check_output("mpc current", shell=True)
    songAndTitle = o.decode("utf-8")
    if songAndTitle != "":
        songAndTitle = songAndTitle.rstrip()

    i = songAndTitle.find("-") + 2
    currentSong = songAndTitle[i:]
 
    f = open(currentSongConfig, 'w')
    f.write(currentSong + "\n")
    f.write(str(currentVolume) + "\n")
    f.write(currentPlaylist + "\n")
    f.close()

def init():
    readSongPlayerConfig()

    print("volume = [" + str(currentVolume) + "]")
    cmd = "amixer set Digital " + str(currentVolume) + "%"
    subprocess.call(cmd, shell=True)

    if currentSong == "":
        cmd = "mpc play " + limitMPCoutput
    else:
        cmd = 'mpc searchplay title "' + currentSong + '"' + limitMPCoutput

    subprocess.call(cmd, shell=True)
    return

# Insert music from my Apple library into mpd and save it as a playlist
def initPlaylist(playlist_name):
    global currentPlaylist

    cmd = "mpc clear" + limitMPCoutput
    subprocess.call(cmd, shell=True)

    print("Loading songs takes a few minutes. Please wait for > prompt")
    for file in os.listdir(directoryMusic):
        if file.endswith(".m4a"):
            dirName = os.path.join(directoryMusic, file)
            fileName = "file://" + dirName
            cmd = 'mpc insert ' + '"' + fileName + '"'
            subprocess.call(cmd, shell=True)

    cmd = "mpc save " + playlist_name
    subprocess.call(cmd, shell=True)

    currentPlaylist = playlist_name
    return

def removePlaylist(p):
    if p == defaultPlaylist:
        print("Cannot remove default playlist: " + defaultPlaylist)    
    else:
        print ("Stopping ...")
        cmd = "mpc stop " + limitMPCoutput
        subprocess.call(cmd, shell=True)
        print("Remove playlist " + p)
        cmd = "mpc rm " + p + limitMPCoutput
        subprocess.call(cmd, shell=True)
        cmd = "mpc clear --wait " + limitMPCoutput
        subprocess.call(cmd, shell=True)

        initPlaylist(defaultPlaylist)


def printMenu():
    print (" ")
    print ("Song Commands:")
    print ("   >[=n]  Play, where n is the song number")
    print ("          n is optional and by default plays the current song")
    print ("   !      Pause")
    print ("   p      Previous")
    print ("   n      Next")
    print ("Volume Commands:")
    print ("   m      Mute volume toggle")
    print ("   +      Increase volume")
    print ("   -      Decrease volume")
    print ("Playlist Commands:")
    print ("   a=f    Add song named f from Music directory to playlist")
    print ("          include .m4a extension. Do not escape or quote")
    print ("   d[=n]  Delete song numbered n from playlist")
    print ("          n is optional and the default is the current song")
    print ("   C      Current playlist")
    print ("   D      Delete all songs from the playlist")
    print ("   f=s    Find and play the first song containing the string s")
    print ("          escape spaces and other character with backslash")
    print ("   I[=n]  Initialize playlist from Music directory")
    print ("          n is optional and by default n = all_songs")
    print ("   L=n    Load playlist named n")
    print ("   P      List playlists")
    print ("   R[=n]  Remove playlist named n")
    print ("          n is optional and the default is current playlist")
    print ("   s[=s]  Show all songs or just songs containing the string s")
    print ("          escape spaces and other character with backslash")
    print ("   S[=n]  Save playlist named n")
    print ("          n is optional and the default is current playlist")
    print ("Exit Commands")
    print ("   o      Shut raspberry pi off")
    print ("   x      Exit and leave music playing")
    print (" Return   Press Enter or Return key to exit and turn off music")

#########################
printMsg("Starting songPlayer")
print("If after reboot, mpd loads last playlist. Please wait ...")

try:

    init()

    ans = True
    while ans:
        printMenu()

        # command order was by type, but changed to alphabetic because it
        # is easier to find the command
        ans = input(">")
        if ans != "" and ans[0] == ">":
            ans2 = ans[1:]
            if ans2 != "" and ans[1] == "=":
                # play song number n
                s = ans[2:]
                print ("play song number " + s)
                cmd = "mpc play " + s  + limitMPCoutput
                subprocess.call(cmd, shell=True)
            else:
                # play
                print("play")
                cmd = "mpc play" + limitMPCoutput
                subprocess.call(cmd, shell=True)
        elif ans == "!":
            # pause
            print("pause")
            cmd = "mpc stop " + limitMPCoutput
            subprocess.call(cmd, shell=True)
        elif ans == "+":
            # volume up
            print ("volume up")
            currentVolume +=5
            if currentVolume > 100:
                currentVolume = 100
            cmd = "amixer set Digital " + str(currentVolume) + "%"
            subprocess.call(cmd, shell=True)
        elif ans == "-":
            # volume down
            print ("volume down")
            currentVolume -=5
            if currentVolume < 0:
                currentVolume = 0
            cmd = "amixer set Digital " + str(currentVolume) + "%"
            subprocess.call(cmd, shell=True)
        elif ans != "" and ans[0] == "a":
            ans2 = ans[1:]
            if ans2 != "" and ans[1] == "=":
                try:
                    # add song
                    file = ans[2:]
                    print ("add song " + file)
                    dirName = os.path.join(directoryMusic, file)
                    fileName = "file://" + dirName
                    # Use add to add to end rather than insert which puts after current
                    cmd = 'mpc add ' + '"' + fileName + '"'
                    print(cmd)
                    subprocess.call(cmd, shell=True)
                except Exception as ex:
                    printMsg("ERROR: an unhandled exception occurred: " + str(ex))
                    print ("Add failed for: " + fileName)
        elif ans == "C":
            # Display current playlist
            print("Current playlist = " + currentPlaylist)
        elif ans != "" and ans[0] == "d":
            ans2 = ans[1:]
            if ans2 != "" and ans[1] == "=":
                # delete song number n
                s = ans[2:]
                print ("delete song number " + s)
                cmd = "mpc del " + s + limitMPCoutput
                subprocess.call(cmd, shell=True)
            else:
                # play
                print("delete current song")
                cmd = "mpc del 0 " + limitMPCoutput
                subprocess.call(cmd, shell=True)
        elif ans == "D":
            if currentPlaylist == defaultPlaylist:
                print("Cannot delete all songs from default playlist")
            else:
                # Delete all songs from the playlist
                cmd = "mpc stop " + limitMPCoutput
                subprocess.call(cmd, shell=True)
                cmd = "mpc clear " + limitMPCoutput
                subprocess.call(cmd, shell=True)
        elif ans != "" and ans[0] == "f":
            ans2 = ans[1:]
            if ans2 != "" and ans[1] == "=":
                # find and play song containing string s
                print("find and play")
                s = ans[2:]
                cmd = "mpc searchplay title " + s
                subprocess.call(cmd, shell=True)
            else:
                print("f requires a string")
        elif ans != "" and ans[0] == "I":
            # initialize playlist
            ans2 = ans[1:]
            if ans2 != "" and ans[1] == "=":
                n = ans[2:]
            else:
                n = defaultPlaylist
            initPlaylist(n)
            currentPlaylist = n
        elif ans != "" and ans[0] == "L":
            # Load playlist
            ans2 = ans[1:]
            if ans2 != "" and ans[1] == "=":
                n = ans[2:]
                initPlaylist(n)
                currentPlaylist = n
        elif ans == "m":
            # mute
            muteVolume = not muteVolume
            if muteVolume == True:
                print ("mute")
                previousVolume = currentVolume
                currentVolume = 0
                cmd = "amixer set Digital " + str(currentVolume) + "%"
            else:
                print ("unmute")
                currentVolume = previousVolume
                cmd = "amixer set Digital " + str(currentVolume) + "%"
            subprocess.call(cmd, shell=True)
        elif ans == "n":
            # next
            print("next")
            cmd = "mpc next " + limitMPCoutput
            subprocess.call(cmd, shell=True)
        elif ans == "o":
            # shutoff raspberry pi and radio
            sys.exit()
        elif ans == "p":
            # previous
            print("previous")
            cmd = "mpc prev " + limitMPCoutput
            subprocess.call(cmd, shell=True)
        elif ans == "P":
            # List all playlists
            cmd = "mpc lsplaylists"
            subprocess.call(cmd, shell=True)
        elif ans != "" and ans[0] == "R":
            # Remove playlist
            ans2 = ans[1:]
            if ans2 != "" and ans[1] == "=":
                n = ans[2:]
                removePlaylist(n)
            else:
                removePlaylist(currentPlaylist)
        elif ans != "" and ans[0] == "s":
            ans2 = ans[1:]
            if ans2 != "" and ans[1] == "=":
                # search songs in playlist containing string s
                print ("find and list songs matching a string (case sensitive)")
                s = ans[2:]
                cmd = "mpc playlist | grep -n " + s
                subprocess.call(cmd, shell=True)
            else:
                # list all songs in playlist
                print ("list all songs in playlist")
                cmd = "mpc playlist | grep -n '-'"
                subprocess.call(cmd, shell=True)
        elif ans != "" and ans[0] == "S":
            # Save playlist
            ans2 = ans[1:]
            if ans2 != "" and ans[1] == "=":
                # Save playlist as n
                n = ans[2:]
                print ("save playlist as " + n)
                cmd = "mpc save " + n
                subprocess.call(cmd, shell=True)
            else:
                # Save current playlist
                print ("save current playlist")
                cmd = "mpc save " + currentPlaylist + limitMPCoutput
                subprocess.call(cmd, shell=True)
        elif ans == "x":
            # exit and leave music playing
            sys.exit()
        elif ans == "":
            # exit and stop music
            sys.exit()
        else:
            print("Unrecognized command: " + ans)

    sys.exit()

except KeyboardInterrupt: # trap a CTRL+C keyboard interrupt
    printMsg("keyboard exception occurred")

except Exception as ex:
    printMsg("ERROR: an unhandled exception occurred: " + str(ex))

finally:
    printMsg("songPlayer terminated")
    writeSongPlayerTxt()
    if ans == "x":
        printMsg("... Song still playing")
        fileLog.close()
    elif ans == "o":
        subprocess.call("mpc stop ", shell=True)
        printMsg("... Shutting down raspberry pi")
        fileLog.close()
        subprocess.call("sudo shutdown -h 0", shell=True)
    else:
        subprocess.call("mpc stop ", shell=True)
        fileLog.close()


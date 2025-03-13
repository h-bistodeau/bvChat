from socket import *
import threading
import hashlib
import sys
import time

# run using ./bvChat-Server

MOTD = "Do what you can, with what you have, where you are. -Ben Franklin"
in_session = []  # keeps track of the usernames currently logged in

port = 12345

userList = {}
userListLock = threading.Lock()

listen_socket = socket(AF_INET, SOCK_STREAM)
listen_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
listen_socket.bind(('', port))
listen_socket.listen(10)

def handleClient(connInfo):

    clientConn, clientAddr = connInfo # a pair of (socket, clientAddr) from accept()
    clientIP = clientAddr[0]

    print("Received connection from %s:%d" %(clientIP, clientAddr[1]))

    clientConn.send("Welcome to to bvChat, please enter your username & password\n".encode())

    try:
        #try to receive the username and password
        user_pass = clientConn.recv(1024).decode()

        # if there is a space within the string split it there and if not send the error message and close the connection
        if " " in user_pass:
            username, password = user_pass.split(" ", 1)
        else:
            clientConn.send("invalid format please use the format <username> <password>.\n".encode())
            clientConn.close()
            return

        #sets a dictionary of the valid usernames/passwords
        valid_users = {}
        try:
            file = open("users.txt","r") #open the file

            # for every line in the txt split the line to set both the passw and usern, add it to the dictonary
            for line in file:
                usern, passw = line.strip().split(" ", 1)
                valid_users[usern] = passw
            file.close()

        # in case the file doesn't exist
        except FileNotFoundError:
            print("file does not exist")
            users = {}

        # if both the username and password are correct and the username ISN'T active send the message of the day
        if username in valid_users.keys() and valid_users[username] == password and username not in in_session:
            in_session.append(username)
            clientConn.send("login successful.\n".encode())
            clientConn.send("Message of the day is: " + MOTD + "\n".encode())

        # if the username and password are correct but the user IS active don't allow the connection
        elif username in valid_users.keys() and valid_users[username] == password and username in in_session:
            clientConn.send("This username is already logged in please try again.\n".encode())
            clientConn.close()

        # if the username and password don't match but the username is valid close connection
        elif username in valid_users.keys() and valid_users[username] != password:
            clientConn.send("incorrect password please try again\n".encode())
            clientConn.close()

        # basically if the username isn't in the system
        else:
            file = open("users.txt","a")
            file.append(username + password + "\n")
            file.close()
            in_session.append(username)
            clientConn.send("User creation & login successful.\n".encode())
            clientConn.send("Message of the day is: " + MOTD + "\n".encode())

        client_msg = clientConn.recv(1024).decode()

        # /tell - direct message to the specified username (must send to the user when they login if they aren't currently)
        if client_msg.startswith("/tell"):
            command, destination, message = client_msg.split(" ", 2)
            if destination in in_session:
                # sent the message to that one (its probably a thread or something idk)
                pass

            # check for when the user goes online or is appended to the in_session list
            else:
                pass

        # /motd - sends the message of the day again
        elif client_msg == "/motd":
            clientConn.send(("Message of the day is: " + MOTD + "\n").encode())

        # /me - emote message using the username
        # Ex. /me is crashing out --> hbistodeau is crashing out

        # /who - lists all in-session users
        elif client_msg == "/who":
            clientConn.send("Users in session are: ".encode())
            for u in in_session:
                clientConn.send((u + ",").encode())

        # /help - displays the list of commands
        elif client_msg == "/help":
            clientConn.send("Available commands: /tell, /who, /motd, /me, /help, /exit\n".encode())

        # /exit - closes connection and alerts other users they left
        elif client_msg == "/exit":
            clientConn.send("Bye.\n".encode())
            # send the message to other users as well

            clientConn.close()

        # Broadcasting is when everyone gets the message (since there's no special command, this is the else statement)

    # Idk when I should get rid of this but PyCharm is pissed off when its gone.
    except ConnectionResetError:
        print("Connection reset by peer")


    running = True
    while running:
        try:
            threading.Thread(target=handleClient, args=(listen_socket.accept(),), daemon=True).start()
        except KeyboardInterrupt:
            print("\n Why'd you stop me?? :( ")
            running = False

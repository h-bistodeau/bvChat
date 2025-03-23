from socket import *
import threading
import time

# run using ./bvChat-Server
# client side we need to have /ban and /unban
MOTD = "Do what you can, with what you have, where you are. -Ben Franklin"
in_session = {}  # keeps track of the usernames currently logged in
offline_msg = {}
bans = {}
failed_login = {}

port = 12345

listen_socket = socket(AF_INET, SOCK_STREAM)
listen_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
listen_socket.bind(('', port))
listen_socket.listen(10)

sessionLock = threading.Lock()

def broadcast(sender, msg):
    with sessionLock:
        for user, conn in in_session.items():
            msg = str(user) + ": " + str(msg) + "\n"
            # ensures you aren't sending something across your own conn or if the other user has you banned
            if user != sender and sender not in bans[user]:
                try:
                    conn.send(msg.encode())
                except:
                    print(f"Error sending message to {user}")

def handleClient(connInfo):

    # take in the connection info and send the inital greeting to the chatroom
    clientConn, clientAddr = connInfo # a pair of (socket, clientAddr) from accept()
    clientIP = clientAddr[0]

    print("Received connection from %s:%d" %(clientIP, clientAddr[1])) # test check

    clientConn.send("Welcome to to bvChat, please enter your username & password\n".encode())

    while True:
        try:
            # try to receive the username and password
            user_pass = clientConn.recv(1024).decode()

            # if there is a space within the string split it there and if not send the error message and close the connection
            if " " not in user_pass:
                clientConn.send("invalid format please use the format <username> <password>.\n".encode())
                clientConn.close()
                return

            username, password = user_pass.split(" ", 1)

            # set a variable for the current time to compare to for failed log in attepmts
            currTime = time.time()

            # if the username is already in the failed login dictionary
            if username in failed_login:
                # create the 3 variable (attempts is pretty clear, 'firstTime' is the timestamp for the first failed attempt, and lockedUntil is the timestamp for when logins become available)
                attempt, firstTime, lockedUntil = failed_login[username]

                if lockedUntil and currTime < lockedUntil:
                    remainingTime = int(lockedUntil - currTime)
                    msg = "too many failed attempts, try again in {} seconds\n".format(remainingTime) # pyCharm came in clutch with the .format() (you learn something new everyday)
                    clientConn.send(msg.encode())
                    clientConn.close()
                    return

                if currTime - firstTime > 30:
                    failed_login[username] = (0, currTime, None)


            # sets a dictionary of the valid usernames/passwords
            valid_users = {}
            try:
                with open("users.txt", "r") as file:  # open the file
                    # for every line in the txt, split the line to set both the passw and usern adding it to the dictionary
                    for line in file:
                        usern, passw = line.strip().split(" ", 1)
                        valid_users[usern] = passw

            # in case the file doesn't exist (idk why it wouldn't but oh well)
            except FileNotFoundError:
                print("file does not exist")

            # if both the username and password are correct and the username
            if username in valid_users.keys() and valid_users[username] == password:
                with sessionLock:
                    # if the username is already in use shut down the connection
                    if username in in_session:
                        clientConn.send("this session is already in use.\n".encode())
                        clientConn.close()
                        return

                    # if it makes it past the if-statement add the username to in_session and send the message of the day
                    in_session[username] = clientConn
                    clientConn.send("login successful.\n".encode())
                    clientConn.send("Message of the day is: " + MOTD + "\n".encode())

                # if the user has any messages sent to them while offline send them once they log in again
                if username in offline_msg.keys():
                    for msg in offline_msg[username]:
                        clientConn.send(("offline message: " + msg).encode())
                    offline_msg[username] = []

                # if there were failed log in attempts prior to this delete the user from dict.
                if username in failed_login:
                    del failed_login[username]

            # if the username and password don't match but the username is valid
            elif username in valid_users.keys() and valid_users[username] != password:

                # check if the username needs to be added to failed login
                if username not in failed_login:
                    failed_login[username] = (1, currTime, None)

                # if the username is already in failed_login grab the variables from the dict.
                else:
                    attempt, firstTime, lockedUntil = failed_login[username]
                    attempt += 1 #increase the failed attempts var.

                    # if this is the third attempt
                    if attempt >= 3:
                        # update the lockedUntil variable using teh current time (since this is when the 3rd attempt took place)
                        failed_login[username] = (attempt, firstTime, currTime + 120)
                        clientConn.send("Too many failed log in attempts you can try again in 2 minutes.\n".encode())
                        clientConn.close()
                        return

                    #if this is attempt 2 basically, we are only updating the attempt variable in the dictionary
                    else:
                        failed_login[username] = (attempt, firstTime, None)

            # basically if the username isn't in the system add them to users.txt and allow the connection
            else:
                with open("users.txt", "a") as file:
                    file.write(username + " " + password + "\n")

                in_session[username] = clientConn
                clientConn.send("User creation & login successful.\n".encode())
                clientConn.send("Message of the day is: " + MOTD + "\n".encode())

            # end of the log in checks, from here on out it's dealing with client messages being sent in and the various commands
            while True:
                # receive a message
                client_msg = clientConn.recv(1024).decode()
                if not client_msg:
                    break  # Client disconnected

                # /tell - direct message to the specified username (must send to the user when they log in if they aren't currently)
                if client_msg.startswith("/tell"):
                    try:
                        command, destination, message = client_msg.split(" ", 2)  # split twice at the spaces, disregarding the command variable
                    except ValueError:
                        print("Invalid command, correct format is /tell <destination username> <message>")

                    msg = "Message from " + username + ": " + message + "\n"  # format the direct message a bit better

                    if destination in in_session:
                        # send the message to that specific user (it's probably a thread or something idk)
                        connection = in_session[destination]
                        connection.send(msg.encode())

                    # if the user is not in session add it to the preexisting list of offline msgs or add the user to the dictionary
                    else:
                        if destination in offline_msg.keys():
                            offline_msg[destination].append(msg)
                        else:
                            offline_msg[destination] = [msg]

                # /motd - sends the message of the day again
                elif client_msg == "/motd":
                    clientConn.send(("Message of the day is: " + MOTD + "\n").encode())

                # /me - emote message using the username
                # Ex. /me is crashing out --> hbistodeau is crashing out
                elif client_msg.startswith("/me"):
                    command, message = client_msg.split(" ", 1)
                    message = username + message + "\n"

                    # send the message to the masses (broadcasting)
                    broadcast(username, message)

                # /who - lists all in-session users
                elif client_msg == "/who":
                    uPrint = ""  # initialize this variable as empty first
                    with sessionLock:
                        for u in in_session:
                            # add on the next user in the list to the string
                            uPrint = uPrint + u + "  "
                    clientConn.send(("Users Online: " + uPrint + "\n").encode())

                # /help - displays the list of commands
                elif client_msg == "/help":
                    clientConn.send("Available commands: /tell, /who, /motd, /me, /help, /exit\n".encode())

                # /exit - closes connection and alerts other users they left
                elif client_msg == "/exit":
                    clientConn.send("Bye.\n".encode())
                    in_session.pop(username, None)

                    # send the message to other users as well
                    exitMsg = "user " + username + " has left the chatroom"
                    broadcast(username, exitMsg)
                    break  # Exit loop on user logout

                # right now I just have the server keeping track of the list of banned usernames
                elif client_msg.startswith("/ban"):
                    command, banned_user = client_msg.split(" ", 1)

                    # determining if the username already has a prior list to just append to
                    if username in bans.keys():
                        bans[username].append(banned_user)
                    else:
                        bans[username] = [banned_user]

                    clientConn.send(("Banned user: " + banned_user + "\n").encode())

                elif client_msg.startswith("/unban"):
                    command, banned_user = client_msg.split(" ", 1)
                    if username in bans and banned_user in bans[username]:
                        bans[username].remove(banned_user)
                        clientConn.send(
                            ("Unbanned: " + banned_user + " you may now send/receive messages from them\n").encode())
                    else:
                        clientConn.send((
                                            "that user is not in your bans list, please use command /ban <username> to add them if you wish\n").encode())

                # Broadcasting is when everyone gets the message (since there's no special command, this is the else statement)
                else:
                    broadcast(username, client_msg)

        # Idk when I should get rid of this but PyCharm is pissed off when it's gone.
        except ConnectionResetError:
            print(f"Connection was reset")
            break  # Exit loop when client disconnects

    # Clean up session when client disconnects
    with sessionLock:
        in_session.pop(username, None)
    broadcast(username, f"User {username} has left the chatroom.\n")
    clientConn.close()


running = True
while running:
    try:
        threading.Thread(target=handleClient, args=(listen_socket.accept(),), daemon=True).start()
    except KeyboardInterrupt:
        print("\n Why'd you stop me?? :( ")
        running = False

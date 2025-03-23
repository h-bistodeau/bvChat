from socket import *
import threading
import time 
from pathLib import Path 

# Variables to keep track of user information
userInfo = 'users.txt' # Store users
loggedIn = {} # Who is logged in
failedLogin = {} # How many failed logins someone has
timeout = {}
offlineMess = {} # Saved direct messages
blocked = {} # Keep track of who has blocked who
messOfTheDay = "Welcome to the chat server!"
port = 8008

# Function to load the users from the persistent file
def loadUsers():
    users = {}
    try:
        # Open the file and read in the usernames and passwords
        with open(userInfo, 'r') as file:
            for line in file:
                username, password = line.strip().split(",")
                users[username] = password
    # If the file isnt found open a new one
    except FileNotFoundError:
        open(userInfo, 'w').close()
    return users

# Save a user to the file
def saveUser(username, password):
    with open(userInfo, 'a') as file:
        file.write(f"{username},{password}\n")

# Send a message to all users
def broadcast(message, sender):
    # If the user is logged in send them the message
    for user, sock in loggedIn.items():
        if user != sender and sender not in blocked.get(user, set()):
            sock.send(f"{sender}: {message}\n".encode())

# Function to send a direct message to a user
def directMessage(sender, reciever, message):
    # If the sender is blocked by the reciever do nothing
    if sender in blocked.get(reciever, set()):
        # Let the sender know they are blocked
        if sender in loggedIn:
            loggedIn.send(b'This user has you blocked.\n')
        return
    # If the user recieving the message is logged in send it to them with the sender name
    if reciever in loggedIn:
        loggedIn[reciever].send(f"(Direct Message from {sender}): {message}\n.".encode())
    # If the user is not logged in save the message to the offline message dictionary
    else:
        offlineMess.setdefault(reciever, []).append(f"(Direct Message from {sender}): {message}\n.".encode())

# Function to handle the connections of the users
def connection(clientSock, clientAddr):
    # Declare the variables global
    global loggedIn, failedLogin, timeout, offlineMess, blocked
    # Load the users information
    users = loadUsers()

    try:
        # Grab the username and password from the client
        cliInformation = clientSock.recv(1024).decode().strip().split(" ", 1)
        # If not <username> <password> disconnect
        if len(cliInformation) != 2:
            clientSock.send(b'Invalid format. (username password). Disconnecting.\n')
            clientSock.close()
            return
        # Store the user information
        username, password = cliInformation
        
        # If the user has to many failed attempts, block them from attempting again
        if username in timeout_users and time.time() - timeout_users[username] < 120:
            clientSock.send(b'Too many failed attempts. Try again later.\n')
            clientSock.close()
            return

        # If the user is already logged in, do not allow another login 
        if username in loggedIn:
            clientSock.send(b'User already logged in.\n')
            clientSock.close()
            return

        # If the user exists continue
        if username in users:
            # If the password is correct continue
            if users[username] == password:
                # Add them to logged in and remove any failed attempts from dictionary
                loggedIn[username] = clientSock
                failedLogin.pop(clientAddr[0], None)
                blocked.setdefault(username, set())

                clientSock.send(b'Welcome to the chat server!\n')
                clientSock.send(f"Message of the Day: {messOfTheDay}.\n".encode())
                print(f"{username} has logged in.")
                broadcast(f"{username} has joined the chat!", "Server") # Broadcast to other users that someone new logged in

                # Check if the user has any DM's sent while disconnected
                if username in offlineMess:
                    for msg in offlineMess[username]:
                        clientSock.send(f"{msg}\n".encode())
                    # Remove message once it is sent
                    del offlineMess[username]
                # While loop to keep the chat running
                while True:
                    try:
                        # Wait for client messages/instructions
                        message = clientSock.recv(1024).decode().strip()
                        # Section to handle special instructions
                        if message.lower() == "/exit":
                            # Disconnect the user if they type exit, make sure other users are aware
                            clientSock.send(b'Goodbye!\n')
                            del loggedIn[username]
                            broadcast(f"{username} has left the chat.", "Server")
                            clientSock.close()
                            break
                        # If statement to handle DM's
                        elif message.lower().startswith("/tell "):
                            parts = message.split(" ", 2)
                            if len(parts) < 3:
                                # If they use the incorrect format send this
                                clientSock.send(b'Usage: /tell <username> <message>\n')
                            else:
                                directMessage(username, parts[1], parts[2])
                        # List the current online users
                        elif message.lower() == "/who":
                            clientSock.send(f'Users online: {", ".join(loggedIn.keys())}\n'.encode())
                        # Send the message of the day
                        elif message.lower() == "/motd":
                            clientSock.send(f"{messOfTheDay}\n".encode())
                        # Display available commands
                        elif message.lower() == "/help":
                            clientSock.send(b'Available commands: /who, /exit, /tell <username> <message>, /motd, /me <emote>, /help, /block <username>, /unblock <username>\n')
                        # Emote
                        elif message.lower().startswith("/me "):
                            emote = message[4:].strip()
                            if emote:
                                # If the wrong format display this to user
                                broadcast(f"*{username} {emote}", "Server")
                            else:
                                clientSock.send(b'Usage: /me <emote>\n')
                        # Handles blocking users
                        elif message.lower().startswith("/block "):
                            parts = message.split(" ", 1)
                            if len(parts) < 2:
                                clientSock.send(b'Usage: /block <username>\n')
                            else:
                                blockUser = parts[1]
                                # If the user tried to block themself make it invalid
                                if blockUser == username:
                                    clientSock.send(b'You cannot block yourself!')
                                # If the user exists then add them to the blocked dictionary
                                elif blockUser in loggedIn or blockUser in users:
                                    blocked[username].add(blockUser)
                                    clientSock.send(f"You have blocked {blockUser}.\n")
                                # If the user doesnt exist go here
                                else:
                                    clientSock.send(b'User not found.\n')
                        # Handles unblocking blocked users
                        elif message.lower().startswith("/unblock "):
                            # Grab the user
                            parts = message.split(" ", 1)
                            # If invoked incorrectly let them know
                            if len(parts < 2):
                                clientSock.send(b'Usage: /unblock <username>\n')
                            # If invoked correctly
                            else:
                                # Grab the user
                                unblockUser = parts[1]
                                # If the users username dont allow
                                if unblockUser == username:
                                    clientSock.send(b'You cannot unblock yourself.\n')
                                # If not seld then make sure it exists in the users blocked dictionary
                                elif unblockUser in blocked.get(username, set()):
                                    blocked[username].remove(unblockUser)
                                    clientSock.send(f"You have unblocked {unblockUser}.\n")
                                # If the user is not blocked
                                else:
                                    clientSock.send(b'User is not blocked.\n')
                        # If not a command it is a message to be broadcast to other users        
                        else:
                            broadcast(message, username)
                    # If someone should fail disconnect the user and make the chat aware
                    except:
                        del loggedIn[username]
                        broadcast(f"{username} has disconnected.", "Server")
                        break
            # If the password is incorrect go here 
            else:
                # Add to failed login
                failedLogin.setdefault(clientAddr[0], []).append(time.time())
                # Keep track of user attempts and if it reaches 3 give them a timeout
                attempts = [t for t in failedLogin[clientAddr[0]] if time.time() - t < 30]
                if len(attempts) >= 3:
                    # Set the timeout and the time it happened
                    timeout[username] = time.time()
                    clientSock.send(b'Too many failed attempts. Try again later.\n')
                else:
                    # If they have more attempts let them know the password was incorrect
                    clientSock.send(b'Incorrect password.\n')
                clientSock.close()
        # If the user does not exist, save them and set their password
        else:
            saveUser(username, password)
            loggedIn[username] = clientSock
            clientSock.send(b'Account created. Welcome!\n')
            print(f"New user {username} registered and logged in.")

    except:
        clientSock.close()

# Server setup
serverSocket = socket(AF_INET, SOCK_STREAM)
serverSocket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
serverSocket.bind(('', port))
serverSocket.listen(32)
print(f"Server listening on port {port}...")

try:
    # Run the server with threads for the users
    while True:
        threading.Thread(target=connection, args=(clientSock, clientAddr), daemon=True).start()
except KeyboardInterrupt:
    print("\nShutting down server...")
    serverSocket.close()

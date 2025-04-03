from socket import *
import threading
import time

# Locks for shared variables
userLock = threading.Lock()
loggedInLock = threading.Lock()
failedLoginLock = threading.Lock()
timeoutLock = threading.Lock()
offlineMessLock = threading.Lock()
blockedLock = threading.Lock()

# Variables to keep track of user information
userInfo = "users.txt"  # Store users
loggedIn = {}  # Who is logged in
failedLogin = {}  # How many failed logins someone has
timeout = {}
offlineMess = {}  # Saved direct messages
blocked = {}  # Keep track of who has blocked who
messOfTheDay = "Welcome to the chat server!"
port = 8008


# Function to load the users from the persistent file
def loadUsers():
    with userLock:
        users = {}
        try:
            # Open the file and read in the usernames and passwords
            with open(userInfo, "r") as file:
                for line in file:
                    username, password = line.strip().split(",")
                    users[username] = password
        # If the file isnt found open a new one
        except FileNotFoundError:
            open(userInfo, "w").close()
        return users


# Save a user to the file
def saveUser(username, password):
    with userLock:
        with open(userInfo, "a") as file:
            file.write(f"{username},{password}\n")


# Send a message to all users
def broadcast(message, sender):
    with loggedInLock:
        # If the user is logged in send them the message
        for user, sock in loggedIn.items():
            if user != sender and sender not in blocked.get(user, set()):
                sock.send(f"{sender}: {message}\n".encode())


# Function to send a direct message to a user
def directMessage(sender, reciever, message):
    with blockedLock:
        # If the sender is blocked by the reciever do nothing
        if sender in blocked.get(reciever, set()):
            with loggedInLock:
                # Let the sender know they are blocked
                if sender in loggedIn:
                    loggedIn[sender].send("This user has you blocked.\n".encode())
                return
    with loggedInLock:
        # If the user recieving the message is logged in send it to them with the sender name
        if reciever in loggedIn:
            loggedIn[reciever].send(
                f"(Direct Message from {sender}): {message}\n".encode()
            )
        # If the user is not logged in save the message to the offline message dictionary
        else:
            with offlineMessLock:
                offlineMess.setdefault(reciever, []).append(
                    f"(Direct Message from {sender}): {message}\n."
                )


# --------- Helper functions for the 'special' commands (makes the connection function readable) -------------
def tell(msg, user, conn):
    parts = msg.split(" ", 2)
    if len(parts) < 3:
        # If they use the incorrect format send this
        conn.send("Usage: /tell <username> <message>\n".encode())
    else:
        directMessage(user, parts[1], parts[2])


def exit(user, conn):
    # Disconnect the user if they type exit, make sure other users are aware
    conn.send(b"Goodbye!\n".encode())
    with loggedInLock:
        del loggedIn[user]
    broadcast(f"{user} has left the chat.", "Server")
    conn.close()


def who(conn):
    with loggedInLock:
        conn.send(f'Users online: {", ".join(loggedIn.keys())}\n'.encode())


def motd(conn):
    conn.send(f"{messOfTheDay}\n".encode())


def help(conn):
    conn.send(
        "Available commands: /who, /exit, /tell <username> <message>, /motd, /me <emote>, /help, /block <username>, /unblock <username>\n".encode()
    )


def me(msg, user, conn):
    emote = msg[4:].strip()
    if emote:
        # If the wrong format display this to user
        broadcast(f"*{user} {emote}", "Server")
    else:
        conn.send("Usage: /me <emote>\n".encode())


def block(msg, user, conn):
    parts = msg.split(" ", 1)
    if len(parts) != 2:
        conn.send("Usage: /block <username>\n".encode)
    else:
        blockUser = parts[1]
        with blockedLock:
            # If the user tried to block themself make it invalid
            if blockUser == user:
                conn.send("You cannot block yourself!".encode())
            # If the user exists then add them to the blocked dictionary
            elif blockUser in loggedIn or blockUser in users:
                blocked[user].add(blockUser)
                conn.send(f"You have blocked {blockUser}.\n".encode())
            # If the user doesnt exist go here
            else:
                conn.send("User not found.\n".encode())


def unblock(msg, user, conn):
    # Grab the user
    parts = msg.split(" ", 1)

    # If invoked incorrectly let them know
    if len(parts) < 2:
        conn.send("Usage: /unblock <username>\n".encode())
    # If invoked correctly
    else:
        # Grab the user
        unblockUser = parts[1]
        with blockedLock:
            # If the users username dont allow
            if unblockUser == user:
                conn.send("You cannot unblock yourself.\n".encode())
            # If not seld then make sure it exists in the users blocked dictionary
            elif unblockUser in blocked.get(user, set()):
                blocked[user].remove(unblockUser)
                conn.send(f"You have unblocked {unblockUser}.\n".encode())
            # If the user is not blocked
            else:
                conn.send("User is not blocked.\n".encode())


# --------------- Function to handle the commands that come from the user ---------------------
def handleCommand(clientSock, clientAddr, username):
    # Main while loop to keep the chat itself running
    while True:
        try:
            # Wait for client messages/instructions
            message = clientSock.recv(1024).decode().strip()

            # Section to handle special instructions
            if message.lower() == "/exit":
                exit(username, clientSock)
                break
            # If statement to handle DM's
            elif message.lower().startswith("/tell "):
                tell(message, username, clientSock)

            # List the current online users
            elif message.lower() == "/who":
                who(clientSock)

            # Send the message of the day
            elif message.lower() == "/motd":
                motd(clientSock)

            # Display available commands
            elif message.lower() == "/help":
                help(clientSock)
            # Emote
            elif message.lower().startswith("/me "):
                me(message, username, clientSock)

            # Handles blocking users
            elif message.lower().startswith("/block "):
                block(message, username, clientSock)

            # Handles unblocking blocked users
            elif message.lower().startswith("/unblock "):
                unblock(message, username, clientSock)

            # If not a command it is a message to be broadcast to other users
            else:
                broadcast(message, username)

        # If someone should fail disconnect the user and make the chat aware
        except:
            with loggedInLock:
                del loggedIn[username]
            broadcast(f"{username} has disconnected.", "Server")
            break


# ---------------  Main function used to handle the users upon connection to the server ------------------
def connection(clientSock, clientAddr):
    # Load in the Users and declare the global variables
    global loggedIn, failedLogin, timeout, offlineMess, blocked, users
    users = loadUsers()

    try:
        # Grab the username and password from the client
        cliInformation = clientSock.recv(1024).decode().strip().split(" ", 1)
        username, password = cliInformation
        # If not <username> <password> disconnect
        if len(cliInformation) != 2:
            clientSock.send(
                "Invalid format. (username password). Disconnecting.\n".encode()
            )
            clientSock.close()
            return
        # Store the user information
        username, password = cliInformation

        with timeoutLock:
            # If the user has to many failed attempts, block them from attempting again
            if username in timeout and time.time() - timeout[username] < 120:
                clientSock.send("Too many failed attempts. Try again later.\n".encode())
                clientSock.close()
                return

        # If the user is already logged in, do not allow another login
        with loggedInLock:
            if username in loggedIn:
                clientSock.send("User already logged in.\n".encode())
                clientSock.close()
                return

        # If the user exists continue
        if username in users:
            # If the password is correct continue
            if users[username] == password:
                # Add them to logged in and remove any failed attempts from dictionary
                with loggedInLock:
                    loggedIn[username] = clientSock
                with failedLoginLock:
                    failedLogin.pop(clientAddr[0], None)
                with blockedLock:
                    blocked.setdefault(username, set())

                clientSock.send("Welcome to the chat server!\n".encode())
                clientSock.send(f"Message of the Day: {messOfTheDay}.\n".encode())
                print(f"{username} has logged in.")
                broadcast(
                    f"{username} has joined the chat!", "Server"
                )  # Broadcast to other users that someone new logged in

                with offlineMessLock:
                    # Check if the user has any DM's sent while disconnected
                    if username in offlineMess:
                        for msg in offlineMess[username]:
                            clientSock.send(f"{msg}\n".encode())
                        # Remove message once it is sent
                        del offlineMess[username]
                handleCommand(clientSock, clientAddr, username)
            # If the password is incorrect go here
            else:
                with failedLoginLock:
                    # Add to failed login
                    failedLogin.setdefault(clientAddr[0], []).append(time.time())
                    # Keep track of user attempts and if it reaches 3 give them a timeout
                    attempts = [
                        t for t in failedLogin[clientAddr[0]] if time.time() - t < 30
                    ]
                if len(attempts) >= 3:
                    with timeoutLock:
                        # Set the timeout and the time it happened
                        timeout[username] = time.time()
                    clientSock.send(
                        "Too many failed attempts. Try again later.\n".encode()
                    )
                else:
                    # If they have more attempts let them know the password was incorrect
                    clientSock.send("Incorrect password.\n".encode())
                clientSock.close()
        # If the user does not exist, save them and set their password
        else:
            saveUser(username, password)
            with loggedInLock:
                loggedIn[username] = clientSock
            clientSock.send("Account created. Welcome!\n".encode())
            print(f"New user {username} registered and logged in.")
            broadcast(f"{username} has joined the chat!", "Server")
            handleCommand(clientSock, clientAddr, username)

    except:
        clientSock.close()


# ---------------------  Server setup  --------------------------------------

serverSocket = socket(AF_INET, SOCK_STREAM)
serverSocket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
serverSocket.bind(("", port))
serverSocket.listen(32)
print(f"Server listening on port {port}...")

try:
    # Run the server with threads for the users
    while True:
        threading.Thread(
            target=connection, args=(serverSocket.accept()), daemon=True
        ).start()
except KeyboardInterrupt:
    print("\nShutting down server...")
    serverSocket.close()



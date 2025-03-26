import threading
from socket import *
import sys

clientSocket = socket(AF_INET, SOCK_STREAM)
running = True
# Make sure the client provides enough args
if len(sys.argv) != 3:
    print("Usage: python3 bvChat-client.py <username> <password>")

# Grab the username and password from args
username = sys.argv[1]
password = sys.argv[2]
SERVER_IP = "127.0.0.1"  # Needs to be changed based on where the server is hosted
SERVER_PORT = 8008


# Function to handle messages recieved from server
def recv_message(client_socket):
    global running

    while running:
        try:
            msg = client_socket.recv(1024).decode().strip()

            # if no message has actually been recieved exit the loop
            if not msg:
                print("Connection closing...")
                break

            # Print the incoming message in place so it does not cover the prompt
            print(f"\r{msg}\n", end="", flush=True)

            print(f"{username}: ", end="", flush=True)

        except ConnectionResetError:
            print("Lost connection with the server.")
            break
        except Exception as e:
            print("Disconnected from server.")
            break
    client_socket.close()
    running = False  # ideally this should stop whatever thread this is running on


def handle_client(client_socket):
    global running

    try:
        # attempt to connect to the server
        client_socket.connect((SERVER_IP, SERVER_PORT))
        print("Connecting to server...")
        # Give the server the username and password of the client
        credentials = f"{username} {password}"
        client_socket.send(credentials.encode())

        # create a thread that listens for incoming messages via the server
        threading.Thread(target=recv_message, args=(client_socket,), daemon=True).start()
    
        # Loop to wait for input from the user
        while running:
            # Print a prompt for the user
            print(f"{username}: ", end="", flush=True)
            # Grab the message and send to the server
            message = input()
            if message.lower() == "/exit":
                client_socket.send(message.encode())
                break

            client_socket.send(message.encode())
    # Ensure no errors happen if the client disconnects without using /exit
    except ConnectionResetError:
        print(" I've lost connection so sorry <3 -your server")
    except KeyboardInterrupt:
        print("\nLogging out...")
        client_socket.send("/exit".encode())
    except Exception as e:
        print("Connection to server failed.")
        return

    running = False
    client_socket.close()
    print("Connection closed.")


handle_client(clientSocket)
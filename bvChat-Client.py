import threading
from socket import *

clientSocket = socket(AF_INET, SOCK_STREAM)
running = True

def recv_message(client_socket):
    global running

    while running:
        try:
            msg = client_socket.recv(1024)

            # if no message has actually been recieved exit the loop
            if not msg:
                print("Connection closed by someone methinks")
                break

            # print whatever message has been recieved
            print(msg.decode())

        except ConnectionResetError:
            print("lost connection with the server")
            break
        except Exception as e:
            print("there was an error prolly when you disconnected from the server")
            break

    client_socket.close()
    running = False # ideally this should stop whatever thread this is running on



def handle_client(client_socket):
    global running

    # prompt the user for the IP and Port numbers
    try:
        server_info =  input("enter the IP and port of the server: ")
        serverIP, serverPort = server_info.split(" ")
    except ValueError:
        print("enter the IP and port of the server (hint: you need both not one)")
        return

    try:
        #attempt to connect to the server
        client_socket.connect((serverIP, int(serverPort)))
        print("Connected to server!")

    except Exception as e:
        print("couldn't connect to the server plz make sure you entered the IP and port correctly <3")
        return

    # create a thread that listens for incoming messages via the server
    threading.Thread(target=recv_message, args=(client_socket,), daemon=True).start()

    while running:
        try:
            message = input()
            if message.lower() == "/exit":
                client_socket.send(message.encode())
                break

            client_socket.send(message.encode())

        except ConnectionResetError:
            print(" I've lost connection so sorry <3 -your server")
            break

    running = False
    client_socket.close()
    print("Connection closed")


handle_client(clientSocket)
exit()

## BV-Chat
# BV-Chat Server
This file creates a runnable server to create a groupchat application (think Discord) where the user can utilize special subcommands within the chat line
to do one of the following actions:
- /tell - this sends a direct message to another user within the server, if the user is offine the message gets stored unitl they login
- /motd - sends a message of the day, this message is also sent upon logging into the server
- /who - this tells you which users are currently online
- /me - an emoticon of sorts where it prints your username to the beginning of your message (/me is happy -> <username> is happy)
- /block - this command blocks a user so you no longer see thier messages both direct message via /tell or within the greater groupchat
- /unblock - removes a previously blocked user so you can see thier messages again
- /exit - is how the user disconnects from the server
- /help - allows the user to see all available commands

This program uses threading to constantly check for incoming messages and direct them to the proper end-users

# BV-Chat Client
This file is the client side code that continuously listens for incoming messages from the server. it requires that the user connect to the server using the 
command line to input the username and password. With a thread running to constantly attempt to recieve new messages (and plenty of error handling) this program
is capable of handling multiple incoming messages.

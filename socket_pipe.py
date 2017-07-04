import threading
import socket
import errno
import sublime, sublime_plugin

# TODO UdpPipe vs TcpPipe?
class SocketPipe(threading.Thread):
    def __init__(self, view, host, port, type="tcp", initial=None):
        threading.Thread.__init__(self)
        self.running = True
        self.view = view
        self.written_characters = 0
        self.buffer = []
        print(type)
        if type == "tcp":
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        elif type == "tcp6":
            self.sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        elif type == "udp":
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        else:
            raise "Invalid type"
        self.sock.connect((host, port))
        print("Connected SocketPipe to %s:%s" % (host, port))
        
        if(initial):
            print("sending %s" % initial)
            self.sock.send(initial.encode('utf-8'))
    
    def go(self):
        self.update_view()
        self.start()
            
    def update_view(self):
        # update view on a main thread timer
        # self.view.set_read_only(False)
        for b in self.buffer:
            self.view.run_command("socket_insert_text", {"content": b})
            # e = self.view.begin_edit()
            # self.view.insert(e, self.written_characters, b.decode("utf-8"))
            # self.view.end_edit(e)
            # self.written_characters += len(b.decode("utf-8"))
            # self.view.sel().clear()
            # self.view.sel().add(sublime.Region(self.view.size(), self.view.size()))
            # self.view.show(self.view.size())
        self.buffer = []
        
        if self.running:
            sublime.set_timeout(self.update_view, 100)
        
    def on_close(self):
        self.running = False
        self.sock.shutdown(socket.SHUT_RDWR)
        self.sock.close()
    
    def send(self, s):
        self.sock.send(s.encode('utf-8'))
        
    def write(self, s):
        self.buffer.append(s)
        
    def bump(self, s):
        self.written_characters += len(s)
        
    def run(self):
        while self.running:
            try:
                read = self.sock.recv(8012)
                self.buffer.append(read.decode('utf8'))
            except socket.error:
                print("connecting...")
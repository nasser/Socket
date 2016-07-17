import threading
import socket
import errno
import sublime, sublime_plugin
from pipe import pipe_workers

# TODO UdpPipe vs TcpPipe?
class SocketPipe(threading.Thread):
    def __init__(self, view, host, port, type="tcp", initial=None):
        threading.Thread.__init__(self)
        self.running = True
        self.view = view
        self.written_characters = 0
        self.buffer = []
        
        if type == "tcp":
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        elif type == "udp":
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        else:
            raise "Invalid type"
        self.sock.connect((host, port))
        print("Connected SocketPipe to %s:%s" % (host, port))
        
        if(initial):
            print("sending %s" % initial)
            self.sock.send(initial)
    
    def go(self):
        self.update_view()
        self.start()
            
    def update_view(self):
        # update view on a main thread timer
        self.view.set_read_only(False)
        for b in self.buffer:
            e = self.view.begin_edit()
            self.view.insert(e, self.written_characters, b.decode("utf-8"))
            self.view.end_edit(e)
            self.written_characters += len(b.decode("utf-8"))
            self.view.sel().clear()
            self.view.sel().add(sublime.Region(self.view.size(), self.view.size()))
            self.view.show(self.view.size())
        self.buffer = []
        
        self.view.set_read_only(True)
        if self.running:
            sublime.set_timeout(self.update_view, 100)
        
    def on_close(self):
        self.running = False
        if(pipe_workers.has_key(self.view.id())):
            pipe_workers.pop(self.view.id())
        self.sock.shutdown(socket.SHUT_RDWR)
        self.sock.close()
    
    def send(self, str):
        self.sock.send(str)
        
    def write(self, str):
        self.buffer.append(str)
        
    def bump(self, str):
        self.written_characters += len(str)
        
    def run(self):
        while self.running:
            try:
                read = self.sock.recv(8012)
                self.buffer.append(read)
            except socket.error:
                print("connecting...")
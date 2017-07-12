import threading
import socket
import errno
import sublime, sublime_plugin
import re


# TODO UdpPipe vs TcpPipe?
class SocketPipe(threading.Thread):
    def __init__(self, view, host, port, type="tcp", initial=None):
        threading.Thread.__init__(self)
        self.running = True
        self.view = view
        self.written_characters = 0
        self.buffer = []
        self.prompt = 0
        self.hist = 0
        self.history = []

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
        self.setup_view()
        self.update_view()
        self.start()

    def setup_view(self):
        self.view.settings().set("scope_name", "source.clojure")
        self.view.settings().set("line_numbers", False)
        self.view.settings().set("gutter", False)
        self.view.settings().set("word_wrap", False)

    def update_view(self):
        # prevent editing repl view if a selection is before the prompt
        oob = False
        self.view.settings().set("noback", False)
        for region in self.view.sel():
            # backspace is a special case, a sublime-keymap binding checks the 'noback' setting
            if region.a == self.prompt and region.b == region.a:
                self.view.settings().set("noback", True)
            if region.a < self.prompt or region.b < self.prompt:
                oob = True
        if oob:
            self.view.set_read_only(True)
        else:
            self.view.set_read_only(False)
        for b in self.buffer:
            self.view.run_command("socket_insert_text", {"content": b})
        self.buffer = []
        if self.running:
            sublime.set_timeout(self.update_view, 100)
        
    def on_close(self):
        self.running = False
        self.sock.shutdown(socket.SHUT_RDWR)
        self.sock.close()
    
    def record_history(self, s):
        rx = re.search("[\\n]*$", s)
        if rx:
            s = s[:len(rx.group()) * -1]
        hlen = len(self.history)
        if s != "" and (hlen == 0 or (hlen > 0 and s != self.history[hlen-1])):
            self.history.append(s)
            self.hist = 0

    def send(self, s):
        self.record_history(s)
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
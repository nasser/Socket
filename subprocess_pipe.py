import subprocess
import threading
import socket
import errno
import sublime, sublime_plugin
from pipe import pipe_workers

# TODO Pipe superclass?
class SubprocessPipe(threading.Thread):
    def __init__(self, view, cmd, args=[], initial=None):
        threading.Thread.__init__(self)
        self.running = True
        self.view = view
        self.written_characters = 0
        self.buffer = []
        
        self.proc = subprocess.Popen([cmd] + args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        if(initial):
            self.proc.stdin.write(initial)
    
    def go(self):
        self.update_view()
        self.start()
            
    def update_view(self):
        # update view on a main thread timer
        self.view.set_read_only(False)
        for b in self.buffer:
            e = self.view.begin_edit()
            self.view.insert(e, self.written_characters, b)
            self.view.end_edit(e)
            self.written_characters += len(b)
            self.view.sel().clear()
            self.view.sel().add(sublime.Region(self.view.size(), self.view.size()))
            self.view.show(self.view.size())
        self.buffer = []
        self.view.set_read_only(True)
        if self.running:
            sublime.set_timeout(self.update_view, 100)
        
    def on_close(self):
        self.running = False
        print pipe_workers
        pipe_workers.pop(self.view.id())
        self.sock.shutdown(socket.SHUT_RDWR)
        self.sock.close()
    
    def send(self, str):
        self.proc.stdin.write(str)
        
    def write(self, str):
        self.buffer.append(str)
        
    def bump(self, str):
        self.written_characters += len(str)
        
    def run(self):
        while self.running:
            read = self.proc.stdout.read(1) # TODO stderr?
            self.buffer.append(read)
import sublime, sublime_plugin
from Socket.socket_pipe import SocketPipe
from Socket.workers import socket_workers, view_connections

def text_at_current_line(view):
  return view.substr(view.line(view.sel()[0])).strip()
  
def text_at_current_selections(view):
  return "".join([view.substr(s) for s in view.sel()])
  
def all_text(view):
  return view.substr(sublime.Region(0, view.size()))
  
def all_socket_views(syntax=None, view_id=None):
    views = []
    for window in sublime.windows():
        for view in window.views():
            if view.settings().get("socket"):
                if (syntax == None or view.settings().get("syntax") == syntax) and (view_id == None or view.id() == view_id):
                    views.append(view)
    return views

class SocketConnectCommand(sublime_plugin.WindowCommand):
    def select_view(self, i):
        views = [v.view for v in socket_workers.values()]
        view_connections[self.window.active_view().id()] = views[i].id()
        self.window.active_view().set_status("socket", "Connected to %s " % views[i].name())
        original_view = self.window.active_view()
        self.window.focus_view(views[i])
        self.window.focus_view(original_view)
        
    def run(self):
        if(len(socket_workers) == 1):
            only_view = list(socket_workers.values())[0].view
            view_connections[self.window.active_view().id()] = only_view.id()
            self.window.active_view().set_status("socket", "Connected to %s " % only_view.name())
            original_view = self.window.active_view()
            self.window.focus_view(only_view)
            self.window.focus_view(original_view)
            
        elif(len(socket_workers) > 0):
            names = [[v.view.name(), v.view.substr(v.view.line(v.view.size()))] for v in list(socket_workers.values())]
            source_view = self.window.active_view()
            self.window.show_quick_panel(names, self.select_view)


class SocketSendBaseCommand(sublime_plugin.TextCommand):
    def text(self):
        return ""
        
    def run(self, edit, show_code=False):
        try:
            for socket_view in all_socket_views(view_id=view_connections[self.view.id()]):
                w = socket_workers[socket_view.id()]
                s = self.text()
                if show_code:
                    w.write(s)
                w.send(s)
        except KeyError:
            # TODO attempt auto-connect
            if(len(socket_workers) == 1):
                only_view = socket_workers.values()[0].view
                view_connections[self.window.active_view().id()] = only_view.id()
                window.active_view().set_status("socket", "Connected to %s " % only_view.name())
            else:
                print("no socket connection")

    
class SocketInsertTextCommand(sublime_plugin.TextCommand):
    def __init__(self, view):
        self.view = view
        self.written_characters = 0
        
    def run(self, edit, content=""):
        self.view.set_read_only(False)
        self.view.insert(edit, self.written_characters, content)
        self.view.set_read_only(True)
        self.written_characters += len(content)
        self.view.sel().clear()
        self.view.sel().add(sublime.Region(self.view.size(), self.view.size()))
        self.view.show(self.view.size())
    
class SocketSendSelectionCommand(SocketSendBaseCommand):
    def text(self):
        return text_at_current_selections(self.view) + "\n"
            
class SocketSendLineCommand(SocketSendBaseCommand):
    def text(self):
        return text_at_current_line(self.view) + "\n"
        
class SocketSendFileCommand(SocketSendBaseCommand):
    def text(self):
        print(all_text(self.view) + "\n")
        return all_text(self.view) + "\n"
        
class SocketSendBlockCommand(SocketSendBaseCommand):
    def text(self):
        old_sel = list(self.view.sel())
        self.view.run_command("expand_selection", {"to": "brackets"})
        self.view.run_command("expand_selection", {"to": "brackets"})
        str = text_at_current_selections(self.view) + "\n"
        self.view.sel().clear()
        for s in old_sel:
            self.view.sel().add(s)
        return str
        
class SocketSendParagraphCommand(SocketSendBaseCommand):
    def text(self):
        old_sel = list(self.view.sel())
        self.view.run_command("expand_selection_to_paragraph")
        str = text_at_current_selections(self.view) + "\n"
        self.view.sel().clear()
        for s in old_sel:
            self.view.sel().add(s)
        return str

class NewSocketCommand(sublime_plugin.WindowCommand):
    def connect(self, view, to):
        view_connections[view.id()] = to.id()
        view.set_status("socket", "Connected to %s " % to.name())
        
    def run(self, type, port, name=None, syntax="", initial="", host="localhost"):
        original_view = self.window.active_view()
        # https://forum.sublimetext.com/t/set-layout-reference/5713
        self.window.run_command("set_layout", {"rows":[0, 0.75, 1], "cols":[0, 1], "cells":[[0, 0, 1, 1], [0, 1, 1, 2]]})
        self.window.run_command("focus_group", {"group":1})
        if name == None:
            name = "%s:%s" % (host, port)
        socketview = self.window.new_file()
        title = "%s (%d)" % (name, socketview.id())
        socketview.set_scratch(True)
        socketview.settings().set("socket", True)
        socketview.set_read_only(True)
        socketview.set_name(title)
        socketview.set_syntax_file(syntax)
        sp = SocketPipe(socketview, host, port, type, initial)
        sp.go()
        socket_workers[socketview.id()] = sp
        # connect original view to new socket
        self.connect(original_view, socketview)
        self.window.run_command("focus_group", {"group":0})
    
class NewAdHocSocketCommand(sublime_plugin.WindowCommand):
    def launch(self):
        self.window.run_command("new_socket", {"type": self.type, "port": self.port, "host":self.host})
        
    def port_done(self, port):
        self.port = int(port)
        self.launch()
        
    def on_data(self, data):
        if self.host == None:
            self.host = data
            self.window.show_input_panel("Port", "11211", self.on_data, None, None)
        elif self.port == None:
            self.port = int(data)
            self.window.show_input_panel("Protocol", "udp", self.on_data, None, None)
        elif self.type == None:
            self.type = data.lower()
            self.launch()
        
    def run(self):
        self.host = None
        self.port = None
        self.type = None
        self.window.show_input_panel("Host", "localhost", self.on_data, None, None)
    
class SocketReplListener(sublime_plugin.EventListener):
    def on_close(self, view):
        if view.id() in socket_workers:
            socket_workers[view.id()].on_close()
            del socket_workers[view.id()]

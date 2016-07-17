from subprocess_pipe import SubprocessPipe
from socket_pipe import SocketPipe
import sublime, sublime_plugin
from pipe import pipe_workers, view_connections

def text_at_current_line(view):
  return view.substr(view.line(view.sel()[0])).strip().encode('utf-8')
  
def text_at_current_selections(view):
  return "".join([view.substr(s) for s in view.sel()]).encode('utf-8')
  
def all_text(view):
  return view.substr(sublime.Region(0, view.size())).encode('utf-8')
  
def all_pipe_views(syntax=None, view_id=None):
    views = []
    for window in sublime.windows():
        for view in window.views():
            if view.settings().get("pipe"):
                if (syntax == None or view.settings().get("syntax") == syntax) and (view_id == None or view.id() == view_id):
                    views.append(view)
    return views

class PipeConnectCommand(sublime_plugin.WindowCommand):
    def select_view(self, i):
        views = [v.view for v in pipe_workers.values()]
        view_connections[self.window.active_view().id()] = views[i].id()
        self.window.active_view().set_status("pipe", "Connected to %s " % views[i].name())
        
    def run(self):
        if(len(pipe_workers) == 1):
            only_view = pipe_workers.values()[0].view
            view_connections[self.window.active_view().id()] = only_view.id()
            self.window.active_view().set_status("pipe", "Connected to %s " % only_view.name())
            
        elif(len(pipe_workers) > 0):
            names = [[v.view.name(), v.view.substr(v.view.line(v.view.size()))] for v in pipe_workers.values()]
            source_view = self.window.active_view()
            
            self.window.show_quick_panel(names, self.select_view)

class PipeSendBaseCommand(sublime_plugin.TextCommand):
    def text(self):
        return ""
        
    def run(self, edit, show_code=False):
        try:
            for pipe_view in all_pipe_views(view_id=view_connections[self.view.id()]):
                pw = pipe_workers[pipe_view.id()]
                str = self.text()
                if show_code:
                    pw.write(str)
                pw.send(str)
        except KeyError, e:
            # TODO attempt auto-connect
            if(len(pipe_workers) == 1):
                only_view = pipe_workers.values()[0].view
                view_connections[self.window.active_view().id()] = only_view.id()
                window.active_view().set_status("pipe", "Connected to %s " % only_view.name())
            else:
                print "no pipe connection"

    
class PipeSendSelectionCommand(PipeSendBaseCommand):
    def text(self):
        return text_at_current_selections(self.view) + "\n"
            
class PipeSendLineCommand(PipeSendBaseCommand):
    def text(self):
        return text_at_current_line(self.view) + "\n"
        
class PipeSendFileCommand(PipeSendBaseCommand):
    def text(self):
        print all_text(self.view) + "\n"
        return all_text(self.view) + "\n"
        
class PipeSendBlockCommand(PipeSendBaseCommand):
    def text(self):
        old_sel = list(self.view.sel())
        self.view.run_command("expand_selection", {"to": "brackets"})
        self.view.run_command("expand_selection", {"to": "brackets"})
        str = text_at_current_selections(self.view) + "\n"
        self.view.sel().clear()
        for s in old_sel:
            self.view.sel().add(s)
        return str
        
class PipeSendParagraphCommand(PipeSendBaseCommand):
    def text(self):
        old_sel = list(self.view.sel())
        self.view.run_command("expand_selection_to_paragraph")
        str = text_at_current_selections(self.view) + "\n"
        self.view.sel().clear()
        for s in old_sel:
            self.view.sel().add(s)
        return str

class NewSubprocessPipeCommand(sublime_plugin.WindowCommand):
    def run(self, cmd, args=[], name=None, syntax="", initial=""):
        if name == None:
            name = cmd
        pipeview = self.window.new_file()
        pipeview.set_scratch(True)
        pipeview.settings().set("pipe", True)
        pipeview.set_read_only(True)
        pipeview.set_name("%s (%d)" % (name, pipeview.id()))
        pipeview.set_syntax_file(syntax)
        sp = SubprocessPipe(pipeview, cmd, args, initial)
        sp.go()
        pipe_workers[pipeview.id()] = sp


class NewSocketPipeCommand(sublime_plugin.WindowCommand):
  def run(self, type, port, name=None, syntax="", initial="", host="localhost"):
    if name == None:
        name = "%s:%s" % (host, port)
    pipeview = self.window.new_file()
    pipeview.set_scratch(True)
    pipeview.settings().set("pipe", True)
    pipeview.set_read_only(True)
    pipeview.set_name("%s (%d)" % (name, pipeview.id()))
    pipeview.set_syntax_file(syntax)
    sp = SocketPipe(pipeview, host, port, type, initial)
    sp.go()
    pipe_workers[pipeview.id()] = sp
    
class PipeReplListener(sublime_plugin.EventListener):
    def on_close(self, view):
        pipe_workers[view.id()].on_close()
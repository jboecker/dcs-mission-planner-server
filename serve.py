import tornado
import tornado.web
import tornado.websocket
import tornado.ioloop
import json
import sys
import os
import subprocess
import zipfile
from pprint import pformat
import io

def findlua():
    for lua in ["/usr/bin/lua", "/app/vendor/lua/bin/lua"]:
        if os.path.isfile(lua):
            return lua
    raise RuntimeError("could not find lua interpreter")
findlua()


class IndexHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("index.html")

class WebsocketEchoHandler(tornado.websocket.WebSocketHandler):
    def open(self):
        pass
        
    def on_message(self, message):
        self.write_message(message.upper())
    
    def on_close(self):
        pass

class MissionLoadTest(tornado.web.RequestHandler):
    def get(self):
        miz = zipfile.ZipFile("missions/opr-free_maykop-coop16.miz")
        mission_str = miz.read("mission")
        miz.close()
        
        p = subprocess.Popen([findlua(), "lua2json.lua"], cwd="lua", stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        stdoutdata, stderrdata = p.communicate(input=mission_str, timeout=20)
        
        missiondata = json.loads(stdoutdata.decode("utf-8"))
        
        self.set_header("Content-Type", "text/plain")
        self.write(pformat(missiondata))

class MissionDownloadTest(tornado.web.RequestHandler):
    def get(self):
        miz_buffer = io.BytesIO()
        miz = zipfile.ZipFile(miz_buffer, "a")

        miz_src = zipfile.ZipFile("missions/opr-free_maykop-coop16.miz", "r")
        for zipinfo in miz_src.infolist():
            if zipinfo.filename == "mission":
                miz.writestr("mission", "Hello, World!")
            else:
                miz.writestr(zipinfo, miz_src.read(zipinfo))
            
        miz_src.close()
        miz.close()
        
        self.set_header("Content-Type", "application/octet-stream")
        self.set_header("Content-Disposition", 'attachment; filename="opr-free_maykop-coop16_planned.miz"')
        self.write(miz_buffer.getvalue())
    
app = tornado.web.Application([
    (r'/', IndexHandler),
    (r'/js/(.*)', tornado.web.StaticFileHandler, {'path': 'js/'}),
    (r'/ws/echo', WebsocketEchoHandler),
    (r'/loadtest', MissionLoadTest),
    (r'/dltest', MissionDownloadTest),
])

if __name__ == "__main__":
    app.listen(int(sys.argv[1]))
    tornado.ioloop.IOLoop.instance().start()

import tornado
import tornado.web
import tornado.websocket
import tornado.ioloop
import json
import sys

class IndexHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("index.html")

class WebsocketEchoHandler(tornado.websocket.WebSocketHandler):
    def on_message(self, message):
        self.write_message(message.upper())


app = tornado.web.Application([
    (r'/', IndexHandler),
    (r'/js/(.*)', tornado.web.StaticFileHandler, {'path': 'js/'}),
    (r'/ws/echo', WebsocketEchoHandler),
])

if __name__ == "__main__":
    app.listen(int(sys.argv[1]))
    tornado.ioloop.IOLoop.instance().start()

import tornado
import tornado.web
import tornado.ioloop
import json
import sys

class IndexHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("index.html")


app = tornado.web.Application([
    (r'/', IndexHandler),
])

if __name__ == "__main__":
    app.listen(int(sys.argv[1]))
    tornado.ioloop.IOLoop.instance().start()

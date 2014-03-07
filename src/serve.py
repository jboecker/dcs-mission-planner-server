import tornado
import tornado.web
import tornado.websocket
import tornado.ioloop
import tornado.template
import json
import sys
import os
import subprocess
import zipfile
from pprint import pformat
import pprint
import io
import keyvaluestore as kv
from util import base36encode
import util
import pyproj
dcs_proj =  pyproj.Proj("+proj=tmerc +lat_0=0 +lon_0=33 +k_0=0.9996 +x_0=-99517 +y_0=-4998115")

next_id_prefix_int = 2

logged_in_websockets = []

class IndexHandler(tornado.web.RequestHandler):
    def fail_auth(self, instance_id=""):
        self.set_header("WWW-Authenticate", 'Basic realm="Mission Planner Instance '+instance_id+'"')
        self.set_status(401)

        
    def get(self):
        instance_id = self.get_argument("instance_id")
        instance_json = kv.get("instance-"+instance_id, None)
        if instance_json is None:
            return self.send_error(404)
        instance = json.loads(instance_json)
        
        auth_header = self.request.headers.get("Authorization", None)
        host_header = self.request.headers.get("Host")
        if not auth_header:
            return self.fail_auth(instance_id)

        import base64
        username, password = base64.decodestring(auth_header.split(" ")[1].encode("ascii")).decode("utf-8").split(":")
        
        if username not in ("blue", "red", "admin"):
            return self.fail_auth(instance_id)
        if instance[username+"_pw"] != password:
            return self.fail_auth(instance_id)
            
        self.render("templates/instance.html", username=username, instance_id=instance_id, instance=instance, host=host_header, protocol=self.request.protocol)

class AirportsKmlHandler(tornado.web.RequestHandler):
    def get(self):
        with open("airports.kml", "r") as f:
            self.set_header("Access-Control-Allow-Origin", "*")
            self.set_header("Access-Control-Allow-Headers", self.request.headers.get("Access-Control-Request-Headers", "*"))
            self.write(f.read())
            self.finish()
    def options(self):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", self.request.headers.get("Access-Control-Request-Headers", "*"))
        self.set_header("Allow", "GET")
        self.finish()

class WebsocketHandler(tornado.websocket.WebSocketHandler):
    def filter_objects(self, objects):
        """
        Filter out all objects that should only be visible to the other side.
        Assumes that this connection is logged in, i.e. self.coalition has been set.
        """
        ret = {}
        for key in objects:
            if "visibility" in objects[key] and objects[key]["visibility"] != self.coalition:
                pass
            else:
                ret[key] = objects[key]
        return ret
        
    def filter_data(self, data):
        ret = json.loads(json.dumps(data))
        ret["objects"] = self.filter_objects(ret["objects"])
        return ret

    def filter_tx(self, tx):
        ret = json.loads(json.dumps(tx))
        ret["updated_data"] = self.filter_objects(ret["updated_data"])
        return ret


    def open(self):
        self.instance_id = None
        self.coalition = None

    def on_message(self, message_str):
        msg = json.loads(message_str)
        if "request" not in msg or "request_id" not in msg:
            self.write_message('{ "success": false, "error_msg": "request or request_id not specified." }')
            return

        request_id = msg["request_id"]
        ret_msg = {}
        
        if not hasattr(self, 'handle_'+msg["request"]+'_request'):
            ret_msg = {"success": False, "error_msg": "invalid request type"}
        else:
            ret_msg = getattr(self, 'handle_'+msg["request"]+'_request')(msg)
            
        ret_msg["request_id"] = request_id
        self.write_message(json.dumps(ret_msg))

    def handle_ping_request(self, msg):
        return { "success": True }

    def handle_create_instance_request(self, msg):
        instance_id = kv.get("next_instance_id") or "1"
        kv.set("next_instance_id", base36encode(int(instance_id, 36) + 1))
        
        instance = {}
        instance["id"] = instance_id
        instance["mizname"] = msg["filename"]
        instance["mizhash"] = msg["md5hash"]
        if msg["no_passwords"]:
            instance["red_pw"] = ""
            instance["blue_pw"] = ""
            instance["admin_pw"] = ""
        else:
            instance["red_pw"] = util.makepw()
            instance["blue_pw"] = util.makepw()
            instance["admin_pw"] = util.makepw()
        
        instance["data"] = msg["data"]
        
        for obj in instance["data"]["objects"].values():
            if "x" in obj and "z" in obj:
                lon, lat = dcs_proj(obj["z"], obj["x"], inverse=True)
                obj["lon"] = lon
                obj["lat"] = lat
                del obj["z"]
                del obj["x"]
        
        kv.set("instance-"+instance_id, json.dumps(instance))

        instance_list = json.loads(kv.get("instance-list", "[]"))
        instance_list.append(instance_id)
        
        kv.set("instance-list", json.dumps(instance_list))
        
        return { "success": True,
                 "instance_id": instance_id,
                 "red_pw": instance["red_pw"],
                 "blue_pw": instance["blue_pw"],
                 "admin_pw": instance["admin_pw"],
        }
        
    def handle_instance_info_request(self, msg):
        instance = json.loads(kv.get("instance-"+msg["instance_id"]))
        admin_pw = msg["admin_pw"]
        
        # verify password
        if admin_pw != instance["admin_pw"]:
            return { "success": False, "error_msg": "Invalid password." }
        
        return { "success":True, "instance_id": msg["instance_id"], "admin_pw":instance["admin_pw"], "blue_pw":instance["blue_pw"], "red_pw":instance["red_pw"] }

    def handle_save_mission_request(self, msg):
        instance = json.loads(kv.get("instance-"+msg["instance_id"]))
        admin_pw = msg["admin_pw"]
        
        # verify password
        if admin_pw != instance["admin_pw"]:
            return { "success": False, "error_msg": "Invalid password." }
        
        data_copy = json.loads(json.dumps(instance["data"]))
        for obj in data_copy["objects"].values():
            if "lat" in obj and "lon" in obj:
                z, x = dcs_proj(obj["lon"], obj["lat"])
                obj["z"] = z
                obj["x"] = x

        return { "success": True, "data": data_copy, "filename": instance["mizname"], "md5hash": instance["mizhash"] }

    def handle_set_mission_state_request(self, msg):
        instance = json.loads(kv.get("instance-"+msg["instance_id"]))
        admin_pw = msg["admin_pw"]
        
        # verify password
        if admin_pw != instance["admin_pw"]:
            return { "success": False, "error_msg": "Invalid password." }

        instance["data"]["missionState"] = msg["missionState"]
        kv.set("instance-"+msg["instance_id"], json.dumps(instance))
        
        return { "success": True }

    def handle_login_request(self, msg):
        global next_id_prefix_int
        
        instance_json = kv.get("instance-"+msg["instance_id"])
        if not instance_json:
            return {"success": False, "error_msg": "instance does not exist."}
        instance = json.loads(instance_json)
        if instance[msg["coalition"]+"_pw"] == msg["password"]:
            self.instance_id = msg["instance_id"]
            self.coalition = msg["coalition"]
            logged_in_websockets.append(self)
            id_prefix = base36encode(next_id_prefix_int) + "/"
            next_id_prefix_int += 1
            return {"success": True, "data": self.filter_data(instance["data"]), "id_prefix": id_prefix}
        else:
            return {"success": False, "error_msg": "invalid password."}
            
    def handle_transaction_request(self, msg):
        instance = json.loads(kv.get("instance-"+self.instance_id))
        if not instance:
            return {"success": False, "error_msg": "instance does not exist."}

        for key in msg["transaction"]["deleted_object_ids"]:
            if key not in instance["data"]["objects"]:
                return {"success": True, "transaction_applied": False, "log": "object already deleted: %s" % key}

        for key, value in msg["transaction"]["preconditions"].items():
            if key not in instance["data"]["objects"]:
                return {"success": True, "transaction_applied": False, "log": "object to be updated does not exist: %s" % key}
            if pformat(value) != pformat(instance["data"]["objects"][key]):
                pprint.pprint(value)
                pprint.pprint(instance["data"]["objects"][key])
                return {"success": True, "transaction_applied": False, "log": "precondition not met: %s" % key}
                
        for key, value in msg["transaction"]["updated_data"].items():
            instance["data"]["objects"][key] = msg["transaction"]["updated_data"][key]
            
        for key in msg["transaction"]["deleted_object_ids"]:
            del instance["data"]["objects"][key]
            
        instance["data"]["version"] += 1
        kv.set("instance-"+self.instance_id, json.dumps(instance))
        
        changeset = msg["transaction"]
        changeset["version_after"] = instance["data"]["version"]
        changeset_str = json.dumps({
            "type": "changeset",
            "changeset": changeset
        })
        for ws in logged_in_websockets:
            if ws != self:
                try:
                    ws.write_message(changeset_str)
                except:
                    print("Error sending changeset.")
                    pass
        
        return { "success": True, "transaction_applied": True, "changeset": changeset }

    def on_close(self):
        if self in logged_in_websockets:
            logged_in_websockets.remove(self)

    
app = tornado.web.Application([
    (r'/', IndexHandler),
    (r'/js/(.*)', tornado.web.StaticFileHandler, {'path': 'js/'}),
    (r'/websocket/', WebsocketHandler),
    (r'/airports.kml', AirportsKmlHandler),
],
debug = True)

if __name__ == "__main__":
    app.listen(int(sys.argv[1]))
    print("Server running @ port {0} - Hit CTRL-C to quit".format(int(sys.argv[1])))
    tornado.ioloop.IOLoop.instance().start()

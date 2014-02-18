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

mizdict = {
    "opr-free_maykop-coop16.miz":"Operation Free Maykop",
    "specops-convoy.miz": "Specops Convoy",
}
MAX_INSTANCES = 500
next_id_prefix_int = 2

logged_in_websockets = []

def findlua():
    for lua in ["/usr/bin/lua", "/app/vendor/lua/bin/lua"]:
        if os.path.isfile(lua):
            return lua
    raise RuntimeError("could not find lua interpreter")
findlua()

class IndexHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("index.html", mizlist=list(mizdict.items()))

class CreateInstanceHandler(tornado.web.RequestHandler):
    def post(self):
        instance_id = kv.get("next_instance_id") or "1"
        kv.set("next_instance_id", base36encode(int(instance_id, 36) + 1))
        
        instance = {}
        instance["id"] = instance_id
        instance["miz"] = self.get_argument("miz")
        instance["mizname"] = mizdict[instance["miz"]]
        if self.get_argument("no_passwords", None) == "on":
            instance["red_pw"] = ""
            instance["blue_pw"] = ""
            instance["admin_pw"] = ""
        else:
            instance["red_pw"] = util.makepw()
            instance["blue_pw"] = util.makepw()
            instance["admin_pw"] = util.makepw()
        
        miz = zipfile.ZipFile(os.path.join("missions", instance["miz"]))
        mission_str = miz.read("mission")
        miz.close()
        
        p = subprocess.Popen([findlua(), "load_mission.lua"], cwd="lua", stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        stdoutdata, stderrdata = p.communicate(input=mission_str, timeout=20)
        
        instance["data"] = json.loads(stdoutdata.decode("utf-8"))
        
        for obj in instance["data"]["objects"].values():
            if "x" in obj and "z" in obj:
                obj["lon"], obj["lat"] = dcs_proj(obj["z"], obj["x"], inverse=True)
                del obj["z"]
                del obj["x"]
        
        kv.set("instance-"+instance_id, json.dumps(instance))

        instance_list = json.loads(kv.get("instance-list", "[]"))
        instance_list.append(instance_id)
        while len(instance_list) > MAX_INSTANCES:
            kv.set("instance-"+instance_list[0], None)
            del instance_list[0]
        kv.set("instance-list", json.dumps(instance_list))
        self.render("create_instance.html", instance=instance)

class InstanceListHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("json.html", data=json.loads(kv.get("instance-list")))
        
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

    def handle_login_request(self, msg):
        global next_id_prefix_int
        
        instance = json.loads(kv.get("instance-"+msg["instance_id"]))
        if not instance:
            return {"success": False, "error_msg": "instance does not exist."}
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
        logged_in_websockets.remove(self)

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

class DownloadHandler(tornado.web.RequestHandler):
    def get(self):
        instance = json.loads(kv.get(self.get_argument("instance_id")))
        admin_pw = self.get_argument("password")
        
        # verify password
        if admin_pw != instance["admin_pw"]:
            raise tornado.web.HTTPError(403)


        miz_buffer = io.BytesIO()
        miz = zipfile.ZipFile(miz_buffer, "a")
        miz_src = zipfile.ZipFile(os.path.join("missions", instance["miz"]), "r")

        
        # write temp input files for save_mission.lua
        data_copy = json.loads(json.dumps(instance["data"]))
        for obj in data_copy["objects"].values():
            if "lat" in obj and "lon" in obj:
                z, x = dcs_proj(obj["lon"], obj["lat"])
                obj["z"] = z
                obj["x"] = x

        with open("lua/json.tmp", "w") as json_file:
            json_file.write(json.dumps(instance["data"]))
        with open("lua/mission.tmp", "wb") as mission_file:
            mission_file.write(miz_src.read("mission"))


        for zipinfo in miz_src.infolist():
            if zipinfo.filename == "mission":
                # call save_mission.lua
                p = subprocess.Popen([findlua(), "save_mission.lua"], cwd="lua",
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE)
                stdoutdata, stderrdata = p.communicate(timeout=20)
                mission_str = stdoutdata.decode("utf-8")
                miz.writestr("mission", mission_str)
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
    (r'/websocket/', WebsocketHandler),
    (r'/create_instance/', CreateInstanceHandler),
    (r'/instance_list/', InstanceListHandler),
    (r'/download/', DownloadHandler),
],
debug = True)

if __name__ == "__main__":
    app.listen(int(sys.argv[1]))
    tornado.ioloop.IOLoop.instance().start()

import keyvaluestore as kv
import json
import util

def upgrade():
    upgrader = Upgrader()
    instance_list = json.loads(kv.get("instance-list", "[]"))
    for instance_id in instance_list:
        upgraded = False
        instance = json.loads(kv.get("instance-"+instance_id))
        schema_version = instance.get("schema_version", 0)
        while schema_version < 1:
            print("upgrading %s from %d to %d" % (instance_id, schema_version, schema_version+1))
            getattr(upgrader, "upgrade_%d_to_%d" % (schema_version, schema_version+1))(instance)
            schema_version = instance.get("schema_version", 0)
            upgraded = True
        if upgraded:
            kv.set("instance-"+instance_id, json.dumps(instance))

class Upgrader:
    def upgrade_0_to_1(self, instance):
        instance["red_spectator_pw"] = util.makepw()
        instance["blue_spectator_pw"] = util.makepw()
        instance["schema_version"] = 1

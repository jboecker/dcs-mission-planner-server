-- save_mission.lua
-- read JSON data with mission file and objects from STDIN,
-- write edited mission file to STDOUT

function table.show(t, name, indent)
   local cart     -- a container
   local autoref  -- for self references

   --[[ counts the number of elements in a table
   local function tablecount(t)
      local n = 0
      for _, _ in pairs(t) do n = n+1 end
      return n
   end
   ]]
   -- (RiciLake) returns true if the table is empty
   local function isemptytable(t) return next(t) == nil end

   local function basicSerialize (o)
      local so = tostring(o)
      if type(o) == "function" then
         local info = debug.getinfo(o, "S")
         -- info.name is nil because o is not a calling level
         if info.what == "C" then
            return string.format("%q", so .. ", C function")
         else 
            -- the information is defined through lines
            return string.format("%q", so .. ", defined in (" ..
                info.linedefined .. "-" .. info.lastlinedefined ..
                ")" .. info.source)
         end
      elseif type(o) == "number" or type(o) == "boolean" then
         return so
      else
         return string.format("%q", so)
      end
   end

   local function addtocart (value, name, indent, saved, field)
      indent = indent or ""
      saved = saved or {}
      field = field or name

      cart = cart .. indent .. field

      if type(value) ~= "table" then
         cart = cart .. " = " .. basicSerialize(value) .. ";\n"
      else
         if saved[value] then
            cart = cart .. " = {}; -- " .. saved[value] 
                        .. " (self reference)\n"
            autoref = autoref ..  name .. " = " .. saved[value] .. ";\n"
         else
            saved[value] = name
            --if tablecount(value) == 0 then
            if isemptytable(value) then
               cart = cart .. " = {};\n"
            else
               cart = cart .. " = {\n"
               for k, v in pairs(value) do
                  k = basicSerialize(k)
                  local fname = string.format("%s[%s]", name, k)
                  field = string.format("[%s]", k)
                  -- three spaces between levels
                  addtocart(v, fname, indent .. "   ", saved, field)
               end
               cart = cart .. indent .. "};\n"
            end
         end
      end
   end

   name = name or "__unnamed__"
   if type(t) ~= "table" then
      return name .. " = " .. basicSerialize(t)
   end
   cart, autoref = "", ""
   addtocart(t, name, indent)
   return cart .. autoref
end









local function find_heli_or_plane_group(name)
   for k, coalition_name in pairs({"red", "blue"}) do
      for country_id=1,#mission.coalition[coalition_name].country do
         for _, heli_or_plane in pairs({"helicopter", "plane"}) do
            
            if mission.coalition[coalition_name].country[country_id][heli_or_plane] then
               for group_id=1,#mission.coalition[coalition_name].country[country_id][heli_or_plane].group do
                  if mission.coalition[coalition_name].country[country_id][heli_or_plane].group[group_id].name == name then
                     return coalition_name, country_id, heli_or_plane, group_id
                     --return "mission.coalition."..coalition_name..".country["..country_id.."].plane.group["..group_id.."]"
                  end
               end
            end
            
         end
      end
   end
   return nil, nil, nil, nil
end


















local JSON = loadfile("JSON.lua")()
json_file = io.open("json.tmp", "r")
data = JSON:decode(json_file:read("*all"))
json_file:close()

local env = {}
local func = loadfile("mission.tmp", nil, env)
func()
mission = env.mission


print("working...")

local routes = {}
local second_waypoints_by_group_name = {}
for _, obj in pairs(data.objects) do
   if obj.type == "CLIENT_ACFT_ROUTE" then
      routes[obj.group_name] = obj.id
      local first_wpt = data.objects[obj.first_waypoint_id]
      if first_wpt.next_waypoint_id ~= "" then
         second_waypoints_by_group_name[obj.group_name] = data.objects[first_wpt.next_waypoint_id]
      end
   end
end



for group_name, route in pairs(routes) do
   local coalition_name, country_id, heli_or_plane, group_id = find_heli_or_plane_group(group_name)
   if coalition_name and country_id and heli_or_plane and group_id then -- there is a group with this name!
      
      -- delete existing waypoints
      local points = mission.coalition[coalition_name].country[country_id][heli_or_plane].group[group_id].route.points
      for i = #points,2,-1 do
         points[i] = nil
      end
      
      -- add new waypoints
      
      local wpt = second_waypoints_by_group_name[group_name]
      local i = 2
      while wpt do
         local n = i - 2
         local name = wpt.name
         if name == "" then name = nil end
         
         mission.coalition[coalition_name].country[country_id][heli_or_plane].group[group_id].route.points[i] = {
            ["x"] = wpt.x,
            ["y"] = wpt.z,
            ["name"] = name,
            ["alt"] = wpt.alt,
            ["type"] = "Turning Point",
            ["action"] = "Turning Point",
            ["alt_type"] = wpt.alt_type,
            ["formation_template"] = "",
            ["properties"] = {
               ["vnav"] = 1,
               ["scale"] = 0,
               ["angle"] = 0,
               ["vangle"] = 0,
               ["steer"] = 2
            },
            ["speed"] = 140,
            ["ETA_locked"] = false,
            ["task"] = {
               ["id"] = "ComboTask",
               ["params"] = {["tasks"] = {}}
            },
            ["speed_locked"] = true
         }
         

         if wpt.next_waypoint_id == "" then
            wpt = nil
            break
         else
            wpt = data.objects[wpt.next_waypoint_id]
            i = i + 1
         end
      end
   end
end

io.write(table.show(mission, 'mission'))

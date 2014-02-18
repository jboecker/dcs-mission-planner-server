-- load_mission.lua
-- read mission file from STDIN, write JSON-encoded mission data to STDOUT

local JSON = loadfile("JSON.lua")()

local last_id = 0
local function new_id()
   last_id = last_id + 1
	return "0/"..last_id
end

local function get_playable_groups(coalition_list)
	local coalition_list = coalition_list or {"red", "blue"}
	
	local playable_groups = {}
    local groupid_to_coalition = {}
	for _, coalition_name in ipairs(coalition_list) do
		local coalition = mission.coalition[coalition_name]
		for _, country in ipairs(coalition.country) do
			if country.plane then
				for _, group in ipairs(country.plane.group) do
					if group.units[1].skill == "Client" then
						playable_groups[#playable_groups+1] = group
                        groupid_to_coalition[group.groupId] = coalition_name
					end
				end
			end
			if country.helicopter then
				for _, group in ipairs(country.helicopter.group) do
					if group.units[1].skill == "Client" then
						playable_groups[#playable_groups+1] = group
                        groupid_to_coalition[group.groupId] = coalition_name
					end
				end
			end
		end
	end
	return playable_groups, groupid_to_coalition
end



local function get_unit_annotations()
	
	local unit_annotations = {}
	for _, coalition_name in ipairs({"red", "blue"}) do
		local coalition = mission.coalition[coalition_name]
		for _, country in ipairs(coalition.country) do
			if country.plane then
				for _, group in ipairs(country.plane.group) do

				end
			end
			if country.helicopter then
				for _, group in ipairs(country.helicopter.group) do

				end
			end
			if country.vehicle then
				for _, group in ipairs(country.vehicle.group) do
					if group.name:match("MP_AIRDEFENCE") then
						unit_annotations[#unit_annotations+1] = {
							["type"] = 'AIRDEFENCE',
							["x"] = group.route.points[1].x,
							["z"] = group.route.points[1].z,
						}
					end
					if group.name:match("MP_ARMOR") then
						unit_annotations[#unit_annotations+1] = {
							["type"] = 'ARMOR',
							["x"] = group.route.points[1].x,
							["z"] = group.route.points[1].z,
						}
					end
				end
			end

		end
	end
	return unit_annotations
end




local env = {}
local func = loadfile(nil, nil, env)
func()
mission = env.mission

data = {
   objects = {},
   version = 1,
   briefing = {
      description = mission.descriptionText,
      blueTask = mission.descriptionBlueTask,
      redTask = mission.descriptionRedTask,
   },
}

-- aircraft waypoints
playable_groups, groupid_to_coalition = get_playable_groups()
for _, group in ipairs(playable_groups) do
   
   local client_acft_route = {
      id = new_id(),
      type = "CLIENT_ACFT_ROUTE",
      group_name = group.name ,
      visibility = groupid_to_coalition[group.groupId]
   }
   data.objects[client_acft_route.id] = client_acft_route
   
   local prev_wpt = nil
   for i, point in ipairs(group.route.points) do
      local wpt = {
         id = new_id(),
         type = "CLIENT_ACFT_WAYPOINT",
         route_id = client_acft_route.id,
         next_waypoint_id = "",
         x = point.x,
         z = point.y,
         alt_type = point.alt_type,
         alt = point.alt,
         name = (point.name or ""),
         visibility = groupid_to_coalition[group.groupId]
      }
      if i == 1 then
         client_acft_route.first_waypoint_id = wpt.id
      end
      data.objects[wpt.id] = wpt
      if prev_wpt ~= nil then
         prev_wpt.next_waypoint_id = wpt.id
      end
      prev_wpt = wpt
   end
end

-- add unit annotations
for _, ua in pairs(get_unit_annotations()) do
   local ann = {
      id = new_id(),
      type = "UNIT",
      unittype = ua.type,
      lat = ua.lat,
      lon = ua.lon
   }
   data.objects[ann.id] = ann
end

for _, coa in pairs({"blue", "red"}) do
   local bullseye = {
      id = new_id(),
      type = "BULLSEYE",
      x = mission.coalition[coa].bullseye.x, 
      z = mission.coalition[coa].bullseye.y,
      coalition = coa,
      visibility = coa,
   }
   data.objects[bullseye.id] = bullseye
end


io.write(JSON:encode(data))

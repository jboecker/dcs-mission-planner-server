local JSON = loadfile("JSON.lua")()
local env = {}

local env = {}
local func = loadfile(nil, nil, env)
func()

testls = {}
for k, v in pairs(env.mission) do
   testls[#testls+1] = k
end

io.write(JSON:encode(testls))

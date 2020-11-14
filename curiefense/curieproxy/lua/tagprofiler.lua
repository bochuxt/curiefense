module(..., package.seeall)

local globals       = require "lua.globals"
local utils         = require "lua.utils"
local rangesbtree   = require "lua.rangesbtree"
local cjson       = require "cjson"
local json_safe   = require "cjson.safe"

local re_match        = utils.re_match
local tag_request     = utils.tag_request
local btree_search    = rangesbtree.btree_search
local json_encode     = json_safe.encode

function match_singles(request_map, list_entry)

  request_map.handle:logDebug(string.format("match_singles request_map %s", json_encode(request_map)))
  request_map.handle:logDebug(string.format("match_singles list_entry %s", json_encode(list_entry)))

  for entry_key, list_entries in pairs(list_entry) do
    request_map.handle:logDebug(string.format("MATCH SINGLES entry_key %s", entry_key))

    -- exact request map
    local entry_match = list_entries[request_map[entry_key]]
    if entry_match then
      return entry_match
    end
    -- exact request map's attr
    entry_match = list_entries[request_map.attrs[entry_key]]
    if entry_match then
      return entry_match
    end

    -- pattern matching for all but ip.
    if entry_key ~= 'ip' then
      for pattern, annotation in pairs(list_entries) do
        local value = request_map.attrs[entry_key]
        if value then
          if re_match(value, pattern) then
            request_map.handle:logDebug(string.format("matched >> match_singles - regex %s %s", value, pattern))
            return annotation
          end
        else
          request_map.handle:logDebug(string.format("request_map.attrs[entry_key] %s -- nil", entry_key))
        end
      end
    end
  end
  -- no match
  return false
end

function match_pairs(request_map, list_entry)

  request_map.handle:logDebug(string.format("match_pairs request_map %s", json_encode(request_map)))
  request_map.handle:logDebug(string.format("match_pairs list_entry %s", json_encode(list_entry)))

  for entry_name, list_entries in pairs(list_entry) do
    for key, valuelist in pairs(list_entries) do
      for _, value in ipairs(valuelist) do
        if request_map[entry_name][key] and value[1] then
          if (request_map[entry_name][key] == value[1] or re_match(request_map[entry_name][key], value[1])) then
            request_map.handle:logDebug(string.format("matched >> match_pairs %s %s", request_map[entry_name][key], value[1]))
            return value[2]
          end
        end
      end
    end
  end
  -- no match
  return false
end


-- unlike singles and ip range, with pairs negation, we must verify the header/arg/cookie exists and yet does not match
-- otherwise,
function negate_match_pairs(request_map, list_entry)
  request_map.handle:logDebug(string.format("negate_match_pairs request_map %s", json_encode(request_map)))
  request_map.handle:logDebug(string.format("negate_match_pairs list_entry %s", json_encode(list_entry)))

  for entry_name, list_entries in pairs(list_entry) do
    for key, valuelist in pairs(list_entries) do
      if (request_map[entry_name][key]) then
        for _, value in ipairs(valuelist) do
          if not re_match(request_map[entry_name][key], value[1]) then
            request_map.handle:logDebug(string.format("NOT matched >> negate_match_pairs %s %s", request_map[entry_name][key], value[1]))
            return value[2]
          end
        end
      end
    end
  end
  -- no match
  return false
end

function match_iprange(request_map, list_entry)
  -- ip ranges (soon enough will convert into a binary-tree)
  local ipnum = request_map.attrs.ipnum
  for _, entry in pairs(list_entry) do
    range, annotation = unpack(entry)
    if ipnum and range[1] and range[2] then
      if ipnum >= range[1] and ipnum <= range[2] then
        request_map.handle:logDebug(string.format("matched >> match_iprange range [%s %s], annotation %s, ipnum %s", range[1] , range[2], annotation, ipnum))
        return annotation
      end
    end
  end
  -- no match
  return false
end

-- returns the first match's annotation or "1" (when normalized)
function match_or_list(request_map, list)
  --- IP > ATTRS > HCA > IPRANGE
  --- EXACT then REGEX
  request_map.handle:logDebug(string.format("match_or_list request_map %s", json_encode(request_map)))

  if list.singles then
    request_map.handle:logDebug(string.format("match_or_list list.singles %s", json_encode(list.singles)))
    local annotation, tags = match_singles(request_map, list.singles)
    if annotation then
      return annotation, list.tags
    end
  end

  if list.pairs then
    request_map.handle:logDebug(string.format("match_or_list list.pairs %s", json_encode(list.pairs)))
    local annotation, tags = match_pairs(request_map, list.pairs)
    if annotation then
      return annotation, list.tags
    end
  end

  if list.iprange and list.iprange.range then
    -- search(1666603009, btree)
    request_map.handle:logDebug(string.format("match_or_list list.iprange.range %s", json_encode(list.iprange.range)))
    local range, annotation = btree_search(request_map.attrs.ipnum, list.iprange, request_map.handle)
    if range then
      request_map.handle:logDebug(string.format("matched >> match_or_list btree_search [%s %s], annotation %s, ipnum %s", range[1] , range[2], annotation, request_map.attrs.ipnum))
      return annotation  or 'ip-range', list.tags
    end
  end

  return false, false
end

-- returns the first match's annotation or "1" (when normalized)
function negate_match_or_list(request_map, list)

  -- not match_x will do the trick.
  if list.negate_singles and next(list.negate_singles) then
    local annotation, tags = match_singles(request_map, list.negate_singles)
    if not annotation then
      return 'negate', list.tags
    end
  end

  if list.negate_pairs and next(list.negate_pairs) then
    local annotation, tags = negate_match_pairs(request_map, list.negate_pairs)
    if annotation then
      return annotation, list.tags
    end
  end

  if list.negate_iprange and next(list.negate_iprange) then
    local annotation, tags = match_iprange(request_map, list.negate_iprange)
    if not annotation then
      return 'negate', list.tags
    end
  end

  return false, false
end

function tag_lists(request_map)

  for _, list in pairs(globals.ProfilingLists) do
    if list.entries_relation == "OR" then

      local annotation, tags = match_or_list(request_map, list)

      if annotation then
        tag_request(request_map, tags)
      end

      annotation, tags = negate_match_or_list(request_map, list)

      if annotation then
        tag_request(request_map, tags)
      end

    end

  end

end

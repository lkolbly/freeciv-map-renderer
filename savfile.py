import math

# Turns a table from a dict of columns to a list of rows (the rows become dicts)
def tableColumnsToDict(table):
	newtable = []
	columns = table.keys()
	for i in range(len(table[columns[0]])):
		row = {}
		for c in columns:
			row[c] = table[c][i]
		newtable.append(row)
	return newtable

# vector_name is one of "bases", "specials", or "roads"
def parseMap_Bitvector(sav, ncols, row, tiles, vector_name, rowdata_prefix):
	nmaps = math.ceil(int(sav["savefile"]["%s_size"%vector_name])/4)
	for x in range(ncols):
		tiles[x][row][vector_name] = set()
	for maj_num in range(nmaps):
		row_data = sav["map"]["%s%02d_%04d"%(rowdata_prefix,maj_num,row)]
		for i in range(4):
			idx = 4*maj_num + i
			if idx > int(sav["savefile"]["%s_size"%vector_name])/4:
				continue
			thing_type = sav["savefile"]["%s_vector"%vector_name][idx]
			for x in range(ncols):
				n = int(row_data[x])
				if n&(1<<i) != 0:
					#print(thing_type)
					tiles[x][row][vector_name].add(thing_type)

def parseMap(sav):
	nrows = int(getSettingValue(sav["settings"]["set"], "ysize"))#int(sav["xsize"])
	ncols = int(getSettingValue(sav["settings"]["set"], "xsize"))#int(sav["ysize"])
	tiles = []
	for i in range(ncols):
		l = []
		for j in range(nrows):
			l.append({})
		tiles.append(l)

	for y in range(nrows):
		# Parse the terrain
		t = sav["map"]["t%04d"%y]
		for x in range(ncols):
			#print(x,y)
			tiles[x][y]["t"] = t[x]

		# Parse the owner
		owner = sav["map"]["owner%04d"%y].split(",")
		for x in range(ncols):
			tiles[x][y]["owner"] = owner[x]

		# Parse the bases
		# The bases are stored 4 at a time in 4-bit hex characters. If there
		# are more than 4 types of bases, there will be ceil(n_base_types/4)
		# maps.
		parseMap_Bitvector(sav, ncols, y, tiles, "bases", "b")

		# Parse the roads (includes rivers)
		parseMap_Bitvector(sav, ncols, y, tiles, "roads", "r")

		# Parse the specials
		parseMap_Bitvector(sav, ncols, y, tiles, "specials", "spe")

		# Parse the resources
		resources = sav["map"]["res%04d"%y]
		for x in range(ncols):
			tiles[x][y]["resource"] = resources[x]

		# Parse the "worked"
		# Each tile is the ID of the city that works it
		worked = sav["map"]["worked%04d"%y].split(",")
		for x in range(ncols):
			if worked[x] != "-":
				tiles[x][y]["worked"] = int(worked[x])

		# TODO: Parse the "known"
	return {"w": ncols, "h": nrows, "tiles": tiles}

def parseSavFile(f):
	result = {}
	section_name = None
	key_name = None
	is_in_table = False
	tbl = None
	table_columns = []
	for line in f.readlines():
		line = line.strip(" \r\n")
		if len(line) == 0:
			continue
		if line[0] == '[':
			# We found a new section
			section_name = line[1:-1]
			result[section_name] = {}
		elif is_in_table:
			# We assume that the } is always on a line of its own.
			if line[0] == '}':
				# Stop parsing the table
				is_in_table = False
				if parts[0] in result[section_name]:
					result[section_name][parts[0]].update(tbl)
				else:
					result[section_name][parts[0]] = tbl
				tbl = None
			else:
				# Add to the table...
				vals = line.split(",")
				i = 0
				for c in table_columns:
					tbl[c].append(vals[i].strip("\""))
					i += 1
				pass
			pass
		else:
			# Split on the equal sign
			parts = line.split("=")
			if len(parts) > 1:
				if parts[1][0] == '{':
					# Start parsing a table
					is_in_table = True
					table_columns = parts[1][1:].split(",")
					tbl = {}
					for i in range(len(table_columns)):
						table_columns[i] = table_columns[i].strip("\"")
					for c in table_columns:
						tbl[c] = []
				else:
					# Just another key
					if parts[0] in result[section_name]:
						raise Exception("Key already exists in this section!")
					if "_vector" in parts[0]:
						# I guess it's a list then...
						vals = parts[1].split(",")
						vec = []
						for v in vals:
							vec.append(v.strip("\""))
						result[section_name][parts[0]] = vec
					else:
						parts[1] = parts[1].strip("\"'")
						result[section_name][parts[0]] = parts[1]
	return result

def getSettingValue(settings_table, key):
	for i in range(len(settings_table["name"])):
		if settings_table["name"][i] == key:
			return settings_table["value"][i]
	return None

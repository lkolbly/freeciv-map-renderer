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

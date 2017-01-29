import os, re, tempfile, bz2, argparse
import json
from PIL import Image, ImageDraw
import matplotlib.pyplot as plt
import progressbar
import random

from savfile import parseSavFile, getSettingValue, parseMap

def tileCenterPixel(image_meta,tile_x,tile_y):
	tile_w = image_meta["tile_w"]
	tile_h = image_meta["tile_h"]
	x = tile_x*tile_w + tile_w / 4
	y = tile_y*tile_h + tile_h / 2
	# Odd rows get shifted 1 to the right
	if tile_y%2 == 1:
		x += tile_w / 2
	return (x,y)

def tileIsoPolygon(image_meta,tile_x,tile_y):
	tile_w = image_meta["tile_w"]
	tile_h = image_meta["tile_h"]
	center = tileCenterPixel(image_meta, tile_x, tile_y)
	points = [
		(center[0], center[1]+tile_h),
		(center[0]+tile_w/2, center[1]),
		(center[0], center[1]-tile_h),
		(center[0]-tile_w/2, center[1])
	]
	return points

def renderTile_SimpleLandWater(tile_data, tile_poly, im_draw, savefile, image_meta):
	water = [' ',':']
	if tile_data["t"] in water:
		im_draw.polygon(tile_poly, fill=(0,0,255,255))
	else:
		im_draw.polygon(tile_poly, fill=(0,255,0,255))

def renderTile_CulturalInfluenceArea(tile_data, tile_poly, im_draw, savefile, image_meta):
	ownerNum = tile_data["owner"]
	if ownerNum == "-":
		return
	owner = savefile["player%d"%int(ownerNum)]
	color = (int(owner["color.r"]), int(owner["color.g"]), int(owner["color.b"]),200)
	im_draw.polygon(tile_poly, fill=color)

# Starting at North and going clockwise
def iter_neighbor_tiles(x, y, w, h):
	if y%2 == 0:
		# This is an even one
		l = [(0,-2), (0,-1), (1,0), (0,1), (0,2), (-1,1), (-1,0), (-1,-1)]
	else:
		# This is an odd one
		l = [(0,-2), (1,-1), (1,0), (1,1), (0,2), (0,1), (-1,0), (0,-1)]
	# Assumes wrap in X, nowrap on y
	for dx,dy in l:
		newx = x+dx
		newy = y+dy
		unwrapped_x = newx
		unwrapped_y = newy
		if newx >= w:
			newx = 0
		if newx < 0:
			newx = w-1
		if newy >= 0 and newy < h:
			yield newx,newy, unwrapped_x, unwrapped_y

def renderTile_Roads(tile_data, tile_poly, im_draw, savefile, image_meta):
	if "Road" not in tile_data["roads"]:
		return
	# See which neighboring tiles have a road
	map_w = image_meta["map_w"]
	map_h = image_meta["map_h"]
	my_center = tileCenterPixel(image_meta,tile_data["x"], tile_data["y"])
	for x,y,unwrapped_x,unwrapped_y in iter_neighbor_tiles(tile_data["x"], tile_data["y"], map_w, map_h):
		if "Road" in savefile["parsed_map"]["tiles"][x][y]["roads"]:
			# Draw a line from here to there
			their_center = tileCenterPixel(image_meta,unwrapped_x,unwrapped_y)
			edge_center = ((their_center[0]+my_center[0])/2, (their_center[1]+my_center[1])/2)
			im_draw.line([edge_center, my_center], fill=(227,178,86,255), width=5)
			pass
		pass

def renderTile_Border(tile_data, tile_poly, im_draw, savefile, image_meta):
	im_draw.polygon(tile_poly, fill=None, outline=(0,0,0,255))

def renderTileLayer(savefile, im, image_meta, renderfunc):
	w = image_meta["w"]
	h = image_meta["h"]
	map_w = image_meta["map_w"]
	map_h = image_meta["map_h"]
	tiles = parseMap(savefile)["tiles"]

	im2 = Image.new("RGBA", (w,h))
	draw2 = ImageDraw.Draw(im2)

	for y in range(map_h):
		for x in range(map_w):
			poly = tileIsoPolygon(image_meta, x, y)
			renderfunc(tiles[x][y], poly, draw2, savefile, image_meta)
	im.paste(im2, mask=im2) # To handle alpha properly

# Renders green for land and blue for water.
def renderSimpleLandWater(savefile,im,image_meta):
	renderTileLayer(savefile, im, image_meta, renderTile_SimpleLandWater)

# Renders the cultural influence area around cities.
def renderCulturalInfluenceArea(savefile, im, image_meta):
	renderTileLayer(savefile, im, image_meta, renderTile_CulturalInfluenceArea)

# Draws a dot for each city
def renderCities(savefile, im_draw, image_meta):
	map_w = image_meta["map_w"]
	map_h = image_meta["map_h"]
	tile_w = image_meta["tile_w"]
	tile_h = image_meta["tile_h"]

	nplayers = int(savefile["players"]["nplayers"])
	for i in range(nplayers):
		player = savefile["player%d"%i]
		for c_i in range(int(player["ncities"])):
			city_x = int(player["c"]["x"][c_i])
			city_y = int(player["c"]["y"][c_i])
			center = tileCenterPixel(image_meta, city_x, city_y)
			points = [(center[0]-tile_h/2, center[1]-tile_h/2), (center[0]+tile_h/2, center[1]+tile_h/2)]
			im_draw.ellipse(points, fill=(255,255,255,255))

# Draws a small dot for each unit
def renderUnits(savefile, im_draw, image_meta):
	map_w = image_meta["map_w"]
	map_h = image_meta["map_h"]
	tile_w = image_meta["tile_w"]
	tile_h = image_meta["tile_h"]

	nplayers = int(savefile["players"]["nplayers"])
	for i in range(nplayers):
		player = savefile["player%d"%i]
		for u_i in range(int(player["nunits"])):
			unit_x = int(player["u"]["x"][u_i])
			unit_y = int(player["u"]["y"][u_i])	
			center = tileCenterPixel(image_meta, unit_x, unit_y)
			points = [(center[0]-tile_h/4, center[1]-tile_h/4), (center[0]+tile_h/4,center[1]+tile_h/4)]
			im_draw.ellipse(points, fill=(255,255,255,255))

# Renders an overview like the minimap in the corner.
# Green for land, blue for water.
# Civ's cultural area is colored.
# White dots for units and cities.
# Assumes the default ruleset, and the amplio2 tileset where applicable.
def renderOverview(savefile, custom_layers=[]):
	w = 1800*2
	h = 800*2
	im = Image.new("RGBA",(w,h))
	draw = ImageDraw.Draw(im)

	# Get the map size
	map_w = int(getSettingValue(savefile["settings"]["set"], "xsize"))
	map_h = int(getSettingValue(savefile["settings"]["set"], "ysize"))

	tile_w = w / map_w
	tile_h = h / map_h

	image_meta = {"w": w, "h": h, "map_w": map_w, "map_h": map_h, "tile_w": tile_w, "tile_h": tile_h}

	# Start with the land/water
	# ' ',':' are water, everything else is land
	renderSimpleLandWater(savefile, im, image_meta)

	# Draw the cultural influence area
	renderCulturalInfluenceArea(savefile, im, image_meta)

	# Draw roads
	renderTileLayer(savefile, im, image_meta, renderTile_Roads)

	renderTileLayer(savefile, im, image_meta, renderTile_Border)

	# Draw dots for each city
	renderCities(savefile, draw, image_meta)
	renderUnits(savefile, draw, image_meta)

	# Render any custom layers
	for layer in custom_layers:
		layer(savefile, draw, image_meta)

	return im

def getValidFilenames(directory):
	# Get all of the files in that directory
	all_files = os.listdir(directory)

	# Get the ones that look like "freeciv-T%04d-Y%05d-auto.sav.bz2"
	filenames = []
	for fname in all_files:
		match = re.match(r"freeciv-T(\d\d\d\d)-Y-?\d+-auto.sav.bz2", fname)
		if match:
			filenames.append((fname, int(match.groups()[0])))
	filenames.sort(key=lambda a: a[1])
	return filenames

# Renders a series of savs from directory using the specified renderfunc
def renderSeries(directory, renderfunc, outfile):
	filenames = getValidFilenames(directory)

	# Get a temporary directory to put the result in
	#dirname = tempfile.mkdtemp(prefix="freeciv-render-")
	with tempfile.TemporaryDirectory() as dirname:
		for fname in filenames:
			f = bz2.open(directory+"/"+fname[0], 'rt')
			im = renderfunc(parseSavFile(f))
			im.save("%s/%04d.png"%(dirname,fname[1]), "PNG")
			print("Rendered turn %04d"%fname[1])

		print("Finished rendering into %s"%dirname)

		# Turn it into a video
		os.system("ffmpeg -framerate 5 -i %s/%%04d.png %s"%(dirname,outfile))

def getTimeData(directory, datafunc, maxframe):
	filenames = getValidFilenames(directory)

	players = {}
	turnno = 0
	bar = progressbar.ProgressBar()
	for fname in bar(filenames):
		f = bz2.open(directory+"/"+fname[0], 'rt')
		sav = parseSavFile(f)
		for key in sav.keys():
			if "player" in key and "players" not in key:
				if key not in players:
					name = sav[key]["username"]
					if name == "Unassigned":
						name = sav[key]["name"]
					players[key] = {"name": name, "color": {"r": int(sav[key]["color.r"]), "g": int(sav[key]["color.g"]), "b": int(sav[key]["color.b"])}, "x": [], "y": []}
				players[key]["x"].append(turnno)
				players[key]["y"].append(datafunc(sav[key]))
		turnno += 1
		#print("Finished turn %d"%turnno)
		if turnno > maxframe:
			break
	return players

def renderTimePlot(directory, datafunc, ylabel, outfile, maxframe):
	players = getTimeData(directory, datafunc, maxframe)

	# Plot it
	for k,v in players.items():
		plt.plot(v["x"], v["y"], '#%02x%02x%02x'%(v["color"]["r"], v["color"]["g"], v["color"]["b"]), label=v["name"])
	plt.legend(loc='upper center', bbox_to_anchor=(0.5, 1.1), ncol=3, fancybox=True, shadow=True, fontsize='small')
	plt.ylabel(ylabel)
	plt.savefig(outfile)
	pass

def dumpTimeData(directory, datafunc, ylabel, outfile, maxframe):
	players = getTimeData(directory, datafunc, maxframe)

	# Format data
	datarows = []
	maxx = 0
	for k,v in players.items():
		for x,y in zip(v["x"], v["y"]):
			#datarows.append(["%s"%x])
			maxx = max(x, maxx)
		break
	for i in range(maxx+1):
		datarows.append(["%s"%i])
	for k,v in players.items():
		for x,y in zip(v["x"], v["y"]):
			datarows[x].append("%s"%y)

	# Output to CSV file
	f = open(outfile, "w")
	f.write("turn,")
	f.write(",".join(list(map(lambda v: "%s - %s"%(v["name"],ylabel), players.values()))))
	f.write("\n")
	for row in datarows:
		f.write(",".join(row))
		f.write("\n")
		#f.write("%s,%s\n"%(row[0], row[1]))
	f.close()
	pass

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description="Read and render FreeCiv maps.")
	subparser = parser.add_subparsers(help='haalp', dest='command')
	parser_series = subparser.add_parser('series', help='Render an entire series of images')
	parser_series.add_argument('directory', type=str, help='The directory of savfiles to render.')
	parser_series.add_argument('outfile', type=str, help='The output video file to create (WEBM).')

	parser_image = subparser.add_parser('frame', help='Render a single frame')
	parser_image.add_argument('file', type=str, help='The sav file (bz2 compresses) to render.')
	parser_image.add_argument('outfile', type=str, help='The output image to create.')
	parser_image.add_argument('--layer', action='append', default=[], help='A python module to load a custom layer from (the function to execute the layer must have the same name as the module itself). Can be specified multiple times.')

	parser_graph = subparser.add_parser('graph', help='Graph something over time')
	parser_graph.add_argument('type', type=str, help='The feature to graph - common ones are: research.techs, nunits, ncities, units_built, units_killed, units_lost')
	parser_graph.add_argument('directory', type=str, help='The directory to look at')
	parser_graph.add_argument('outfile', type=str, help='The output image to create.')
	parser_graph.add_argument('--maxframe', type=int, help='The maximum frame to go to', default=100000)

	parser_csv = subparser.add_parser('data', help='Dump CSV data over time')
	parser_csv.add_argument('type', type=str, help='The feature to dump to the CSV file.')
	parser_csv.add_argument('directory', type=str, help='The directory to look at')
	parser_csv.add_argument('outfile', type=str, help='The output image to create.')
	parser_csv.add_argument('--maxframe', type=int, help='The maximum frame to go to', default=100000)

	args = parser.parse_args()
	print(args)
	if args.command == "series":
		renderSeries(args.directory, renderOverview, args.outfile)
	elif args.command == "frame":
		# Load all of the custom layers
		layers = []
		for layerName in args.layer:
			m = __import__(layerName)
			layers.append(getattr(m, layerName))

		f = bz2.open(args.file, 'rt')
		im = renderOverview(parseSavFile(f), layers)
		im.save(args.outfile)
	elif args.command == "graph":
		renderTimePlot(args.directory, lambda a: a[args.type], args.type, args.outfile, args.maxframe)
	elif args.command == "data":
		dumpTimeData(args.directory, lambda a: a[args.type], args.type, args.outfile, args.maxframe)

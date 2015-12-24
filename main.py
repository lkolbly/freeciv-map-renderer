import os, re, tempfile, bz2, argparse
import json
from PIL import Image, ImageDraw
import matplotlib.pyplot as plt

from savfile import parseSavFile, getSettingValue

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

# Renders green for land and blue for water.
def renderSimpleLandWater(savefile,im_draw,image_meta):
	map_w = image_meta["map_w"]
	map_h = image_meta["map_h"]
	tile_w = image_meta["tile_w"]
	tile_h = image_meta["tile_h"]
	water = [' ',':']
	for y in range(map_h):
		row = savefile["map"]["t%04d"%y]
		for x in range(map_w):
			poly = tileIsoPolygon(image_meta, x, y)
			if row[x] in water:
				im_draw.polygon(poly, fill=(0,0,255,255))
			else:
				im_draw.polygon(poly, fill=(0,255,0,255))

# Renders the cultural influence area around cities.
def renderCulturalInfluenceArea(savefile, im, image_meta):
	map_w = image_meta["map_w"]
	map_h = image_meta["map_h"]
	tile_w = image_meta["tile_w"]
	tile_h = image_meta["tile_h"]
	w = image_meta["w"]
	h = image_meta["h"]

	im2 = Image.new("RGBA", (w,h))
	draw2 = ImageDraw.Draw(im2)
	for y in range(map_h):
		row = savefile["map"]["owner%04d"%y].split(",")
		for x in range(map_w):
			if row[x] == "-":
				continue
			owner = savefile["player%d"%int(row[x])]
			color = (int(owner["color.r"]), int(owner["color.g"]), int(owner["color.b"]),240)
			poly = tileIsoPolygon(image_meta, x, y)
			draw2.polygon(poly, fill=color)

	im.paste(im2, mask=im2)

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
			points = [(center[0]-tile_w/2, center[1]-tile_h/2), (center[0]+tile_h/2, center[1]+tile_h/2)]
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
			points = [(center[0]-tile_w/4, center[1]-tile_h/4), (center[0]+tile_w/4,center[1]+tile_h/4)]
			im_draw.ellipse(points, fill=(255,255,255,255))

# Renders an overview like the minimap in the corner.
# Green for land, blue for water.
# Civ's cultural area is colored.
# White dots for units and cities.
# Assumes the default ruleset, and the amplio2 tileset where applicable.
def renderOverview(savefile):
	w = 1800
	h = 800
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
	renderSimpleLandWater(savefile, draw, image_meta)

	# Draw the cultural influence area
	renderCulturalInfluenceArea(savefile, im, image_meta)

	# Draw dots for each city
	renderCities(savefile, draw, image_meta)
	renderUnits(savefile, draw, image_meta)

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

def renderTimePlot(directory, datafunc, ylabel, outfile):
	filenames = getValidFilenames(directory)

	players = {}
	turnno = 0
	for fname in filenames:
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
		print("Finished turn %d"%turnno)

	# Plot it
	for k,v in players.items():
		plt.plot(v["x"], v["y"], '#%02x%02x%02x'%(v["color"]["r"], v["color"]["g"], v["color"]["b"]), label=v["name"])
	plt.legend(loc='upper center', bbox_to_anchor=(0.5, 1.1), ncol=3, fancybox=True, shadow=True, fontsize='small')
	plt.ylabel(ylabel)
	plt.savefig(outfile)
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

	parser_graph = subparser.add_parser('graph', help='Graph something over time')
	parser_graph.add_argument('type', type=str, help='The feature to graph - common ones are: research.techs, nunits, ncities, units_built, units_killed, units_lost')
	parser_graph.add_argument('directory', type=str, help='The directory to look at')
	parser_graph.add_argument('outfile', type=str, help='The output image to create.')

	args = parser.parse_args()
	print(args)
	if args.command == "series":
		renderSeries(args.directory, renderOverview, args.outfile)
	elif args.command == "frame":
		f = bz2.open(args.file, 'rt')
		im = renderOverview(parseSavFile(f))
		im.save(args.outfile)
	elif args.command == "graph":
		renderTimePlot(args.directory, lambda a: a[args.type], args.type, args.outfile)
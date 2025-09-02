import csv
import glob
import pytiled_parser
from pathlib import Path

# Add two custom properties to the top left tile for each sprite/graphic in your Tileset, called 'GM' and 'Moves'
# Set GM to the Gamesmaster Sprite no. you'll use for this graphic
# Set Moves to 1 for where you want Gamesmaster to use a 'PLACE' command. If set to 0, a BACK command is used
# (In future additional custom properties may be possible to implement other aspects)
# Add an Object Layer, and put rectangles where you want a 'BLOCK definition to be used
# You can add a custom Property to any rectangles either called 'Plane' or Type,
# and then the block will use these values in Gamesmaster too.
# Without these custom properties, Plane and Type will both default to 1
# Place all .tsm files in the same directory as this code, and it will automatically compile all
# tilesets into one file, with room order as per the filename order.
# -- copy this .bin file to your Sam disk to be used by Gamesmaster


#File output data written in binary format with the following headers:
###################################################################

# 'R'  (binary 82)  -signifies room data follows
# No rooms in file
# No rows per room
# No columns per room
# data for Rows x Columns x Rooms
# 'B' (binary 66) - signifies BLOCK data follows
# no rooms
# LUT of two values - which is cumulative no of blocks (v1+v2) to allow upto 510 blocks to be defined e.g.
#   4,0
#   8,0
#  ..
#   250,0
#   255,4
#   255,50   - means data for this room can be found 255+50=305 x 7 bytes later
#
#Block data then in format b,x,y,w,h,plane,type
#i.e. to get block data for room 2, it is at 7x(v1+v2)

#output file name for binary file used by Gamesmaster on Sam Coupe
rofile='roomGM.bin'

ts_file = Path("sprites.tsx")
my_ts = pytiled_parser.parse_tileset(ts_file)
no_tiles=my_ts.tile_count
LUT=dict()
LUTline=dict()

for n in range (0,no_tiles):
    if n in my_ts.tiles:
        gm = dict.get(my_ts.tiles[n].properties, 'GM')
        moves = dict.get(my_ts.tiles[n].properties, 'Moves')
        LUTline=({'GM':gm,'Moves':moves})
        LUT[n]=LUTline


#Get list of files in directoru with .csv extension
tmxfiles = []
for file in glob.glob("*.tmx"):
    tmxfiles.append(file)

no_rooms=len(tmxfiles)

map_file = Path(tmxfiles[0])
my_map = pytiled_parser.parse_map(map_file)

#print(len(my_map.layers))
#assumes Layer 0 is map, Layer 1 is objects
nocols=0
norows=0
norows=(len(my_map.layers[0].data))
nocols=(len(my_map.layers[0].data[0]))

blocks=[]
bf_outt=[]
bf_out=[]   #blocks data output
#open files one at a time, convert to GM sprites using LUT, output as binary file for use on Sam
with open(rofile, 'wb') as file:
    file.write((82).to_bytes(1, 'big')) #write "R" at start
    file.write(no_rooms.to_bytes(1, 'big'))
    file.write(nocols.to_bytes(1, 'big'))
    file.write(norows.to_bytes(1, 'big'))

    for roomf in tmxfiles:
        map_file = Path(roomf)
        my_map = pytiled_parser.parse_map(map_file)
        reader=(my_map.layers[0].data)
        for row in reader:
            accm=0
            o_row=[]
            no_map= {'GM':0,'Moves':0}

            for tl in range(0,len(row)):
                tiled=row[tl]-1 #tiled adds 1 to reference shown in Tileset and csv output in TMX files
                vals=LUT.get((tiled),no_map)
                gm=vals['GM']
                mo=vals['Moves']
                if mo==1:gm=int(gm)+128
                o_row.append(int(gm))

                accm=accm+int(gm)

            #code to count consecutive 0s and help speed up GamesMaster execution by allowing skipping ahead
            if accm==0:o_row[0]=255 #place 255 in rows with nothing in (causes next row in GM code)

            compz=1 #turn off in testing
            if compz==1:
                zs=0 #zero start position
                zc=0 #no. of zeros consecutively
                for bv in range(0, len(o_row)):
                    if (o_row[bv]==0):
                        if zs==0:#found new start of zeros
                            zs=bv
                        zc=zc+1
                    if(o_row[bv]>0)  :
                        if (zs>0): #ie end of range of zeros
                            if zc>3:
                                o_row[zs]=255-zc #when GM sees a value > [255-31=] 224 it knows it can just skip ahead the next (255-x) values
                        zs=0
                        zc=0

                    if (zs > 0):  # ie end of row reached and still a ZS to use
                        if zc > 3:
                            o_row[zs] = 255 - zc

            for bv in range(0,len(o_row)):
                file.write(o_row[bv].to_bytes(1,'big'))

        blocklayer=len(my_map.layers)
        if(blocklayer>1):
            noblocks=0
            for n in range (0,len(my_map.layers[1].tiled_objects)):
                if not(hasattr(my_map.layers[1].tiled_objects[n],'text')): #for future implementation of text maybe
                    noblocks=noblocks+1
                    p=1
                    t=1
                    pt = dict.get(my_map.layers[1].tiled_objects[n].properties, 'Plane')
                    if (pt != None):#check for custom property 'Plane'- leave as 1 if not found
                        p=pt
                    tt = dict.get(my_map.layers[1].tiled_objects[n].properties, 'Type')
                    if (tt != None):#check for custom property 'Plane' - leave as 1 if not found
                        t=tt
                    x=(my_map.layers[1].tiled_objects[n].coordinates.x)/2
                    y=(my_map.layers[1].tiled_objects[n].coordinates.y)
                    w=(my_map.layers[1].tiled_objects[n].size.width)/2
                    h=(my_map.layers[1].tiled_objects[n].size.height)
                    if(x+w)>255:
                        w=255-x
                    if(y+h)>191:
                        h=191-y
                    bf_outt.append([n,x,y,w,h,p,t])
            print("Blocks needed in room:", noblocks)
        print(roomf," complete")
        bf_out.append(bf_outt)
        bf_outt=[]
        #print("--Next room")
        print("")
        #blocks=[] #next room
    file.write((66).to_bytes(1, 'big'))  # ASCII 'B' signifies start of BLOCKs data
    file.write(no_rooms.to_bytes(1, 'big')) #for check that room no. in data

    #write room block data LUT into file (running total of bytes ahead to get room block data)
    rt=0
    rtot=0
    rtot2=0
    for bd in bf_out:
        rt=len(bd)
        rtot=rtot+rt
        rtot2=0
        if(rtot>255):#allow for upto 500 entries ~100 rooms
            rtot2=rtot-255
            rtot=rtot-255
        file.write(rtot.to_bytes(1, 'big'))  # for check that room no. in data
        file.write(rtot2.to_bytes(1, 'big'))  # for check that room no. in data


    for bdb in bf_out: #write all block data out (bd=every block in every room,bd2 = every block in each room, bd3 every value in each block
        for bd3 in bdb:
            for bd2 in bd3:
                if(bd2>255):bd2=255
                file.write(int(bd2).to_bytes(1, 'big'))  # for check that room no. in data

print (no_rooms," rooms processed")

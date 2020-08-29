#**************************************************************************************************
# Copyright (c) 2006 Gas Powered Games Corp. All Rights Reserved. 
# Gas Powered Games and Supreme Commander are the exclusive trademarks of Gas Powered Games Corp.
#**************************************************************************************************

def DumpSCA(filename):
    
    import struct,string

    data = file(filename, 'rb').read()

    fileheader_fmt = '4sllflllll'
    fileheader_size = struct.calcsize(fileheader_fmt)   

    start,stop = 0,fileheader_size
    
    (magic,             \
     version,           \
     numframes,         \
     durationseconds,   \
     numbones,          \
     namesoffset,       \
     linksoffset,       \
     firstframeoffset,  \
     framesize) = struct.unpack(fileheader_fmt,data[start:stop])
    
    print "----------------"
    print " Animation Header"
    print "----------------"
    print "File Type:",magic
    print "Version:",version
    print "NumFrames:",numframes
    print "NumBones:",numbones
    print "Duration: %-10.5f" % durationseconds
    print "NamesOffset:",namesoffset
    print "LinkOffset:",linksoffset
    print "DataOffset:",firstframeoffset
    print "FrameSize:",framesize
    
    print "\n----------------"
    print " Bone Info"
    print "----------------"

    start = namesoffset
    stop = linksoffset
    rawnames = struct.unpack(str(stop-start)+'s',data[start:stop])

    bonenames = string.split(rawnames[0],'\0')[:-1]

    links_fmt = str(numbones)+'l'
    links_size = struct.calcsize(links_fmt)
    
    start = linksoffset
    stop = start + links_size
    bonelinks = struct.unpack(links_fmt,data[start:stop])

    b = 0
    for b in range(0,len(bonenames)) :
        if (bonelinks[b] == -1) :
            print  "#%d %-12s (<local root>)" % (b, bonenames[b])
        else :
            print  "#%d %-12s (child of #%d %s)" % (b, bonenames[b], bonelinks[b], bonenames[bonelinks[b]])
    
    print "\n----------------"
    print " Animation Data"
    print "----------------"

    vec3_prettyprint = "(%11.5f,%11.5f,%11.5f)"
    quat_prettyprint = "(%11.5f,%11.5f,%11.5f,%11.5f)"

    frameheader_fmt = 'fl'
    frameheader_size = struct.calcsize(frameheader_fmt)

    posrot_fmt = '3f4f'
    posrot_size = struct.calcsize(posrot_fmt)

    start,stop = firstframeoffset,firstframeoffset+posrot_size
    root_posrot = struct.unpack(posrot_fmt,data[start:stop])

    print ("Root Delta:  Pos: " + vec3_prettyprint + " Rot:  " + quat_prettyprint) % root_posrot

    for f in range (0, numframes) :
        start,stop = stop,stop+frameheader_size           
        (keytime,keyflags) = struct.unpack(frameheader_fmt,data[start:stop])
        # Don't dump all the keys, only the beginning, middle, and end...
        dumpit = (f < 2) or ((f > (numframes/2)-2) and (f < (numframes/2+1))) or f > (numframes-3) 
        if dumpit :
            print "\nFrame: %-4d Time: %-11.5f Flags: 0x%08X\n" % (f, keytime, keyflags)
        for b in range (0, numbones) :
            start,stop = stop,stop+posrot_size
            keydata = struct.unpack(posrot_fmt,data[start:stop])
            if dumpit:
                print "   %2d: %-14s " % (b,'['+bonenames[b]+']'), (" Pos: " + vec3_prettyprint + " Rot:  " + quat_prettyprint) % keydata

if __name__ == '__main__' :
    import sys
    from os import path 

    if len(sys.argv) == 2 :
        DumpSCA(sys.argv[1])
    else:
        print "usage %s <SCA filename>" % path.basename(sys.argv[0])

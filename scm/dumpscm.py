#**************************************************************************************************
# Copyright (c) 2006 Gas Powered Games Corp. All Rights Reserved. 
# Gas Powered Games and Supreme Commander are the exclusive trademarks of Gas Powered Games Corp.
#**************************************************************************************************

import math

#define some pretty print formats
vec4pp = "[%11.5f,%11.5f,%11.5f,%11.5f]"                             
vec3pp = "[%11.5f,%11.5f,%11.5f]"                             
vec2pp = "[%11.5f,%11.5f]"                             

def DumpVert(v,d):

    print( "VERT[%4d]" % v                       )
    print( ("  Pos:      " + vec3pp) % d[0:3]    )
    print( ("  Tangent:  " + vec3pp) % d[3:6]    )
    print( ("  Normal:   " + vec3pp) % d[6:9]    )
    print( ("  Binormal: " + vec3pp) % d[9:12]   )
    print( ("  UV0:      " + vec2pp) % d[12:14]  )
    print( ("  UV1:      " + vec2pp) % d[14:16]  )
    print(  "  Bone %3d" % d[16:17]              )


def quaternion_to_euler(q0,q1,q2,q3):
    yaw = math.atan2(2.*(q0*q3+q1*q2), 1.-2.*(q2*q2 + q3*q3))
    pitch = math.asin(2.*(q0*q2-q3*q1))
    roll = math.atan2(2.*(q0*q1+q2*q3), 1.-2.*(q1*q1 + q2*q2))
    return math.degrees(roll), math.degrees(pitch), math.degrees(yaw)

def load_bones(file):

    import struct

    data = file.read()
    result = { }    # dictionary of tuples (parentname,posxyz,orientationwxyz)
    
    start,stop = 0,struct.calcsize('4sL')
    marker,version = struct.unpack('4sL',data[start:stop])

    start,stop = stop,stop+struct.calcsize('2L')
    boneoffset,bonecount = struct.unpack ('2L',data[start:stop])

    start,stop = stop,stop+struct.calcsize('3L')
    vertoffset,extravertoffset,vertcount = struct.unpack ('3L',data[start:stop])

    start,stop = stop,stop+struct.calcsize('2L')
    indexoffset,indexcount = struct.unpack ('2L',data[start:stop])
    tricount = indexcount/3

    start,stop = stop,stop+struct.calcsize('2L')
    infooffset,infocount = struct.unpack ('2L',data[start:stop])
    
    padding = str(32-(stop+4)%32)+'s4s'
    start = stop+struct.calcsize(padding)
    stop = boneoffset
    rawnames = struct.unpack(str(stop-start)+'s',data[start:stop])

    bonenames = rawnames[0].split(b'\0')[:-1]

    bonestruct = '16f3f4f4i'
    bonesize = struct.calcsize(bonestruct)
    start,stop = boneoffset,boneoffset+bonesize
    
    for b in range(0,bonecount):
        bone = struct.unpack(bonestruct,data[start:stop])
        start,stop = stop,stop+bonesize
        
        bonename = bonenames[b].decode('utf-8')
        parentname = "" if bone[24]==-1 else bonenames[bone[24]].decode('utf-8')
        pos_xyz = bone[16:19]
        orientation_wxyz = bone[19:23]
        orientation_rpw = list(quaternion_to_euler(*orientation_wxyz))

        result[bonename] = (parentname, pos_xyz, orientation_wxyz, orientation_rpw)

    """
    result = {
        name: (parent, [ a-b for a,b in zip(xyz,result[parent][1]) ] if parent in result else xyz, wxyz, rpw )
        for name,(parent,xyz,wxyz,rpw) in result.items()
    }
    """

    return result


def DumpSCM(filename) :
    
    import struct,string

    with open(filename, 'rb') as file:
        data = file.read()

    start,stop = 0,struct.calcsize('4sL')
    marker,version = struct.unpack('4sL',data[start:stop])

    start,stop = stop,stop+struct.calcsize('2L')
    boneoffset,bonecount = struct.unpack ('2L',data[start:stop])

    start,stop = stop,stop+struct.calcsize('3L')
    vertoffset,extravertoffset,vertcount = struct.unpack ('3L',data[start:stop])

    start,stop = stop,stop+struct.calcsize('2L')
    indexoffset,indexcount = struct.unpack ('2L',data[start:stop])
    tricount = indexcount/3

    start,stop = stop,stop+struct.calcsize('2L')
    infooffset,infocount = struct.unpack ('2L',data[start:stop])

    print( "*** HEADER ***\n"                                                                                   )

    print( 'File Type: %s' %marker                                                                              )
    print( 'Version: %d' % version                                                                              )
    print( 'Bone count: %d, Bone offset: %d' % (bonecount,boneoffset)                                           )
    print( 'Vertex count: %d, Vertex offset: %d, ExtraVert offset: %d' % (vertcount,vertoffset,extravertoffset) )
    print( 'Triangle coun:t %d, Triangle offset: %d' % (tricount,indexoffset)                                   )
    print( 'Info count: %d, Info offset: %d' % (infocount,infooffset)                                           )

    padding = str(32-(stop+4)%32)+'s4s'
    start = stop+struct.calcsize(padding)
    stop = boneoffset
    rawnames = struct.unpack(str(stop-start)+'s',data[start:stop])

    print( "\n*** BONE NAMES ***\n")
    bonenames = rawnames[0].split(b'\0')[:-1]
    for b in range(0,len(bonenames)):
        print( "[%2d] %s" % (b,bonenames[b]))

    print( "\n*** BONE DATA ***\n")

    bonestruct = '16f3f4f4i'
    bonesize = struct.calcsize(bonestruct)
    start,stop = boneoffset,boneoffset+bonesize
    for b in range(0,bonecount):
        bone = struct.unpack(bonestruct,data[start:stop])
        start,stop = stop,stop+bonesize
        print( "\nBONE %d : [%s]" % (b,bonenames[b]))
        print( ' Parent Bone')
        if (bone[24] == -1) :
            print( '  -1 <root>')
        else :
            print( '  %d <%s>' % (bone[24],bonenames[bone[24]]))
        print( ' Parent Relative Position'   )
        print( ('  '+vec3pp) % bone[16:19]   )
        print( ' Parent Relative Rotation'   )
        print( ('  ' +vec4pp) % bone[19:23]  )
        print( ' Rest Pose Inverse'          )
        for row in range(4):
            print(('  '+ vec4pp) % bone[row*4:row*4+4])

    print( "\n*** VERTEX DATA ***\n")

    vertstruct = '3f3f3f3f2f2f4B'
    vertsize = struct.calcsize(vertstruct)
    stop = vertoffset
    if (vertcount < 7):
        for v in range(0,vertcount):
            start,stop = stop,stop+vertsize
            vert = struct.unpack(vertstruct,data[start:stop])
            DumpVert(v,vert)
    else:
        for v in range(0,3):
            start,stop = stop,stop+vertsize
            vert = struct.unpack(vertstruct,data[start:stop])
            DumpVert(v,vert)
        print( "...skipping %d verts..." % (vertcount-5))
        stop = vertoffset+(vertsize*(vertcount-3))
        for v in range(vertcount-3,vertcount):
            start,stop = stop,stop+vertsize
            vert = struct.unpack(vertstruct,data[start:stop])
            DumpVert(v,vert)

    if (extravertoffset != 0) :
        print( "EXTRAVERTS (first 5 only...)\n")
        extravertstruct = '2f'
        extravertsize = struct.calcsize(extravertstruct)
        start,stop = extravertoffset,extravertoffset+extravertsize
        for v in range(0,min(5,vertcount)):
            xvert = struct.unpack(extravertstruct,data[start:stop])
            start,stop = stop,stop+extravertsize
            print( xvert[0:2])
    else :
        print( "No EXTRAVERT data for this model\n")

    print( "\n*** TRIANGLE INDICES ***\n")

    tristruct = '3h'
    trisize = struct.calcsize(tristruct)
    stop = indexoffset

    if (tricount < 7) :
        for t in range(0,tricount):
            start,stop = stop,stop+trisize
            tri = struct.unpack(tristruct,data[start:stop])
            print( tri[0],  )
            print( tri[1],  )
            print( tri[2]   )
    else :
        for t in range(0,3):
            start,stop = stop,stop+trisize
            tri = struct.unpack(tristruct,data[start:stop])
            print ("%4d: %s" % (t, tri))
        print ("...skipping %d triangles..." % (tricount-5))
        stop = indexoffset+(trisize*(tricount-3))
        for t in range(tricount-3,tricount):
            start,stop = stop,stop+trisize
            tri = struct.unpack(tristruct,data[start:stop])
            print( "%4d: %s" % (t, tri))
                    
    print( "\n*** INFO ***\n")

    infostruct = str(infocount)+'s'
    infosize = struct.calcsize(infostruct)
    start,stop = infooffset,infooffset+infosize
    info = struct.unpack(infostruct,data[start:stop])
    infostrings = string.split(info[0],'\0')[:-1]
    for i in infostrings:
        print( " %s" % i)

if __name__ == '__main__' :
    import sys
    from os import path 

    if len(sys.argv) == 2 :
        DumpSCM(sys.argv[1])
    else:
        print( "usage %s <SCM filename>" % path.basename(sys.argv[0]))






import copy
import numpy
import os
import struct
import sys

class Piece:

    def __init__(self, name, parent, xyz0, rpw0):
        """
        @param name, parent: strings
        """

        self.xyz0 = copy.copy(list(xyz0))
        self.rpw0 = copy.copy(list(rpw0))

        self.xyz_offset = [0., 0., 0.]
        self.rpw_offset = [0., 0., 0.]

        self.name = name
        self.parent = parent

        self.cur_xyz = [ copy.copy(self.xyz0) ]
        self.vel_xyz = [0., 0., 0.]
        self.target_xyz = copy.copy(self.xyz0)

        # rpw: roll(about +X), pitch(about +Y), yaw(about +Z)
        self.cur_rpw = [ copy.copy(self.rpw0) ]
        self.rate_rpw = [0., 0., 0.]
        self.target_rpw = copy.copy(self.rpw0)

    def reset(self):
        self.cur_xyz = [ self.cur_xyz[-1] ]
        self.vel_xyz = [0., 0., 0.]
        self.target_xyz = copy.copy(self.cur_xyz[-1])

        # rpw: roll(about +X), pitch(about +Y), yaw(about +Z)
        self.cur_rpw = [ self.cur_rpw[-1] ]
        self.rate_rpw = [0., 0., 0.]
        self.target_rpw = copy.copy(self.cur_rpw[-1])

    def get_frames(self):
        return self.cur_xyz, self.cur_rpw

    def set_move_offset(self, axis_idx, x0):
        self.xyz_offset[axis_idx] = x0

    def set_turn_offset(self, axis_idx, x0):
        self.rpw_offset[axis_idx] = x0

    def move_now(self, axis_idx, target):
        target +=  self.xyz_offset[axis_idx]
        self.cur_xyz[-1][axis_idx] = self.xyz0[axis_idx] + target
        self.vel_xyz[axis_idx] = 0.
        self.target_xyz[axis_idx] = self.cur_xyz[-1][axis_idx]

    def turn_now(self, axis_idx, target):
        target +=  self.rpw_offset[axis_idx]
        self.cur_rpw[-1][axis_idx] = self.rpw0[axis_idx] + target
        self.rate_rpw[axis_idx] = 0.
        self.target_rpw[axis_idx] = self.cur_rpw[-1][axis_idx]

    def move_at_speed(self, axis_idx, target, speed):
        target +=  self.xyz_offset[axis_idx]
        self.vel_xyz[axis_idx] = speed
        self.target_xyz[axis_idx] = self.xyz0[axis_idx] + target

    def turn_at_speed(self, axis_idx, target, speed):
        target +=  self.rpw_offset[axis_idx]
        self.rate_rpw[axis_idx] = speed
        self.target_rpw[axis_idx] = self.rpw0[axis_idx] + target

    def step(self, dt):
        # dt in seconds

        def update(x, speed, xtarget, dt):
            # return new_x, new_speed
            if (xtarget-x)*speed >= 0.:
                dxdt = speed
            else:
                dxdt = -speed

            xupd = x + dxdt * dt
            if (x <= xtarget <= xupd) or (xupd <= xtarget <= x):
                # overshoot
                return xtarget, 0.
            else:
                return xupd, speed

        self.cur_xyz += [copy.copy(self.cur_xyz[-1])]
        self.cur_rpw += [copy.copy(self.cur_rpw[-1])]
        for n in range(3):
            self.cur_xyz[-1][n],self.vel_xyz[n] = update(self.cur_xyz[-1][n],self.vel_xyz[n],self.target_xyz[n],dt)
            self.cur_rpw[-1][n],self.rate_rpw[n] = update(self.cur_rpw[-1][n],self.rate_rpw[n],self.target_rpw[n],dt)


def parse_nbos(script):
    statements = []
    vars = { }
    for _statement in script.split(';'):
        _statement = _statement.strip()
        statement = _statement.replace(',', ' ')
        statement = statement.replace('\n', ' ')
        words = [w for w in statement.split(' ') if len(w)>0]
        if len(words) == 0:
            continue
        statements += [words]
        vars[words[0]] = _statement[len(words[0]):].strip()

    return statements, vars


def run_nbos(statements, pieces, vars, fps):
    """
    @param script: string containing the (not)bos script
    @param pieces: dictionary of Piece objects
    """

    SCALE_FACTORS = [2.5, 2.5, -2.5]
    def apply_scale_factor(coord, axis):
        return coord/SCALE_FACTORS[axis]
        
    ROTATION_SCALE_FACTORS = [1.0, -1.0, 1.0]
    def apply_rotation_factor(coord, axis):
        return coord*numpy.sign(ROTATION_SCALE_FACTORS[axis])

    def str_to_axis_idx(axis_str):
        return { 'x-axis':0, 'y-axis':1, 'z-axis':2 }[axis_str]

    t = 0.
    def to_float(number_str):
        try:
            return float(number_str)
        except ValueError:
            if number_str[0]=="'" and number_str[-1]=="'":
                return eval(number_str[1:-1], {'t':t, 'cos':numpy.cos, 'sin':numpy.sin})
            else:
                return float(number_str[1:-1])

    for words in statements:
        words[0] = words[0].lower()

        if words[0] == 'scales':
            SCALE_FACTORS = [ to_float(w) for w in (words[1],words[2],words[3]) ]

        elif words[0] == 'rotation-scales':
            ROTATION_SCALE_FACTORS = [ to_float(w) for w in (words[1],words[2],words[3]) ]

        elif words[0] == 'scm-file-path':
            pass
            
        elif words[0] == 'not-looped':
            pass

        elif words[0] == 'set-turn-offset':
            name, axis, position = words[1], str_to_axis_idx(words[3]), to_float(words[4])
            pieces[name].set_turn_offset(axis, position)
            
        elif words[0] == 'set-move-offset':
            name, axis, position = words[1], str_to_axis_idx(words[3]), to_float(words[4])
            pieces[name].set_move_offset(axis, position)

        elif words[0] == 'move':
            name, axis, position, speed = words[1], str_to_axis_idx(words[3]), to_float(words[4]), words[5].lower()
            if speed=='now':
                if t>0. or 'not-looped' in vars:
                    pieces[name].move_now(axis, apply_scale_factor(position, axis))
            elif speed=='speed':
                speed = to_float(words[6])
                pieces[name].move_at_speed(
                    axis,
                    apply_scale_factor(position,axis),
                    apply_scale_factor(speed,axis))

        elif words[0] == 'turn':
            name, axis, position, speed = words[1], str_to_axis_idx(words[3]), to_float(words[4]), words[5].lower()
            if speed=='now':
                if t>0. or 'not-looped' in vars:
                    pieces[name].turn_now(axis, apply_rotation_factor(position, axis))
            elif speed=='speed':
                pieces[name].turn_at_speed(
                    axis,
                    apply_rotation_factor(position, axis),
                    apply_rotation_factor(to_float(words[6]), axis))

        elif words[0] == 'sleep':
            dt = 1. / fps
            for name,piece in pieces.items():
                countdown = to_float(words[1]) / 1000.
                countdown = max(dt, countdown)
                while countdown > dt-1e-3:
                    piece.step(dt)
                    countdown -= dt
            t += to_float(words[1]) / 1000.

        else:
            raise ValueError("unknown nBOS command: '{}'".format(words[0]))

    return pieces


def make_sca_header(
    num_frames, duration, num_bones,
    bone_names_section_length, bone_links_section_length,
    frame_size):

    format = '4sllflllll'
    version = 5
    bone_names_offset = struct.calcsize(format)
    bone_links_offset = bone_names_offset + bone_names_section_length
    first_frame_offset = bone_links_offset + bone_links_section_length

    return struct.pack(
        format,
        b'ANIM', version,
        num_frames, duration, num_bones, 
        bone_names_offset, bone_links_offset, first_frame_offset,
        frame_size) 

def make_sca_bone_names_section(bone_names):
    return bytes('\0'.join(bone_names) + '\0', 'utf-8')

def make_sca_bone_links_section(bone_links):
    format = '{}l'.format(len(bone_links))
    return struct.pack(format, *bone_links)

def make_sca_bone_key_frame(pos_xyz, orientation_wxyz):
    format = '7f'
    return struct.pack(format, *pos_xyz, *orientation_wxyz)

def make_sca_key_frame(time, pos_xyz_per_bone, orientation_wxyz_per_bone):
    data = struct.pack('fl', time, 0)
    for pos_xyz, orientation_wxyz in zip(pos_xyz_per_bone, orientation_wxyz_per_bone):
        data += make_sca_bone_key_frame(pos_xyz, orientation_wxyz)
    return data

def make_sca_anim_data(
    fps,
    root_delta_xyz, root_delta_wxyz,
    pos_xyz_per_bone_per_frame, orientation_wxyz_per_bone_per_frame):

    data_head = struct.pack('7f', *root_delta_xyz, *root_delta_wxyz)
    data = b''
    for frame_number, (pos_xyz_per_bone, orientation_wxyz_per_bone) in enumerate(zip(
        pos_xyz_per_bone_per_frame,
        orientation_wxyz_per_bone_per_frame)):

        t = float(frame_number) / fps
        data += make_sca_key_frame(t, pos_xyz_per_bone, orientation_wxyz_per_bone)

    return data_head, data


def quaternion_multiply(q1, q2):
    w1, x1, y1, z1 = q1
    w2, x2, y2, z2 = q2
    return numpy.array([
        w1*w2 - x1*x2 -y1*y2 - z1*z2,
        w1*x2 + x1*w2 + y1*z2 - z1*y2,
        w1*y2 - x1*z2 + y1*w2 + z1*x2,
        w1*z2 + x1*y2 - y1*x2 + z1*w2])


def quaternion_conjugate(q):
    return numpy.array([q[0], -q[1], -q[2], -q[3]])


def unit_quaternion_divide(q1,q2):
    return quaternion_multiply(q1, quaternion_conjugate(q2))


def rpw_to_quaternion(rpw):
    half_angles = numpy.radians(rpw)/2.
    cosines = numpy.cos(half_angles)
    sines = numpy.sin(half_angles)

    yaw = numpy.array([cosines[2], 0., 0., sines[2]])
    pitch = numpy.array([cosines[1], 0., sines[1], 0.])
    roll = numpy.array([cosines[0], sines[0], 0., 0.])
    q = quaternion_multiply(yaw,pitch)
    q = quaternion_multiply(q,roll)
    return q


def to_sca(pieces, fps):
    """
    @param pieces dictionary of tuples: (Piece() object, xyz history, rpw history)
    """

    # ------- bone names section
    bone_names = [ name for name,_ in pieces.items() ]
    bone_names_section = make_sca_bone_names_section(bone_names)

    # ------- bone links section
    bone_links = [
        bone_names.index(pieces[name].parent) if pieces[name].parent in bone_names and pieces[name].parent != name else -1
        for name in bone_names ]
    bone_links_section = make_sca_bone_links_section(bone_links)

    # ------- animation data section
    # num_frames
    for name,piece in pieces.items():
        num_frames = len(piece.cur_xyz)
        break

    # collate and coordinate transform pose data
    pos_xyz_per_bone_per_frame = numpy.zeros((num_frames,len(bone_names),3),dtype=numpy.float)
    orientation_wxyz_per_bone_per_frame = numpy.zeros((num_frames,len(bone_names),4),dtype=numpy.float)
    orientation_wxyz_per_bone_per_frame[:,:,0] = 1.
    for name,piece in pieces.items():
        xyz_per_frame, rpw_per_frame = piece.get_frames()
        for frame_num,xyz in enumerate(xyz_per_frame):
            bone_num = bone_names.index(name)
            pos_xyz_per_bone_per_frame[frame_num,bone_num,:] = xyz
        for frame_num,rpw in enumerate(rpw_per_frame):
            bone_num = bone_names.index(name)
            q = rpw_to_quaternion(rpw)
            orientation_wxyz_per_bone_per_frame[frame_num,bone_num,:] = q

    # root bone delta
    root_pos_delta = [0., 0., 0.]
    root_orientation_delta = [1., 0., 0., 0.]

    # finally animation data
    anim_data_head, anim_data = make_sca_anim_data(
        fps, root_pos_delta, root_orientation_delta,
        pos_xyz_per_bone_per_frame, orientation_wxyz_per_bone_per_frame)

    # -------- header section
    frame_size = int(len(anim_data)/num_frames)
    assert(len(anim_data) == frame_size * num_frames)
    header = make_sca_header(
        num_frames, float(num_frames-1)/fps, len(bone_names),
        len(bone_names_section), len(bone_links_section),
        frame_size)
    
    return header + bone_names_section + bone_links_section + anim_data_head + anim_data


def construct_pieces(scm_filename):
    with open(scm_filename, 'rb') as file:
        bones = scm.dumpscm.load_bones(file)
        pieces = {
            name: Piece(name, parent, xyz0, rpw0)
            for name,(parent,xyz0,wxyz0,rpw0) in bones.items()
        }
    return pieces


def process_nbos(nbosfile, args):
    print("NBOS script:{}".format(nbosfile))
    with open(nbosfile, 'rt') as file:
        script = file.read()
    statements, vars = parse_nbos(script)

    try:
        # command line scm overrides scm-file-path directive in nbos file
        scmfile = args.scmfile or vars['scm-file-path']
    except KeyError:
        # otherwise default look for scm with similar name/path as nbos file
        scmfile = os.path.splitext(nbosfile)[0]+'.scm'

    scmdir = os.path.dirname(scmfile)
    nbosdir = os.path.dirname(nbosfile)
    if scmdir=='' and nbosdir!='':
        # prepend a path if required and available
        scmfile = os.path.join(nbosdir,scmfile)

    print("  SCM input:{}".format(scmfile))
    pieces = construct_pieces(scmfile)
    run_nbos(statements, pieces, vars, args.fps)
    
    if not 'not-looped' in vars:
        # run again using final position as new starting position
        for _,piece in pieces.items():
            piece.reset()
        run_nbos(statements, pieces, vars, args.fps)

    scafile = args.scafile or os.path.splitext(nbosfile)[0]+'.sca'
    print("  SCA output:{}".format(scafile))
    with open(scafile, 'wb') as file:
        file.write(to_sca(pieces, args.fps))


def recursive_process_filespec(filespec, args):

    if os.path.isfile(filespec) and os.path.splitext(filespec)[-1].lower()==".nbos":
        process_nbos(filespec, args)
        
    elif os.path.isdir(filespec):
        for subdir, dirs, files in os.walk(filespec):
            for file in files:
                recursive_process_filespec(os.path.join(subdir,file), args)


if __name__ == "__main__":

    try:

        import argparse
        import scm.dumpscm
        import traceback

        parser = argparse.ArgumentParser()
        parser.add_argument('filespec', nargs='*', help='path to the .nbos (not)bos file(s) containing the TA annimation script, and/or directories in which to search for .nbos files.')
        parser.add_argument('--scmfile', help='path to the existing file containing .scm supcom model associated with the script. Overrides any "scm-file-path" statement in the nBOS file', default=None)
        parser.add_argument('--scafile', help='path of the new supcom .sca animation file to create.  Default matches the nbosfile but with extension ".sca"', default=None)
        parser.add_argument('--fps', type=float, help='frames per second.  default=30', default=30.)
        args = parser.parse_args()

        for filespec in args.filespec:
            recursive_process_filespec(filespec, args)

    except:
        traceback.print_exc()
        input("Press Enter to continue ...")

    else:
        input("Press Enter to continue ...")

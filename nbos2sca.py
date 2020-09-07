import copy
import numpy
import struct
import sys

class Piece:

    def __init__(self, name, parent, xyz0, rpw0):
        """
        @param name, parent: strings
        """

        self.name = name
        self.parent = parent

        self.cur_xyz = [ [x for x in xyz0] ]
        self.vel_xyz = [0., 0., 0.]
        self.target_xyz = [x for x in xyz0]

        # rpw: roll(about +X), pitch(about +Y), yaw(about +Z)
        self.cur_rpw = [ [x for x in rpw0] ]
        self.rate_rpw = [0., 0., 0.]
        self.target_rpw = [x for x in rpw0]

    def get_frames(self):
        return self.cur_xyz, self.cur_rpw

    def move_now(self, axis_idx, target):
        self.cur_xyz[-1][axis_idx] = self.cur_xyz[0][axis_idx] + target
        self.vel_xyz[axis_idx] = 0.
        self.target_xyz[axis_idx] = self.cur_xyz[-1][axis_idx]

    def turn_now(self, axis_idx, target):
        self.cur_rpw[-1][axis_idx] = self.cur_rpw[0][axis_idx] + target
        self.vel_rpw[axis_idx] = 0.
        self.target_rpw[axis_idx] = self.cur_rpw[-1][axis_idx]

    def move_at_speed(self, axis_idx, target, speed):
        self.vel_xyz[axis_idx] = speed
        self.target_xyz[axis_idx] = self.cur_xyz[0][axis_idx] + target

    def turn_at_speed(self, axis_idx, target, speed):
        self.rate_rpw[axis_idx] = speed
        self.target_rpw[axis_idx] = self.cur_rpw[0][axis_idx] + target

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


def parse_cob(script, pieces, fps):
    """
    @param script: string containing the (not)bos script
    @param pieces: dictionary of Piece objects
    """

    SCALE_FACTORS = [2.5, 2.5, -2.5]
    def apply_scale(coord, axis):
        return coord/SCALE_FACTORS[axis]

    def str_to_axis_idx(axis_str):
        return { 'x-axis':0, 'y-axis':1, 'z-axis':2 }[axis_str]

    def to_float(number_str):
        try:
            return float(number_str)
        except ValueError:
            return float(number_str[1:-1])

    for statement in script.split(';'):

        statement = statement.strip()
        statement = statement.replace(',', ' ')
        statement = statement.replace('\n', ' ')
        words = [w.lower() for w in statement.split(' ') if len(w)>0]
        if len(words) == 0:
            continue

        if words[0] == 'scales':
            SCALE_FACTORS = [ to_float(w) for w in (words[1],words[2],words[3]) ]

        elif words[0] == 'move':
            name, axis, position, speed = words[1], str_to_axis_idx(words[3]), to_float(words[4]), words[5]
            if speed=='now':
                pieces[name].move_now(axis, apply_scale(position, axis))
            elif speed=='speed':
                speed = to_float(words[6])
                pieces[name].move_at_speed(axis, apply_scale(position,axis), apply_scale(speed,axis))

        elif words[0] == 'turn':
            name, axis, position, speed = words[1], str_to_axis_idx(words[3]), to_float(words[4]), words[5]
            if speed=='now':
                pieces[name].turn_now(axis, position)
            elif speed=='speed':
                pieces[name].turn_at_speed(axis, position, to_float(words[6]))

        elif words[0] == 'sleep':
            dt = 1. / fps
            for name,piece in pieces.items():
                t = to_float(words[1]) / 1000.
                while t > dt-1e-3:
                    piece.step(dt)
                    t -= dt

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
            orientation_wxyz_per_bone_per_frame[frame_num,bone_num,:] = rpw_to_quaternion(rpw)

    # root bone delta
    """
    root_bone_idx = bone_links.index(-1)
    root_pos_delta = pos_xyz_per_bone_per_frame[-1,root_bone_idx,:] - pos_xyz_per_bone_per_frame[0,root_bone_idx,:]
    root_orientation_delta = unit_quaternion_divide(
        orientation_wxyz_per_bone_per_frame[-1,root_bone_idx,:],
        orientation_wxyz_per_bone_per_frame[0,root_bone_idx,:])
    """
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


if __name__ == "__main__":

    import argparse
    import scm.dumpscm

    parser = argparse.ArgumentParser()
    parser.add_argument('--nbosfile', help='path to the .nbos (not)bos file containing the TA annimation script')
    parser.add_argument('--scmfile', help='path to the existing file containing .scm supcom model associated with the script')
    parser.add_argument('--scafile', help='path of the new supcom .sca animation file to create')
    parser.add_argument('--fps', type=float, help='frames per second', default=30.)

    args = parser.parse_args()

    with open(args.scmfile, 'rb') as file:
        bones = scm.dumpscm.load_bones(file)
        pieces = {
            name: Piece(name, parent, xyz0, rpw0)
            for name,(parent,xyz0,wxyz0,rpw0) in bones.items()
        }

    with open(args.nbosfile, 'rt') as file:
        script = file.read()
        parse_cob(script, pieces, args.fps)

    with open(args.scafile, 'wb') as file:
        file.write(to_sca(pieces, args.fps))

/**************************************************************************************************
Copyright (c) 2006 Gas Powered Games Corp. All Rights Reserved. 
Gas Powered Games and Supreme Commander are the exclusive trademarks of Gas Powered Games Corp.
***************************************************************************************************/

#ifndef SCAFILE_H
#define SCAFILE_H


// SScaFileHeader -- The header for .SCA files.
//
struct SScaFileHeader
{
    // The FOURCC 'ANIM'
    unsigned long mMagic;

    // The .SCA version number.
    unsigned long mVersion;

    // The number of frames in this animation.
    unsigned long mNumFrames;

    // The duration (in seconds) of this animation.  
    // The animation plays at (mNumFrames-1)/mDuration frames per second.
    float mDuration;

    // The number of bones in this animation.
    unsigned long mNumBones;

    // Offset of the bone names (SScaFileBoneNames[0])
    unsigned long mBoneNamesOffset;

    // Offset of the bone link info (SScaFileBoneLinks[0])
    unsigned long mBoneLinksOffset;

    // Offset of the actual animation data (SScaFileAnimData[0])
    unsigned long mFirstFrameOffset;

    // The number of bytes in one animation frame.
    unsigned long mFrameSize;
};

// SScaFileBoneNames -- The bone names used in this animation.
//
struct SScaFileBoneNames
{
    // Array of bone names.  There are header.mNumBones NUL terminated
    // strings concatenated together starting here.
    char mBoneNameData[1]; //(array size is mNumBones)
};

// SScaFileBoneLinks -- The parent links for the bones used in this animation.
//
struct SScaFileBoneLinks
{
    // Array of bone indices. 
    unsigned long mParentBoneIndex[]; //(array size is mNumBones)
};

// SScaFileBoneKeyframe -- The data for single bone at a single key
// frame.
//
struct SScaFileBoneKeyframe
{
    // Position relative to the parent bone.
    // Vector (x,y,z)
    float mPosition[3];

    // Rotation relative to the parent bone.
    // Quaternion (w,x,y,z)
    float mRotation[4];
};

// SScaFileKeyframe -- The data about a single key frame.
//
struct SScaFileKeyframe
{
    // The time (in seconds) of this keyframe.
    float mTime;

    // Various flags.  None defined yet.
    unsigned long mFlags;

    // Array of keyframe data for each bone.
    SScaFileBoneKeyframe mBones[1];  //(array size is mNumBones)
};

// SScaFileAnimData -- The actual animation data.
//
struct SScaFileAnimData
{
    // The total position delta between the first frame and the last frame.
    // Vector (x,y,z)
    float mPositionDelta[3];

    // The total orientation delta between the first frame and the last frame.
    // Quaternion (w,x,y,z)
    float mOrientDelta[4];

    // The per-frame data.
    SScaFileKeyframe mFrames[1];  //(array size is mNumFrames)
};


#endif SCAFILE_H

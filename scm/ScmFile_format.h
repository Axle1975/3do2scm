/**************************************************************************************************
Copyright (c) 2006 Gas Powered Games Corp. All Rights Reserved. 
Gas Powered Games and Supreme Commander are the exclusive trademarks of Gas Powered Games Corp.
***************************************************************************************************/

#ifndef SCMFILE_H
#define SCMFILE_H

// SCM VERSION 5 DATA LAYOUT

// Multi-byte data is writting in little-endian ("Intel") format 

// There are 5 required and 2 optional sections in an SCM file, each indicated by a leading FOURCC code:

// FOURCC  |  Contents
// --------+------------------------
// 'MODL'  | Header info
// 'NAME'  | List of bone name strings
// 'SKEL'  | Array of bone data
// 'VTXL'  | Array of basic vertex data
// 'TRIS'  | Array of triangle indices
// 'VEXT'  | Array of extra vertex data (OPTIONAL SECTION)
// 'INFO'  | List of null terminated information strings (OPTIONAL SECTION)

// Section offsets in the file header point to the start of the data for that section (ie, the first byte AFTER
// the section's identifying FOURCC) Padding characters are added to the end of each section to ensure that 
// the next section is 16-byte aligned. Ommitted sections are indicated by an offset of 0. 
 
// *** All offsets are relative to the start of the file ***

//
//
struct ScmHeader
{

    // The FOURCC 'MODL'
    unsigned long mMagic;

	// The .SCM version number
    unsigned long mVersion;

    // Offset to SCM_BoneData[0]
    unsigned long mBoneOffset;
    
    // Number of elements in SCM_BoneData that actually influence verts (no reference points)
    unsigned long mWeightedBoneCount;

    // Offset of basic vertex data section (SCM_VertData[0])
    unsigned long mVertexOffset;

    // Offset of extra vertex data section (SCM_VertExtraData[0]) 
    // Contains additional per-vertex information. *** Currently unused (and omitted) in SupCom 1.0 ***
    unsigned long mVertexExtraOffset;   

    // Number of elements in the SCM_VertData array
    // (and the SCM_VertExtraData array, if mVertexExtraOffset != 0)
    unsigned long mVertexCount;        

    // Offset of the triangle index section (SCM_TriangleData[0])
    unsigned long mIndexOffset;         

    // Number of elements in the SCM_TriangleData array
    unsigned long mIndexCount;          

    // Offset of information section (SCM_InfoData[0])
    unsigned long mInfoOffset;
              
    // Number of elements in the SCM_InfoData list
    unsigned long mInfoCount;           

    // Number of elements in the SCM_BoneData array (including 'reference point' bones)
    unsigned long mTotalBoneCount;      
};

//
//
struct ScmBoneData
{
	// Inverse transform of the bone relative to the local origin of the mesh
    // 4x4 Matrix with row major (i.e. D3D default ordering)
    float mRestPoseInverse[4][4];

     // Position relative to the parent bone.
    // Vector (x,y,z)
    float mPosition[3];

    // Rotation relative to the parent bone.
    // Quaternion (w,x,y,z)
    float mRotation[4];

	// Offset of the bone's name string
    unsigned long mNameOffset;

	// Index of the bone's parent in the SCM_BoneData array
    unsigned long mParentBoneIndex;

    unsigned long RESERVED_0;      
    unsigned long RESERVED_1;      
};

//
//
struct ScmVertData
{
	// Position of the vertex relative to the local origin of the mesh
    float mPosition[3];

	// 'Tangent Space' normal, tangent & binormal unit vectors
    float mNormal[3];
    float mTangent[3];
    float mBinormal[3];

	// Two sets of UV coordinates 
    float mUV0[2];
    float mUV1[2];

    // Up to 4-bone skinning can be supported using additional 
    // indices (in conjunction with bone weights in the optional VertexExtra array)
    // Skinned meshes are not used in SupCom 1.0 so only mBoneIndex[0] is expected
    // to contain a valid index.
    unsigned char mBoneIndex[4]; 
};

struct ScmTriangleData
{
    unsigned short triIndices[3];
};


#endif SCMFILE_H

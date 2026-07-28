
# Written by Aexadev on 15/07/26 - 28/07/26

from inc_noesis import *
import noesis # type: ignore
import rapi  # type: ignore
import os



def registerNoesisTypes():
    for ext in [".main", ".playerdata", ".mission", ".submap", ".map"]:
        handle = noesis.register("Kapow Engine Compiled Asset", ext)
        noesis.setHandlerTypeCheck(handle, ChkPak)
        noesis.setHandlerExtractArc(handle, LoadPak)
        
    thd = noesis.register("Kapow Engine Texture", ".kpwtex")
    noesis.setHandlerTypeCheck(thd, texChk)
    noesis.setHandlerLoadRGBA(thd, texLoad)   
    
    kpmdl = noesis.register("Kapow Engine Model", ".model") 
    noesis.setHandlerTypeCheck(kpmdl, ChkMdl)
    noesis.setHandlerLoadModel(kpmdl, LoadMdl)
    
    global LOAD_ANIMS
    LOAD_ANIMS = False                                        
    hAnimToggle = noesis.registerTool("Load animation", loadAnimToggle)
    noesis.setToolSubMenuName(hAnimToggle, "kapowEngine(TOD)")
    noesis.checkToolMenuItem(hAnimToggle, LOAD_ANIMS)
    
    global LOAD_ANIMS_AUTO
    LOAD_ANIMS_AUTO = True                                        
    hAnimToggleA = noesis.registerTool("Load animation auto", loadAnimToggleA)
    noesis.setToolSubMenuName(hAnimToggleA, "kapowEngine(TOD)")
    noesis.checkToolMenuItem(hAnimToggleA, LOAD_ANIMS)

    return 1

def loadAnimToggle(toolIndex):
    global LOAD_ANIMS
    LOAD_ANIMS = not LOAD_ANIMS
    noesis.checkToolMenuItem(toolIndex, LOAD_ANIMS)
    return 1

def loadAnimToggleA(toolIndex):
    global LOAD_ANIMS_AUTO
    LOAD_ANIMS_AUTO = not LOAD_ANIMS_AUTO
    noesis.checkToolMenuItem(toolIndex, LOAD_ANIMS_AUTO)
    return 1

def ChkMdl(data):
    bs = NoeBitStream(data)
    if len(data) >28:
        val2 = bs.readInt()
        bs.seek(bs.readInt()-4,NOESEEK_REL)
        val = bs.readBytes(6)
        if val == b"/data/" and val2 == 3:
            return 1 
        else: return 0
    else: return 0


def ChkPak(data):
    bs = NoeBitStream(data)
    if len(data) >28:
        bs.seek(37)
        if bs.readUShort() == 0x7F90:
            return 1
        
        
        
        bs.seek(28,NOESEEK_ABS)
        bs.seek(bs.readInt()-4,NOESEEK_REL)
        val = bs.readBytes(6)
        if val == b"/data/":
            return 1 
        else: return 0
        
        
        
    else: return 0
    
    
def texChk(data):
    bs = NoeBitStream(data)
    if bs.readBytes(8) == b"KPOWTXTR": return 1
    else:
        return 0
    

TEX_FMT = {
    1: "A8R8G8B8",
    7: "DXT1",
    8: "DXT2",
    9: "DXT3",
    10: "DXT4",
    11: "DXT5"
}
def LoadPak(fileName, fileLen, justChecking):
    data = rapi.loadIntoByteArray(fileName)
    
    ChkPak(data)

    bs = NoeBitStream(data)
    
    noesis.logPopup()
    if justChecking:
        return 1 
    
    if rapi.getInputName().endswith(".map"):
        bs.seek(0x12B)
        td = bs.readBytes(len(data)-bs.tell())
        bs = NoeBitStream(td)
    
    TS = bs.readUInt()
    PCHKSUM = bs.readUInt()
    CCHKSUM = bs.readUInt()
    FILE_COUNT = bs.readUInt()
    if FILE_COUNT == 0: noesis.doException("Empty file.")
    INFO_SIZE = bs.readUInt()
    MAX_ASSET_SIZE = bs.readUInt()

    INFO_START = bs.tell()
    INFO_END = INFO_START + INFO_SIZE

    resourcePos = INFO_START
    _thisStart = INFO_START
    

    bs.seek(INFO_END, NOESEEK_ABS)
    RESOURCE_SIZES = [bs.readUInt() for _ in range(FILE_COUNT)]
    imageDataOffset = bs.tell()
    for f in range(FILE_COUNT):
        currentResourcePos = resourcePos

        bs.seek(currentResourcePos, NOESEEK_ABS)
        ASSET_TYP = bs.readUInt()

        nameFieldPos = bs.tell()
        nameRel = bs.readInt()
        OFS_FNAME = (nameFieldPos + nameRel) & ~3

        bs.seek(OFS_FNAME, NOESEEK_ABS)
        FNAME = bs.readString()

        print(f, FNAME)

        if f + 1 < FILE_COUNT:
            resourcePos = FindNext(
                bs,
                currentResourcePos,
                INFO_START,
                INFO_END
            )
            _thisEnd = resourcePos
        else:
            _thisEnd = INFO_END

        bs.seek(_thisStart, NOESEEK_ABS)
        dta = bs.readBytes(_thisEnd - _thisStart)

        if ASSET_TYP == 0:  # Texture
            gfxField = currentResourcePos + 0x28

            bs.seek(gfxField, NOESEEK_ABS)
            gfxOffset = (gfxField + bs.readInt()) & ~3

            bs.seek(gfxOffset + 0x14, NOESEEK_ABS)
            width = bs.readUInt()
            height = bs.readUInt()
            formatIndex = bs.readUInt()
            bs.seek(imageDataOffset, NOESEEK_ABS)
            tdta = bs.readBytes(RESOURCE_SIZES[f])

            writer = NoeBitStream()
            writer.writeBytes(b"KPOWTXTR")
            writer.writeUInt(width)
            writer.writeUInt(height)
            writer.writeUInt(formatIndex)
            writer.writeUInt(len(tdta))
            writer.writeBytes(tdta)

            FNAME = os.path.splitext(FNAME)[0] + ".kpwtex"
            dta = writer.getBuffer()
            

        rapi.exportArchiveFile(FNAME, dta)
        imageDataOffset += RESOURCE_SIZES[f]

        _thisStart = _thisEnd

    return 1



def texLoad(dta,texList):
    bs = NoeBitStream(dta)
    bs.readBytes(8)
    WIDTH = bs.readUInt()
    HEIGHT = bs.readUInt()
    PFMT = TEX_FMT.get(bs.readUInt())
    rawDta = bs.readBytes(bs.readUInt())
    
    if PFMT == "DXT1":
        rgba = rapi.imageDecodeDXT(rawDta, WIDTH, HEIGHT, noesis.FOURCC_DXT1)
        
    elif PFMT =="A8R8G8B8":
        rgba = rapi.imageDecodeRaw(rawDta, WIDTH, HEIGHT, "b8g8r8a8")
        
    elif PFMT =="DXT2":
        pass
    elif PFMT =="DXT3":
        rgba = rapi.imageDecodeDXT(rawDta, WIDTH, HEIGHT, noesis.FOURCC_DXT3)
    elif PFMT =="DXT4":
        pass
    elif PFMT =="DXT5":
        rgba = rapi.imageDecodeDXT(rawDta, WIDTH, HEIGHT, noesis.FOURCC_DXT5)
    
    tex = NoeTexture("_tex", WIDTH, HEIGHT, rgba, noesis.NOESISTEX_RGBA32)
    texList.append(tex)
    return 1
        


def FindNext(bs, pos, infoStart, infoEnd):
    pos += 4

    while pos + 28 <= infoEnd:
        bs.seek(pos, NOESEEK_ABS)

        assetType = bs.readUInt()
        nameRel = bs.readInt()
        globalId = bs.readUInt()
        mark = bs.readUInt()

        namePos = (pos + 4 + nameRel) & ~3

        if (assetType <= 10 and globalId == 0 and
            mark == 0xBAADF00D and
            infoStart <= namePos < infoEnd):

            bs.seek(namePos, NOESEEK_ABS)

            if bs.readString().startswith("/data"):
                return pos

        pos += 4

    noesis.doException("Next resource not found.")
    
    
def Align4(bs):
        bs.seek(-bs.tell() %4,NOESEEK_REL)
        
def ReadOfsRelToAbs(bs):
    relativeto = bs.tell()
    relativeOffset = bs.readInt()
    absoluteOffset = relativeto + relativeOffset
    return absoluteOffset 


VERTEX_LAYOUTS = {
    (0x044, 20): {"color": 16},
    (0x104, 24): {"uv0": 16},
    (0x144, 28): {"color": 16, "uv0": 20},
    (0x012, 24): {"normal": 12},
    (0x042, 16): {"color": 12},
    (0x052, 28): {"normal": 12, "color": 24},
    (0x112, 32): {"normal": 12, "uv0": 24},
    (0x212, 40): {"normal": 12, "uv0": 24, "uv1": 32},
    (0x142, 24): {"color": 12, "uv0": 16},
    (0x152, 36): {"normal": 12, "color": 24, "uv0": 28},
    (0x112, 48): {"normal": 12, "uv0": 24},
    (0x012, 40): {"normal": 12},
}

import struct


D3DPT_POINTLIST = 1
D3DPT_LINELIST = 2
D3DPT_LINESTRIP = 3
D3DPT_TRIANGLELIST = 4
D3DPT_TRIANGLESTRIP = 5
D3DPT_TRIANGLEFAN = 6

D3D_TO_RPG_PRIMITIVE = {
    D3DPT_TRIANGLELIST: noesis.RPGEO_TRIANGLE,
    D3DPT_TRIANGLESTRIP: noesis.RPGEO_TRIANGLE_STRIP,
    D3DPT_TRIANGLEFAN: noesis.RPGEO_TRIANGLE_FAN,
}

def LoadMdl(data, mdl_list):
    bs = NoeBitStream(data)
    rapi.rpgCreateContext()
    rapi.rpgSetPosScaleBias((-1.0, 1.0, 1.0), None)
    #noesis.logPopup()
    #rapi.rpgSetOption(noesis.RPGOPT_TRIWINDBACKWARD, 1)
    #rapi.rpgSetOption(noesis.RPGOPT_SWAPHANDEDNESS, 1)

    ASSET_TYP = bs.readUInt()
    OFS_FNAME = ReadOfsRelToAbs(bs)

    bs.seek(OFS_FNAME, NOESEEK_ABS)
    FNAME = bs.readString()
    print(FNAME)

    #TEXTURE LIST
    bs.seek(0x20, NOESEEK_ABS)
    OFS_TEX_LIST = RelOffs(bs)
    TEX_LIST_COUNT = bs.readUInt()
    texList = []

    for t in range(TEX_LIST_COUNT):
        bs.seek(OFS_TEX_LIST + t * 8 + 4, NOESEEK_ABS)
        OFF_TEX_NAME = RelOffs(bs)

        if OFF_TEX_NAME == 0:
            texList.append("")
            continue

        bs.seek(OFF_TEX_NAME, NOESEEK_ABS)
        tName = bs.readString()
        print(tName)
        texList.append(tName)

    #MESH LIST
    bs.seek(0x30, NOESEEK_ABS)
    OFF_MESH_LIST = RelOffs(bs)
    MESH_LIST_COUNT = bs.readUInt()

    #MATERIALS
    matList = []
    inputDir = rapi.getDirForFilePath(rapi.getInputName())
    inputDir = inputDir.replace("\\", "/")
    rtPthMrk = inputDir.lower().find("/data/")
    root = inputDir[:rtPthMrk] if rtPthMrk >= 0 else inputDir

    for t in range(len(texList)):
        if texList[t]:
            textureRelPath = texList[t].replace("\\", "/").lstrip("/")
            texturePath = os.path.join(root, textureRelPath)
            texturePath = os.path.splitext(texturePath)[0] + ".kpwtex"
            texturePath = texturePath.replace("\\", "/")
        else:
            texturePath = ""

        mat = NoeMaterial("_mat%d" % t, texturePath)
        mat.setTexture(texturePath)
        matList.append(mat)

    if len(matList) == 0:
        matList.append(NoeMaterial("_mat0", ""))

    #BONES
    boneList = []
    boneNames = []

    for m in range(MESH_LIST_COUNT):
        meshPos = OFF_MESH_LIST + m * 0x7C

        bs.seek(meshPos, NOESEEK_ABS)
        position = NoeVec3((bs.readFloat(), bs.readFloat(), bs.readFloat()))
        rotation = NoeQuat((bs.readFloat(), bs.readFloat(), bs.readFloat(), bs.readFloat()))

        bs.seek(meshPos + 0x1C, NOESEEK_ABS)
        OFF_MESH_NAME = RelOffs(bs)

        if OFF_MESH_NAME:
            bs.seek(OFF_MESH_NAME, NOESEEK_ABS)
            meshName = bs.readString()
        else:
            meshName = "mesh_%d" % m

        bs.seek(meshPos + 0x58, NOESEEK_ABS)
        parentIndex = bs.readInt()

        if rotation.length() > 0.0:
            rotation = rotation.normalize()

        boneMatrix = rotation.toMat43()
        boneMatrix[3] = position
        boneMatrix = boneMatrix.swapHandedness()

        boneNames.append(meshName)
        boneList.append(NoeBone(m, meshName, boneMatrix, None, parentIndex))

    boneList = rapi.multiplyBones(boneList)

    #MESH
    for m in range(MESH_LIST_COUNT):
        meshPos = OFF_MESH_LIST + m * 0x7C

        bs.seek(meshPos + 0x24, NOESEEK_ABS)
        OFF_SK_LIST = RelOffs(bs)
        SK_LIST_CNT = bs.readUInt()

        for s in range(SK_LIST_CNT):
            skinnedMeshPos = OFF_SK_LIST + s * 0x3C
            print("++++++++++ MESH [%d/%d] SUBMESH [%d/%d] ++++++++++++" % (
                m + 1,
                MESH_LIST_COUNT,
                s + 1,
                SK_LIST_CNT
            ))

            bs.seek(skinnedMeshPos, NOESEEK_ABS)
            OFF_MESHBUF = RelOffs(bs)

            if OFF_MESHBUF == 0:
                continue
            bs.seek(skinnedMeshPos + 0x08, NOESEEK_ABS)
            OFF_TEX_SET_LIST = RelOffs(bs)
            TEX_SET_COUNT = bs.readUInt()
            textureIndex = 0

            if OFF_TEX_SET_LIST and TEX_SET_COUNT > 0:
                bs.seek(OFF_TEX_SET_LIST, NOESEEK_ABS)
                textureIndex = bs.readInt()

            if textureIndex < 0 or textureIndex >= len(matList):
                textureIndex = 0

            #MESHBUFFER
            bs.seek(OFF_MESHBUF + 0x0C, NOESEEK_ABS)
            OFF_VERTEXBUF = RelOffs(bs)
            OFF_INDEXBUF = RelOffs(bs)

            if OFF_VERTEXBUF == 0 or OFF_INDEXBUF == 0:
                continue

            #VERTEXBUFFER
            bs.seek(OFF_VERTEXBUF, NOESEEK_ABS)
            VERTEX_COUNT = bs.readUInt()
            bs.readUInt()
            FVF_FORMAT = bs.readUInt()
            PVTX_SIZE = bs.readUInt()
            OFF_VTXARRAY = RelOffs(bs)
            FVF_STRIDE = bs.readUShort()

            bs.seek(OFF_VTXARRAY, NOESEEK_ABS)
            fvfBuf = bs.readBytes(PVTX_SIZE)

            layout = VERTEX_LAYOUTS.get((FVF_FORMAT, FVF_STRIDE))

            if layout is None:
                noesis.doException(
                    'Unsupported vertex format FVF=0x%X stride=%d'
                    % (FVF_FORMAT, FVF_STRIDE)
                )

            expectedVertexSize = VERTEX_COUNT * FVF_STRIDE

            if len(fvfBuf) < expectedVertexSize:
                noesis.doException(
                    'Vertex data too small: expected %d, got %d'
                    % (expectedVertexSize, len(fvfBuf))
                )

            #INDEXBUFFER
            bs.seek(OFF_INDEXBUF, NOESEEK_ABS)
            INDEX_COUNT = bs.readUInt()
            bs.readUInt()
            TOPOLOGY = bs.readUInt()
            OFF_INDEX_ARRAY = RelOffs(bs)

            primitiveType = D3D_TO_RPG_PRIMITIVE.get(TOPOLOGY)

            if primitiveType is None:
                noesis.doException(
                    'Unsupported primitive topology %d'
                    % TOPOLOGY
                )

            if OFF_INDEX_ARRAY == 0 or INDEX_COUNT < 3:
                continue

            bs.seek(OFF_INDEX_ARRAY, NOESEEK_ABS)
            idxBuf = bs.readBytes(INDEX_COUNT * 2)

            bs.seek(OFF_INDEX_ARRAY + INDEX_COUNT * 2, NOESEEK_ABS)
            Align4(bs)
            OFF_SKIN_DATA = bs.tell()

            skinBuffers = WSkinning(
                data,
                fvfBuf,
                OFF_SKIN_DATA,
                VERTEX_COUNT,
                FVF_STRIDE,
                len(boneList)
            )

            if skinBuffers:
                boneIdxBuf, boneWgtBuf = skinBuffers
                isSmoothSkin = True
            else:
                boneIdxBuf = bytearray(
                    struct.pack("<4I", m, 0, 0, 0) * VERTEX_COUNT
                )
                boneWgtBuf = bytearray(
                    struct.pack("<4f", 1.0, 0.0, 0.0, 0.0) * VERTEX_COUNT
                )
                isSmoothSkin = False

            noeMeshName = "%s_%d" % (boneNames[m], s)

            rapi.rpgClearBufferBinds()

            if isSmoothSkin:
                rapi.rpgSetTransform(None)
            else:
                rapi.rpgSetTransform(boneList[m].getMatrix())

            rapi.rpgSetName(noeMeshName)
            rapi.rpgSetMaterial(matList[textureIndex].name)
            rapi.rpgBindPositionBuffer(
                fvfBuf,
                noesis.RPGEODATA_FLOAT,
                FVF_STRIDE
            )

            if 'normal' in layout:
                rapi.rpgBindNormalBufferOfs(
                    fvfBuf,
                    noesis.RPGEODATA_FLOAT,
                    FVF_STRIDE,
                    layout['normal']
                )

            if 'uv0' in layout:
                rapi.rpgBindUV1BufferOfs(
                    fvfBuf,
                    noesis.RPGEODATA_FLOAT,
                    FVF_STRIDE,
                    layout['uv0']
                )

            if 'uv1' in layout:
                rapi.rpgBindUV2BufferOfs(
                    fvfBuf,
                    noesis.RPGEODATA_FLOAT,
                    FVF_STRIDE,
                    layout['uv1']
                )

            if 'color' in layout:
                rapi.rpgBindColorBufferOfs(
                    fvfBuf,
                    noesis.RPGEODATA_UBYTE,
                    FVF_STRIDE,
                    layout['color'],
                    4
                )

            if boneList:
                rapi.rpgBindBoneIndexBuffer(boneIdxBuf, noesis.RPGEODATA_UINT, 16, 4)
                rapi.rpgBindBoneWeightBuffer(boneWgtBuf, noesis.RPGEODATA_FLOAT, 16, 4)

            rapi.rpgCommitTriangles(
                idxBuf,
                noesis.RPGEODATA_USHORT,
                INDEX_COUNT,
                primitiveType
            )
            rapi.rpgSetTransform(None)

    mdl = rapi.rpgConstructModel()


    mdl.setModelMaterials(NoeModelMaterials([], matList))
    mdl.setBones(boneList)

    if (LOAD_ANIMS or LOAD_ANIMS_AUTO) and boneList:
        if LOAD_ANIMS:
            animFile = rapi.loadPairedFileGetPath("Kapow Engine animation", ".animation")
            if animFile:
                animation = LoadAnim(boneList, animFile, None)

                if animation:
                    mdl.setAnims([animation])
                    rapi.setPreviewOption("setAnimSpeed", str(animation.frameRate))  
                    
                    
        elif LOAD_ANIMS_AUTO:
            
            animPaths = []
            noeAnims = []
            for root, dirs, names in os.walk(inputDir):
                for name in names:
                    if name.lower().endswith(".animation"):
                        animPaths.append(os.path.join(root, name))
            
            for i,animPath in enumerate(animPaths):
                animData = rapi.loadIntoByteArray(animPath)
                animation = LoadAnim(boneList, (animData,animPath), None)
                noeAnims.append(animation)
            
            if len(noeAnims)>0:
                mdl.setAnims(noeAnims)
                rapi.setPreviewOption("setAnimSpeed", str(animation.frameRate))        
               
                        
                        
    rapi.setPreviewOption("setSkelToShow", str(1))
    mdl_list.append(mdl)
    return 1


def RelOffs(bs):
    relTo = bs.tell()
    rel = bs.readInt()
    if (rel & ~3) == 0:
        return 0

    return (relTo + rel) & ~3


def WSkinning(data, fvfBuf, offset, vertexCount, fvfStride, boneCount):
    skinStride = fvfStride + 0x40
    skinEnd = offset + vertexCount * skinStride

    if skinEnd > len(data):
        return None

    boneIdxBuf = bytearray()
    boneWgtBuf = bytearray()

    for v in range(vertexCount):
        skinVertex = offset + v * skinStride
        fvfVertex = v * fvfStride

        if data[skinVertex:skinVertex + fvfStride] != fvfBuf[fvfVertex:fvfVertex + fvfStride]:
            return None

        indices = struct.unpack_from("<8I", data, skinVertex + fvfStride)
        weights = struct.unpack_from("<8f", data, skinVertex + fvfStride + 0x20)
        influences = []

        for w in range(8):
            if indices[w] < boneCount and weights[w] > 0.0 and weights[w] <= 1.01:
                influences.append((indices[w], weights[w]))

        if len(influences) == 0:
            return None

        influences.sort(key=lambda influence: influence[1], reverse=True)
        influences = influences[:4]
        weightTotal = sum(influence[1] for influence in influences)
        packedIndices = [0, 0, 0, 0]
        packedWeights = [0.0, 0.0, 0.0, 0.0]

        for w in range(len(influences)):
            packedIndices[w] = influences[w][0]
            packedWeights[w] = influences[w][1] / weightTotal

        boneIdxBuf.extend(struct.pack("<4I", *packedIndices))
        boneWgtBuf.extend(struct.pack("<4f", *packedWeights))

    return boneIdxBuf, boneWgtBuf



BNELST = [
    "GamePivot", "Bip", "Pelvis", "Spine", "Spine1", "Spine2", "Spine3",
    "Neck", "Head", "Chin", "ChinR", "ChinL", "Eyelid", "EyeBR", "EyeBL",
    "EyeR", "EyeL", "L Clavicle", "L UpperArm", "L Forearm", "L Hand",
    "L Finger0", "L Finger01", "L Finger1", "L Finger11", "L Finger2",
    "L Finger21", "L ForeTwist", "L ForeTwist1", "R Clavicle", "R UpperArm",
    "R Forearm", "R Hand", "R Finger0", "R Finger01", "R Finger1",
    "R Finger11", "R Finger2", "R Finger21", "R ForeTwist", "R ForeTwist1",
    "L Thigh", "L Calf", "L Foot", "L Toe0", "R Thigh", "R Calf",
    "R Foot", "R Toe0"
]


def LoadAnim(bones, file, boneLengths):
    data, filename = file
    bs = NoeBitStream(data)

    if bs.readUInt() != 9:
        noesis.doException("Animation header check failed")

    bs.seek(0x20, NOESEEK_ABS)
    FRAME_RATE = bs.readFloat()

    bs.seek(0x28, NOESEEK_ABS)
    FRAME_COUNT = bs.readUInt()

    bs.seek(0x5C, NOESEEK_ABS)
    OFF_TRACK_DATA = RelOffs(bs)
    TRACK_DATA_SIZE = bs.readUInt()
    POS_TRACK_COUNT = bs.readUShort()
    ROT_TRACK_COUNT = bs.readUShort()

    if not OFF_TRACK_DATA or OFF_TRACK_DATA + TRACK_DATA_SIZE * 4 > len(data):
        noesis.doException("Invalid animation track data")

    bs.seek(OFF_TRACK_DATA, NOESEEK_ABS)
    TRK_COUNT = bs.readUInt()

    nameToIdx = {b.name: b.index for b in bones}
    kfBones = []

    for trkIdx in range(TRK_COUNT):
        bs.seek(OFF_TRACK_DATA + (trkIdx + 1) * 12, NOESEEK_ABS)
        TRACK_FLAGS = bs.readUInt()
        namIdx = TRACK_FLAGS & 0xFFF

        if TRACK_FLAGS & 0x4000:
            BNAME = BNELST[namIdx]
        else:
            bs.seek(OFF_TRACK_DATA + namIdx, NOESEEK_ABS)
            BNAME = bs.readString()

        bs.seek(OFF_TRACK_DATA + trkIdx * 12 + 4, NOESEEK_ABS)
        POS_OFFSET = bs.readUInt() & 0xFFFFFF
        ROT_OFFSET = bs.readUInt() & 0xFFFFFF

        boneIdx = nameToIdx.get(BNAME)

        if boneIdx is None and trkIdx == 0:
            boneIdx = nameToIdx.get("pivot_0")

        if boneIdx is None:
            continue

        rotKF = []
        trsKF = []

        for kfIdx in range(FRAME_COUNT):
            TIME = (kfIdx / FRAME_RATE)

            if POS_OFFSET:
                posWord = POS_OFFSET

                if not TRACK_FLAGS & 0x1000:
                    posWord += kfIdx * POS_TRACK_COUNT * 3

                bs.seek(OFF_TRACK_DATA + posWord * 4, NOESEEK_ABS)
                trs = NoeVec3((-bs.readFloat(), bs.readFloat(), bs.readFloat())) #ax cor
                trsKF.append(NoeKeyFramedValue(TIME, trs))

            if ROT_OFFSET:
                rotWord = ROT_OFFSET

                if not TRACK_FLAGS & 0x2000:
                    rotWord += kfIdx * ROT_TRACK_COUNT * 2

                bs.seek(OFF_TRACK_DATA + rotWord * 4, NOESEEK_ABS)
                rotW = bs.readShort() / 32767.0
                rotX = bs.readShort() / 32767.0
                rotY = bs.readShort() / 32767.0
                rotZ = bs.readShort() / 32767.0
                rot = NoeQuat((-rotX, rotY, rotZ, -rotW)) #ax cor

                if rot.length() > 0.0:
                    rot = rot.normalize()

                rotKF.append(NoeKeyFramedValue(TIME, rot))

        trk = NoeKeyFramedBone(boneIdx)

        if rotKF:
            trk.setRotation(rotKF, noesis.NOEKF_ROTATION_QUATERNION_4)

        if trsKF:
            trk.setTranslation(trsKF, noesis.NOEKF_TRANSLATION_VECTOR_3)

        if rotKF or trsKF:
            kfBones.append(trk)

    return NoeKeyFramedAnim(
        os.path.splitext(os.path.basename(filename))[0],
        bones,
        kfBones,
        FRAME_RATE
    )

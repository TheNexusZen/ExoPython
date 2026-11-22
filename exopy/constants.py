THEMES = {
    "mountains": "mountains",
    "halloween": "halloween",
    "christmas": "christmas",
    "custom": "custom",
}

DEFAULT_SETTINGS = {
    "music": None,
    "AllowDirectionChange": False,
    "DisableRevivePads": False,
    "DisableStartAnim": False,
    "DisableReplays": False,
    "EnableSensors": False,
    "DisableScreenRotation": False,
    "CenterCamera": False,
    "Private": False,
}

TILE_IDS = {
    "start": -1356673834,
    "finish": -957301678,
    "terrain": 1078723247,
    "text": 589791300,
    "rect": -1718767673,
    "rect_outline": -168878848,
    "sprite": 1718870758,
    "booster": 968991814,
    "pattern_quad": -319845761,
    "arc": 2044847310,
}

OBJECT_PROPERTIES = {
    "Color": (0, "color"), "Resolution": (1, "i32"), "FillMode": (2, "i32"),
    "SecondaryColor": (3, "color"), "Thickness": (4, "f32"), "TotalAngle": (5, "i32"),
    "Corners": (6, "i32"), "Blending": (7, "i32"), "GridOffset": (8, "vec2"),
    "CornerRadius": (9, "f32"), "Width": (10, "f32"), "Height": (11, "f32"),
    "BorderColor": (12, "color"), "BorderThickness": (13, "f32"), "PhysicsType": (14, "i32"),
    "Friction": (15, "f32"), "TerrainCorners": (16, "tcorners"), "Direction": (17, "i32"),
    "Impulse": (18, "i32"), "Killer": (19, "bool"), "RoundReflexAngles": (20, "bool"),
    "RoundCollider": (21, "bool"), "Radius": (22, "f32"), "Size": (23, "f32"),
    "ReverseDirection": (24, "bool"), "CollisionDetector": (25, "bool"), "Pattern": (26, "i32"),
    "PatternTiling": (27, "vec2"), "PatternOffset": (28, "vec2"), "Bounce": (32, "bool"),
    "RestoreVelocity": (34, "bool"), "Sprite": (35, "str"), "Trigger": (36, "bool"),
    "Health": (37, "f32"), "DamageFromJump": (38, "bool"), "DamageFromDash": (39, "bool"),
    "ReverseDirOnDamage": (40, "bool"), "Floating": (41, "bool"), "LinkedObjects": (42, "vi32"),
    "FlipX": (43, "bool"), "FlipY": (44, "bool"), "Text": (45, "str"),
    "FontSize": (46, "f32"), "EditorColor": (47, "color"), "Color2": (48, "color"),
    "Color3": (49, "color"), "Color4": (50, "color"), "ParticleTexture": (51, "str"),
    "Duration": (52, "f32"), "Delay": (53, "f32"), "Loop": (54, "bool"),
    "AutoPlay": (55, "bool"), "LifetimeMin": (56, "f32"), "LifetimeMax": (57, "f32"),
    "SimulationSpace": (58, "i32"), "Rate": (59, "f32"), "Burst": (60, "i32"),
    "EmitterShape": (61, "i32"), "EmitterWidth": (62, "f32"), "EmitterHeight": (63, "f32"),
    "EmitterTotalAngle": (64, "f32"), "SizeMin": (65, "f32"), "SizeMax": (66, "f32"),
    "SizeOverLifetime": (67, "bool"), "StartSizeMultiplier": (68, "f32"),
    "EndSizeMultiplier": (69, "f32"), "SpeedMin": (71, "f32"), "SpeedMax": (72, "f32"),
    "SpeedLimit": (73, "f32"), "SpeedDampen": (74, "f32"), "RotationMin": (75, "f32"),
    "RotationMax": (76, "f32"), "RotationSpeed": (77, "f32"), "ColorOverLifetime": (78, "bool"),
    "StartColorMultiplier": (79, "color"), "EndColorMultiplier": (80, "color"),
    "GravityMultiplier": (81, "f32"), "AnchorPos": (82, "vec2"),
    "MoonInnerRadius": (83, "f32"), "MoonOffset": (84, "f32"),
}

class StaticType:
    Bool, Int, Float, String, Color, Vector = 0, 1, 2, 3, 4, 5
    Sound, Music, Object, ObjectSet, Transition = 6, 7, 8, 9, 10
    Easing, Sprite, Script, Layer = 11, 12, 13, 14

class DynamicType:
    BoolConstant = 0
    BoolVariable = 1
    BoolNot = 2
    BoolAnd = 3
    BoolOr = 4
    BoolEqualBool = 5
    BoolEqualNumber = 6
    BoolEqualString = 7
    BoolEqualColor = 8
    BoolEqualVector = 9
    BoolEqualObject = 10
    BoolNotEqualBool = 11
    BoolNotEqualNumber = 12
    BoolNotEqualString = 13
    BoolNotEqualColor = 14
    BoolNotEqualVector = 15
    BoolNotEqualObject = 16
    BoolLess = 17
    BoolLessOrEqual = 18
    BoolGreater = 19
    BoolGreaterOrEqual = 20
    BoolObjectDead = 21
    BoolPlayerOnGround = 22
    BoolPlayerOnWalljump = 23
    BoolPlayerOnBooster = 24
    BoolPlayerOnSwing = 25
    BoolPlayerInFloatingZone = 26
    BoolPlayerUsingGlider = 27
    BoolObjectsColliding = 28
    BoolInputPressed = 29
    BoolInputPressedLeft = 30
    BoolInputPressedRight = 31
    BoolInputHeld = 32
    BoolInputHeldLeft = 33
    BoolInputHeldRight = 34
    BoolInputReleased = 35
    BoolInputReleasedLeft = 36
    BoolInputReleasedRight = 37
    IntConstant = 38
    IntVariable = 39
    IntAdd = 40
    IntSubtract = 41
    IntMultiply = 42
    IntDivide = 43
    IntModulo = 44
    IntMin = 45
    IntMax = 46
    IntAbs = 47
    IntSign = 48
    IntRound = 49
    IntCeil = 50
    IntFloor = 51
    IntRandom = 52
    IntRepeatCount = 53
    IntObjectDirection = 54
    IntObjectSetCount = 55
    FloatConstant = 56
    FloatVariable = 57
    FloatAdd = 58
    FloatSubtract = 59
    FloatMultiply = 60
    FloatDivide = 61
    FloatModulo = 62
    FloatMin = 63
    FloatMax = 64
    FloatAbs = 65
    FloatSign = 66
    FloatRound = 67
    FloatCeil = 68
    FloatFloor = 69
    FloatCos = 70
    FloatSin = 71
    FloatTan = 72
    FloatAcos = 73
    FloatAsin = 74
    FloatAtan = 75
    FloatSqrt = 76
    FloatPow = 77
    FloatRandom = 78
    FloatTime = 79
    FloatSemitones = 80
    FloatVectorX = 81
    FloatVectorY = 82
    FloatVectorLength = 83
    FloatVectorLengthSqr = 84
    FloatVectorDistance = 85
    FloatVectorDistanceSqr = 86
    FloatVectorDot = 87
    FloatVectorAngle = 88
    FloatVectorAngleBetween = 89
    FloatObjectRotation = 90
    FloatObjectGlobalRotation = 91
    FloatCameraViewportSize = 92
    FloatDamageAmount = 93
    StringConstant = 94
    StringVariable = 95
    StringFromInt = 96
    StringFromFloat = 97
    StringConcat = 98
    ColorConstant = 99
    ColorValues = 100
    ColorVariable = 101
    ColorObjectColor = 102
    VectorConstant = 103
    VectorValues = 104
    VectorVariable = 105
    VectorAdd = 106
    VectorSubtract = 107
    VectorMultiply = 108
    VectorDivide = 109
    VectorNormalize = 110
    VectorPerpendicular = 111
    VectorReflect = 112
    VectorObjectPos = 113
    VectorObjectGlobalPos = 114
    VectorObjectScale = 115
    VectorObjectGlobalScale = 116
    VectorObjectVelocity = 117
    VectorCameraPos = 118
    SoundConstant = 119
    SoundVariable = 120
    MusicConstant = 121
    MusicVariable = 122
    ObjectConstant = 123
    ObjectVariable = 124
    ObjectAnyObject = 125
    ObjectFirstFromSet = 126
    ObjectRandomFromSet = 127
    ObjectElementFromSet = 128
    ObjectSourceObject = 129
    ObjectCollidedObject = 130
    ObjectTargetObject = 131
    ObjectPlayer = 132
    ObjectParent = 133
    ObjectSetConstant = 134
    ObjectSetVariable = 135
    ObjectSetConcat = 136
    ObjectSetPlayers = 137
    ObjectSetObjectsWithTag = 138
    TransitionConstant = 139
    TransitionVariable = 140
    EasingConstant = 141
    EasingVariable = 142
    ObjectSetChildren = 143
    BoolObjectActivated = 144
    FloatLevelTime = 145
    BoolPlayerJumpLocked = 146
    StringObjectTag = 147
    SpriteConstant = 148
    SpriteVariable = 149
    ScriptConstant = 150
    ScriptVariable = 151
    BoolParameter = 152
    IntParameter = 153
    FloatParameter = 154
    StringParameter = 155
    ColorParameter = 156
    VectorParameter = 157
    SoundParameter = 158
    MusicParameter = 159
    ObjectParameter = 160
    ObjectSetParameter = 161
    TransitionParameter = 162
    EasingParameter = 163
    SpriteParameter = 164
    ScriptParameter = 165
    BoolObjectsCollidingWithPoint = 166
    FloatRoundDecimals = 167
    VectorPointerPositionDeprecated = 168
    VectorPointerWorldPositionDeprecated = 169
    VectorCollisionPoint = 170
    VectorCollisionNormal = 171
    ObjectRepeatObject = 172
    VectorClosestFromPoint = 173
    ObjectSetAllObjects = 174
    ObjectSetObjectsInLayer = 175
    ObjectSetObjectsInCircle = 176
    LayerConstant = 177
    LayerVariable = 178
    LayerParameter = 179
    VectorRotate = 180
    IntLastSoundInstance = 181
    ObjectSetUnion = 182
    ObjectSetIntersection = 183
    ObjectSetDifference = 184
    ObjectSetRemoveAtIndex = 185
    VectorPointerPosition = 186
    VectorPointerWorldPosition = 187
    BoolPointerDown = 188
    BoolPointerHeld = 189
    BoolPointerReleased = 190
    FloatColorR = 191
    FloatColorG = 192
    FloatColorB = 193
    FloatColorA = 194
    StringSubstring = 195
    IntStringLength = 196


class OldActionType:
    RunScript = 0
    StopScripts = 1
    Wait = 2
    WaitFrames = 3
    Move = 4
    Jump = 5
    Slam = 6
    Charge = 7
    Scale = 8
    Rotate = 9
    RotateAround = 10
    SetDirection = 11
    Activate = 12
    Deactivate = 13
    PlaySound = 14
    PlayMusic = 15
    SetCinematic = 16
    SetInputEnabled = 17
    PanCameraToObject = 18
    CameraFollowPlayer = 19
    ShowGameText = 20
    SetVulnerable = 21
    Color = 22
    Damage = 23
    Kill = 24
    Finish = 25
    SetGravity = 26
    SetVelocity = 27


class ActionID:
    Repeat, RepeatWhile, ConditionBlock, Wait, WaitFrames = 0, 1, 2, 3, 4
    Move, Scale, Rotate, RotateAround = 5, 6, 7, 8
    SetVariable, ResetVariable, ResetObject = 9, 10, 11
    SetColor, SetTransparency, SetSecondaryColor, SetSecondaryTransparency = 12, 13, 14, 15
    SetBorderColor, SetBorderTransparency, SetSprite, SetText, SetEnabled = 16, 17, 18, 19, 20
    Activate, Deactivate, Damage, Kill, GameFinish = 21, 22, 23, 24, 25
    CameraPan, CameraFollowPlayer, CameraZoom, CameraZoomReset = 26, 27, 28, 29
    CameraOffset, CameraOffsetReset, CameraShake = 30, 31, 32
    PlaySound, PlayMusic, SetDirection, SetGravity, SetVelocity = 33, 34, 35, 36, 37
    SetCinematic, SetInputEnabled, SetTimerEnabled, GameTextShow = 38, 39, 40, 41
    DialogueShow, StopScript, TransitionIn, TransitionOut, TimeScale = 42, 43, 44, 45, 46
    RunFunction, SetVariableOverTime, RepeatForEachObject = 47, 48, 49
    StopSound, PlayParticleSystem, StopParticleSystem = 50, 51, 52

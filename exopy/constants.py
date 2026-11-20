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
    BoolConstant, BoolVariable, BoolNot, BoolAnd, BoolOr = 0, 1, 2, 3, 4
    BoolEqualBool, BoolEqualNumber, BoolNotEqualNumber = 5, 6, 12
    BoolLess, BoolLessOrEqual, BoolGreater, BoolGreaterOrEqual = 17, 18, 19, 20
    IntConstant, IntVariable = 38, 39
    IntAdd, IntSubtract, IntMultiply, IntDivide, IntModulo = 40, 41, 42, 43, 44
    IntRandom = 52
    FloatConstant, FloatVariable = 56, 57
    FloatAdd, FloatSubtract, FloatMultiply, FloatDivide = 58, 59, 60, 61
    FloatVectorDistance = 85
    StringConstant, StringVariable, StringFromInt, StringFromFloat, StringConcat = 94, 95, 96, 97, 98
    ColorConstant, ColorVariable = 99, 101
    VectorConstant, VectorVariable = 103, 105
    VectorObjectPos, VectorObjectGlobalPos = 113, 114
    SoundConstant, SoundVariable, MusicConstant, MusicVariable = 119, 120, 121, 122
    ObjectConstant, ObjectVariable, ObjectPlayer = 123, 124, 132
    ObjectSetConstant, ObjectSetVariable, ObjectSetPlayers, ObjectSetObjectsWithTag = 134, 135, 137, 138
    TransitionConstant, TransitionVariable, EasingConstant, EasingVariable = 139, 140, 141, 142
    FloatLevelTime = 145
    SpriteConstant, SpriteVariable, ScriptConstant, ScriptVariable = 148, 149, 150, 151
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
    LayerConstant, LayerVariable, LayerParameter = 177, 178, 179
    VectorPointerPosition, VectorPointerWorldPosition = 186, 187
    BoolPointerDown, BoolPointerHeld, BoolPointerReleased = 188, 189, 190

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

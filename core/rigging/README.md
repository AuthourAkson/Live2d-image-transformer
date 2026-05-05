# 自动骨骼绑定模块 (Auto Rigging)

## 功能
- 基于图层信息自动生成 Live2D 骨骼参数
- 建立部件间的父子层级关系
- 生成标准 Cubism 参数集 (角度、呼吸、部位特有参数)

## 依赖
无外部依赖，仅使用 Python 标准库 + 本项目的 LayerInfo 数据类。

## API 参考

### `auto_rig(layers: list[LayerInfo]) -> RigResult`
自动绑定骨骼。

```python
from core.rigging import auto_rig

rig = auto_rig(layers)

print(f"参数数量: {rig.metadata['total_parameters']}")
print(f"部件数量: {rig.metadata['total_parts']}")
print(f"根部件: {rig.metadata['root_part']}")

# 查看层次结构
for part, parent in rig.hierarchy.items():
    print(f"  {part} → parent: {parent}")
```

### 返回类型
```python
@dataclass
class RigResult:
    parameters: list[ParameterDef]  # 参数定义
    parts: list[PartBinding]        # 部件绑定关系
    hierarchy: dict                 # {part: parent}
    metadata: dict                  # 元信息

@dataclass
class ParameterDef:
    id: str          # "ParamAngleX"
    name: str        # "角度 X"
    default: float   # 0.0
    min: float       # -30.0
    max: float       # 30.0
```

## 标准参数集
| 参数 ID | 说明 | 范围 |
|---|---|---|
| ParamAngleX/Y/Z | 全局角度 | [-30, 30] |
| ParamBodyAngleX/Y/Z | 身体角度 | [-10, 10] |
| ParamBreath | 呼吸 | [0, 1] |
| ParamHeadAngleX/Y | 头部角度 | [-15, 15] |
| ParamEyeLOpen/ROpen | 眼睛开合 | [0, 1] |
| ParamMouthOpenY | 嘴纵向开合 | [0, 1] |

## 骨骼层级 (hierarchy)
```
head          (root, parent=None)
  └─ torso    (parent=head)
       ├─ left_upper_arm   → left_forearm   → left_hand
       ├─ right_upper_arm  → right_forearm  → right_hand
       ├─ left_thigh       → left_leg       → left_foot
       └─ right_thigh      → right_leg      → right_foot
```

## 注意事项
- 这是基础模板绑定，面部细节 (眉毛、睫毛、口型变化) 需手动细化
- 物理效果 (头发摆动、衣服飘动) 需额外配置
- 可在 `STANDARD_PARAMETERS` 和 `PART_PARAM_BINDINGS` 中扩展自定义参数

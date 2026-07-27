# Tetrahedral mesh 명명 변경 보고서

- 작성일: 2026-07-27
- 작업 브랜치: `codex/mrcp-tet-10.1-port`
- 작업 저장소: `/Users/yhuh/Study/installation/gate/Gate-10.1/opengate`
- 목적: 메쉬 전체를 뜻하던 `G4Tet` 계열 이름을 `TetrahedralMesh`로 명확히 하고, `TetGen`은 입력 파일 형식을 나타내는 이름에만 사용한다.

## 명명 원칙

1. 사용자에게 보이는 OpenGATE volume type은 `TetrahedralMesh`로 한다.
2. Python 구현 클래스는 OpenGATE 관례에 맞춰 `TetrahedralMeshVolume`로 한다.
3. TetGen의 `.node`/`.ele` 파일을 읽는 C++ 함수에만 `from_tetgen`을 표시한다.
4. Geant4의 단일 사면체 solid 클래스인 `G4Tet`과 그 바인딩 `pyG4Tet.cpp`는 변경하지 않는다.
5. 이번 기능은 아직 upstream에 공개되지 않았으므로 혼동되는 기존 공개 별칭 `G4Tet`/`G4TetVolume`은 유지하지 않는다.

## 변경 내용

| 기존 함수·이름 | 변경 함수·이름 | 위치 | 주요 내용 |
|---|---|---|---|
| 단일 파일 `g4_bindings/GateTetMeshG4Tet.cpp` | `GateTetrahedralMeshParameterisation.h`, `GateTetrahedralMeshParameterisation.cpp`, `pyGateTetrahedralMesh.cpp` | `core/opengate_core/opengate_lib/` | OpenGATE 자체 기능의 관례에 맞춰 클래스 선언, mesh 구현, Python 바인딩을 세 파일로 분리했다. |
| `GateTetNestedParam` | `GateTetrahedralMeshParameterisation` | `opengate_lib/GateTetrahedralMeshParameterisation.h`: 27행 부근<br>`opengate_lib/GateTetrahedralMeshParameterisation.cpp`: 185행 부근 | 각 tetrahedron의 solid, material, region 및 시각 속성을 copy number별로 제공하는 parameterisation 클래스다. |
| `g_param_store` | `g_tetrahedral_mesh_parameterisations` | `opengate_lib/GateTetrahedralMeshParameterisation.cpp`: 276행 부근 | 실행 중 parameterisation 객체가 소멸하지 않도록 보관하는 전역 저장소다. |
| `build_tet_mesh_g4tet_internal` | `build_tetrahedral_mesh_impl` | `opengate_lib/GateTetrahedralMeshParameterisation.cpp`: 281, 350행 부근 | TetGen 파싱, `G4Tet` 생성, material 매핑과 `G4PVParameterised` 생성을 담당하는 내부 구현이다. |
| `build_tet_mesh_g4tet` | `build_tetrahedral_mesh_from_tetgen` | 선언: `GateTetrahedralMeshParameterisation.h`: 68행 부근<br>구현: `.cpp`: 309행 부근<br>등록: `pyGateTetrahedralMesh.cpp`: 48행 부근 | material 포인터와 표시 속성을 받아 TetGen mesh를 생성하는 주 builder다. |
| `build_tet_mesh_g4tet_compat` | `build_tetrahedral_mesh_from_tetgen_material_names` | 선언: `GateTetrahedralMeshParameterisation.h`: 80행 부근<br>구현: `.cpp`: 327행 부근<br>등록: `pyGateTetrahedralMesh.cpp`: 77행 부근 | material 이름 사전을 material 포인터 사전으로 변환한 뒤 같은 내부 builder를 호출한다. |
| `init_GateTetMeshG4Tet` | `init_GateTetrahedralMesh` | `opengate_lib/pyGateTetrahedralMesh.cpp`: 46행 부근<br>`core/opengate_core/opengate_core.cpp`: 312, 595행 부근 | Python 등록 전용 파일에서 tetrahedral mesh builder를 `opengate_core` module에 등록한다. |
| `G4TetVolume` | `TetrahedralMeshVolume` | `opengate/geometry/volumes.py`: 1589, 1872행 부근 | OpenGATE에서 tetrahedral mesh 전체를 나타내는 volume 클래스다. `process_cls` 등록과 C++ builder 호출도 함께 변경했다. |
| `G4TetSolid` | `TetrahedralMeshEnvelopeSolid` | `opengate/geometry/solids.py`: 813, 859행 부근 | mesh를 담는 envelope box를 준비하는 보조 solid다. 실제 반환물이 단일 `G4Tet`이 아니라 envelope임을 이름에 표시했다. |
| import 및 등록 키 `G4TetVolume`, `G4Tet` | import 및 등록 키 `TetrahedralMeshVolume` | `opengate/managers.py`: 76, 1115행 부근 | 문자열 volume type을 Python 클래스로 연결한다. OpenGATE의 `type + "Volume"` 규칙에 따라 `add_volume("TetrahedralMesh", ...)`가 동작한다. |
| `simulation.add_volume("G4Tet", name)` | `simulation.add_volume("TetrahedralMesh", name)` | `opengate/contrib/phantoms/mrcp.py`: 173행 부근 | MRCP_AF 또는 MRCP_AM phantom을 새 공개 volume type으로 생성한다. |
| VS Code 검사 `build_tet_mesh_g4tet` | VS Code 검사 `build_tetrahedral_mesh_from_tetgen` | `/Users/yhuh/Documents/Opengate10.1/OpenGATE-MRCP.code-workspace`: 76행 부근 | VS Code binding 확인 task가 새 공개 C++ builder의 등록 여부를 검사하도록 변경했다. |

## 사용자 API

변경 후 기본 사용법:

```python
phantom = simulation.add_volume("TetrahedralMesh", "mrcp")
```

MRCP helper 사용법:

```python
phantom = add_mrcp_phantom(
    simulation,
    phantom_type="MRCP_AM",
    node_file="custom.node",
    ele_file="custom.ele",
    material_file="custom.material",
)
```

`phantom_type="MRCP_AM"`을 선택해도 사용자가 파일명을 직접 지정하면 `custom.*` 값이 그대로 사용된다. 기본값인 `MRCP_AF.node`, `MRCP_AF.ele`, `MRCP_AF.material`일 때만 AM 기본 파일명으로 자동 치환된다.

## 유지한 이름

| 파일/심볼 | 유지 이유 |
|---|---|
| `core/opengate_core/g4_bindings/pyG4Tet.cpp` | Geant4의 실제 단일 tetrahedron solid인 `G4Tet` 바인딩이므로 이름이 정확함 |
| `opengate_core.G4Tet` | mesh type이 아니라 한 개의 Geant4 solid를 뜻하므로 유지 |
| `TetGen` 및 `from_tetgen` | `.node`/`.ele` 입력 형식 또는 입력 backend를 정확히 설명하는 위치에만 유지 |

## 검증 결과

| 검증 항목 | 결과 |
|---|---|
| Python 파일 `py_compile` | 통과 |
| VS Code workspace JSON 구문 | 통과 |
| CMake 재구성 | 통과 |
| C++ Release 빌드 | 통과 (`Built target opengate_core`) |
| `opengate_core.G4Tet` 유지 | `True` |
| `build_tetrahedral_mesh_from_tetgen` 등록 | `True` |
| `build_tetrahedral_mesh_from_tetgen_material_names` 등록 | `True` |
| 기존 `build_tet_mesh_g4tet` 제거 | 확인 |
| `simulation.add_volume("TetrahedralMesh", "mrcp")` | `TetrahedralMeshVolume` 생성 확인 |
| MRCP v15 `--mode build` | 통과 |
| MRCP_AF mesh 로딩 | 총 tetrahedra `8,582,677`, scoring 대상 `48,012` |
| Geant4 engine 초기화 | 3파일 분리 후 통과, 약 `17.99 s` |

## 참고 사항

- 최초 컴파일에서 원본 미추적 C++ 파일 상단에 있던 단독 백틱 문자(U+0060) 문법 오류를 발견해 제거했다.
- 3파일 분리 후 첫 컴파일에서 Geant4 11.4의 `G4VTouchable` type alias와 불필요한 전방 선언의 충돌을 확인해 해당 선언을 제거했다.
- CMake 경고는 기존 minimum-version deprecation 경고이며 이번 이름 변경에 따른 오류가 아니다.
- 커밋, push, GitHub pull request는 수행하지 않았다.

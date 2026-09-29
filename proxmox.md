# EchoMap

> **A spatial mapping engine that hears the room first and looks second.**  
> 노트북의 **스피커 + 마이크를 주 감각**, 카메라를 보조 감각으로 사용해 실내 공간의 구조를 추정하고 2D/3D 지도로 재구성하는 로컬 우선 공간 인식 프로젝트.

---

## 1. 한 줄 결론

**EchoMap은 과학적·물리적·소프트웨어적으로 구현 가능하다.**

이미 연구에서는 다음이 각각 입증되어 있다.

- 스피커가 chirp를 내고 마이크가 반사음을 받아 **Room Impulse Response(RIR)** 를 측정할 수 있다.
- RIR의 **초기 반사(Early Reflections)** 도착 시간을 이용해 벽과 방의 기하 구조를 추정할 수 있다.
- 하나의 이동형 스피커+마이크 노드만으로도 여러 위치에서 측정하면 **room shape reconstruction**이 가능하다.
- 스마트폰의 내장 스피커·마이크·IMU만으로 **Acoustic SLAM + room geometry reconstruction**을 수행한 연구가 존재한다.
- 따라서 EchoMap의 핵심 차별점은 “새 물리 현상을 발명하는 것”이 아니라, **기존에 입증된 음향 공간 추론을 일반 노트북에서 실용적인 로컬 시스템으로 묶는 것**이다.

---

# 2. 프로젝트 철학

일반적인 공간 인식은 보통 다음 순서다.

```text
Camera / LiDAR
      ↓
Geometry
      ↓
Map
```

EchoMap은 반대로 **음향을 1차 공간 센서**로 둔다.

```text
Speaker
   ↓
Known Chirp
   ↓
Room
   ↓
Reflections / Reverberation
   ↓
Microphone
   ↓
Room Impulse Response
   ↓
Acoustic Geometry
   ↓
2D / 3D Spatial Map
```

카메라는 주 센서가 아니다.

```text
ACOUSTIC
  ├─ 거리 후보
  ├─ 반사면
  ├─ 방 크기/형상
  ├─ 공간 고유 특성
  └─ 위치 변화

CAMERA
  ├─ 이동량 보조
  ├─ 방향 보조
  ├─ 물체 식별
  └─ texture / semantic label
```

즉:

> **소리가 공간을 만들고, 카메라는 그 공간을 설명한다.**

---

# 3. 왜 음향인가?

카메라는 시야각과 가려짐에 제한된다.

```text
        Camera
          ↓
       \ 120° /
        \    /
         \  /
```

반면 소리는 한 방향으로만 존재하지 않는다.

```text
                 WALL
          ↖       ↑       ↗
            \     |     /
              \   |   /
 WALL ←────── Speaker ──────→ WALL
              /   |   \
            /     |     \
          ↙       ↓       ↘
                 WALL
```

한 번 발생한 소리는 방 안의 여러 표면에서 반사된다.

마이크가 받는 신호에는 단순한 “한 개의 거리”가 아니라 **공간 전체가 소리에 남긴 응답**이 들어 있다.

이를 **Room Impulse Response, RIR**이라고 한다.

---

# 4. 핵심 물리

## 4.1 알려진 신호 발사

EchoMap은 임의의 음악이나 음성이 아니라 분석하기 쉬운 신호를 사용한다.

예:

- linear chirp
- logarithmic / exponential sweep
- MLS 계열 신호
- 짧은 broadband pulse

초기 MVP에서는 **chirp**가 가장 단순하다.

```text
frequency

20kHz |              /
      |            /
      |          /
      |        /
 5kHz |______/
      +---------------- time
```

송신한 신호를 이미 알고 있으므로 녹음된 신호와 비교해 반사 성분을 분리할 수 있다.

---

## 4.2 직접음과 반사음

마이크에는 대략 다음이 들어온다.

```text
Time →

| DIRECT
|   ▲
|   │     ▲ Reflection #1
|   │     │
|   │     │    ▲ Reflection #2
|   │     │    │
|   │     │    │      ▲ Reflection #3
|___|_____|____|______|________________
```

이를 크게 나누면:

```text
Direct Sound
     ↓
Early Reflections
     ↓
Higher-order Reflections
     ↓
Late Reverberation
```

### Early Reflections

벽, 천장, 바닥 등 주요 반사면의 위치를 추정하는 데 가장 중요하다.

### Late Reverberation

정확한 벽 하나의 위치보다는 다음과 같은 공간 전체 특성에 유용하다.

- 방 크기
- 흡음 정도
- 개방/폐쇄 정도
- 공간 식별
- 장소 간 차이

---

# 5. 거리 정보

소리는 유한한 속도로 움직인다.

실내의 일반적인 조건에서 음속은 대략:

```text
~343 m/s
```

예를 들어 반사음의 왕복 시간이 `Δt`라면, 단순한 정면 반사에서는:

```text
distance ≈ speed_of_sound × Δt / 2
```

따라서 EchoMap의 음향 데이터에는 **실제 미터 단위 거리 정보**가 들어갈 수 있다.

이것은 단안 영상 기반 3D가 겪는 scale ambiguity를 보완하는 데도 사용할 수 있다.

---

# 6. 핵심 아이디어: 한 번이 아니라 여러 위치에서 듣는다

단일 위치에서 얻은 RIR 하나만으로 복잡한 방 전체를 완벽하게 해석하는 것은 어렵다.

EchoMap의 핵심은 **이동하면서 반복 측정하는 것**이다.

```text
Position A
   ●
   └─ chirp → RIR_A

          ↓ move

Position B
        ●
        └─ chirp → RIR_B

          ↓ move

Position C
              ●
              └─ chirp → RIR_C
```

각 측정에서 얻은 반사 후보를 공간상에 겹친다.

예:

```text
A measurement → wall candidate α
B measurement → wall candidate β
C measurement → wall candidate γ

α ≈ β ≈ γ
        ↓
Persistent Plane
        ↓
WALL
```

우연한 반사나 잘못된 peak는 위치가 바뀌면서 일관성을 잃지만, 실제 벽은 여러 측정에서 같은 기하 조건을 만족한다.

---

# 7. EchoMap의 센서 우선순위

## Primary

### Speaker

알려진 probe signal을 방에 방사한다.

### Microphone

직접음, 초기 반사, 후기 잔향을 기록한다.

---

## Secondary

### Camera

카메라는 공간 구조를 대신 만들기보다 다음 용도로 사용한다.

- optical odometry
- 이동량 추정
- 회전량 추정
- 물체 분류
- 벽/문/가구 의미 부여
- texture 획득

즉 카메라가 120° 정도만 보더라도 문제가 되지 않는다.

EchoMap에서 카메라의 역할은 **전 방향 공간 센서**가 아니라 보조 추적기다.

---

# 8. 전체 처리 파이프라인

```text
┌──────────────────────────────┐
│          ECHOMAP             │
└──────────────────────────────┘

          SPEAKER
             │
             ▼
         Chirp / Sweep
             │
             ▼
            ROOM
             │
        reflections
             │
             ▼
        MICROPHONE
             │
             ▼
   Audio preprocessing
             │
             ▼
    RIR estimation
             │
       ┌─────┴─────┐
       ▼           ▼
 Early echoes   Late reverb
       │           │
       ▼           ▼
 reflection     room feature
 candidates       vector
       │
       ▼
 Geometry hypotheses
       │
       │        Camera
       │          │
       │     motion estimate
       │          │
       └────┬─────┘
            ▼
      Sensor Fusion
            │
            ▼
      Acoustic SLAM
            │
            ▼
    Spatial Graph / Mesh
            │
       ┌────┴────┐
       ▼         ▼
      2D        3D
      Map       Map
```

---

# 9. 소프트웨어 모듈

```text
echomap/
├── capture/
│   ├── speaker
│   ├── microphone
│   └── camera
│
├── acoustic/
│   ├── chirp
│   ├── deconvolution
│   ├── rir
│   ├── peak_detection
│   ├── echo_matching
│   └── reverberation
│
├── vision/
│   ├── odometry
│   └── semantics
│
├── geometry/
│   ├── reflection_candidates
│   ├── plane_solver
│   ├── room_model
│   └── uncertainty
│
├── slam/
│   ├── trajectory
│   ├── loop_closure
│   └── fusion
│
├── render/
│   ├── point_cloud
│   ├── mesh
│   └── viewer
│
└── app/
```

---

# 10. 데이터 모델

EchoMap은 단순 point cloud보다 **Acoustic Spatial Map**을 목표로 한다.

예:

```yaml
surface:
  id: wall_03

  geometry:
    type: plane
    distance: 2.84
    confidence: 0.87

  acoustic:
    reflection_strength: 0.81
    decay: 0.19
    absorption_estimate: 0.14

  visual:
    label: wall
    confidence: 0.93
```

그러면 EchoMap은 단순히:

> “여기에 벽이 있다.”

에서 끝나지 않고,

> “여기에 벽이 있고, 이런 방식으로 소리를 반사하는 표면이다.”

까지 표현할 수 있다.

---

# 11. MVP

## EchoMap V0 — Hear a Wall

목표:

> **노트북 스피커와 마이크만으로 주요 반사면 하나의 거리를 검출한다.**

### 기능

1. chirp 생성
2. 스피커 출력
3. 동시에 마이크 녹음
4. 직접음 제거/정렬
5. RIR 계산
6. 첫 번째 강한 early reflection 검출
7. 거리로 변환
8. 반복 측정 후 안정도 계산

### 성공 조건

실제 벽 거리와 측정값의 관계가 반복 가능하게 나타날 것.

정확도 자체보다 **거리 변화가 실제 이동과 일관되게 대응하는지**가 먼저다.

---

# 12. V1 — Hear a Room

목표:

> **기기를 이동시키며 여러 RIR을 수집해 방의 2D 외곽 구조를 추정한다.**

```text
RIR_001
RIR_002
RIR_003
 ...
RIR_N
    │
    ▼
Echo correspondence
    │
    ▼
Wall hypotheses
    │
    ▼
2D room map
```

카메라를 이용해 노트북의 상대적 이동 경로를 보조한다.

---

# 13. V2 — Acoustic SLAM

목표:

> **사용자의 이동 경로와 방 구조를 동시에 추정한다.**

추정 대상:

```text
device trajectory
+
wall geometry
+
room identity
+
measurement uncertainty
```

각 측정값에는 반드시 confidence를 저장한다.

```text
wall candidate
distance = 2.72 m
confidence = 0.63
```

EchoMap은 불확실한 반향 하나를 벽으로 확정하지 않는다.

여러 위치의 관측이 일치할수록 confidence를 올린다.

---

# 14. V3 — 3D EchoMap

2D 벽 검출에서 다음으로 확장한다.

- 바닥
- 천장
- 수직 벽
- 큰 가구
- 문/개구부 후보

출력:

```text
        ceiling
   ┌─────────────┐
   │             │
   │       ┌──┐  │
   │       │  │  │
   │       └──┘  │
   │             │
   └─────────────┘
         floor
```

최종적으로:

```text
RIR observations
      +
trajectory
      +
camera semantics
      ↓
Acoustic 3D Scene
```

---

# 15. V4 — Acoustic Material Map

기하 구조뿐 아니라 표면의 음향 특성을 축적한다.

예:

```text
Surface A
  strong reflection
  low absorption
  → glass / concrete candidate

Surface B
  weak high-frequency reflection
  high absorption
  → curtain / fabric candidate
```

초기에는 재질을 단정하지 않고 **acoustic signature**만 저장한다.

시각 정보와 결합하면 이후 의미 추론이 가능하다.

---

# 16. 현실적인 한계

EchoMap이 가능하다는 것과 모든 환경에서 완벽하다는 것은 다르다.

## Laptop Audio Hardware

노트북 제조사마다 다음이 다르다.

- 스피커 주파수 응답
- 마이크 주파수 응답
- 마이크 개수
- 자동 gain control
- noise suppression
- echo cancellation
- DSP
- sample rate

따라서 시작할 때 **device calibration**이 필요하다.

---

## Near-inaudible chirp

17~20 kHz 부근 신호는 일부 장치에서 사용할 수 있지만 모든 노트북에서 안정적으로 재생/녹음된다고 가정하면 안 된다.

EchoMap은 특정 주파수를 강제하지 않고 장치별 calibration으로 usable band를 찾아야 한다.

```text
frequency sweep
      ↓
speaker response
      +
microphone response
      ↓
usable acoustic band
```

---

## Multipath

방에서는 수많은 반사가 겹친다.

```text
speaker
  ↓
wall A
  ↓
wall B
  ↓
mic
```

따라서 “peak 하나 = 벽 하나”로 단순 처리하면 실패한다.

여러 위치에서 반복 측정하고 **공간적으로 일관된 반사만 남기는 과정**이 핵심이다.

---

## Soft Materials

커튼, 침구, 카펫 등은 반사를 약하게 만들 수 있다.

반대로 유리·콘크리트·타일 같은 표면은 강한 반사를 만든다.

따라서 모든 표면이 동일한 품질로 검출되지는 않는다.

---

## Environmental Noise

다음은 성능을 떨어뜨릴 수 있다.

- 사람 대화
- 음악
- TV
- 에어컨
- 팬
- 외부 소음
- 다른 EchoMap 장치

probe signal과 correlation/deconvolution을 이용해 일반 소리와 구분하되, SNR 한계는 존재한다.

---

# 17. EchoMap이 하지 않아도 되는 것

초기 목표에서는 다음을 요구하지 않는다.

- 사진 수준의 3D texture reconstruction
- mm 단위 LiDAR 정확도
- 한 번의 chirp로 완벽한 3D 복원
- 모든 물체의 재질 판별
- 완전 무음 동작
- 실시간 60 FPS 3D reconstruction

이것들을 처음부터 목표로 잡으면 프로젝트의 핵심이 흐려진다.

---

# 18. EchoMap의 진짜 성공 기준

첫 성공은 예쁜 3D 렌더가 아니다.

### Stage 1

```text
벽에 가까워짐
      ↓
EchoMap이 거리 감소를 감지
```

### Stage 2

```text
방을 이동
    ↓
같은 벽을 여러 위치에서 재검출
```

### Stage 3

```text
여러 벽
   ↓
2D room outline
```

### Stage 4

```text
floor + walls + ceiling
          ↓
       3D room
```

### Stage 5

```text
acoustic geometry
        +
visual semantics
        ↓
multimodal spatial model
```

---

# 19. 로컬 우선

EchoMap의 핵심 처리 과정은 모두 로컬에서 수행 가능하도록 설계한다.

```text
Capture
  ↓
Signal Processing
  ↓
Geometry
  ↓
SLAM
  ↓
Rendering
```

클라우드 API는 핵심 동작에 필요하지 않는다.

초기 단계의 RIR 추정, FFT, correlation, peak detection, geometry fitting은 일반 CPU에서도 가능하다.

고급 vision/3D reconstruction이나 학습 기반 feature extractor를 추가할 경우 GPU 가속을 선택적으로 사용할 수 있다.

---

# 20. 연구 근거

EchoMap의 핵심 구성 요소는 이미 각각 연구로 검증되어 있다.

## Room shape reconstruction with a single mobile acoustic sensor

**IEEE GlobalSIP, 2015**

- 이동형 단일 노드
- co-located loudspeaker + microphone
- first-order echo arrival time 사용
- polygonal room geometry reconstruction

DOI:

`10.1109/GlobalSIP.2015.7418371`

이 연구는 EchoMap의 핵심 가정인:

> **“하나의 이동형 스피커+마이크로 방 구조를 역산할 수 있는가?”**

에 대해 **가능**이라는 근거를 제공한다.

---

## Indoor Smartphone SLAM With Acoustic Echoes

**IEEE Transactions on Mobile Computing, 2024**

사용 장비:

- smartphone loudspeaker
- smartphone microphone
- IMU

방법:

- near-inaudible chirp 발사
- acoustic echo 기록
- echoic location feature 추출
- trajectory reconstruction
- room geometry reconstruction

논문 보고 결과에는 living room, office, shopping mall에서 sub-meter 수준의 localization 성능이 포함된다.

DOI:

`10.1109/TMC.2023.3323393`

EchoMap은 IMU가 없는 노트북에서도 **카메라 기반 motion estimation**을 보조 수단으로 사용할 수 있다.

---

## Geometrical room acoustic modeling literature

Room impulse response는 일반적으로:

```text
direct sound
+
early reflections
+
late reverberation
```

으로 해석할 수 있으며, 초기 반사는 개별 reflection path의 공간 정보를 포함한다.

이는 EchoMap이 early reflection과 late reverberation을 서로 다른 정보원으로 다루는 근거가 된다.

---

# 21. 개발 원칙

### 1. Acoustic First

카메라만으로 3D를 만든 뒤 음향을 덧붙이는 프로젝트로 변질시키지 않는다.

### 2. Evidence Before Guess

한 번의 반향으로 벽을 확정하지 않는다.

### 3. Confidence Everywhere

모든 공간 추정 결과에 불확실성을 남긴다.

### 4. Hardware Agnostic

특정 노트북 모델에 종속되지 않도록 calibration layer를 둔다.

### 5. Local First

핵심 공간 인식은 네트워크 없이 동작한다.

### 6. Progressive Reconstruction

완성된 3D를 한 번에 만들기보다 관측이 누적될수록 공간이 점차 확정되게 한다.

---

# 22. 최종 비전

EchoMap의 최종 결과물은 단순한 3D mesh가 아니다.

```text
                    EchoMap
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
       Geometry     Acoustics     Semantics
          │            │            │
     where it is   how it sounds  what it is
          └────────────┼────────────┘
                       ▼
              Spatial World Model
```

즉:

> **공간이 어디에 있는지, 어떻게 울리는지, 무엇으로 이루어져 있는지를 하나의 지도에 저장한다.**

---

# 23. README용 짧은 설명

> **EchoMap hears a room before it sees it.**  
> A local-first acoustic spatial mapping engine that uses ordinary speakers and microphones to reconstruct indoor geometry from echoes, with vision used only as a secondary sense.

한국어:

> **EchoMap은 공간을 먼저 듣고, 필요한 곳만 본다.**  
> 일반 스피커와 마이크의 반향을 이용해 실내 구조를 추정하고, 카메라를 보조 감각으로 사용하는 로컬 우선 공간 인식 엔진.

---

# 24. 초기 개발 순서

```text
E0  Audio I/O calibration
 ↓
E1  Chirp generation + synchronized recording
 ↓
E2  RIR extraction
 ↓
E3  Early reflection detection
 ↓
E4  Single-wall distance experiment
 ↓
E5  Moving measurements
 ↓
E6  Camera motion estimation
 ↓
E7  Multi-position echo matching
 ↓
E8  2D wall reconstruction
 ↓
E9  Acoustic SLAM
 ↓
E10 3D planes
 ↓
E11 Visual semantics
 ↓
E12 Acoustic Spatial Map
```

**가장 먼저 증명할 것은 E4다.**

> 노트북 하나로 벽을 향해 이동했을 때, EchoMap이 반향만으로 그 거리 변화에 일관되게 반응하는가?

이게 성공하면 EchoMap의 핵심 물리 파이프라인은 살아 있다.

---

## Status

**Feasibility:** ✅ Possible  
**Primary sensing:** Acoustic  
**Secondary sensing:** Vision  
**Special hardware required for MVP:** No  
**Cloud required:** No  
**Target:** Local acoustic spatial mapping / Acoustic SLAM

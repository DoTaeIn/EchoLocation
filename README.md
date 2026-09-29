# 🔊 EchoLocation (EchoMap)

> **"EchoMap hears a room before it sees it."**  
> 일반 노트북의 스피커와 마이크를 주 감각(Primary Sense)으로 사용해 실내 공간의 구조를 추정하고 2D/3D 지도로 재구성하는 **로컬 우선(Local-first) 음향 공간 인식 엔진**입니다. 카메라는 보조 감각으로만 사용됩니다.

## 🌟 프로젝트 철학

보통의 공간 인식(SLAM, 3D Reconstruction)은 카메라나 LiDAR를 최우선 센서로 활용합니다.
하지만 EchoLocation은 **음향(Acoustics)을 1차 공간 센서**로 둡니다.

1. **소리가 공간을 만듭니다:** 스피커로 Chirp 신호를 발생시키고 반사음(RIR: Room Impulse Response)을 측정하여 방의 기하학적 구조와 거리를 파악합니다.
2. **카메라는 거들 뿐입니다:** 카메라는 이동량(Odometry)을 추정하고 물체를 식별하는 등 보조적인 역할만 수행합니다.

## 🚀 개발 로드맵 (Master Plan)

현재 프로젝트는 4단계의 마스터 플랜을 따라 진행되고 있습니다.

*   **Phase 1: MVP (V0 — Hear a Wall)**
    *   오디오 캘리브레이션 (Usable Band 탐색)
    *   직접음/반사음 분리 및 초기 반사(Early Reflection) 검출을 통한 '단일 벽면 거리' 측정
*   **Phase 2: 2D Room Mapping (V1 — Hear a Room)**
    *   노트북을 이동하며 수집된 다중 위치 반향 매칭
    *   2D 방 외곽 구조(Room Outline) 재구성
*   **Phase 3: Acoustic SLAM (V2)**
    *   센서 퓨전(음향 기하 후보 + 카메라 이동량)을 통한 로컬라이제이션 및 맵핑 동시 수행
*   **Phase 4: 3D Multimodal Map (V3, V4)**
    *   바닥, 천장 등 3D 기하 확장 및 시각적 의미(Visual Semantics, 재질 등) 부여

## 🛠 기술 스택
- **Language:** Python 3
- **Audio Processing:** `sounddevice`, `numpy`, `scipy`
- **Visualization:** `matplotlib`

## 📁 디렉토리 구조
```text
.
├── proxmox.md           # 상세 기획 및 컨셉 문서
├── scripts/
│   └── 00_calibration.py # 오디오 I/O 캘리브레이션 스크립트 (Phase 1)
├── echomap/             # 메인 모듈 패키지 (개발 예정)
│   ├── capture/
│   ├── acoustic/
│   ├── vision/
│   ├── geometry/
│   ├── slam/
│   └── render/
└── requirements.txt
```

## 🏁 시작하기

이 프로젝트는 의존성 관리를 위해 가상환경(`.venv`) 사용을 권장합니다.

```bash
# 가상 환경 활성화
source .venv/bin/activate

# 의존성 설치
pip install -r requirements.txt

# 오디오 캘리브레이션 실행 (마이크 권한 필요)
python scripts/00_calibration.py
```

import cv2
import numpy as np
import sounddevice as sd
import scipy.signal as signal
import threading
import time

# Global variables for cross-thread access
pos_x, pos_y = 400.0, 400.0
measurements = []  # List of (x, y, [distances])
is_running = True

def generate_chirp(duration, fs, f0, f1):
    t = np.linspace(0, duration, int(fs * duration), endpoint=False)
    sweep = signal.chirp(t, f0, duration, f1, method='linear')
    fade_len = int(fs * duration * 0.05)
    window = np.ones_like(sweep)
    if fade_len > 0:
        window[:fade_len] = np.linspace(0, 1, fade_len)
        window[-fade_len:] = np.linspace(1, 0, fade_len)
    return sweep * window

def audio_ping_thread():
    global pos_x, pos_y, measurements, is_running
    fs = 48000
    f0, f1 = 4000, 12000
    chirp_duration = 0.1
    recording_duration = 0.5
    chirp_sig = generate_chirp(chirp_duration, fs, f0, f1)
    playback_sig = np.pad(chirp_sig, (0, int(fs * (recording_duration - chirp_duration))))
    
    # 초기 안정화를 위해 2초 대기
    time.sleep(2)
    
    while is_running:
        # 소리를 쏘는 시점의 현재 카메라 위치를 복사해둠
        current_x, current_y = pos_x, pos_y
        
        try:
            # Play and record (0.5초 소요, 이 스레드만 블록됨)
            rec = sd.playrec(playback_sig, samplerate=fs, channels=1, blocking=True)
            rec = rec.flatten()
            
            # Extract RIR (에코 탐지)
            rir = signal.correlate(rec, chirp_sig, mode='full')
            max_idx = np.argmax(np.abs(rir))
            rir_causal = rir[max_idx:]
            
            t = np.linspace(0, len(rir_causal)/fs, len(rir_causal))
            dist = (t * 343.0) / 2
            
            rir_plot = np.abs(rir_causal) / (np.max(np.abs(rir_causal)) + 1e-9)
            peaks, _ = signal.find_peaks(rir_plot, height=0.03, distance=int(0.1 / (343.0 / fs / 2)))
            peaks = peaks[dist[peaks] > 0.3] # 노트북 자체 소리(0m) 제외
            
            dists = dist[peaks]
            
            # 측정 결과 저장
            measurements.append((current_x, current_y, dists))
            print(f"[음향 SLAM] Ping! 위치 ({current_x:.1f}, {current_y:.1f}) -> {len(dists)}개의 반사면 감지")
            
        except Exception as e:
            print(f"Audio Error: {e}")
            
        # 다음 핑까지 2초 대기 (종료 신호를 빠르게 받기 위해 0.1초씩 쪼개서 쉼)
        for _ in range(20):
            if not is_running: break
            time.sleep(0.1)

def run_acoustic_slam():
    global pos_x, pos_y, measurements, is_running
    print("=" * 60)
    print(" EchoMap Phase 3: Acoustic SLAM (Sensor Fusion)")
    print("=" * 60)
    print("카메라(Vision)와 스피커/마이크(Acoustic)를 동기화합니다...")
    
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return
        
    feature_params = dict(maxCorners=100, qualityLevel=0.3, minDistance=7, blockSize=7)
    lk_params = dict(winSize=(15, 15), maxLevel=2, criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03))
                     
    ret, old_frame = cap.read()
    if not ret: return
    
    old_gray = cv2.cvtColor(old_frame, cv2.COLOR_BGR2GRAY)
    p0 = cv2.goodFeaturesToTrack(old_gray, mask=None, **feature_params)
    
    slam_map = np.zeros((800, 800, 3), dtype=np.uint8)
    px_per_m = 50.0 # 스케일: 1미터 = 50 픽셀
    
    # ----------------------------------------
    # 멀티스레드: 카메라가 움직이는 동안 백그라운드에서 소리를 계속 쏨
    # ----------------------------------------
    audio_thread = threading.Thread(target=audio_ping_thread)
    audio_thread.start()
    
    print("\n[READY] 자유롭게 방 안을 걸어 다니세요!")
    print("★ 이동 규칙 ★")
    print("1. 카메라는 항상 진행 방향(정면)을 바라보게 해 주세요.")
    print("2. 너무 빠르게 홱 돌리면 궤적이 끊어질 수 있으니 부드럽게 이동하세요.")
    print("3. 2초마다 '새소리(Chirp)'가 울리며 화면에 메아리 반경(파란 원)이 쌓입니다.")
    print("\n종료하려면 SLAM 맵 창을 클릭하고 키보드 'q'를 누르세요.\n")
    
    frame_count = 0
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret: break
        
        frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        frame_count += 1
        
        # 1. 시각 오도메트리 연산 (궤적 갱신)
        if p0 is not None and len(p0) > 0:
            p1, st, err = cv2.calcOpticalFlowPyrLK(old_gray, frame_gray, p0, None, **lk_params)
            
            if p1 is not None:
                good_new = p1[st == 1]
                good_old = p0[st == 1]
                
                if len(good_new) > 0:
                    dx = np.mean(good_old[:, 0] - good_new[:, 0]) 
                    dy = np.mean(good_old[:, 1] - good_new[:, 1])
                    
                    # 스케일 조절 (픽셀 이동량)
                    pos_x += dx * 0.5
                    pos_y += dy * 0.5
                    
                    pos_x = np.clip(pos_x, 0, 799)
                    pos_y = np.clip(pos_y, 0, 799)
                    
                    # 초록색 점으로 궤적 찍기
                    cv2.circle(slam_map, (int(pos_x), int(pos_y)), 2, (0, 255, 0), -1)
                
                p0 = good_new.reshape(-1, 1, 2)
                
                # 특징점 재탐지
                if len(p0) < 15 or frame_count % 30 == 0:
                    new_p0 = cv2.goodFeaturesToTrack(frame_gray, mask=None, **feature_params)
                    if new_p0 is not None: p0 = new_p0
            else:
                p0 = cv2.goodFeaturesToTrack(frame_gray, mask=None, **feature_params)
        else:
            p0 = cv2.goodFeaturesToTrack(frame_gray, mask=None, **feature_params)
            
        old_gray = frame_gray.copy()
        
        # 2. 음향 + 시각 퓨전 맵 그리기
        map_display = slam_map.copy()
        
        # 저장된 모든 음향 측정치(메아리)를 맵 위에 그림
        for (mx, my, dists) in measurements:
            # 핑을 쏜 위치 (빨간 점)
            cv2.circle(map_display, (int(mx), int(my)), 4, (0, 0, 255), -1) 
            
            # 에코 거리 (파란 원)
            for d in dists:
                if d < 10.0: # 10m 이내의 에코만 표시
                    radius = int(d * px_per_m)
                    cv2.circle(map_display, (int(mx), int(my)), radius, (255, 150, 50), 1)
        
        # 화면 출력
        cv2.imshow('SLAM Map (Green: Path, Blue: Echoes)', map_display)
        # 웹캠 원본은 작게 줄여서 띄움 (원하지 않으면 꺼도 됨)
        # cv2.imshow('Webcam View', frame)
        
        if cv2.waitKey(30) & 0xFF == ord('q'):
            break
            
    is_running = False
    audio_thread.join()
    cap.release()
    cv2.destroyAllWindows()
    
    cv2.imwrite("slam_result.png", map_display)
    print(f"\n성공적으로 종료되었습니다. 최종 결과가 slam_result.png 에 저장되었습니다!")

if __name__ == "__main__":
    run_acoustic_slam()

import numpy as np
import sounddevice as sd
import scipy.signal as signal
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

def generate_chirp(duration, fs, f0, f1):
    t = np.linspace(0, duration, int(fs * duration), endpoint=False)
    sweep = signal.chirp(t, f0, duration, f1, method='linear')
    fade_len = int(fs * duration * 0.05)
    window = np.ones_like(sweep)
    if fade_len > 0:
        window[:fade_len] = np.linspace(0, 1, fade_len)
        window[-fade_len:] = np.linspace(1, 0, fade_len)
    return sweep * window

def extract_stereo_rir(recorded, source, fs, speed_of_sound=343.0, mic_dist=0.15):
    # Cross-correlate for Left and Right channels
    rir_L = signal.correlate(recorded[:, 0], source, mode='full')
    rir_R = signal.correlate(recorded[:, 1], source, mode='full')
    
    # Align to direct sound
    max_idx_L = np.argmax(np.abs(rir_L))
    rir_causal_L = rir_L[max_idx_L:]
    rir_causal_R = rir_R[max_idx_L:]
    
    t = np.linspace(0, len(rir_causal_L)/fs, len(rir_causal_L))
    distance = (t * speed_of_sound) / 2
    
    rir_plot_L = np.abs(rir_causal_L) / (np.max(np.abs(rir_causal_L)) + 1e-9)
    peaks, _ = signal.find_peaks(rir_plot_L, height=0.015, distance=int(0.1 / (speed_of_sound / fs / 2)))
    peaks = peaks[distance[peaks] > 0.3] # Ignore direct sound
    
    points_3d = []
    
    for p in peaks:
        dist = distance[p]
        amp = rir_plot_L[p]
        
        # Calculate angle (Time Difference of Arrival)
        window_size = int(0.002 * fs) # 2ms window
        start = max(0, p - window_size)
        end = min(len(rir_causal_L), p + window_size)
        
        chunk_L = rir_causal_L[start:end]
        chunk_R = rir_causal_R[start:end]
        
        angle_azimuth = 0.0
        if len(chunk_L) > 0 and len(chunk_R) > 0:
            corr = signal.correlate(chunk_L, chunk_R, mode='full')
            lag = np.argmax(corr) - (len(chunk_L) - 1)
            time_diff = lag / fs
            
            val = time_diff * speed_of_sound / mic_dist
            val = np.clip(val, -1.0, 1.0)
            angle_azimuth = np.arcsin(val)
            
        # Generate 3D surface points (since we only have horizontal angle, we approximate vertical spread)
        # This draws an arc of points at the given distance and azimuth to simulate a "wall surface"
        for elevation in np.linspace(-np.pi/6, np.pi/6, 30):
            # Convert Spherical to Cartesian
            x = dist * np.cos(elevation) * np.sin(angle_azimuth) # Left/Right
            y = dist * np.cos(elevation) * np.cos(angle_azimuth) # Forward
            z = dist * np.sin(elevation)                         # Up/Down
            
            # Add random noise to make it a "Cloud" instead of a perfect line
            x += np.random.normal(0, 0.03)
            y += np.random.normal(0, 0.03)
            z += np.random.normal(0, 0.03)
            
            points_3d.append((x, y, z, amp))
                
    return points_3d

def run_3d_pointcloud():
    print("=" * 60)
    print(" EchoMap 3D: Stereo Acoustic Point Cloud")
    print("=" * 60)
    
    fs = 48000
    f0, f1 = 4000, 12000
    chirp_duration = 0.1
    recording_duration = 0.8
    chirp_sig = generate_chirp(chirp_duration, fs, f0, f1)
    playback_sig = np.pad(chirp_sig, (0, int(fs * (recording_duration - chirp_duration))))
    
    print("\n[안내] 맥북의 스테레오 마이크(좌/우 2채널)를 이용합니다.")
    print("소리가 도달하는 시간차(TDOA)를 계산해 방향을 알아내고, 3D 점군(Point Cloud)을 그립니다.")
    input("준비되셨으면 엔터를 눌러주세요...")
    
    print("\n--> 띠릭! (측정 중...)")
    try:
        recorded = sd.playrec(playback_sig, samplerate=fs, channels=2, blocking=True)
    except Exception as e:
        print("\n[에러] 스테레오(2채널) 녹음 지원 오류. 모노(1채널)로 강제 진행합니다...")
        recorded = sd.playrec(playback_sig, samplerate=fs, channels=1, blocking=True)
        recorded = np.column_stack((recorded, recorded))
        
    print("반사음 분석 및 3D 매핑 중...")
    points = extract_stereo_rir(recorded, chirp_sig, fs)
    
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')
    
    if len(points) == 0:
        print("감지된 반사음이 없습니다.")
        return
        
    points = np.array(points)
    x = points[:, 0]
    y = points[:, 1]
    z = points[:, 2]
    amps = points[:, 3]
    
    # 노트북 위치
    ax.scatter([0], [0], [0], color='red', s=150, label='Laptop (Sensor)', marker='^')
    
    # 반사면 (포인트 클라우드)
    scatter = ax.scatter(x, y, z, c=amps, cmap='viridis', s=10, alpha=0.5, label='Acoustic Echo Surfaces')
    
    plt.colorbar(scatter, label='Echo Strength')
    
    ax.set_xlabel('X (Right/Left) [m]')
    ax.set_ylabel('Y (Forward) [m]')
    ax.set_zlabel('Z (Up/Down) [m]')
    ax.set_title("3D Acoustic Point Cloud (Stereo DoA)")
    
    # Limit view to front hemisphere (Y > 0)
    ax.set_ylim(0, max(5, y.max()))
    ax.legend()
    
    output_filename = "3d_pointcloud_result.png"
    plt.savefig(output_filename)
    print(f"\n🎉 3D 점군 생성 완료! {output_filename} 파일을 확인해 보세요.")

if __name__ == "__main__":
    run_3d_pointcloud()
